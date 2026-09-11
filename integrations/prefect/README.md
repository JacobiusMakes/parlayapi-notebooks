# Private UFC coverage check with Prefect

Run a one-shot coverage diagnostic before a private sports-data workflow. The
flow returns selection counts, observation ages and label-disagreement counts
by canonical sportsbook and method. It reuses the [UFC client and validator](../../labs/ufc-methods/README.md).
FanDuel KO/TKO stays distinct from DraftKings and Novig KO/TKO/DQ.
It does not return prices, fighter names, event IDs or raw responses.

## Run the synthetic example

From a clone of this repository, using Python 3.12:

```sh
python -m venv .venv
. .venv/bin/activate
pip install -r integrations/prefect/requirements.txt
PREFECT_SERVER_ANALYTICS_ENABLED=false python integrations/prefect/coverage_flow.py
```

The default uses fictional identities and clocks, ignores account keys and makes
no ParlayAPI request. Prefect may start a local temporary API server; if your
Prefect profile points to a server or Cloud, orchestration metadata goes there.
Only the boolean `live` parameter and aggregate results cross the task boundary.

## Explicit private account request

[Create your own account](https://parlay-api.com/signup?utm_source=prefect&utm_medium=community_recipe&utm_campaign=private_coverage_20260911),
then supply your own key through `PARLAY_API_KEY` in your private runtime or
secret manager. Do not put the key in source, command arguments, Prefect flow
parameters or shared outputs. Run:

```sh
PREFECT_SERVER_ANALYTICS_ENABLED=false python integrations/prefect/coverage_flow.py --live
```

This makes one scoped request to `/v1/sports/mma_mixed_martial_arts/props` for
FanDuel, DraftKings and Novig method-of-victory markets, with a 500-row limit.
Account access and usage charges follow your current API plan. No retry,
schedule, deployment, polling loop or raw-data export is configured. Responses
are capped at 2 MiB with socket and elapsed read budgets inherited from the
client. This is not an absolute wall-clock deadline across DNS and transport.

## Interpret the result

| `status` | Meaning |
|---|---|
| `observed` | Validated upcoming selections were returned in the scoped response. |
| `empty` | A complete accepted response yielded no upcoming selections. |
| `incomplete` | HTTP 200 lacked an explicit false `x-result-has-more`, or reported truncation/unknown truncation metadata. Counts are withheld. |
| `error` | Missing credentials, unsuccessful HTTP response, transport failure or validation error. Details are deliberately withheld. |

Prefect's **Completed** state means the diagnostic executed. Downstream steps
must branch on `status`. An empty result does not prove a book lacks a market;
`observed` does not establish full sportsbook coverage or a freshness SLA.
Observation ages use the API's explicit collector clock. Label disagreements
remain counts requiring private investigation; names are not normalized or merged.
A missing truncation header is accepted when `x-result-has-more` is explicitly
false, matching the API's optional truncation-header behavior.

## Privacy and validation

Keys and payloads exist only in ordinary local variables inside the task.
Fetch and validation failures become fixed statuses before Prefect sees them;
exception messages are not logged. Task caching and task/flow result persistence
are disabled. Prefect still records run metadata and status; this is not a claim
that your runtime, debugger or a modified flow cannot inspect process memory.
Keep this workflow private. Repository licensing grants no right to redistribute
ParlayAPI data or operate a public white-label feed.

Validated with **Prefect 3.8.5 on Python 3.12**, using its actual temporary-server
test harness: synthetic execution, a fake live transport, private failure handling,
and stored orchestration metadata inspection. No real account request, hosted
Prefect deployment or production schedule was exercised.

```sh
pip install pytest
PREFECT_SERVER_ANALYTICS_ENABLED=false python -m pytest -q integrations/prefect/test_coverage_flow.py
```

Prefect references: [flows](https://docs.prefect.io/v3/api-ref/python/prefect-flows),
[tasks](https://docs.prefect.io/v3/api-ref/python/prefect-tasks).
