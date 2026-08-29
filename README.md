# ParlayAPI notebooks: sports betting analytics in Python

Five polished, self-contained Jupyter notebooks for working with live and historical
sportsbook odds from [ParlayAPI](https://parlay-api.com). Every notebook opens in
Google Colab with one click, runs top to bottom, and explains its math as it goes.

No API key? Every notebook still runs: it falls back to the keyless demo endpoint
(`/v1/try/...`), which serves the first 5 events per sport, moneyline only, capped
at 60 requests per hour. A [free API key](https://parlay-api.com/signup) (no card
required) unlocks all events, all 30+ sportsbooks, and every market.

## The notebooks

| # | Notebook | What it teaches | Open |
|---|----------|-----------------|------|
| 01 | [Quickstart](01-quickstart.ipynb) | Fetch live odds, flatten them into a tidy pandas DataFrame, shop the best price, save a CSV. | [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/JacobiusMakes/parlayapi-notebooks/blob/main/01-quickstart.ipynb) |
| 02 | [No-vig and EV](02-no-vig-and-ev.ipynb) | Strip the bookmaker margin two ways, verify against canonical cases (-110/-110 to +100/+100, 4.76% vig), and score any price's EV against the no-vig fair line. | [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/JacobiusMakes/parlayapi-notebooks/blob/main/02-no-vig-and-ev.ipynb) |
| 03 | [Line movement](03-line-movement.ipynb) | Poll the odds feed on an interval, build a movement table, and chart price paths per bookmaker with matplotlib. | [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/JacobiusMakes/parlayapi-notebooks/blob/main/03-line-movement.ipynb) |
| 04 | [Closing line value](04-closing-line-value.ipynb) | Grade bet prices against real closing lines from the historical archive (back to 2005), with the devig done properly first. | [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/JacobiusMakes/parlayapi-notebooks/blob/main/04-closing-line-value.ipynb) |
| 05 | [Parlay pricing](05-parlay-pricing.ipynb) | Combine legs the way the books do, watch the vig compound, and learn why correlation breaks naive multiplication. | [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/JacobiusMakes/parlayapi-notebooks/blob/main/05-parlay-pricing.ipynb) |

The math in these notebooks follows the same conventions as ParlayAPI's browser
calculators ([no-vig](https://parlay-api.com/tools/no-vig-calculator),
[parlay](https://parlay-api.com/tools/parlay-calculator),
[EV](https://parlay-api.com/tools/ev-calculator)), and each notebook asserts the
canonical cases so drift shows up as a failed cell, not a silent wrong number.

## Running locally

```bash
pip install -r requirements.txt
jupyter lab
```

Paste your API key into the config cell at the top of any notebook, or export it
once as an environment variable:

```bash
export PARLAYAPI_KEY=your_key_here
```

## Links

- API home: [parlay-api.com](https://parlay-api.com)
- Docs: [parlay-api.com/docs](https://parlay-api.com/docs)
- Free key (no card): [parlay-api.com/signup](https://parlay-api.com/signup)
- Plans and historical lookback windows: [parlay-api.com/pricing](https://parlay-api.com/pricing)
- Discord bot for your server: [parlayapi-discord-bot](https://github.com/JacobiusMakes/parlayapi-discord-bot)

## License

MIT. The notebooks are for research and education; nothing here is betting advice.
