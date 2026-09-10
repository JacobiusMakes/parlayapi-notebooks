# Experimental Dify integration: private prop coverage

Use a fictional example to learn how a Dify tool can check one bookmaker and market before you connect your own API account. This tool returns counts, observation/write ages and incomplete-response warnings. It never emits prices, participant names or raw source rows.

**Status:** source integration with local Dify SDK tests. It has not been remotely debugged, installed in a Dify workspace, packaged or listed in the Marketplace. No live service acceptance is claimed.

## Run the fictional example locally

Use Python 3.12 in an isolated environment. From this directory:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r plugin/requirements.txt
.venv/bin/python run_demo.py
```

The demo requires no key and makes no network requests. It returns `synthetic: true`, one fictional observed selection, and separate age summaries. These are illustrative values, not current coverage.

To run the offline regression tests:

```bash
.venv/bin/python -m pip install pytest
.venv/bin/python -m pytest -q tests
```

Tests invoke the real SDK with synthetic data and mocked HTTP. They cover malformed responses, exact market scope, duplicate identities, metadata uncertainty, key validation, response bounds and redacted errors. SDK dependencies may emit upstream warnings under pytest.

## Develop in your private Dify workspace

The runtime source is in [plugin/](plugin/README.md), with provider credentials, tool schema, manifest and [privacy disclosure](plugin/PRIVACY.md). Follow the current [official plugin development documentation](https://docs.dify.ai/en/develop-plugin/overview) to obtain the Dify CLI and connect your authorized development workspace. Do not treat this source checkout as a verified installable package.

Run Demo first. If you explicitly select Live, supply your own ParlayAPI key through the provider secret field. One invocation sends one bounded props request and consumes the account's applicable credits. The key-check preflight consumes no credits. Keep your workspace private and never commit credentials or real outputs. Missing or malformed paging metadata cannot establish absent coverage; a recent observation is not a recent price change.

Before publishing a Marketplace PR, the [official checklist](https://docs.dify.ai/en/develop-plugin/publishing/standards/contributor-covenant-code-of-conduct) requires: “Works end-to-end. Tested via remote debugging; production-ready.” That step remains outstanding. Package runtime files only with the official CLI after validation; exclude environments, tests, secrets and caches.

The software is covered by this repository's MIT license. API access and data-use rights are separate. This integration grants no public redistribution or white-label data rights. [API docs](https://parlay-api.com/docs) describe service access; no full coverage or profit guarantee is implied.
