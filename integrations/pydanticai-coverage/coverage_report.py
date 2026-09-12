"""Typed sport metadata for a private PydanticAI research workflow."""

import argparse
import asyncio
import json
import sys
from typing import Literal

from fastmcp.client.transports import StdioTransport
from pydantic import BaseModel, ConfigDict, Field
from pydantic_ai import Agent, ModelRetry, RunContext
from pydantic_ai.mcp import MCPToolset

PUBLIC_TOOL = "parlayapi_live_sports"
SYNTHETIC_ROWS = [
    {"key": "fictional_alpha", "event_count": 4},
    {"key": "fictional_beta", "event_count": None},
]
SYNTHETIC_REQUEST = ["fictional_alpha", "fictional_beta", "fictional_gamma"]


class SportObservation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    sport_key: str
    reported_events: int | None = Field(default=None, ge=0, strict=True)
    status: Literal["reported", "unknown_count", "not_observed", "invalid"]


class CoverageReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source: Literal["synthetic", "public_metadata"]
    sports: tuple[SportObservation, ...]
    invalid_rows: int = Field(ge=0)
    requested_observations: Literal["all_reported", "partial", "none_reported"]
    market_coverage: Literal["unknown"] = "unknown"
    freshness: Literal["unknown"] = "unknown"


def summarize(rows: list, requested: list[str], source: str) -> CoverageReport:
    """Report supplied counts without turning absent observations into zeroes."""
    if (
        not isinstance(rows, list)
        or not requested
        or len(set(requested)) != len(requested)
    ):
        raise ValueError(
            "Expected a metadata list and unique, nonempty requested sport keys"
        )
    if any(not isinstance(key, str) or not key.strip() for key in requested):
        raise ValueError("Requested sport keys must be nonempty strings")
    indexed = {}
    invalid_rows = 0
    for row in rows:
        if (
            not isinstance(row, dict)
            or not isinstance(row.get("key"), str)
            or not row["key"].strip()
        ):
            invalid_rows += 1
            continue
        indexed.setdefault(row["key"], []).append(row)
        count = row.get("event_count")
        if count is not None and (type(count) is not int or count < 0):
            invalid_rows += 1
    observations = []
    for key in requested:
        matches = indexed.get(key, [])
        count = None
        if not matches:
            status = "not_observed"
        elif len(matches) > 1:
            status = "invalid"
        else:
            value = matches[0].get("event_count")
            if value is None:
                status = "unknown_count"
            elif type(value) is not int or value < 0:
                status = "invalid"
            else:
                status, count = "reported", value
        observations.append(
            SportObservation(sport_key=key, reported_events=count, status=status)
        )
    reported = sum(item.status == "reported" for item in observations)
    return CoverageReport(
        source=source,
        sports=tuple(observations),
        invalid_rows=invalid_rows,
        requested_observations=(
            "all_reported"
            if reported == len(requested)
            else "partial"
            if reported
            else "none_reported"
        ),
    )


def build_agent() -> Agent:
    """Let a caller supply a model explicitly; the tool returns only the report."""
    agent = Agent(
        deps_type=CoverageReport,
        output_type=CoverageReport,
        retries=0,
        instructions="Call coverage_report and return its exact report. Missing data is unknown.",
    )

    @agent.tool
    def coverage_report(ctx: RunContext[CoverageReport]) -> CoverageReport:
        """Read the precomputed sport metadata report, without API or price access."""
        return ctx.deps

    @agent.output_validator
    def preserve_observations(
        ctx: RunContext[CoverageReport], output: CoverageReport
    ) -> CoverageReport:
        if output != ctx.deps:
            raise ModelRetry(
                "Return the exact observed report without modifying counts or statuses"
            )
        return output

    return agent


def make_toolset() -> MCPToolset:
    transport = StdioTransport(
        command=sys.executable,
        args=["-m", "parlayapi_mcp.server"],
        env={
            "PARLAYAPI_KEY": "",
            "PARLAY_API_KEY": "",
            "PARLAYAPI_BASE_URL": "https://parlay-api.com",
        },
        keep_alive=False,
    )
    return MCPToolset(
        transport,
        max_retries=0,
        tool_error_behavior="error",
        prefer_tasks=False,
        init_timeout=15,
        read_timeout=30,
    )


async def inspect_public(requested: list[str], *, call_api: bool) -> dict:
    async with asyncio.timeout(45):
        async with make_toolset() as toolset:
            tools = {tool.name: tool for tool in await toolset.list_tools()}
            if PUBLIC_TOOL not in tools:
                raise RuntimeError(
                    "The expected read-only metadata tool was not advertised"
                )
            if not call_api:
                return {
                    "available_tool": PUBLIC_TOOL,
                    "api_called": False,
                    "model_called": False,
                }
            rows = await toolset.direct_call_tool(PUBLIC_TOOL, {})
            return summarize(rows, requested, "public_metadata").model_dump(mode="json")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode", choices=["synthetic", "discover", "public"], default="synthetic"
    )
    parser.add_argument(
        "--sports", nargs="+", help="Exact sport keys to check in public metadata"
    )
    args = parser.parse_args()
    if args.mode == "public" and not args.sports:
        parser.error("--mode public requires --sports with exact sport keys")
    if args.mode == "synthetic":
        result = summarize(SYNTHETIC_ROWS, SYNTHETIC_REQUEST, "synthetic").model_dump(
            mode="json"
        )
    else:
        result = asyncio.run(
            inspect_public(args.sports or [], call_api=args.mode == "public")
        )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
