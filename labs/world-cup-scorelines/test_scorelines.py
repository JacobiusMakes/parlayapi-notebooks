from pathlib import Path
import sqlite3
import unittest

from build import normalize


def fixture(score, **fields):
    match = dict(team1="First", team2="Second", date="2022-12-18", round="Final", score=score)
    return dict(match, **fields)


class ScoreTests(unittest.TestCase):
    def test_phase_boundaries(self):
        for score, decision, winner in [
            ([0, 1], "Regulation", "Second"),
            ({"ft": [1, 1], "et": [2, 1]}, "Extra time", "First"),
            ({"ft": [2, 2], "et": [3, 3], "p": [4, 2]}, "Shoot-out", "First"),
        ]:
            with self.subTest(score=score):
                self.assertEqual(normalize(2022, 1, fixture(score))[-2:], (decision, winner))
        row = normalize(2022, 1, fixture([0, 0], group="Group A", round="Matchday 1"))
        self.assertEqual(row[7:], (0, 0, None, None, None, None, "Draw", None))

    def test_inconsistent_or_missing_phase_is_rejected(self):
        for score in [
            {"ft": [0, 0]}, {"ft": [1, 0], "et": [2, 0]},
            {"ft": [2, 2], "et": [1, 2]}, {"ft": [0, 0], "et": [0, 0]},
            {"ft": [0, 0], "p": [3, 2]}, {"ft": [1, 1], "et": [1, 1], "p": [2, 2]},
            {"ft": [True, 2]}, {"ft": [1, -1]},
        ]:
            with self.subTest(score=score), self.assertRaises(ValueError):
                normalize(2022, 1, fixture(score))

    def test_shipped_database(self):
        uri = Path(__file__).with_name("worldcup.db").resolve().as_uri() + "?mode=ro"
        db = sqlite3.connect(uri, uri=True)
        self.addCleanup(db.close)
        self.assertEqual(db.execute("PRAGMA integrity_check").fetchone(), ("ok",))
        self.assertEqual(db.execute("SELECT count(*) FROM matches").fetchone(), (360,))
        self.assertEqual(db.execute("SELECT count(*) FROM sources").fetchone(), (5,))
        self.assertEqual(db.execute("SELECT * FROM knockout_summary").fetchall(), [
            (2010, 16, 12, 2, 2), (2014, 16, 8, 4, 4), (2018, 16, 11, 1, 4),
            (2022, 16, 11, 0, 5), (2026, 32, 23, 5, 4),
        ])
        self.assertEqual(db.execute("""
            SELECT team1, team2, regulation1, regulation2, extra_time1, extra_time2,
                   shootout1, shootout2, winner FROM finals WHERE tournament = 2022
        """).fetchone(), ("Argentina", "France", 2, 2, 3, 3, 4, 2, "Argentina"))


if __name__ == "__main__":
    unittest.main()
