"""Optional direct checks against the existing lab, with socket connections blocked."""

import unittest
from unittest.mock import patch

from build_dataset import build, load_lab
from reality_check import HERE, read_json


class ExistingLabReferenceChecks(unittest.TestCase):
    def test_generated_fixtures_reproduce_exactly_without_network(self):
        with patch("socket.socket.connect", side_effect=AssertionError("No network permitted")):
            questions, key = build()
        self.assertEqual(questions, read_json(HERE / "questions.json"))
        self.assertEqual(key, read_json(HERE / "answer-key.json"))

    def test_actual_existing_comparator_matches_declared_cases(self):
        expected = {"ORC-05": "Event identity: the records differ",
                    "ORC-06": "Point/line differs", "ORC-07": "Period: the records differ",
                    "ORC-08": "Settlement rules are not fully supplied",
                    "ORC-09": "Retrieval time cannot replace it", "ORC-10": None, "ORC-11": None}
        with patch("socket.socket.connect", side_effect=AssertionError("No network permitted")):
            lab = load_lab()
            for q in read_json(HERE / "questions.json")["questions"]:
                if q["id"] not in expected:
                    continue
                evidence = q["evidence"]
                reasons = lab.compare_records(evidence["record_a"], evidence["candidates_b"],
                    evidence["maximum_age_minutes"], evidence["maximum_source_gap_minutes"],
                    evidence["now_minute"])
                with self.subTest(question=q["id"]):
                    if expected[q["id"]] is None:
                        self.assertEqual(reasons, [])
                    else:
                        self.assertTrue(any(expected[q["id"]] in reason for reason in reasons), reasons)


if __name__ == "__main__":
    unittest.main()
