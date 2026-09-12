# ParlayAPI sport metadata with PydanticAI

Check whether the sports your application needs have reported event counts before
starting private research. This small recipe produces a typed `CoverageReport`,
then shows how a PydanticAI agent can consume it without inventing missing data.

The default runs fictional metadata locally. No account, model, API request or MCP
subprocess is needed. It deliberately includes a reported count, an unknown count
and a sport that was not observed. There are no example odds.

## Run it

Use Python 3.12. From this directory:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python coverage_report.py
python -m unittest -v test_coverage_report.py
```

The dependencies pin `pydantic-ai-slim[mcp]==2.43.0` and
`parlayapi-mcp==0.3.7`. The slim package avoids installing model provider SDKs.

The synthetic result includes:

```json
{
  "source": "synthetic",
  "sports": [
    {"sport_key": "fictional_alpha", "reported_events": 4, "status": "reported"},
    {"sport_key": "fictional_beta", "reported_events": null, "status": "unknown_count"},
    {"sport_key": "fictional_gamma", "reported_events": null, "status": "not_observed"}
  ],
  "invalid_rows": 0,
  "requested_observations": "partial",
  "market_coverage": "unknown",
  "freshness": "unknown"
}
```

`all_reported` means every requested sport had one valid count in the supplied
metadata. It does not establish sportsbook coverage, market availability, source
freshness or that games are currently in progress. Missing sports stay
`not_observed`, never zero. Duplicate sport keys and malformed counts become
`invalid`; a reported zero remains zero.

## Connect through PydanticAI's MCP client

First check the published server's advertised tool without making an API call:

```bash
python coverage_report.py --mode discover
```

Then explicitly make one public metadata call for exact sport keys:

```bash
python coverage_report.py --mode public --sports soccer_epl
```

This uses PydanticAI's `MCPToolset` with `StdioTransport` and calls only
`parlayapi_live_sports`, backed by `/live/api/sports`. Both API key aliases are
blanked in the child environment, and the API origin is fixed. The MCP session
closes after the operation. Errors propagate without automatic retries; the
operation has a 45 second outer timeout.

The recipe prints only requested sport counts and their observation states. It
does not expose the server's account actions or raw odds tools to an agent.
Discovery validates the local transport, while the separate public mode checks
metadata delivery at that moment. Neither validates paid API access.

## A typed agent with deterministic evidence

`build_agent()` creates a real PydanticAI agent with one local `coverage_report`
tool, `CoverageReport` dependencies and structured output. Its output validator
rejects any change to the supplied report, with no repair retries. This keeps
coverage facts in deterministic code while your application decides how to use
them. Constructing the agent does not call a model.

Exercise the agent and tool locally with PydanticAI's testing model:

```python
import asyncio

from pydantic_ai import models
from pydantic_ai.models.test import TestModel

from coverage_report import SYNTHETIC_REQUEST, SYNTHETIC_ROWS, build_agent, summarize

models.ALLOW_MODEL_REQUESTS = False
report = summarize(SYNTHETIC_ROWS, SYNTHETIC_REQUEST, "synthetic")
result = asyncio.run(
    build_agent().run(
        "Return the coverage report",
        deps=report,
        model=TestModel(
            call_tools=["coverage_report"],
            custom_output_args=report.model_dump(mode="json"),
        ),
    )
)
assert result.output == report
print(result.output.model_dump_json(indent=2))
```

`TestModel` is an in-process fixture, not model inference. For a private
application, explicitly supply your chosen PydanticAI model to `run` or
`run_sync` and install that provider's dependencies separately. That may incur
provider charges and send the aggregate report to that provider. The recipe
never supplies an API key or raw response to the agent.

## Next: private research

Use your own [ParlayAPI account](https://parlay-api.com/signup?utm_source=pydanticai&utm_medium=integration&utm_campaign=sport_metadata_recipe)
for private sportsbook and market research. Check the [API documentation](https://parlay-api.com/docs)
and [current plans](https://parlay-api.com/pricing?utm_source=pydanticai&utm_medium=integration&utm_campaign=sport_metadata_recipe)
for access and allowances. An observed event count is a starting point for a
coverage question, not a guarantee that a particular book or prop is available.

This example's code uses the repository's [MIT license](../../LICENSE).
API data follows the [service terms](https://parlay-api.com/terms); API access
does not grant public redisplay or redistribution rights. Keep account data
private. This recipe does not place bets or promise trading results.

AI-assisted code, with runtime and focused regression validation. This is a
community example, not an endorsement by the PydanticAI project.
