# Which UFC method-of-victory markets can I actually get?

Check your own account for pre-fight fighter-to-win-by-decision, submission and knockout selections across FanDuel, DraftKings and Novig. This recipe makes **one request**, then prints a private count by sportsbook and exact method, with the youngest and oldest collector observation ages. It does not print or save prices.

FanDuel and DraftKings pre-match delivery was verified on September 9, 2026. Novig is included in the same request. Availability changes by event and sportsbook; an empty result is not evidence that a sportsbook itself has no markets. Fanatics and theScore Bet method coverage is unverified and is not claimed here.

## Try the code without an account

Requires Python 3.10 or newer, no packages:

```sh
python3 labs/ufc-methods/ufc_methods.py --demo
```

The demo uses invented fighters and timestamps, never current odds. It ignores account keys and makes no network requests.

## Check your own coverage

Create or use your [ParlayAPI account](https://parlay-api.com/signup), then find your key in the dashboard. Consult [endpoint access and documentation](https://parlay-api.com/docs) and [plan allowances](https://parlay-api.com/pricing).

Set `PARLAY_API_KEY` in your private shell environment. Avoid putting the key in saved code or shell history. In Bash, this hidden prompt sets it for this session:

```bash
read -r -s -p 'ParlayAPI key: ' PARLAY_API_KEY
printf '\n'
export PARLAY_API_KEY
python3 labs/ufc-methods/ufc_methods.py
unset PARLAY_API_KEY
```

Optional filters operate locally, without extra API requests:

```sh
python3 labs/ufc-methods/ufc_methods.py --player 'Your Exact Fighter Name'
python3 labs/ufc-methods/ufc_methods.py --date 2026-09-12
```

The date is a UTC event date, not a card label. The example date is the September 2026 Noche weekend; change it for your event.

## Keep different settlement rules separate

| Exact key | Meaning in this recipe |
|---|---|
| `method_of_victory_decision` | Fighter wins by decision |
| `method_of_victory_submission` | Fighter wins by submission |
| `method_of_victory_ko_tko` | FanDuel KO/TKO selection |
| `method_of_victory_ko_tko_dq` | DraftKings or Novig KO/TKO/DQ selection |

The script never merges KO/TKO with KO/TKO/DQ. Check each sportsbook's settlement rules before comparing or acting on prices. Collector observation age is when the collector observed the offer; it is not a promise about sportsbook update speed or end-to-end latency.

## The underlying request

If you prefer curl, this equivalent request returns the **full private props response, including prices**:

```bash
curl --fail --silent --show-error --max-time 15 \
  'https://parlay-api.com/v1/sports/mma_mixed_martial_arts/props?bookmakers=fanduel,draftkings,novig&markets=method_of_victory&oddsFormat=american&limit=500' \
  -H "X-API-Key: ${PARLAY_API_KEY}"
```

Use the Python script for bounded coverage counts: it caps the body at 2 MiB, uses a 15-second network/read budget, makes no retries or redirects, and refuses a truncated or unconfirmed `x-result-has-more` header. It validates timestamps and fighter identities before reporting counts. It does not paginate, poll, or export results.

Keep your account responses and executed outputs private. Do not publish live data, screenshots of account results, or keys in shared notebooks, repositories or websites. This is a bring-your-own-key client recipe, not a public odds feed or permission to redistribute data.

Run offline checks:

```sh
python3 -m unittest discover -s labs/ufc-methods -p 'test_*.py'
```
