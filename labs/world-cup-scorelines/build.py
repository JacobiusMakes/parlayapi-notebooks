"""Rebuild the historical score database and CSV using Python's standard library."""
import argparse
import csv
from datetime import date
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
from urllib.request import urlopen

COMMIT = "516d3825c3bd23fdc298c4014e84bde78f2d4965"
SOURCES = {
    2010: "a02429be186ba377d4099c79ee00ec57fe1b1926b7b34fc786c4cc671777efb3",
    2014: "a68c6150fca6e37b5e9ff2eba3100ad47241a5c1f6d518a8fabb555260c371a0",
    2018: "6af380e875cc52fe12073ab7862fbe8d3e5505ee029cb84d8b5480bf6d603d11",
    2022: "f4f0499c30076bc8e3702f400765900797fb22212a32aaa8137e1dfc49449a68",
    2026: "0ae2c18109b5aa86bc11928b43586ca430c234804d5bbf808d2c3bf2051ecfca",
}
ROUNDS = {
    "Round of 32": "Round of 32", "Round of 16": "Round of 16",
    "Quarterfinals": "Quarter-final", "Quarter-finals": "Quarter-final", "Quarter-final": "Quarter-final",
    "Semifinals": "Semi-final", "Semi-finals": "Semi-final", "Semi-final": "Semi-final",
    "Third-place play-off": "Third place", "Match for third place": "Third place", "Final": "Final",
}
SCHEMA = """
CREATE TABLE matches (
    tournament INTEGER NOT NULL, source_row INTEGER NOT NULL, match_date TEXT NOT NULL,
    stage TEXT NOT NULL, group_name TEXT, team1 TEXT NOT NULL, team2 TEXT NOT NULL,
    regulation1 INTEGER NOT NULL, regulation2 INTEGER NOT NULL,
    extra_time1 INTEGER, extra_time2 INTEGER, shootout1 INTEGER, shootout2 INTEGER,
    decision TEXT NOT NULL, winner TEXT, PRIMARY KEY (tournament, source_row),
    UNIQUE (tournament, match_date, team1, team2)
);
CREATE TABLE sources (tournament INTEGER PRIMARY KEY, source_url TEXT NOT NULL, sha256 TEXT NOT NULL);
CREATE VIEW knockout_summary AS
SELECT tournament, count(*) AS knockout_matches,
       sum(decision = 'Regulation') AS decided_in_regulation,
       sum(decision = 'Extra time') AS decided_in_extra_time,
       sum(decision = 'Shoot-out') AS decided_on_penalties
FROM matches WHERE stage != 'Group' GROUP BY tournament ORDER BY tournament;
CREATE VIEW finals AS SELECT * FROM matches WHERE stage = 'Final' ORDER BY tournament;
CREATE VIEW shootouts AS SELECT * FROM matches WHERE decision = 'Shoot-out' ORDER BY match_date, source_row;
"""


def pair(score, key):
    value = score[key]
    if not isinstance(value, list) or len(value) != 2 or any(type(n) is not int or n < 0 for n in value):
        raise ValueError(f"Invalid {key} score pair: {value!r}")
    return tuple(value)


def normalize(year, index, match):
    team1, team2 = match["team1"], match["team2"]
    if not all(isinstance(t, str) and t.strip() for t in (team1, team2)) or team1 == team2:
        raise ValueError("Expected two distinct named teams")
    day = date.fromisoformat(match["date"])
    if day.year != year:
        raise ValueError("Match date outside the tournament year")
    group = match.get("group")
    stage = "Group" if group else ROUNDS[match["round"]]
    raw = match["score"]
    score = {"ft": raw} if isinstance(raw, list) else raw
    ft = pair(score, "ft")
    et = pair(score, "et") if "et" in score else None
    pens = pair(score, "p") if "p" in score else None
    tied = ft[0] == ft[1]
    if bool(et) != (stage != "Group" and tied):
        raise ValueError("Extra-time field disagrees with stage and regulation score")
    if et and any(after < before for before, after in zip(ft, et)):
        raise ValueError("Extra-time score must be cumulative")
    if bool(pens) != bool(et and et[0] == et[1]) or (pens and pens[0] == pens[1]):
        raise ValueError("Shoot-out field disagrees with extra-time score")
    deciding_score = pens or et or ft
    a, b = deciding_score
    winner = team1 if a > b else team2 if b > a else None
    decision = "Shoot-out" if pens else "Extra time" if et else "Regulation" if winner else "Draw"
    return (year, index, day.isoformat(), stage, group, team1, team2, *ft,
            *(et or (None, None)), *(pens or (None, None)), decision, winner)


def load_sources(source_dir):
    records, sources = [], []
    for year, digest in SOURCES.items():
        url = f"https://raw.githubusercontent.com/openfootball/worldcup.json/{COMMIT}/{year}/worldcup.json"
        if source_dir is None:
            with urlopen(url, timeout=30) as response:
                raw = response.read()
        else:
            raw = (source_dir / f"{year}.json").read_bytes()
        if hashlib.sha256(raw).hexdigest() != digest:
            raise ValueError(f"Source hash mismatch for {year}")
        sources.append((year, url, digest))
        for index, match in enumerate(json.loads(raw)["matches"], start=1):
            try:
                records.append(normalize(year, index, match))
            except (ValueError, KeyError, TypeError) as error:
                raise ValueError(f"Invalid source row {year}/{index}: {error}") from error
    return records, sources


def build(output, source_dir=None):
    records, sources = load_sources(source_dir)
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output) as temp:
        temp = Path(temp)
        db = sqlite3.connect(temp / "worldcup.db")
        try:
            db.executescript(SCHEMA)
            db.executemany("INSERT INTO matches VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", records)
            db.executemany("INSERT INTO sources VALUES (?,?,?)", sources)
            db.commit()
            cursor = db.execute("SELECT * FROM matches ORDER BY tournament, source_row")
            with (temp / "matches.csv").open("w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f, lineterminator="\n")
                writer.writerow([col[0] for col in cursor.description])
                writer.writerows(cursor)
        finally:
            db.close()
        for name in ("worldcup.db", "matches.csv"):
            (temp / name).replace(output / name)
    print(f"Wrote {len(records)} matches from {len(sources)} tournaments to {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--source-dir", type=Path, help="Read pinned JSON files named YEAR.json from this directory")
    args = parser.parse_args()
    build(args.output, args.source_dir)
