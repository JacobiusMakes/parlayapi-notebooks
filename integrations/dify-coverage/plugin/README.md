# ParlayAPI Coverage

Check what one ParlayAPI prop response actually contains before connecting it to an agent workflow. The tool returns bookmaker and market counts, observation/write ages, and incomplete-response warnings. It returns no live prices, participant names or raw source rows.

The plugin is free. Live requests require your own ParlayAPI account and use that account's API credits. Each live request consumes the applicable endpoint credits; no automatic retry or pagination is performed. Service access and quotas are separate from this plugin.

## Setup and use

1. Follow the local setup in [the integration guide](../README.md) and run `run_demo.py` through the SDK. Before using this in Dify, complete the official remote-debug setup in an authorized private workspace. No installable package is provided yet.
2. Use **Demo** for a fictional local example. The provider schema marks the key optional and SDK tests verify the no-key path. Actual Dify workspace behavior remains unverified.
3. For live checks, obtain your own key from https://parlay-api.com/signup and enter it in the provider's secret input. Credential validation sends one no-credit GET to `/v1/meta/api-key-check`. The plugin discards all account details and uses only the `valid` boolean.
4. Select **Live**, one sport key such as `mma_mixed_martial_arts`, one bookmaker key such as `fanduel`, and one exact prop market key or the `method_of_victory` family.
5. Inspect the returned status and warnings before using the counts. Keep the workspace and its outputs private.

Only HTTPS access to `parlay-api.com:443` is required. There are no user-controlled URLs, automatic schedules, outbound webhooks, write operations, model calls or shell commands. The key is sent in `X-API-Key`, never in a URL.

## Reading the result

- `observed`: rows appeared in the bounded response; this is not a full-book coverage promise.
- `not_observed`: the response was empty and its paging metadata did not indicate a cut. It does not establish that the sportsbook lacks the market.
- `partial` / `inconclusive`: the API reported truncation, more pages or missing paging metadata. Do not treat the result as complete.
- `error`: the request failed or its schema did not match. An error is never converted into absent coverage.

`observation_age_seconds` and `write_age_seconds` are distinct. Missing clocks remain unknown. A recent observation does not mean the quote recently changed. KO/TKO and KO/TKO/DQ have different settlement scope and are counted separately.

Fictional Demo output, excerpted:

```json
{"synthetic": true, "status": "observed", "observed_selection_count": 1, "observed_market_counts": {"method_of_victory_ko_tko": 1}}
```

## Limits and privacy

One request, at most 500 returned rows, a 1 MB response cap, 10-second HTTP timeouts and no redirects/retries. A separate elapsed body-read check runs after each received chunk; these limits are not an absolute 10-second wall-clock deadline. Requests never forward environment proxy settings. Raw data is parsed only in memory and is not returned or logged by the plugin. Your Dify installation can retain tool parameters and summary outputs according to its own configuration. See PRIVACY.md.

This is a coverage diagnostic, not betting advice, a bet executor, a public odds feed or a redistribution license. Use account data only within your permitted private use.

Maintainer/support: https://github.com/JacobiusMakes/ParlayAPI/issues
Service documentation: https://parlay-api.com/docs
Plugin source: https://github.com/JacobiusMakes/parlayapi-notebooks/tree/main/integrations/dify-coverage

Experimental source only. Local SDK tests pass; Dify remote debugging and package installation have not been verified. This is not a Marketplace listing.
