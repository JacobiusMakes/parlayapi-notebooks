import contextlib
import copy
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import triage


HERE = Path(__file__).parent


class Decisions(unittest.TestCase):
    def case(self, **changes):
        return dict(triage.example_cases()[0], **changes)

    def decision(self, **changes):
        return triage.triage(self.case(**changes))

    def test_delay_seconds_counts_from_receipt(self):
        result = self.decision()
        self.assertEqual(result['decision'], 'review_one_read_retry_after_wait')
        self.assertEqual(result['earliest_manual_review_at'], '2026-01-01T00:00:30Z')
        self.assertEqual(result['attempts_remaining_under_entered_limit'], 1)

    def test_http_date_rounds_positive_fraction_up(self):
        result = self.decision(retry_after='Thu, 01 Jan 2026 00:00:30 GMT', received_at='2026-01-01T00:00:00.000001Z')
        self.assertEqual(result['retry_timing']['minimum_wait_seconds'], 30)
        self.assertEqual(result['earliest_manual_review_at'], '2026-01-01T00:00:30.000001Z')

    def test_past_date_and_zero_do_not_invent_a_loop(self):
        for hint in ['0', '000', 'Thu, 01 Jan 2026 00:00:00 GMT']:
            result = self.decision(retry_after=hint, received_at='2026-01-01T00:00:01Z', wait_budget_seconds=0)
            self.assertEqual(result['retry_timing']['minimum_wait_seconds'], 0)
            self.assertEqual(result['automatic_requests_made'], 0)
        self.assertEqual(self.decision(retry_after='0', attempts_used=2)['decision'], 'stop_attempt_budget')

    def test_absent_empty_and_ambiguous_wait_remain_unknown(self):
        for hint in [None, '', [], ['30', '30'], ['30', '60'], '30, 60']:
            result = self.decision(retry_after=hint)
            self.assertIsNone(result['retry_timing']['minimum_wait_seconds'])
            self.assertEqual(result['decision'], 'review_wait_instruction')
            self.assertIsNone(result['earliest_manual_review_at'])

    def test_single_extracted_field_and_optional_whitespace(self):
        self.assertEqual(self.decision(retry_after=[' \t30\t '])['retry_timing']['minimum_wait_seconds'], 30)

    def test_invalid_dates_and_unsupported_formats_are_unrecognized(self):
        for hint in ['Fri, 01 Jan 2026 00:00:30 GMT', 'Thu, 32 Jan 2026 00:00:30 GMT',
                     'Thu, 01 Jan 2026 24:00:00 GMT', 'Thu, 01 Jan 2026 00:00:60 GMT',
                     'Thursday, 01-Jan-26 00:00:30 GMT', 'Thu Jan  1 00:00:30 2026',
                     '+30', '-1', '1.5', 'Infinity', '30\n', '３０']:
            result = self.decision(retry_after=hint)
            self.assertEqual(result['retry_timing']['state'], 'unrecognized', hint)
            self.assertIsNone(result['earliest_manual_review_at'])

    def test_large_delay_is_not_capped_to_fit_budget(self):
        result = self.decision(retry_after=str(triage.MAX_SAFE_INTEGER))
        self.assertEqual(result['decision'], 'stop_wait_budget')
        self.assertEqual(result['retry_timing']['minimum_wait_seconds'], triage.MAX_SAFE_INTEGER)
        for text in [str(triage.MAX_SAFE_INTEGER + 1), '9' * 128]:
            result = self.decision(retry_after=text)
            self.assertEqual(result['retry_timing']['state'], 'outside_model_range')
            self.assertIsNone(result['earliest_manual_review_at'])

    def test_budget_counts_completed_attempt_and_never_truncates_wait(self):
        for used in [2, 3, 1000]:
            result = self.decision(attempts_used=used)
            self.assertEqual(result['decision'], 'stop_attempt_budget')
            self.assertEqual(result['attempts_remaining_under_entered_limit'], 0)
            self.assertIsNone(result['earliest_manual_review_at'])
        self.assertEqual(self.decision(wait_budget_seconds=29)['decision'], 'stop_wait_budget')
        self.assertEqual(self.decision(wait_budget_seconds=30)['decision'], 'review_one_read_retry_after_wait')

    def test_read_repeatability_is_explicit_and_method_bounded(self):
        for method in ['POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS']:
            self.assertEqual(self.decision(method=method)['decision'], 'stop_repeatability_unconfirmed')
        self.assertEqual(self.decision(read_only_confirmed=False)['decision'], 'stop_repeatability_unconfirmed')
        case = self.case(); del case['read_only_confirmed']
        self.assertEqual(triage.triage(case)['decision'], 'stop_repeatability_unconfirmed')
        self.assertEqual(self.decision(method='HEAD')['decision'], 'review_one_read_retry_after_wait')

    def test_auth_access_and_service_failures_remain_distinct(self):
        expected = {401: 'check_credentials', 403: 'inspect_access_denial', 400: 'inspect_request_failure',
                    404: 'inspect_request_failure', 500: 'check_service_failure', 502: 'check_service_failure',
                    504: 'check_service_failure', 302: 'review_redirect', 100: 'inspect_incomplete_response',
                    None: 'stop_transport_unknown'}
        for status, decision in expected.items():
            result = self.decision(status=status)
            self.assertEqual(result['decision'], decision)
            self.assertIsNone(result['earliest_manual_review_at'])
        self.assertEqual(self.decision(status=503)['decision'], 'review_one_read_retry_after_wait')

    def test_success_never_claims_a_required_observation(self):
        for status in [200, 201, 204, 206, 299]:
            result = self.decision(status=status)
            self.assertEqual(result['decision'], 'inspect_required_result')
            self.assertIsNone(result['useful_output_verified'])
            self.assertIsNone(result['earliest_manual_review_at'])

    def test_extreme_calendar_values_do_not_overflow(self):
        result = self.decision(received_at='9998-12-31T23:59:59Z', retry_after='86400', wait_budget_seconds=86400)
        self.assertEqual(result['earliest_manual_review_at'], '9999-01-01T23:59:59Z')
        self.assertEqual(self.decision(retry_after='Fri, 31 Dec 9999 23:59:59 GMT')['decision'], 'stop_wait_budget')

    def test_invalid_input_types_and_bounds_are_refused(self):
        for field, values in {
            'status': [True, '429', 99, 600, 429.0], 'method': ['get', None, []],
            'attempts_used': [False, 0, 1001], 'attempt_limit': [True, 0, 11],
            'wait_budget_seconds': [-1, 86401, 0.5, True],
            'received_at': ['2026-01-01', '2026-01-01T00:00:00', '2026-01-01T00:00:00+00:00', '2026-02-30T00:00:00Z', '9999-01-01T00:00:00Z'],
            'read_only_confirmed': ['true', 1, None], 'retry_after': [30, True, ['30'] * 5, [None], 'a' * 129],
        }.items():
            for value in values:
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    self.decision(**{field: value})

    def test_no_arbitrary_body_key_url_or_headers_accepted(self):
        for name in ['body', 'api_key', 'url', 'headers', 'Authorization']:
            with self.assertRaises(ValueError):
                triage.triage(self.case(**{name: 'PRIVATE-MARKER'}))

    def test_report_has_bounded_cohort_and_does_not_modify_inputs(self):
        cases = triage.example_cases(); before = copy.deepcopy(cases)
        result = triage.report(cases, invented_fixture=True)
        self.assertEqual(cases, before)
        self.assertEqual(len(result['cases']), 12)
        self.assertEqual([r['case_number'] for r in result['cases']], list(range(1, 13)))
        self.assertEqual(result['API_requests_made'], 0)
        self.assertEqual(result['files_written'], 0)
        self.assertTrue(result['invented_fixture'])
        self.assertIsNone(triage.report(cases)['invented_fixture'])
        for bad in [[], cases * 2, {}, None]:
            with self.assertRaises(ValueError):triage.report(bad)


