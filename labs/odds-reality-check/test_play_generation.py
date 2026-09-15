"""Stdlib-only checks that the standalone quiz has one fixture/scoring authority."""

import ast
from fractions import Fraction
import hashlib
import unittest

from build_play_notebook import HERE, render
from reality_check import LABELS, dataset, grade, read_json


class GeneratedQuizTests(unittest.TestCase):
    def test_generated_notebook_reproduces_exactly(self):
        self.assertEqual((HERE / "play.py").read_text(), render())

    def notebook_parts(self):
        tree = ast.parse(render())
        setup = next(node for node in tree.body if isinstance(node, ast.With))
        literals = {}
        for node in setup.body:
            if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
                try:
                    literals[node.targets[0].id] = ast.literal_eval(node.value)
                except ValueError:
                    pass
        return tree, literals

    def test_embedded_fixture_bytes_and_hashes_are_exact(self):
        _, literals = self.notebook_parts()
        for name, file, digest in (("QUESTION_BYTES", "questions.json", "dataset_sha256"),
                                   ("KEY_BYTES", "answer-key.json", "answer_key_sha256")):
            self.assertEqual(literals[name], (HERE / file).read_bytes())
            self.assertEqual(hashlib.sha256(literals[name]).hexdigest(), literals["DIGESTS"][digest])

    def test_shared_scorer_ast_and_results_match_cli(self):
        tree, literals = self.notebook_parts()
        embedded = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "grade_payload")
        original = next(n for n in ast.parse((HERE / "reality_check.py").read_text()).body
                        if isinstance(n, ast.FunctionDef) and n.name == "grade_payload")
        embedded.decorator_list = []
        self.assertEqual(ast.dump(embedded), ast.dump(original))
        namespace = {"Fraction": Fraction, "LABELS": LABELS}
        exec(compile(ast.Module(body=[embedded], type_ignores=[]), "<generated-scorer>", "exec"), namespace)
        questions, answers = dataset()
        full = {"dataset_version": questions["dataset_version"], "responses": [
            {"id": qid, "label": row["label"]} for qid, row in answers.items()]}
        cases = [full, {**full, "responses": []}, {**full, "responses": full["responses"][:1]},
                 read_json(HERE / "baselines/always-supported.json"),
                 read_json(HERE / "baselines/always-insufficient.json")]
        for case in cases:
            self.assertEqual(namespace["grade_payload"](case, questions, answers, literals["DIGESTS"]), grade(case))
        for case in ({**full, "responses": full["responses"] + [full["responses"][0]]},
                     {**full, "responses": [{"id": "unknown", "label": "supported"}]}):
            with self.assertRaises(ValueError):
                namespace["grade_payload"](case, questions, answers, literals["DIGESTS"])


if __name__ == "__main__":
    unittest.main()
