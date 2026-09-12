import asyncio
import contextlib
import io
import json
import unittest
from unittest.mock import AsyncMock, patch

from pydantic_ai import models
from pydantic_ai.exceptions import UnexpectedModelBehavior
from pydantic_ai.models.test import TestModel

import coverage_report as coverage


class CoverageTests(unittest.TestCase):
    def setUp(self):
        self.report = coverage.summarize(
            coverage.SYNTHETIC_ROWS, coverage.SYNTHETIC_REQUEST, "synthetic"
        )

    def test_default_does_not_call_model_network_or_mcp(self):
        with (
            patch("sys.argv", ["coverage_report.py"]),
            patch(
                "socket.socket.connect", side_effect=AssertionError("network forbidden")
            ),
            patch.object(
                coverage, "make_toolset", side_effect=AssertionError("MCP forbidden")
            ),
            patch.object(
                coverage, "build_agent", side_effect=AssertionError("model forbidden")
            ),
            contextlib.redirect_stdout(io.StringIO()) as output,
        ):
            coverage.main()
        self.assertEqual(
            json.loads(output.getvalue()), self.report.model_dump(mode="json")
        )

    def test_missing_and_null_are_not_zero_or_complete(self):
        self.assertEqual(self.report.requested_observations, "partial")
        self.assertEqual(
            [item.status for item in self.report.sports],
            ["reported", "unknown_count", "not_observed"],
        )
        self.assertIsNone(self.report.sports[-1].reported_events)
        self.assertEqual(self.report.market_coverage, "unknown")
        self.assertEqual(self.report.freshness, "unknown")

    def test_zero_is_a_reported_count_not_a_coverage_claim(self):
        report = coverage.summarize(
            [{"key": "a", "event_count": 0}], ["a"], "synthetic"
        )
        self.assertEqual(report.sports[0].reported_events, 0)
        self.assertEqual(report.requested_observations, "all_reported")
        self.assertEqual(report.market_coverage, "unknown")

    def test_malformed_counts_and_duplicate_keys_fail_closed(self):
        for value in [True, -1, 1.5, "3"]:
            with self.subTest(value=value):
                report = coverage.summarize(
                    [{"key": "a", "event_count": value}], ["a"], "synthetic"
                )
                self.assertEqual(report.sports[0].status, "invalid")
                self.assertEqual(report.invalid_rows, 1)
        report = coverage.summarize(
            [{"key": "a", "event_count": 3}, {"key": "a", "event_count": 3}, None],
            ["a"],
            "synthetic",
        )
        self.assertEqual(report.sports[0].status, "invalid")
        self.assertEqual(report.requested_observations, "none_reported")
        self.assertEqual(report.invalid_rows, 1)

    def test_invalid_response_and_requests_are_rejected(self):
        for rows, requested in [({}, ["a"]), ([], []), ([], ["a", "a"]), ([], [""])]:
            with (
                self.subTest(rows=rows, requested=requested),
                self.assertRaises(ValueError),
            ):
                coverage.summarize(rows, requested, "synthetic")

    def test_real_agent_tool_and_structured_output_using_local_test_model(self):
        with patch.object(models, "ALLOW_MODEL_REQUESTS", False):
            result = asyncio.run(
                coverage.build_agent().run(
                    "Return the coverage report",
                    deps=self.report,
                    model=TestModel(
                        call_tools=["coverage_report"],
                        custom_output_args=self.report.model_dump(mode="json"),
                    ),
                )
            )
        self.assertEqual(result.output, self.report)
        returns = [
            part
            for message in result.all_messages()
            for part in message.parts
            if getattr(part, "part_kind", None) == "tool-return"
        ]
        self.assertTrue(any(part.tool_name == "coverage_report" for part in returns))

    def test_agent_rejects_invented_count_without_retry(self):
        invented = self.report.model_dump(mode="json")
        invented["sports"][0]["reported_events"] = 999
        with (
            patch.object(models, "ALLOW_MODEL_REQUESTS", False),
            self.assertRaises(UnexpectedModelBehavior),
        ):
            asyncio.run(
                coverage.build_agent().run(
                    "Return the coverage report",
                    deps=self.report,
                    model=TestModel(call_tools=[], custom_output_args=invented),
                )
            )

    def test_public_call_is_single_read_only_call_and_errors_propagate(self):
        toolset = AsyncMock()
        toolset.__aenter__.return_value = toolset
        toolset.list_tools.return_value = [
            type("Tool", (), {"name": coverage.PUBLIC_TOOL})()
        ]
        toolset.direct_call_tool.return_value = coverage.SYNTHETIC_ROWS
        with patch.object(coverage, "make_toolset", return_value=toolset):
            result = asyncio.run(
                coverage.inspect_public(coverage.SYNTHETIC_REQUEST, call_api=True)
            )
        self.assertEqual(result["source"], "public_metadata")
        toolset.direct_call_tool.assert_awaited_once_with(coverage.PUBLIC_TOOL, {})
        toolset.direct_call_tool.side_effect = RuntimeError("metadata unavailable")
        with (
            patch.object(coverage, "make_toolset", return_value=toolset),
            self.assertRaises(RuntimeError),
        ):
            asyncio.run(coverage.inspect_public(["a"], call_api=True))

    def test_mcp_environment_blanks_keys_and_pins_origin(self):
        with patch.object(coverage, "StdioTransport") as transport:
            with patch.object(coverage, "MCPToolset"):
                coverage.make_toolset()
        self.assertEqual(
            transport.call_args.kwargs["env"],
            {
                "PARLAYAPI_KEY": "",
                "PARLAY_API_KEY": "",
                "PARLAYAPI_BASE_URL": "https://parlay-api.com",
            },
        )


if __name__ == "__main__":
    unittest.main()
