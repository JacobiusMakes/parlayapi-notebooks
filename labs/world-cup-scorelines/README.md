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

## Read one final

Argentina and France were level **2-2 after regulation** in 2022. Their cumulative score after extra time was **3-3**. Argentina won the separate shoot-out **4-2**. To retrieve the three score pairs in team order, run this query in the browser's SQL editor or in a local SQLite client.

```sql
SELECT team1, team2, regulation1, regulation2,
       extra_time1, extra_time2, shootout1, shootout2, winner
FROM finals
WHERE tournament = 2022;
```

`team1` and `team2` follow the order in the source. They imply no home-ground advantage. Regulation includes stoppage time. Extra-time columns hold the cumulative score at the end of extra time. Shoot-out columns contain converted kicks only. Empty extra-time or shoot-out fields mean that phase was not played in these records. Group-stage draws have an empty winner.

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
