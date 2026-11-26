# Budget several API jobs without hiding unknown costs

A runnable Python kit for a project with more than one request shape. Model each
upstream job, keep its entered unit cost separate, and retain unpriced work in
the result. The CSV template, JSON export and notebook need Python 3.9 or later
and the standard library. No package installation, API key or API request is
needed for the model.

[Open the self-contained notebook in Colab](https://colab.research.google.com/github/JacobiusMakes/parlayapi-notebooks/blob/main/labs/request-budget/request-budget.ipynb)
or download [budget_audit.py](budget_audit.py) and run it locally. Colab account
and runtime requirements still apply. Its default cells use invented inputs;
keep private assumptions in the local command-line workflow.

## Run the worked example

```sh
python3 budget_audit.py --example --format table
python3 budget_audit.py --example
```

The first command displays a short table. The second exports JSON to standard
output. All names, windows and credit rates in this example are invented.

| Job | Base requests | Additional retries | Planned requests | Entered unit credits | Estimated credits |
|---|---:|---:|---:|---:|---:|
| pregame-board | 96 | 5 | 101 | 0.1 | 10.1 |
| event-detail | 16 | 0 | 16 | unknown | unknown |

The total is **117 proposed requests**. The known estimated subtotal is **10.1
credits**. The full credit estimate stays **unknown** because event-detail has
no entered unit cost. A known zero rate and a missing rate produce different
results. The model never checks account usage or current billing rules.

Download the [example CSV](example-jobs.csv) and [complete example JSON](example-report.json).

## Keep the window boundary explicit

The pregame job runs for seven minutes and refreshes every five minutes. It polls
at 0 and 300 seconds. Its 420-second end is excluded. Two separately polled
sports, three requests per refresh and eight complete windows produce 96 base
requests. A five percent allowance rounds up once over that job's complete base
count, adding five requests.

The event-detail window starts at 23:55 and lasts ten minutes. Its two polls are
23:55 on day zero and 00:00 on day one. The 00:05 end is excluded. Crossing
midnight still counts as one window. Clock labels use a relative 24-hour day;
they do not resolve calendar dates, timezones or daylight-saving transitions.

Each row is one actual upstream job in your proposed design. `consumer_count`
records its readers. If two widgets really share one fetch, record one job with
two readers. The reader count does not multiply requests. Separate rows remain
separate jobs; this model does not discover cache reuse or deduplicate a design.

Only the first twelve poll markers are displayed per job. Counts and the last
poll offset cover the complete modeled window.

## Enter your own assumptions

Save a private copy of the CSV and edit its rows:

```sh
python3 budget_audit.py --input my-jobs.csv
python3 budget_audit.py --input my-jobs.csv --output new-budget.json
```

The output option creates a complete new file and refuses to replace an existing
path. On POSIX systems it creates an owner-only file. The input file stays
unchanged. Input is limited to 64 KiB and 100 jobs.

| Column | Meaning |
|---|---|
| job_id | Unique label of 1 to 64 letters, digits, dots, underscores or hyphens |
| active_minutes | Duration of one active window, 0 to 1440 |
| interval_seconds | Refresh interval, 1 to 86400 |
| sports | Number of sports actually requested separately, 1 to 10000 |
| requests_per_refresh | Requests per separately polled sport, including every required endpoint and page |
| active_windows | Complete repetitions of this window, 0 to 366 |
| retry_percent | Additional requests as a percentage of that job's base count, rounded up once per job |
| credits_per_request | Verified-for-your-scenario unit cost as decimal text, or blank for unknown |
| consumer_count | Optional reader count, default 1; does not multiply upstream work |
| start_time | Optional HH:MM label for the first poll |

Counts must be whole numbers. Decimal rates support up to twelve integer and
twelve fractional digits. Arithmetic uses exact integers; credit amounts export
as decimal strings. Aggregate request counts beyond portable exact JSON integer
storage are rejected. Blank costs stay unknown, including on an inactive job.

The kit does not read environment keys or accept a credentials column. Keep keys
and private API responses out of the CSV, shared notebooks and repository issues.
User-supplied CSV values are labelled assumptions with unknown fixture provenance.

## Take the plan into a private evaluation

Use the [evaluation workbench](https://parlay-api.com/tools/evaluation-lab?utm_source=github&utm_medium=budget_kit&utm_campaign=request-budget-kit)
to record the output and exact fields your project needs. For a single job,
the [browser workload planner](https://parlay-api.com/tools/api-workload?utm_source=github&utm_medium=budget_kit&utm_campaign=request-budget-kit)
can provide a quick starting point.

Verify the exact request shape, entitlement, pagination and credit cost in the
[current documentation](https://parlay-api.com/docs). An entered rate is an
arithmetic assumption until you verify it. Then use your own
[account and key privately](https://parlay-api.com/signup?utm_source=github&utm_medium=budget_kit&utm_campaign=request-budget-kit)
and compare the actual result with your requirements.

## Maintain the kit

```sh
python3 -m unittest discover -s labs/request-budget -p 'test_*.py' -v
python3 labs/request-budget/build_notebook.py --check
```

Run these commands from the repository root. After changing the model, run
`build_notebook.py` without `--check` to regenerate the self-contained notebook,
CSV and JSON example. Published notebook outputs and execution counts are empty.
Its cells execute the same model definitions as the CLI. Colab output omission is
requested as an additional precaution; it is not access control.

MIT-licensed code, maintained by the ParlayAPI team with AI assistance. API access
and data-use permissions follow the current terms and applicable account agreement.
