# Odds Reality Check

**Can you tell what sports-data evidence actually proves?**

Twelve tiny cases. Three possible answers. A fresh heartbeat, a disappearing quote and two almost identical home-run markets can each tempt you into a claim the records do not support.

This is an **open educational challenge**, not a held-out scientific benchmark, model ranking or coverage certification. Every fixture, sportsbook, athlete, event, clock and contract is fictional. No real sportsbook feed, customer data, API key or model call is involved. Nothing here estimates betting profit or recommends a bet.

## Play in your browser

[Open the interactive Odds Reality Check](https://molab.marimo.io/github/JacobiusMakes/parlayapi-notebooks/blob/main/labs/odds-reality-check/play.py/wasm?mode=read&show-code=false).

Open each of the twelve case cards, read its evidence and choose **Supported**, **Contradicted** or **Insufficient evidence**. Click **Score and reveal answers** below the cards to see your score out of twelve, the explanation for each case and a downloadable result. Answers are initially unselected; missing answers count against the complete denominator. The last submitted result stays visible while you edit, until you submit again. The answer key is then visible, so subsequent attempts are practice.

The marimo WebAssembly preview downloads its runtime, then runs this notebook in your browser. It needs no API key or local Python installation. The notebook does not make network calls or send answers to ParlayAPI. The public source includes the answer key, so this is an educational exercise rather than a concealed test.

For local interactive play using an existing Python 3.12+ environment with `marimo==0.24.0`:

```sh
python3 -m marimo run labs/odds-reality-check/play.py
```

## Try it

Requires Python 3.10+ and its standard library. From the repository root:

```sh
python3 labs/odds-reality-check/reality_check.py questions > questions-only.json
python3 labs/odds-reality-check/reality_check.py template > my-responses.json
# Read the questions and replace each empty label in my-responses.json.
python3 labs/odds-reality-check/reality_check.py grade my-responses.json
```

Use one of these exact labels:

| Label | Meaning |
| --- | --- |
| `supported` | The supplied evidence establishes the claim under its explicit synthetic contract. |
| `contradicted` | The supplied evidence establishes the opposite. |
| `insufficient_evidence` | Neither conclusion is established. A missing field is not automatically a contradiction. |

[questions.json](questions.json) contains the complete public exercise. [response-template.json](response-template.json) has the expected submission shape. The [answer key](answer-key.json) is deliberately separate, with a short explanation per case. If trying this with an assistant, give it only the public questions and response format first; do not include the answer key, build script or tests. The CLI makes no model calls. The open key means this is unsuitable for claims of contamination-free AI performance.

The submission schema is exact:

```json
{
  "dataset_version": "0.1.0",
  "responses": [
    {"id": "ORC-01", "label": "insufficient_evidence"}
  ]
}
```

That one-row illustration is a **partial submission**, not a complete result. Each response needs exactly `id` and `label`; prose explanations belong outside the scored JSON. Empty template labels must be filled before grading. Unknown IDs, duplicate IDs, repeated JSON object keys, extra schema fields and invalid labels fail clearly with exit code 2. Missing answers count against the full denominator. An empty or partially correct submission cannot receive a perfect score.

## What the result means

The fixture set has four cases per class. The grader reports exact correct/12, the numerical score, each class's recall (correct answers divided by all four cases in that class), and the macro average of those three recalls. Missing answers stay in each denominator. Because the dataset is balanced, overall accuracy and macro recall coincide here.

`false_supported_claim_count` counts a `supported` prediction on either of the other two classes. This is an overclaiming count within this exercise, not a measured real-world error rate. The output also includes answered/missing counts, incorrect and missing IDs, dataset version, and SHA-256 hashes of the exact question and answer-key files.

Two reproducible constant-label baselines illustrate why caution alone is insufficient:

| Explicit synthetic baseline | Correct | Macro recall | False supported claims |
| --- | --- | --- | --- |
| Always answer `supported` | 4/12 | 1/3 | 8 |
| Always answer `insufficient_evidence` | 4/12 | 1/3 | 0 |

**Neither baseline is an AI result. No external model has been tested.** Inputs and generated results are in [baselines/](baselines/).

```sh
python3 labs/odds-reality-check/reality_check.py grade labs/odds-reality-check/baselines/always-supported.json
python3 labs/odds-reality-check/reality_check.py grade labs/odds-reality-check/baselines/always-insufficient.json
```

## Why these cases exist

The exercise separates event identity from team names in a fictional MLB-style doubleheader, standard from alternate home-run thresholds, and full-game from partial-game periods. It also separates retrieval time, process heartbeats and quote source time. The snapshot cases deliberately declare their own replacement and ordering contract; they do **not** document ParlayAPI or any sportsbook's behavior. The late removal cases use source revision, not arrival order. Positive controls ensure that the correct response is sometimes a supported claim.

The twelve authored cases are small, visible and intentionally related. Two share the same event sequence with opposite claims; snapshot cases differ primarily in completeness. They are useful for teaching and inspecting a reasoning failure, but do not represent independent samples of real-world reliability. Scores cannot establish a provider's coverage, latency, settlement accuracy or an assistant's general competence.

## Reuse, provenance and checks

[build_dataset.py](build_dataset.py) loads the existing [Hamilton lab adapter](../../integrations/hamilton-comparability/lab_adapter.py), which imports the [odds-comparability teaching lab](../odds-comparability/odds_comparability.py). Comparison cases derive from its `synthetic_records` and retain its field schema. The original `compare_records` function is reused directly by optional reference checks; there is no copied comparator. The snapshot and revision cases introduce explicit fictional contracts beyond that earlier lesson.

Normal grading does not import marimo. Run the standard-library suite:

```sh
python3 -m unittest discover -s labs/odds-reality-check -p 'test_*.py' -v
```

If Python 3.12+ and the existing lab's `marimo==0.24.0` runtime are already installed, the optional checks call the original comparator and verify deterministic fixture regeneration with socket connections blocked:

```sh
python3 labs/odds-reality-check/reference_checks.py
# Intentional fixture rebuild, only when editing the exercise:
python3 labs/odds-reality-check/build_dataset.py
```

Changing question bytes changes the reported dataset hash. Version any published semantic change and regenerate baseline results. An open answer key can change independently, so preserve both hashes with any shared score.

### Browser artifact maintenance

The standalone [play.py](play.py) embeds the exact bytes of `questions.json` and `answer-key.json`, checks their SHA-256 hashes, and uses the same pure `grade_payload` function as the CLI. It does not depend on fetching sibling files in WebAssembly. [build_play_notebook.py](build_play_notebook.py) generates it from [play_template.py.txt](play_template.py.txt), those authoritative fixtures and the scorer source. Edit those inputs, then regenerate; do not hand-edit the generated notebook.

```sh
python3 labs/odds-reality-check/build_play_notebook.py
python3 -m unittest discover -s labs/odds-reality-check -p 'test_*.py' -v
# Existing Python 3.12+ / marimo 0.24.0 environment:
python3 -m marimo check labs/odds-reality-check/play.py
python3 labs/odds-reality-check/reference_play.py
```

The optional execution tests run the actual notebook with socket connections and DNS resolution blocked. They check the unsubmitted state and score parity for complete, partial, empty and constant-label submissions. Browser rendering and interaction should also be checked before publishing a new preview.

Prepared by Astra, an AI assistant working with the ParlayAPI team. Review, adapt and share the synthetic exercise under the repository's MIT license. That license grants no rights to redistribute provider data. Builders seeking real data can inspect [ParlayAPI](https://parlay-api.com/) and verify their exact requirements separately.
