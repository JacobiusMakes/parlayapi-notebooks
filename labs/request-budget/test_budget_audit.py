import contextlib
import io
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import budget_audit as model
import build_notebook

ROOT = Path(__file__).resolve().parent


def job(**changes):
    value = dict(model.parse_jobs_csv(model.EXAMPLE_CSV)[0])
    value.update(changes)
    return value


class BudgetAuditTests(unittest.TestCase):
    def test_worked_fixture_preserves_the_unpriced_job(self):
        r = model.audit_jobs(model.parse_jobs_csv(model.EXAMPLE_CSV))
        a, b = r['jobs']
        self.assertEqual((a['base_requests'], a['additional_retry_requests'], a['planned_requests']), (96, 5, 101))
        self.assertEqual((b['planned_requests'], b['estimated_credits']), (16, None))
        self.assertEqual((r['planned_requests'], r['known_estimated_credit_subtotal']), (117, '10.1'))
        self.assertIsNone(r['total_estimated_credits'])
        self.assertEqual(r['unpriced_job_ids'], ['event-detail'])
        self.assertEqual(r['api_requests_made'], 0)
        self.assertEqual(r['actual_credit_usage'], 'not_observed')

    def test_seven_minute_window_includes_the_partial_interval(self):
        r = model.audit_jobs([job(sports=1, requests_per_refresh=1, active_windows=1, retry_percent=0)])
        self.assertEqual(r['planned_requests'], 2)
        self.assertEqual([m['offset_seconds'] for m in r['jobs'][0]['poll_markers']], [0, 300])

    def test_exact_window_end_is_excluded(self):
        r = model.audit_jobs([job(active_minutes=5, sports=1, requests_per_refresh=1, active_windows=1, retry_percent=0)])
        self.assertEqual(r['planned_requests'], 1)
        self.assertEqual(r['jobs'][0]['last_poll_offset_seconds'], 0)

    def test_empty_windows_have_no_polls_and_zero_repetitions_have_no_requests(self):
        a = model.audit_jobs([job(active_minutes=0)])
        self.assertEqual((a['planned_requests'], a['jobs'][0]['poll_markers']), (0, []))
        b = model.audit_jobs([job(active_windows=0)])
        self.assertEqual(b['planned_requests'], 0)

    def test_unknown_cost_stays_unknown_even_with_zero_requests(self):
        r = model.audit_jobs([job(credits_per_request='', active_windows=0)])
        self.assertIsNone(r['total_estimated_credits'])
        self.assertEqual(r['known_estimated_credit_subtotal'], '0')

    def test_known_zero_cost_is_not_unknown(self):
        r = model.audit_jobs([job(credits_per_request='0')])
        self.assertEqual(r['total_estimated_credits'], '0')
        self.assertEqual(r['unpriced_job_ids'], [])

    def test_mixed_rates_keep_separate_exact_subtotals(self):
        jobs = model.parse_jobs_csv(model.EXAMPLE_CSV)
        jobs[1]['credits_per_request'] = '0.2'
        r = model.audit_jobs(jobs)
        self.assertEqual([x['estimated_credits'] for x in r['jobs']], ['10.1', '3.2'])
        self.assertEqual(r['total_estimated_credits'], '13.3')

    def test_twelve_place_decimal_arithmetic_is_exact(self):
        r = model.audit_jobs([job(active_minutes=1, interval_seconds=20, sports=1,
                                 requests_per_refresh=1, active_windows=1, retry_percent=0,
                                 credits_per_request='0.100000000001')])
        self.assertEqual(r['total_estimated_credits'], '0.300000000003')

    def test_multiple_readers_do_not_duplicate_an_explicit_shared_job(self):
        a = model.audit_jobs([job(consumer_count=1)])
        b = model.audit_jobs([job(consumer_count=23)])
        self.assertEqual(a['planned_requests'], b['planned_requests'])
        self.assertEqual(a['total_estimated_credits'], b['total_estimated_credits'])

    def test_crossing_midnight_does_not_split_a_window(self):
        r = model.audit_jobs([model.parse_jobs_csv(model.EXAMPLE_CSV)[1]])['jobs'][0]
        self.assertEqual(r['polls_per_window'], 2)
        self.assertEqual(r['poll_markers'], [
            {'offset_seconds': 0, 'day_offset': 0, 'clock_label': '23:55:00'},
            {'offset_seconds': 300, 'day_offset': 1, 'clock_label': '00:00:00'}])
        self.assertEqual(r['planned_requests'], 16)

    def test_marker_sampling_does_not_reduce_totals(self):
        r = model.audit_jobs([job(active_minutes=1440, interval_seconds=1, sports=1,
                                 requests_per_refresh=1, active_windows=1, retry_percent=0)])['jobs'][0]
        self.assertEqual((r['planned_requests'], len(r['poll_markers']), r['omitted_markers']), (86400, 12, 86388))
        self.assertEqual(r['last_poll_offset_seconds'], 86399)

    def test_invalid_costs_cannot_become_zero(self):
        for value in [-1, 0, True, 'NaN', 'Infinity', '-0.1', '1e-3', '1.0000000000001']:
            with self.subTest(value=value), self.assertRaises(ValueError):
                model.audit_jobs([job(credits_per_request=value)])

    def test_invalid_counts_clocks_and_portable_overflow_fail(self):
        cases = [dict(sports=True), dict(interval_seconds=0), dict(active_minutes=1.5),
                 dict(active_windows=-1), dict(consumer_count=0), dict(start_time='24:00'),
                 dict(start_time='12:60'), dict(active_minutes=1440, interval_seconds=1,
                 sports=10000, requests_per_refresh=10000, active_windows=366, retry_percent=1000)]
        for value in cases:
            with self.subTest(value=value), self.assertRaises(ValueError):
                model.audit_jobs([job(**value)])

    def test_duplicate_ids_unknown_fields_and_empty_jobs_fail(self):
        for jobs in [[], [job(), job()], [job(api_key='never-serialize-this')], [job(job_id='private\nlabel')]]:
            with self.assertRaises(ValueError):
                model.audit_jobs(jobs)

    def test_csv_shape_and_size_are_bounded(self):
        header = model.EXAMPLE_CSV.splitlines()[0]
        for text in ['', header, header + ',job_id\n', model.EXAMPLE_CSV + 'short,row\n', 'x' * 65537]:
            with self.assertRaises(ValueError):
                model.parse_jobs_csv(text)
        too_many = header + '\n' + '\n'.join(model.EXAMPLE_CSV.splitlines()[1:2] * 101)
        with self.assertRaises(ValueError):
            model.parse_jobs_csv(too_many)

    def test_table_distinguishes_unknown_from_zero(self):
        r = model.audit_jobs([job(credits_per_request='0'), job(job_id='unpriced', credits_per_request='')])
        text = model.format_table(r)
        self.assertIn('pregame-board | 101 | 0 | 0', text)
        self.assertIn('unpriced | 101 | unknown | unknown', text)
        self.assertIn('Total estimated credits: unknown', text)

    def test_cli_example_ignores_keys_and_exports_actual_json(self):
        env = dict(os.environ, PARLAY_API_KEY='DO-NOT-READ-OR-PRINT-TEST-KEY')
        p = subprocess.run([sys.executable, str(ROOT / 'budget_audit.py'), '--example'],
                           text=True, capture_output=True, env=env, check=True)
        self.assertNotIn(env['PARLAY_API_KEY'], p.stdout + p.stderr)
        r = json.loads(p.stdout)
        self.assertEqual(r['planned_requests'], 117)
        self.assertTrue(r['invented_fixture'])

    def test_cli_private_csv_and_exclusive_atomic_output(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'assumptions.csv'
            target = Path(folder) / 'result.json'
            source.write_text(model.EXAMPLE_CSV)
            args = [sys.executable, str(ROOT / 'budget_audit.py'), '--input', str(source), '--output', str(target)]
            subprocess.run(args, check=True, capture_output=True)
            before = target.read_bytes()
            self.assertIsNone(json.loads(before)['invented_fixture'])
            self.assertEqual(json.loads(before)['input_source'], 'user_supplied_assumptions')
            if os.name == 'posix':
                self.assertEqual(target.stat().st_mode & 0o777, 0o600)
            second = subprocess.run(args, capture_output=True)
            self.assertNotEqual(second.returncode, 0)
            self.assertEqual(target.read_bytes(), before)
            self.assertEqual(list(Path(folder).glob('.budget-*')), [])
            self.assertEqual(source.read_text(), model.EXAMPLE_CSV)

    def test_failed_export_leaves_existing_file_untouched_and_removes_own_temp(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / 'existing.json'
            target.write_text('existing-content')
            with self.assertRaises(FileExistsError):
                model.write_new_file(target, 'replacement')
            self.assertEqual(target.read_text(), 'existing-content')
            self.assertEqual(list(Path(folder).glob('.budget-*')), [])

    def test_interval_longer_than_window_keeps_its_initial_poll(self):
        r = model.audit_jobs([job(interval_seconds=600)])['jobs'][0]
        self.assertEqual(r['polls_per_window'], 1)
        self.assertEqual(r['last_poll_offset_seconds'], 0)

    def test_clock_label_is_optional_and_midnight_is_not_missing(self):
        a = model.audit_jobs([job(start_time='  ')])['jobs'][0]
        self.assertIsNone(a['start_time_label'])
        self.assertEqual(a['poll_markers'][0], {'offset_seconds': 0})
        b = model.audit_jobs([job(start_time=' 00:00 ')])['jobs'][0]
        self.assertEqual(b['start_time_label'], '00:00')
        self.assertEqual(b['poll_markers'][0]['clock_label'], '00:00:00')

    def test_aggregate_overflow_is_checked_across_jobs(self):
        a = job(active_minutes=1440, interval_seconds=1, sports=10000,
                requests_per_refresh=10000, active_windows=300, retry_percent=100)
        model.audit_jobs([a])
        with self.assertRaises(ValueError):
            model.audit_jobs([a, dict(a, job_id='another-job')])

    def test_cli_stdin_preserves_unknown_provenance(self):
        p = subprocess.run([sys.executable, str(ROOT / 'budget_audit.py'), '--input', '-'],
                           text=True, input=model.EXAMPLE_CSV, capture_output=True, check=True)
        r = json.loads(p.stdout)
        self.assertEqual(r['planned_requests'], 117)
        self.assertEqual(r['input_source'], 'user_supplied_assumptions')
        self.assertIsNone(r['invented_fixture'])

    def test_cli_default_runs_with_network_and_prompts_blocked(self):
        with mock.patch.object(socket, 'socket', side_effect=AssertionError('network forbidden')), \
             mock.patch('builtins.input', side_effect=AssertionError('input forbidden')), \
             contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(model.main(['--example']), 0)
        self.assertEqual(json.loads(output.getvalue())['planned_requests'], 117)

    def test_credentials_column_is_rejected_without_echoing_its_value(self):
        lines = model.EXAMPLE_CSV.splitlines()
        text = lines[0] + ',api_key\n' + lines[1] + ',DO-NOT-ECHO-THIS-KEY\n'
        p = subprocess.run([sys.executable, str(ROOT / 'budget_audit.py'), '--input', '-'],
                           text=True, input=text, capture_output=True)
        self.assertEqual(p.returncode, 2)
        self.assertEqual(p.stdout, '')
        self.assertNotIn('DO-NOT-ECHO-THIS-KEY', p.stderr)

    def test_cli_oversized_input_is_rejected_before_export(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / 'result.json'
            p = subprocess.run([sys.executable, str(ROOT / 'budget_audit.py'), '--input', '-', '--output', str(target)],
                               text=True, input='x' * 65537, capture_output=True)
            self.assertEqual(p.returncode, 2)
            self.assertFalse(target.exists())

    def test_generated_artifacts_match_the_real_source(self):
        for name, expected in build_notebook.generated_files().items():
            self.assertEqual((ROOT / name).read_text(), expected, name)

    def test_all_published_notebook_code_cells_run_offline_without_saved_outputs(self):
        notebook = json.loads((ROOT / 'request-budget.ipynb').read_text())
        self.assertTrue(notebook['metadata']['colab']['private_outputs'])
        namespace = {'__name__': '__notebook__'}
        with mock.patch.object(socket, 'socket', side_effect=AssertionError('network forbidden')), \
             mock.patch('builtins.input', side_effect=AssertionError('input forbidden')), \
             contextlib.redirect_stdout(io.StringIO()):
            for c in notebook['cells']:
                if c['cell_type'] == 'code':
                    self.assertEqual(c['outputs'], [])
                    self.assertIsNone(c['execution_count'])
                    exec(compile(''.join(c['source']), '<published-notebook>', 'exec'), namespace)
        self.assertEqual(namespace['priced_report']['total_estimated_credits'], '13.3')
        self.assertIsNone(namespace['report']['total_estimated_credits'])


if __name__ == '__main__':
    unittest.main()
