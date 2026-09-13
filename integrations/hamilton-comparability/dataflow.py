"""A Hamilton DAG that keeps the original records and comparison reasons."""

import json

import lab_adapter


def fictional_records(scenario: str, source_age: int) -> tuple[dict, list[dict]]:
    """Generate only fictional records through the shared teaching lab."""
    return lab_adapter.load_lab().synthetic_records(scenario, source_age)


def comparison_reasons(
    fictional_records: tuple[dict, list[dict]], max_age: int, max_time_gap: int
) -> list[str]:
    """Preserve the lab's explanations, including missing and duplicate data."""
    return lab_adapter.load_lab().compare_records(
        *fictional_records, max_age=max_age, max_time_gap=max_time_gap
    )


def comparison_result(
    fictional_records: tuple[dict, list[dict]],
    comparison_reasons: list[str],
    scenario: str,
    source_age: int,
    max_age: int,
    max_time_gap: int,
) -> dict:
    """Include evidence and assumptions; comparability is not a trading signal."""
    left, candidates = fictional_records
    return {
        "synthetic": True,
        "scenario": scenario,
        "status": (
            "comparability_not_established" if comparison_reasons
            else "comparable_under_example_rules"
        ),
        "reasons": comparison_reasons,
        "records": {"left": left, "candidates": candidates},
        "assumptions": {
            "now_minute": 720,
            "source_age": source_age,
            "max_age": max_age,
            "max_time_gap": max_time_gap,
            "time_unit": "minutes within a fictional day",
        },
        "limitations": (
            "Synthetic teaching rules only. This is not evidence of a good bet, "
            "executable liquidity, verified real-world settlement rules, or API coverage."
        ),
    }


def result_json(comparison_result: dict) -> str:
    """Serialize all candidates, nulls, reasons and declared tolerances."""
    return json.dumps(comparison_result, indent=2, sort_keys=True, allow_nan=False)
