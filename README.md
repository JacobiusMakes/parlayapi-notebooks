# ParlayAPI notebooks: private sports-data research in Python

Five self-contained notebooks for learning the analysis code before connecting
an account. Open a notebook in Colab and choose **Run all**: the default `offline`
mode runs the local mathematical examples without API calls or key prompts.
Illustrative calculations are not current market observations.

| Notebook | Topic | Run in Colab |
|---|---|---|
| [01 Quickstart](01-quickstart.ipynb) | Nested event data, a DataFrame, and an optional private CSV | [Open](https://colab.research.google.com/github/JacobiusMakes/parlayapi-notebooks/blob/main/01-quickstart.ipynb) |
| [02 No-vig and EV](02-no-vig-and-ev.ipynb) | Existing proportional and additive examples and their test cases | [Open](https://colab.research.google.com/github/JacobiusMakes/parlayapi-notebooks/blob/main/02-no-vig-and-ev.ipynb) |
| [03 Line movement](03-line-movement.ipynb) | Optional polling and a movement chart | [Open](https://colab.research.google.com/github/JacobiusMakes/parlayapi-notebooks/blob/main/03-line-movement.ipynb) |
| [04 Closing line value](04-closing-line-value.ipynb) | Local grading examples and an optional account archive request | [Open](https://colab.research.google.com/github/JacobiusMakes/parlayapi-notebooks/blob/main/04-closing-line-value.ipynb) |
| [05 Parlay pricing](05-parlay-pricing.ipynb) | Existing independent-price math and correlation caveats | [Open](https://colab.research.google.com/github/JacobiusMakes/parlayapi-notebooks/blob/main/05-parlay-pricing.ipynb) |

## Choose API access explicitly

The configuration cell has three modes:

- `offline`: the default. No network requests, account prompts, polling, or CSV export.
- `demo`: a limited anonymous sample. Environment keys are ignored. The odds demo
  returns at most five US moneyline events, with a shared limit of 60 requests per
  hour per IP. Availability varies; an empty response does not explain missing data.
- `account`: requests within your own account allowance. A hidden runtime prompt
  asks for your key when the first account request is made. Never paste a key into
  a code cell. Existing environment keys do not change the selected mode.

Use a private notebook copy before selecting `account`. Each reader supplies
their own [account and key](https://parlay-api.com/signup). Current endpoint
access, source coverage and allowances are described in the
[API docs](https://parlay-api.com/docs) and [pricing](https://parlay-api.com/pricing).
A free account does not promise every event, source, or market.

Additional actions have separate switches, all off by default:
`RUN_EXTRA_API_CHECKS`, `RUN_POLLING`, and `SAVE_PRIVATE_CSV`.
The line-movement lesson only polls after `RUN_POLLING` is enabled in a live mode.
The quickstart writes an optional CSV to a private temporary file outside the
repository. The request code uses the fixed HTTPS API origin, does not follow
redirects, bounds response size and time, and does not retry automatically.

## Keep keys and results out of shared code

Published notebooks have empty outputs and execution counts. Colab's output
omission setting is enabled as an additional precaution. Other notebook hosts
may handle this differently; it is not access control or a guarantee that a
modified notebook cannot save output.

Keep executed account notebooks and CSVs private. Clear every output before
sharing code or saving a notebook to GitHub. Do not upload API responses, keys,
or private bet logs. Finish by restarting the runtime; the final cell also drops
the notebook's stored key reference. Changing modes alone does not erase outputs
from earlier cells.

The MIT license covers software. API access does not grant public redisplay or
redistribution rights. Data use follows the [applicable terms](https://parlay-api.com/terms)
and any written agreement. These defaults do not amend existing customer contracts.

## Local use and checks

```bash
python -m pip install -r requirements.txt
jupyter lab
```

Run the offline tests after installing the dependencies:

```bash
MPLBACKEND=Agg python -m unittest -v test_notebook_privacy.py
```

The tests execute every default notebook cell with network and key prompts
blocked, then separately exercise explicit anonymous and account requests with
mocked responses and a fake key. They do not contact ParlayAPI.

For the maintained one-request Python command and response validation, see the
[parlay-api SDK](https://github.com/JacobiusMakes/parlay-api-python).
The notebooks retain their existing educational analysis methods; those methods
are assumptions and examples, not trading recommendations or profit forecasts.
