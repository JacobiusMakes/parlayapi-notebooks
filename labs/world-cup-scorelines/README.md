# Which World Cup matches were decided after 90 minutes?

Of the 96 knockout-stage matches in the men's World Cups from 2010 through 2026, **31 were level after regulation**. Twelve were decided in extra time and 19 went to a penalty shoot-out. The knockout count includes the third-place match at each tournament. The 2026 edition had a round of 32.

[Open the tournament comparison in Datasette Lite][summary] · [Browse the 19 shoot-outs][shootouts] · [Inspect all five finals][finals]

The explorer loads SQLite in your browser. You can search, filter and run SQL without an account. For offline work, download the [360-match CSV][csv] or the [SQLite database][db]. Both contain the group stage as well as the knockout rounds.

| Tournament | Knockout matches | Decided in regulation | Decided in extra time | Decided on penalties |
|---:|---:|---:|---:|---:|
| 2010 | 16 | 12 | 2 | 2 |
| 2014 | 16 | 8 | 4 | 4 |
| 2018 | 16 | 11 | 1 | 4 |
| 2022 | 16 | 11 | 0 | 5 |
| 2026 | 32 | 23 | 5 | 4 |

For a report or class presentation, [download the editorial chart, caption and data credit](../../press/world-cup-knockout-results.md).

## Read one final

Argentina and France were level **2-2 after regulation** in 2022. Their cumulative score after extra time was **3-3**. Argentina won the separate shoot-out **4-2**. To retrieve the three score pairs in team order, run this query in the browser's SQL editor or in a local SQLite client.

```sql
SELECT team1, team2, regulation1, regulation2,
       extra_time1, extra_time2, shootout1, shootout2, winner
FROM finals
WHERE tournament = 2022;
```

`team1` and `team2` follow the order in the source. They imply no home-ground advantage. Regulation includes stoppage time. Extra-time columns hold the cumulative score at the end of extra time. Shoot-out columns contain converted kicks only. Empty extra-time or shoot-out fields mean that phase was not played in these records. Group-stage draws have an empty winner.

## Try the report desk

You're building a first-half results report. At the first deadline, a regulation score and another match's halftime score have arrived. Decide which fields you can publish, then advance the clock until the scorer and the book each confirm their part of the report. The lesson uses fictional records and includes an answer key.

[Try the three deadlines in your browser][desk] or [download the Jupyter notebook](report-desk.ipynb) to edit the records yourself.

## Find the original record

