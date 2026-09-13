"""Behavior tests execute Hamilton, including a fresh process with sockets blocked."""

import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

import lab_adapter
from run import build_driver


class DataflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.driver = build_driver()

    def execute(self, scenario="matching", **changes):
        inputs = dict(scenario=scenario, source_age=1, max_age=5, max_time_gap=2)
        inputs.update(changes)
        return json.loads(self.driver.execute(["result_json"], inputs=inputs)["result_json"])

    def test_matching_preserves_evidence_and_qualified_status(self):
        result = self.execute()
        self.assertTrue(result["synthetic"])
        self.assertEqual(result["status"], "comparable_under_example_rules")
        self.assertEqual(result["reasons"], [])
        self.assertEqual(result["records"]["left"]["price"], -110)
        self.assertEqual(result["records"]["candidates"][0]["price"], -105)
        self.assertEqual(result["assumptions"]["now_minute"], 720)
        self.assertIn("not evidence of a good bet", result["limitations"])

    def test_contract_mismatches_retain_specific_reasons(self):
        for scenario, reason in (
            ("event", "Event identity"), ("market", "Market"),
            ("outcome", "Named outcome"), ("point", "Point/line differs"),
            ("period", "Period"), ("settlement", "Settlement rules"),
        ):
            with self.subTest(scenario=scenario):
                result = self.execute(scenario)
                self.assertEqual(result["status"], "comparability_not_established")
                self.assertTrue(any(reason in item for item in result["reasons"]))

    def test_duplicate_is_unresolved_and_neither_price_disappears(self):
        result = self.execute("duplicate")
        self.assertIn("neither price is selected", result["reasons"][0])
        self.assertEqual([row["price"] for row in result["records"]["candidates"]], [-105, -115])

    def test_missing_candidate_stays_missing(self):
        result = self.execute("missing")
        self.assertEqual(result["records"]["candidates"], [])
        self.assertIn("no price to compare", result["reasons"][0])

    def test_unknown_timestamp_is_not_filled_from_retrieval_time(self):
        result = self.execute("unknown_time")
        candidate = result["records"]["candidates"][0]
        self.assertIsNone(candidate["source_minute"])
        self.assertEqual(candidate["retrieved_minute"], 720)
        self.assertTrue(any("Retrieval time cannot replace it" in item for item in result["reasons"]))

    def test_unknown_rules_stay_unknown(self):
        result = self.execute("unknown_rules")
        self.assertIsNone(result["records"]["candidates"][0]["settlement"])
        self.assertIn("Settlement rules are not fully supplied.", result["reasons"])

    def test_stale_source_remains_stale_after_recent_retrieval(self):
        result = self.execute(source_age=12)
        self.assertTrue(any("12 minutes old" in item for item in result["reasons"]))
        self.assertTrue(any("11 minutes apart" in item for item in result["reasons"]))
        self.assertEqual(result["records"]["candidates"][0]["retrieved_minute"], 720)

    def test_age_and_gap_tolerances_are_independent_and_inclusive(self):
        self.assertEqual(self.execute(source_age=5, max_age=5, max_time_gap=4)["reasons"], [])
        age = self.execute(source_age=5, max_age=4, max_time_gap=4)
        gap = self.execute(source_age=5, max_age=5, max_time_gap=3)
        self.assertEqual(len(age["reasons"]), 1)
        self.assertIn("outside your 4-minute age limit", age["reasons"][0])
        self.assertEqual(len(gap["reasons"]), 1)
        self.assertIn("beyond your 3-minute gap limit", gap["reasons"][0])
        self.assertEqual(gap["assumptions"]["max_time_gap"], 3)

    def test_future_source_preserves_both_failure_reasons(self):
        result = self.execute("future_time")
        self.assertTrue(any("future source timestamp" in item for item in result["reasons"]))
        self.assertTrue(any("inconsistent source/retrieval" in item for item in result["reasons"]))

    def test_dag_calls_shared_validator_instead_of_reimplementing_it(self):
        lab = lab_adapter.load_lab()
        with patch.object(lab, "compare_records", wraps=lab.compare_records) as compare:
            result = self.execute("point", max_age=7, max_time_gap=3)
        compare.assert_called_once_with(
            result["records"]["left"], result["records"]["candidates"],
            max_age=7, max_time_gap=3,
        )

    def test_cli_rejects_negative_tolerances(self):
        for option in ("--source-age", "--max-age", "--max-time-gap"):
            with self.subTest(option=option):
                process = subprocess.run(
                    [sys.executable, "run.py", option, "-1"],
                    cwd=Path(__file__).parent, capture_output=True, text=True, timeout=30,
                )
                self.assertEqual(process.returncode, 2)
                self.assertIn("nonnegative integer", process.stderr)
                self.assertEqual(process.stdout, "")

    def test_fresh_cli_import_and_dag_run_with_network_blocked(self):
        script = '''
import runpy
import socket
import sys
from unittest.mock import patch

attempts = []
def blocked(*args, **kwargs):
    attempts.append(True)
    raise AssertionError("Network is forbidden in this example")

sys.argv = ["run.py", *sys.argv[1:]]
with patch.object(socket.socket, "connect", blocked), \\
     patch.object(socket.socket, "connect_ex", blocked), \\
     patch.object(socket.socket, "sendto", blocked), \\
     patch.object(socket, "create_connection", blocked), \\
     patch.object(socket, "getaddrinfo", blocked):
    runpy.run_path("run.py", run_name="__main__")
assert not attempts, "A dependency attempted network access"
'''
        for scenario in ("matching", "duplicate", "unknown_time"):
            with self.subTest(scenario=scenario):
                process = subprocess.run(
                    [sys.executable, "-c", script, "--scenario", scenario],
                    cwd=Path(__file__).parent, capture_output=True, text=True, timeout=30,
                )
                self.assertEqual(process.returncode, 0, process.stderr)
                result = json.loads(process.stdout)
                self.assertTrue(result["synthetic"])
                if scenario == "matching":
                    self.assertEqual(result["status"], "comparable_under_example_rules")
                elif scenario == "duplicate":
                    self.assertEqual(len(result["records"]["candidates"]), 2)
                    self.assertIn("neither price is selected", result["reasons"][0])
                else:
                    self.assertIsNone(result["records"]["candidates"][0]["source_minute"])
                    self.assertTrue(any("Retrieval time cannot replace it" in item for item in result["reasons"]))


if __name__ == "__main__":
    unittest.main()
