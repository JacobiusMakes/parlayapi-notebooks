# What should I check after my first API response?

Rehearse the next decision before adding retries to an integration. This small
Python 3.9+ command uses only the standard library. It sends no requests, reads
no environment keys, prompts for no credentials and writes no files. Its twelve
examples and timestamps are invented; they do not describe current ParlayAPI
limits, account access or service health.

Download [triage.py](triage.py) and run the complete example:

```sh
python3 triage.py --example
```

Or, from this repository's root:

```sh
python3 labs/response-triage/triage.py --example
```

Compare the [invented input cases](cases.example.json) with the
[complete expected JSON](expected.example.json).

## Work the twelve decisions

Every example starts with an entered total limit of two attempts, including
the request already made, and a remaining wait budget of sixty seconds unless
the row changes it. Read-only behavior is explicitly confirmed for the GET
examples. This declaration is an assumption supplied by the learner.

| Case | Invented observation | Next decision in this model |
|---|---|---|
| 1 | 429, `Retry-After: 30`, one attempt used | Review one further read after at least 30 seconds |
| 2 | 429, a GMT date 29.999999 seconds after receipt | Round the positive fraction up to 30 seconds |
| 3 | 429, no wait instruction | Review the response and documentation; waiting time is unknown |
| 4 | 429, two conflicting wait values | Keep the wait ambiguous |
| 5 | 429, both allowed attempts already used | Stop at the attempt budget |
| 6 | 429, 30-second wait but only 10 seconds of wait budget | Stop; do not shorten the wait |
| 7 | POST with a wait instruction | Stop; this model only reviews confirmed read-only GET or HEAD |
| 8 | 401 | Check authentication privately |
| 9 | 403 | Inspect the denial and exact request access |
| 10 | 200 | Inspect whether the required result is actually present |
| 11 | 503 with a 15-second wait instruction | Review one further read after the wait, within the entered budgets |
| 12 | No recorded HTTP status | Check the outcome before repeating anything |

The model never performs the suggested next action. A review time does not
promise a successful response, fresh data, a free request or authorization to
make the call. Check your exact request, entitlement and cost before deciding.
After an actual attempt, update the count rather than reusing an old budget.
Shared callers need their own coordinated budget; this command does not track
them or enforce a rate limit.

## Enter a minimal local case

Save a private JSON file containing a list like this:

```json
[
  {
    "method": "GET",
    "status": 429,
    "received_at": "2026-01-01T00:00:00Z",
    "retry_after": "30",
    "read_only_confirmed": true,
    "attempts_used": 1,
    "attempt_limit": 2,
    "wait_budget_seconds": 60
  }
]
```

```sh
python3 triage.py --input private-case.json
# Or provide the same JSON through standard input:
python3 triage.py --input - < private-case.json
```

Keep the input minimal. Do not paste a key, URL, authorization header, response
body, account identifier or personal data. Those extra fields are refused.
The output contains normalized decisions, not the original wait text or file
path. Normal input errors produce a fixed message without echoing the input.
Your shell, editor and any files you create remain your own responsibility.

| Field | Meaning and bounds |
|---|---|
| `method` | An uppercase GET, HEAD, POST, PUT, PATCH, DELETE or OPTIONS |
| `status` | An integer from 100 through 599, or `null` when no status was recorded |
| `received_at` | Explicit UTC, such as `2026-01-01T00:00:00.000001Z`; years 1970 through 9998 |
| `retry_after` | Optional text, `null`, or a list of extracted values; multiple values remain ambiguous |
| `read_only_confirmed` | Optional boolean, default false; confirm the actual operation before setting it |
| `attempts_used` | 1 through 1,000 attempts already consumed |
| `attempt_limit` | 1 through 10 total attempts, including the completed one |
| `wait_budget_seconds` | 0 through 86,400 seconds remaining for the indicated wait |

Use 1 through 20 cases and at most 16 KiB of UTF-8 JSON. Repeated JSON fields,
nonfinite numbers and unsupported fields are refused. The program labels file
or stdin input as user-supplied assumptions with unknown fixture provenance;
it does not authenticate a response or certify that private input is synthetic.

## Read a wait instruction carefully

HTTP 429 indicates rate limiting and can include `Retry-After`.
[RFC 6585, section 4](https://www.rfc-editor.org/rfc/rfc6585.html#section-4)
does not prescribe the server's counting policy. `Retry-After` can express a
nonnegative integer delay after receipt or an HTTP date; it also has meaning
with 503 and redirection responses.
[RFC 9110, section 10.2.3](https://www.rfc-editor.org/rfc/rfc9110.html#section-10.2.3)
defines those forms.

This teaching parser accepts decimal seconds up to `2**53-1` and canonical
IMF-fixdate GMT dates with a matching weekday. It deliberately returns obsolete
HTTP-date forms as unrecognized. HTTP recipients have broader parsing duties
under [RFC 9110, section 5.6.7](https://www.rfc-editor.org/rfc/rfc9110.html#section-5.6.7);
this rehearsal is not a general-purpose HTTP client or production retry parser.

The received-at timestamp and the date instruction are assumed to share an
accurate UTC clock. Clock accuracy and clock skew are not checked. Positive
fractional waits round up to a whole second. Past dates and an explicit zero
retain a zero minimum, while missing, malformed, unsupported or ambiguous
instructions remain unknown. A known minimum is never shortened to fit the
entered budget. Redirects are always held for a separate review in this model.

## Turn transport success into a useful evaluation

An HTTP success leaves `useful_output_verified` unknown in every case. The
command does not inspect a response body. Specify the event, bookmaker, market,
outcome, price and source timestamp your project actually needs, then check
those exact returned fields in your private environment.

Use the [evaluation workbench](https://parlay-api.com/tools/evaluation-lab?utm_source=github&utm_medium=recipe&utm_campaign=response-triage)
to prepare that acceptance rule. The
[request-budget kit](../request-budget/README.md) helps model several request
shapes and unknown unit costs. Neither tool confirms current access or delivery.
Before an account request, consult the current
[API documentation](https://parlay-api.com/docs) and use your own
[account and key](https://parlay-api.com/signup?utm_source=github&utm_medium=recipe&utm_campaign=response-triage)
privately. No signup is needed to run this rehearsal.

## Maintain the example

```sh
python3 -m unittest discover -s labs/response-triage -p 'test_*.py' -v
```

Tests import the actual decision code, exercise the CLI, block network and key
prompts for the default example, and distinguish unknown timing from zero.
This is an educational decision model, not measured customer behavior,
production coverage or evidence that a later retry succeeded.
