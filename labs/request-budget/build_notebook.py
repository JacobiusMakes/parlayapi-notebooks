"""Rebuild the self-contained offline notebook and example report from real code."""
import argparse
import ast
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def cell(kind, ident, text):
    item = {'cell_type': kind, 'id': ident, 'metadata': {}, 'source': text.splitlines(True)}
    if kind == 'code':
        item.update({'execution_count': None, 'outputs': []})
    return item


def generated_files():
    source = ROOT / 'budget_audit.py'
    text = source.read_text()
    tree = ast.parse(text)
    # Keep original source segments so generation is stable across Python versions.
    entry_test = ast.dump(ast.parse("__name__ == '__main__'", mode='eval').body)
    nodes = [node for node in tree.body if not (
        isinstance(node, ast.If) and ast.dump(node.test) == entry_test)]
    core = '\n\n'.join(ast.get_source_segment(text, node) for node in nodes) + '\n'
    notebook = {
        'nbformat': 4, 'nbformat_minor': 5,
        'metadata': {'kernelspec': {'display_name': 'Python 3', 'language': 'python', 'name': 'python3'},
                     'language_info': {'name': 'python'},
                     'colab': {'provenance': [], 'private_outputs': True}},
        'cells': [
            cell('markdown', 'overview', '''# Budget several API jobs without hiding unknown costs

Run all cells with Python 3.9 or later. Everything needed is in this notebook;
there are no package installs, network requests, API-key prompts or default file writes.

All job names, windows and credit rates in this exercise are invented. The model
calculates entered assumptions. It does not check current endpoint entitlement,
actual metering or account usage.
'''),
            cell('code', 'real-model', core),
            cell('markdown', 'two-jobs', '''## One known rate and one unknown rate

The first job has two readers sharing one declared upstream job. Its seven-minute
window has polls at zero and five minutes. The second starts at 23:55 and crosses
midnight. Each full window counts once. Its unit cost is deliberately blank.
'''),
            cell('code', 'run-example', "example_jobs = parse_jobs_csv(EXAMPLE_CSV)\nreport = audit_jobs(example_jobs)\nreport['invented_fixture'] = True\nprint(format_table(report))\nassert report['planned_requests'] == 117\nassert report['total_estimated_credits'] is None\n"),
            cell('code', 'clock-markers', "print(json.dumps(report['jobs'][1]['poll_markers'], indent=2))\n"),
            cell('markdown', 'entered-rate', '''## Try a second explicitly entered rate

The next cell supplies another invented rate of 0.2 credits per request. This
makes the arithmetic complete under those assumptions; it does not verify that
an API request is actually metered at that rate. Change the CSV values above to
rehearse a different window, number of pages or retry allowance.
'''),
            cell('code', 'all-priced', "priced_jobs = [dict(job) for job in example_jobs]\npriced_jobs[1]['credits_per_request'] = '0.2'\npriced_report = audit_jobs(priced_jobs)\nprint(format_table(priced_report))\nassert priced_report['total_estimated_credits'] == '13.3'\n"),
            cell('markdown', 'next-step', '''## Take the assumptions into your own evaluation

Use the [evaluation workbench](https://parlay-api.com/tools/evaluation-lab?utm_source=colab&utm_medium=notebook&utm_campaign=request-budget-kit)
to record the exact output and fields your project needs. Verify current request
costs and entitlement in the [documentation](https://parlay-api.com/docs).

The [source kit](https://github.com/JacobiusMakes/parlayapi-notebooks/tree/main/labs/request-budget)
includes a CSV template and a command-line JSON export. Keep your own assumptions,
keys and private API responses out of public notebooks. Published outputs are
empty and Colab output omission is requested; this is not access control.
'''),
        ],
    }
    spec = importlib.util.spec_from_file_location('request_budget_core', source)
    model = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(model)
    report = model.audit_jobs(model.parse_jobs_csv(model.EXAMPLE_CSV))
    report['invented_fixture'] = True
    return {
        'request-budget.ipynb': json.dumps(notebook, indent=2, ensure_ascii=False) + '\n',
        'example-jobs.csv': model.EXAMPLE_CSV,
        'example-report.json': json.dumps(report, indent=2, ensure_ascii=False) + '\n',
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    for name, text in generated_files().items():
        path = ROOT / name
        if args.check:
            if not path.exists() or path.read_text() != text:
                raise SystemExit('Generated file is stale: ' + name)
        else:
            path.write_text(text)


if __name__ == '__main__':
    main()
