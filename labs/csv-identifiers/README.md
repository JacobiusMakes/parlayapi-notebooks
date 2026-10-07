# Keep sports research identifiers intact through CSV imports

A player or event identifier can contain only digits and still be text. Converting it to a number can silently change the identity your research joins on.

This lesson uses three original fictional records. It does not contact an API, contain sportsbook prices or reproduce a provider's schema.

| Identifier as supplied | Deliberately bad conversion | Result |
| --- | --- | --- |
| `000123` | Integer | `123` |
| `9007199254740993` | Float, then integer | `9007199254740992` |
| `004200` | Integer | `4200` |

The first and third conversions remove leading zeros. The second cannot represent the original integer exactly through a float. A join can then fail or point at a different record. These Python examples demonstrate coercion mistakes; they are not claims about how every spreadsheet behaves.

## Run the example

Only Python's standard library is needed:

```bash
python3 labs/csv-identifiers/example.py
```

[example.py](example.py) checks its result against literal expected output before printing it. [input.csv](input.csv) and [expected-output.txt](expected-output.txt) provide the exact fictional input and result. No credentials or network calls are involved.

## Preserve identity before joining

Read identifiers as strings and keep that type throughout the pipeline. Convert fields to numbers only when the data contract says they are quantities.

```python
import csv

with open("labs/csv-identifiers/input.csv", newline="") as source:
    records = list(csv.DictReader(source))

assert records[0]["participant_id"] == "000123"
assert records[1]["participant_id"] == "9007199254740993"
```

Python's default CSV reader returns strings. Explicit numeric-conversion settings can change that behavior. See the [Python CSV reader contract](https://docs.python.org/3/library/csv.html#csv.reader).

For a spreadsheet, choose a text type for the identifier column during import and compare the resulting values with the original file. CSV quotation protects delimiters and quotation syntax. It does not guarantee a spreadsheet's column type or prevent automatic conversion.

Do this check before matching two files. Keep the original identifier alongside any normalized join key so that collisions or changes remain inspectable.

## Give missing values a meaning

A blank CSV field cannot by itself distinguish an unknown observation from intentionally empty text. Python's CSV writer writes both `None` and `""` as empty fields. That transformation is not reversible from the field alone. [Python CSV writer contract](https://docs.python.org/3/library/csv.html#csv.writer).

The fictional file carries a separate state:

| State | Meaning in this example | Reconstructed value |
| --- | --- | --- |
| `unknown` | No known observation | `None` |
| `observed_empty` | Intentionally empty text | `""` |
| `observed` | Literal value is present | `"0"` |

These states are teaching conventions. A real provider's contract must define its fields; do not infer their meaning from blankness or assume this example's names are API fields.

## Connect the lesson to a real project

Identifier integrity is one acceptance check. You also need the right event, market, selection and time. Continue with the [odds comparability lesson](../odds-comparability/README.md) to inspect those separate questions.

For a ParlayAPI project, try the [limited public playground](https://parlay-api.com/playground?utm_source=github&utm_medium=developer_recipe&utm_campaign=csv_identifiers_20261006) or read the [API documentation](https://parlay-api.com/docs?utm_source=github&utm_medium=developer_recipe&utm_campaign=csv_identifiers_20261006). The exercise runs fully offline without an account. Use private own-key results only for permitted internal research and keep API data out of public repositories; data access does not grant redistribution rights.
