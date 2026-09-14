import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from reality_check import HERE, LABELS, dataset, grade, read_json


class GraderTests(unittest.TestCase):
    def setUp(self):
        questions, answers = dataset()
        self.perfect = {"dataset_version": questions["dataset_version"], "responses": [
            {"id": qid, "label": row["label"]} for qid, row in answers.items()]}

    def test_known_correct(self):
        result = grade(self.perfect)
        self.assertEqual(result["exact_score"], "12/12")
        self.assertEqual(result["macro_average_exact"], "1")
        self.assertEqual(result["false_supported_claim_count"], 0)
        self.assertEqual(len(result["dataset_sha256"]), 64)

    def test_all_wrong(self):
        for row in self.perfect["responses"]:
            row["label"] = LABELS[(LABELS.index(row["label"]) + 1) % 3]
        self.assertEqual(grade(self.perfect)["exact_score"], "0/12")

    def test_missing_is_in_denominator(self):
        self.perfect["responses"].pop()
        result = grade(self.perfect)
        self.assertEqual(result["exact_score"], "11/12")
        self.assertEqual(result["missing"], 1)
        self.assertLess(result["macro_average_recall"], 1)

    def test_empty_submission_has_zero_score(self):
        self.perfect["responses"] = []
        result = grade(self.perfect)
        self.assertEqual(result["exact_score"], "0/12")
        self.assertEqual(result["missing"], 12)

    def test_duplicate_and_unknown_ids_fail(self):
        for extra in (self.perfect["responses"][0], {"id": "ORC-999", "label": "supported"}):
            candidate = copy.deepcopy(self.perfect)
            candidate["responses"].append(extra)
            with self.assertRaises(ValueError):
                grade(candidate)

    def test_schema_errors_fail(self):
        invalid = [None, [], {}, {**self.perfect, "dataset_version": "wrong"},
                   {**self.perfect, "unexpected": True},
                   {**self.perfect, "responses": {}},
                   {**self.perfect, "responses": [{"id": "ORC-01", "label": "maybe"}]},
                   {**self.perfect, "responses": [{"id": [], "label": "supported"}]},
                   {**self.perfect, "responses": [{"id": "ORC-01", "label": True}]},
                   {**self.perfect, "responses": [{"id": "ORC-01"}]}]
        for candidate in invalid:
            with self.subTest(candidate=candidate), self.assertRaises(ValueError):
                grade(candidate)

    def test_json_duplicate_keys_and_nonfinite_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"
            for body in ('{"responses":[],"responses":[]}', '{"x":NaN}'):
                path.write_text(body)
                with self.assertRaises(ValueError):
                    read_json(path)

    def test_explicit_synthetic_baselines(self):
        for name, false_claims in (("always-supported", 8), ("always-insufficient", 0)):
            result = grade(read_json(HERE / "baselines" / f"{name}.json"))
            self.assertEqual(result["exact_score"], "4/12")
            self.assertEqual(result["macro_average_exact"], "1/3")
            self.assertEqual(result["false_supported_claim_count"], false_claims)
            recorded = read_json(HERE / "baselines" / f"{name}-result.json")
            self.assertEqual(result, recorded["grade"])

    def test_question_export_contains_no_answer_key(self):
        result = subprocess.run([sys.executable, str(HERE / "reality_check.py"), "questions"],
                                check=True, capture_output=True, text=True)
        public = json.loads(result.stdout)
        self.assertNotIn("answers", public)
        for question in public["questions"]:
            self.assertNotIn("label", question)
            self.assertNotIn("explanation", question)

    def test_cli_invalid_schema_returns_two(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"
            path.write_text('{"dataset_version":"0.1.0","responses":[{"id":"ORC-01","label":"guess"}]}')
            result = subprocess.run([sys.executable, str(HERE / "reality_check.py"), "grade", str(path)],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertIn("Invalid label", result.stderr)
            self.assertEqual(result.stdout, "")


class EvidenceTests(unittest.TestCase):
    def test_snapshot_absence_depends_on_completeness_and_scope(self):
        questions, answers = dataset()
        by_id = {q["id"]: q for q in questions["questions"]}
        partial = by_id["ORC-01"]["evidence"]
        complete = by_id["ORC-02"]["evidence"]
        self.assertEqual(partial["previous"], complete["previous"])
        self.assertFalse(partial["next"]["complete"])
        self.assertTrue(complete["next"]["complete"])
        self.assertEqual(complete["previous"]["scope"], complete["next"]["scope"])
        self.assertGreater(complete["next"]["source_revision"], complete["previous"]["source_revision"])
        self.assertEqual(answers["ORC-01"]["label"], "insufficient_evidence")
        self.assertEqual(answers["ORC-02"]["label"], "supported")

    def test_later_arrival_cannot_overrule_source_order(self):
        questions, _ = dataset()
        for q in questions["questions"]:
            if q["id"] in ("ORC-03", "ORC-12"):
                events = q["evidence"]["events"]
                self.assertEqual(max(events, key=lambda e: e["arrival"])["operation"], "remove")
                self.assertEqual(max(events, key=lambda e: e["source_revision"])["operation"], "restore")


if __name__ == "__main__":
    unittest.main()