class Command(unittest.TestCase):
    def run_cli(self, args, stdin=None, cwd=None):
        return subprocess.run([sys.executable, str(HERE / 'triage.py'), *args], input=stdin,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10, cwd=cwd)

    def test_example_runs_with_network_prompts_and_environment_access_blocked(self):
        out = io.StringIO()
        with mock.patch('socket.socket', side_effect=AssertionError('network')), \
             mock.patch('builtins.input', side_effect=AssertionError('prompt')), \
             mock.patch('os.getenv', side_effect=AssertionError('environment')), \
             mock.patch('builtins.open', side_effect=AssertionError('file access')), \
             mock.patch('pathlib.Path.open', side_effect=AssertionError('file access')), \
             contextlib.redirect_stdout(out):
            self.assertEqual(triage.main(['--example']), 0)
        result = json.loads(out.getvalue())
        self.assertEqual(result, triage.report(triage.example_cases(), invented_fixture=True))

    def test_example_file_and_literal_decisions_match_executable(self):
        cases = json.loads((HERE / 'cases.example.json').read_text())
        expected = json.loads((HERE / 'expected.example.json').read_text())
        self.assertEqual(cases, triage.example_cases())
        self.assertEqual(expected, triage.report(cases, invented_fixture=True))
        self.assertEqual([r['decision'] for r in expected['cases']], [
            'review_one_read_retry_after_wait', 'review_one_read_retry_after_wait',
            'review_wait_instruction', 'review_wait_instruction', 'stop_attempt_budget',
            'stop_wait_budget', 'stop_repeatability_unconfirmed', 'check_credentials',
            'inspect_access_denial', 'inspect_required_result', 'review_one_read_retry_after_wait',
            'stop_transport_unknown'])

    def test_cli_file_and_stdin_are_user_assumptions_and_write_nothing(self):
        with tempfile.TemporaryDirectory() as folder:
            f = Path(folder) / 'assumptions.json'
            f.write_text(json.dumps(triage.example_cases()))
            before = {v.name: v.read_bytes() for v in Path(folder).iterdir()}
            for args, data in [(['--input', str(f)], None), (['--input', '-'], f.read_bytes())]:
                result = self.run_cli(args, data, cwd=folder)
                self.assertEqual(result.returncode, 0, result.stderr)
                parsed = json.loads(result.stdout)
                self.assertIsNone(parsed['invented_fixture'])
                self.assertEqual(parsed['input_source'], 'user_supplied_assumptions')
            self.assertEqual(before, {v.name: v.read_bytes() for v in Path(folder).iterdir()})

    def test_cli_failures_do_not_echo_input_or_private_path(self):
        case = dict(triage.example_cases()[0], api_key='PRIVATE-MARKER')
        bad = [json.dumps([case]).encode(), b'{"PRIVATE-MARKER":', b'\xffPRIVATE-MARKER',
               b' ' * (triage.MAX_BYTES + 1), b'[' * 2000, b'[NaN]', b'[Infinity]',
               b'[{"status":429,"status":200}]']
        for data in bad:
            result = self.run_cli(['--input', '-'], data)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(result.stdout, b'')
            self.assertNotIn(b'PRIVATE-MARKER', result.stderr)
        result = self.run_cli(['--input', '/nonexistent/PRIVATE-MARKER.json'])
        self.assertEqual(result.returncode, 2)
        self.assertNotIn(b'PRIVATE-MARKER', result.stderr)

    def test_source_selection_is_required_and_exclusive(self):
        for args in [[], ['--example', '--input', '-']]:
            self.assertEqual(self.run_cli(args).returncode, 2)


if __name__ == '__main__':
    unittest.main()
