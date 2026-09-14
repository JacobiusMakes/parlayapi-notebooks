"""Offline, standard-library grader for the synthetic Odds Reality Check."""

import argparse
from collections import Counter
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
LABELS = ("supported", "contradicted", "insufficient_evidence")


def reject_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON object key: {key}")
        result[key] = value
    return result


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"),
                      object_pairs_hook=reject_duplicate_keys,
                      parse_constant=lambda value: (_ for _ in ()).throw(
                          ValueError(f"Invalid JSON constant: {value}")))


def dataset():
    questions = read_json(HERE / "questions.json")
    key = read_json(HERE / "answer-key.json")
    ids = [q["id"] for q in questions["questions"]]
    answers = {a["id"]: a for a in key["answers"]}
    if (len(ids) != 12 or len(set(ids)) != 12 or len(key["answers"]) != 12
            or set(ids) != set(answers)
            or Counter(a["label"] for a in answers.values()) != Counter(dict.fromkeys(LABELS, 4))
            or key["dataset_version"] != questions["dataset_version"]):
        raise ValueError("Dataset/answer-key integrity check failed")
    return questions, answers


def identity():
    """Hash exact public question bytes; answer-key hash is reported separately."""
    return {
        "dataset_sha256": hashlib.sha256((HERE / "questions.json").read_bytes()).hexdigest(),
        "answer_key_sha256": hashlib.sha256((HERE / "answer-key.json").read_bytes()).hexdigest(),
    }


def grade(submission):
    questions, answers = dataset()
    if not isinstance(submission, dict) or set(submission) != {"dataset_version", "responses"}:
        raise ValueError("Submission requires exactly dataset_version and responses")
    if submission["dataset_version"] != questions["dataset_version"]:
        raise ValueError("Submission dataset_version does not match")
    if not isinstance(submission["responses"], list):
        raise ValueError("responses must be a JSON array")
    predictions = {}
    for row in submission["responses"]:
        if not isinstance(row, dict) or set(row) != {"id", "label"}:
            raise ValueError("Each response requires exactly id and label")
        qid, label = row["id"], row["label"]
        if not isinstance(qid, str) or qid not in answers:
            raise ValueError(f"Unknown question ID: {qid!r}")
        if qid in predictions:
            raise ValueError(f"Duplicate question ID: {qid}")
        if not isinstance(label, str) or label not in LABELS:
            raise ValueError(f"Invalid label for {qid}; choose one of {LABELS}")
        predictions[qid] = label
    correct = sum(predictions.get(qid) == answer["label"] for qid, answer in answers.items())
    per_class = {}
    for label in LABELS:
        members = [qid for qid, answer in answers.items() if answer["label"] == label]
        hits = sum(predictions.get(qid) == label for qid in members)
        per_class[label] = {"correct": hits, "total": len(members),
                            "recall": hits / len(members), "exact": f"{hits}/{len(members)}"}
    macro = sum(Fraction(row["correct"], row["total"]) for row in per_class.values()) / len(LABELS)
    return {
        "dataset_version": questions["dataset_version"], **identity(),
        "synthetic_only": True, "total": len(answers), "answered": len(predictions),
        "missing": len(answers) - len(predictions), "correct": correct,
        "score": correct / len(answers), "exact_score": f"{correct}/{len(answers)}",
        "macro_average_recall": float(macro), "macro_average_exact": str(macro),
        "per_class": per_class,
        "false_supported_claim_count": sum(
            label == "supported" and answers[qid]["label"] != "supported"
            for qid, label in predictions.items()),
        "missing_ids": [qid for qid in answers if qid not in predictions],
        "incorrect_ids": [qid for qid, label in predictions.items() if answers[qid]["label"] != label],
        "interpretation": "Closed synthetic exercise, not model, profit, coverage or production certification.",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("questions", help="Export public questions without the answer key")
    commands.add_parser("template", help="Export a blank response template; fill labels before grading")
    grading = commands.add_parser("grade", help="Grade a response JSON file")
    grading.add_argument("submission", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "questions":
            result = read_json(HERE / "questions.json")
        elif args.command == "template":
            questions = read_json(HERE / "questions.json")
            result = {"dataset_version": questions["dataset_version"],
                      "responses": [{"id": q["id"], "label": ""} for q in questions["questions"]]}
        else:
            result = grade(read_json(args.submission))
        print(json.dumps(result, indent=2, allow_nan=False))
        return 0
    except (ValueError, OSError, KeyError, TypeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