The data come from [OpenFootball's World Cup JSON][upstream] under [CC0 1.0][license]. Each row retains the tournament and the one-based position of the match in its source file. The `sources` table contains the five pinned URLs and SHA-256 digests. All winner and decision fields are derived from the recorded scores.

To rebuild the files with Python 3 and its standard library, download [build.py](build.py) and run:

```sh
python3 build.py --output rebuilt
```

With the five original files already saved as `2010.json` through `2026.json` at four-year intervals, add `--source-dir PATH` for an offline build. The script checks each file against its pinned digest before importing it.

ParlayAPI maintains this explorer. For a project that matches results to odds, write down the fixture, market period and settlement rule before comparing a price to an outcome. [Open the feed evaluation lab](https://parlay-api.com/tools/evaluation-lab?utm_source=github&utm_medium=dataset&utm_campaign=world_cup_scorelines).

[upstream]: https://github.com/openfootball/worldcup.json/tree/516d3825c3bd23fdc298c4014e84bde78f2d4965
[license]: https://github.com/openfootball/worldcup.json/blob/516d3825c3bd23fdc298c4014e84bde78f2d4965/LICENSE.md
[summary]: https://lite.datasette.io/?url=https://raw.githubusercontent.com/JacobiusMakes/parlayapi-notebooks/main/labs/world-cup-scorelines/worldcup.db#/worldcup/knockout_summary
[shootouts]: https://lite.datasette.io/?url=https://raw.githubusercontent.com/JacobiusMakes/parlayapi-notebooks/main/labs/world-cup-scorelines/worldcup.db#/worldcup/shootouts
[finals]: https://lite.datasette.io/?url=https://raw.githubusercontent.com/JacobiusMakes/parlayapi-notebooks/main/labs/world-cup-scorelines/worldcup.db#/worldcup/finals
[csv]: https://github.com/JacobiusMakes/parlayapi-notebooks/releases/download/world-cup-scorelines-v1/matches.csv
[db]: https://github.com/JacobiusMakes/parlayapi-notebooks/releases/download/world-cup-scorelines-v1/worldcup.db

[desk]: https://shinylive.io/py/app/#code=NobwRAdghgtgpmAXGKAHVA6VBPMAaMAYwHsIAXOcpMAMwCdiYACAZwAsBLCbJjmVYnTJMAgujxM6cKITIcAbnAlSIAEzh0JAVw4AdCPUZN1LANa9%2Bg4QCU4JOqokAbKBRZkA%2BlPuPJdwaosEiz2cB4sWgBGAFZ2ZBJyhKZwnhExcfr6aKgeOkwAvEw6WFAA5mE0TjqqABT6TA1FHBhsAEx1YADCUBBM2MRaTKhRThzsTGRscExsUE40cvCsoQD8umAAlHj1jcWoHQCaA0xQUkxwqhxyEKUTU0wAsgCMAOx%2BAkJMNIJMABKnkR%2B8hYTAAanM4BgmABJdTkDg0HiTaY0Dh0dwAWlm82WgmmPVUd2mcAAHrBUE5poDiKYAOQg7wBC6sFJkSnwchfH6JZLCAAqAA4mKQ-gCfpSoJcbidhNiFnxIUwAKIyNhMQguPhMCBwC4gqCsAZ0QiQ9ZbHYNYpcYaeOiSjjEDyRLRkMikFgddSS0Y69YSdadNjEYgsfHvKxcW5e1Q%2B6Y1ACqfM6Gz9Fsa6YzmczwHWTwFiAArAAGP1MXP5gsF0u5gCciCLVbAAF0JFxY-k%2BXQtHBzb1ds1rS6PIQpklASTPWMbXBq2ARKpCQaSAZRrJI7ipHR1YJvHIRa4mHnC43e%2BnimwAMwdADqs2EUlVzORxjgZjN2z7luaAzINo8FBJTxFDoSJXD4DpUBkXl3zTK0ID-Ec7FMccOnYYgAHdZwAZSDdCiSYYCEQ4ZkpA%2BMgYM-JoMB-P8AKAjRQMWDoehYdCNAos9mn2dY%2BSmUNWA4ElhToDhSi4OY-B8fU1Hw4hUD3aAnG3OhdwdXpThRDg11IOYoV46YTHMQgeiGEYxjVA0QjxJh0M4SkTgmLTeV4EF3A4JwlNQSgpVKDAOMaOQ2TgfJ1gAMTRTE5XDT5DNTCAUwgfR1BoFk6GAmpB3iYUXRtYJXxYNSNkQNMAAEHzXRQMGMpxCDTZKCLGDhIkpGoirTdNIKSFICiYUZ3BqRkHBYBKs14FLMowS4WGnVriso0bOt5DBsm8mpbB8Doj0rbCABZSysqRwiiWJZH9MAi0AZAIS02EasykMgtDoXoWCsC4agGrkty3Lghig7qEUkDBvDgBRmQAHkKCbo1jVqtiYZJsHyFwYEiVQDToRAmAGoG7BBxRfDoDAXsek0PA4VQNgS0qVHUQm6LquAUsWlJZvaxp7se3p1l0TIwAwaJiC4GoaHWEBCeB0HVAAXwaMWiaNUnyZlpgQFpJgAHomFpfnBYgbG0hOsgNmVuX5DmbspfWT7JF4Xp5Ea5q4FhzJKLK7yNAwenKPqli2LoVn5saAGIGIYQJrQ9CA9G9MOaesswFvLS1QO-EZNDV12UoYRjN6fpBgidArBlO4xhfb0uDgNYwDZhoU%2BCUIt0KFw3FtfwHBqe2Csd1r67xI70lO22bUm6QYwr53A4aUo7XUCRqXMJvXFfVuNs7pqWrhnkUn7w3W3gl0R-LnUJ9G2PehFsBnjeVF0TILE5hSlPMZAFOZZqF%2BG6llN9EFaKKEJdOQUORkGftPSUcA34gHnl-bmiVoDoB6mIfY2RcgcDymlDQCV8BgDINgLy1A6JgClngcA0B4DUEMlgXABBlwUCoMgQwzA0ZkBkC4FgoYQR8DIsYVwrCoDsJdiVZhfD2HCwYAAL0oB2LsPZ9Aan4SCdaAQ5ox1xpLTG7g6BpmJsaMI5MNFkC0ZRA2cRMYPQpDOSiZsqhwAMUY-QKcd5xB6h0YgNBUSEA4BJFOWj8DxyvrOG%2B7gZgPzNPoLeqRjrOMKB0Uk5J7Lz1nIKWcAS-HrCCbKUJaSwD-BAuKUeLAwlwMGoEHqOZKJKPbuWRAO0ABs2Enillce4rSXilI%2BJSa8WcUhShaGbmpd88cLwXUaZsD86ZKm1GqTtF42FWhNPWG4jxbSNzsWyQ8F4oyzoZJCfMQZ6xLrzLGWmSZm18w7QFLOAA4lsrG6w4n8AScGUwSSBTXTOqk7ZEVMl7OyeCeyEpAj7LAE4EM5FjkVLblMsAR4do1muUchITlt4mMHusLyahIz%2BQaKc6p21slYQvPtUITi0UwqutipguKYV1gbNcolfiImkqyusdCpAKJNhdownhFBFjTC4UXPlLt6rN2Xl4KFNRmZZVRVlaGFc2qUUIC6JZPU%2BUYEYWMNxggYCuBqHKnUt0Gg6rIIhEEhRgBbm%2BF9W2v0uphxSoTGVBRChOoJI5eA6qGAwE1Va412MJb4w2EwCG6plXuM5ZRYOocmDGtNSou6KRObxy0BAUwId0KJWySHGNrgRzrhKbA9MorgmFB1RONVGqXq%2Bt1eLNRgbrbfV6LGvihrQ0qSzmUy1PxG05pNXxMa7rISVq1XQP1taTSSyDfkReLcI3ph0SaM18czo6yFi9IQb1HUKz0YSK1NsfpKvbeQSmaYAaUj1qbc2KJu02sPSoMgX8mAAEJChPHjZmM%2B8dlyVC0tcW4JTCl%2BIXa%2BNMn671Z2AEWJsGBrHdmCNuwpcD6qkSsHq0esYFWqIenHEANd-GvC%2BN8%2B%2BOIU7rExsWleAQBpQqCKs5lEh9U9nGVmHiQoUMboAayTO5AyO9SXu4cVG0ANIrtfRsuY8DXMYaFLbBuD8HIEIVLJsQA
