# v0.1.0 implementation checks

Local validation on September 14, 2026:

- Standard-library suite: 12 tests passed in 0.100 seconds after the final fixture correction.
- Optional existing-lab reference suite: 2 tests passed in 0.280 seconds using the existing marimo 0.24.0 environment. These checks block socket connections, reproduce the question/key fixtures, and call the original comparator for seven scenarios.
- Synthetic always-supported baseline: 4/12 correct, macro recall 1/3, eight false supported claims.
- Synthetic always-insufficient baseline: 4/12 correct, macro recall 1/3, zero false supported claims.
- No external model evaluation, API call, package installation, real data, production action or publication was performed to build this exercise.

Reproduce from the repository root:

```sh
python3 -m unittest discover -s labs/odds-reality-check -p 'test_*.py' -v
# Requires the existing teaching lab's marimo runtime:
python3 labs/odds-reality-check/reference_checks.py
```

The standard-library tests cover a fully correct submission, a fully wrong submission, partial and empty submissions, duplicate and unknown IDs, malformed schemas, duplicate JSON keys, nonfinite JSON constants, question export without the key, CLI error status, both baseline results, snapshot completeness/scope and source revision versus arrival order. These are implementation checks, not evidence of real sportsbook coverage or AI performance.

## Browser notebook implementation, September 15, 2026

- All 15 standard-library tests passed in 0.097 seconds, including exact embedded fixture bytes/hashes, deterministic notebook regeneration and shared scorer AST/result parity.
- Two actual marimo execution checks passed in 0.121 seconds with socket connections and DNS blocked. The default form has twelve unanswered controls and no result. The real result cell matches CLI scoring for complete, partial, empty and constant-label submissions.
- `marimo check play.py` reported no issues using the existing marimo 0.24.0 runtime.
- Dataset question/key bytes and version remain unchanged. Existing synthetic baseline result files still match the CLI grader.
- No package installation, model/API call, production action or publication was performed for this implementation. Browser rendering/interaction verification is a separate publishing check.
