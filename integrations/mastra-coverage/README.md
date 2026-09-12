# Private soccer moneyline shape checks with Mastra

Before a private analysis workflow treats a soccer moneyline as a two-outcome
market, check whether Draw is missing. This recipe runs two real Mastra steps:
inspect one response privately, then gate incomplete outcome sets using aggregate
metadata. No model provider, API key or paid service is needed for the default run.

## Run the synthetic example

Use Node.js 22.13 or newer. From this directory:

```sh
npm ci --ignore-scripts
npm run demo
npm test
```

The default ignores account credentials and makes no network requests. The
fictional fixture contains only presence metadata, not invented betting prices.
It reports two complete and two incomplete sets across two synthetic books,
`synthetic: true`, `decision: review_incomplete_groups` and
`shapeCheckPassed: false`. These counts teach the workflow, not current coverage.

## Make one explicit private account request

[Create your own API account](https://parlay-api.com/signup?utm_source=mastra&utm_medium=community_recipe&utm_campaign=private_coverage_20260912)
and provide its key through `PARLAY_API_KEY` in your private runtime or secret
manager. Keep the key out of source, terminal arguments, workflow inputs and logs.
An existing environment key never switches the default run to live mode.

```sh
npm run live
```

This makes one request to `/v1/sports/soccer_epl/odds` with
`regions=global`, `bookmakers=pinnacle,draftkings,fanduel`, `markets=h2h`,
`oddsFormat=decimal` and `include=slim`. No pagination loop, automatic retry,
polling, schedule or raw-data export is configured. The transport uses the fixed
HTTPS origin, rejects redirects, aborts after 15 seconds and bounds the response
to 2 MiB. More than 500 events or invalid response structure fail closed.

The live request consumes your account's applicable allowance. See current
[pricing](https://parlay-api.com/pricing?utm_source=mastra&utm_medium=community_recipe&utm_campaign=private_coverage_20260912)
and [API documentation](https://parlay-api.com/docs). An account does not promise
every book, fixture or market will be present.

## Interpret the gate

| Field | Meaning |
|---|---|
| `complete` | Supplied event/book moneyline sets with exactly one home, away and Draw outcome, finite decimal prices greater than 1, and no handicap point. |
| `incomplete` | Supplied moneylines that fail those checks, including duplicate markets or outcomes. Their odds cannot be treated as a complete three-way set. |
| `missingRequestedBooks` | Requested books with no supplied h2h group anywhere in this response. It does not prove that those books lack the market. |
| `groupsWithoutH2h` | Supplied event/book entries with no h2h market. |
| `skippedDerivedGroups` | Supplied event/book entries whose team labels mention corners, bookings or cards. They are excluded from moneyline completeness counts. |
| `shapeCheckPassed` | Every supplied h2h group passed shape checks, every requested book supplied at least one group, and no supplied book entry lacked h2h. |
| `status: incomplete_response` | The server reported more data, truncation or an unrecognized value in an available paging/truncation header. Counts are withheld. |
| `status: error` | Credential, transport, size, HTTP or validation failure. Counts and exception details are withheld. |
| `status: empty` | No h2h groups were supplied. Stop rather than infer absent coverage. |

Mastra workflow success means the diagnostic executed. Branch on the result
before doing further work. `shapeCheckPassed` checks supplied outcome structure
only. It does not establish fresh prices, identical timestamps, every requested
book on every fixture, complete event coverage, full response completeness or
readiness to bet. This recipe does not compute probabilities or recommend bets.

The nested REST schema is the same one used by this repository's
[quickstart](../../01-quickstart.ipynb): event `sport_key`, `home_team`,
`away_team`, then `bookmakers[].markets[].outcomes[]`. `include=slim` omits raw
upstream JSON while retaining that normalized structure. This is not a parser
for combined WebSocket `home_ml`/`away_ml`/`draw_ml` rows. The current REST odds
route does not require paging headers, so their absence is not treated as an
error and is not proof of complete coverage. If present, partial-response flags
stop the check. Team labels mentioning corners, bookings or cards are skipped
and counted separately; this is a conservative label check, not universal
market taxonomy. A response containing only skipped groups stops the workflow.

## Keep the workflow private

Only `live: boolean` and the aggregate summaries cross Mastra step boundaries.
Keys, participant names, event IDs, odds and raw errors remain inside the local
inspection function. No storage or telemetry exporter is configured; workflow
snapshot persistence is disabled. Keep any Mastra workspace, runtime output
and downstream analysis private. A debugger or modified integration can still
inspect process memory. If you add tracing, persistence or hosted orchestration,
review its data handling before using an account key.

The repository's MIT license covers code. API use follows the
[applicable terms](https://parlay-api.com/terms); this recipe grants no public
redisplay, redistribution or white-label data rights.

Validated locally with **@mastra/core 1.66.0 and Node.js 22.22.0**, using the
actual workflow runtime in synthetic mode and with a mocked live transport.
Focused tests cover missing Draw, null/invalid prices, duplicate outcomes and
markets, absent requested books, response bounds, redacted failures and private
step results. No real account request, hosted deployment or Mastra endorsement
is claimed. This is a ParlayAPI-authored integration developed with AI assistance.

Mastra references: [workflow](https://mastra.ai/reference/workflows/workflow),
[step](https://mastra.ai/reference/workflows/step).
