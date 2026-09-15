"""Generate the standalone marimo quiz from authoritative local fixtures/scorer."""

import ast
import hashlib
from pathlib import Path

HERE = Path(__file__).resolve().parent


def render():
    grader = (HERE / "reality_check.py").read_text(encoding="utf-8")
    function = next(n for n in ast.parse(grader).body
                    if isinstance(n, ast.FunctionDef) and n.name == "grade_payload")
    scorer = ast.get_source_segment(grader, function)
    questions = (HERE / "questions.json").read_bytes()
    key = (HERE / "answer-key.json").read_bytes()
    replacements = {
        "__QUESTION_BYTES__": repr(questions),
        "__KEY_BYTES__": repr(key),
        "__QUESTION_SHA__": repr(hashlib.sha256(questions).hexdigest()),
        "__KEY_SHA__": repr(hashlib.sha256(key).hexdigest()),
        "__PURE_GRADER__": scorer,
    }
    template = (HERE / "play_template.py.txt").read_text(encoding="utf-8")
    for marker, content in replacements.items():
        if template.count(marker) != 1:
            raise ValueError(f"Expected exactly one marker: {marker}")
        template = template.replace(marker, content)
    return template


if __name__ == "__main__":
    (HERE / "play.py").write_text(render(), encoding="utf-8")
