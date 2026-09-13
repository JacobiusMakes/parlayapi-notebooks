"""Run the synthetic comparability DAG; no API, account or model required."""

import argparse

from hamilton import driver

import dataflow

SCENARIOS = (
    "matching", "event", "market", "outcome", "point", "period", "settlement",
    "unknown_rules", "unknown_time", "future_time", "missing", "duplicate",
)


def nonnegative_integer(value: str) -> int:
    number = int(value)
    if number < 0:
        raise argparse.ArgumentTypeError("must be a nonnegative integer")
    return number


def build_driver():
    return driver.Builder().with_modules(dataflow).build()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", choices=SCENARIOS, default="matching")
    parser.add_argument("--source-age", type=nonnegative_integer, default=1)
    parser.add_argument("--max-age", type=nonnegative_integer, default=5)
    parser.add_argument("--max-time-gap", type=nonnegative_integer, default=2)
    args = parser.parse_args(argv)
    result = build_driver().execute(["result_json"], inputs=vars(args))
    print(result["result_json"])


if __name__ == "__main__":
    main()
