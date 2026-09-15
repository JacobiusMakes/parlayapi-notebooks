"""Optional real marimo execution checks using the existing installed runtime."""

from types import SimpleNamespace
import unittest
from unittest.mock import patch

import play
from reality_check import dataset, grade


class PlayExecutionTests(unittest.TestCase):
    def run_app(self, choices=None):
        with patch("socket.socket.connect", side_effect=AssertionError("No network")), \
                patch("socket.getaddrinfo", side_effect=AssertionError("No DNS")):
            return play.app.run(defs={"quiz": SimpleNamespace(value=choices)} if choices is not None else None)

    def test_default_waits_for_submit_and_has_twelve_choices(self):
        _, definitions = self.run_app()
        self.assertIsNone(definitions["result"])
        self.assertIsNone(definitions["quiz"].value)
        self.assertEqual(len(definitions["quiz"].element.elements), 12)
        self.assertIn("Score and reveal answers", definitions["quiz"].text)
        self.assertIn("<style>", definitions["quiz"].element.text)
        self.assertIn(".orc-case { border:", definitions["quiz"].element.text)

    def test_actual_result_cell_matches_full_score_and_partial_scoring(self):
        questions, answers = dataset()
        full = {qid: row["label"] for qid, row in answers.items()}
        for choices in (full, {qid: label if index == 0 else None
                              for index, (qid, label) in enumerate(full.items())},
                        dict.fromkeys(full, "supported"), dict.fromkeys(full, None)):
            _, definitions = self.run_app(choices)
            submission = {"dataset_version": questions["dataset_version"], "responses": [
                {"id": qid, "label": label} for qid, label in choices.items() if label is not None]}
            self.assertEqual(definitions["result"], grade(submission))


if __name__ == "__main__":
    unittest.main()
