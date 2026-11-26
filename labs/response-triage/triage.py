"""Rehearse a first-response decision without sending requests or reading keys."""

import argparse
from datetime import datetime, timedelta
from email.utils import format_datetime, parsedate_to_datetime
import json
from pathlib import Path
import re
import sys


MAX_BYTES = 16384
MAX_CASES = 20
MAX_SAFE_INTEGER = 2 ** 53 - 1
REQUIRED = {
    'method', 'status', 'received_at', 'attempts_used', 'attempt_limit',
    'wait_budget_seconds',
}
OPTIONAL = {'retry_after', 'read_only_confirmed'}
UTC_PATTERN = r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z'
HTTP_DATE_PATTERN = (
    r'(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun), [0-9]{2} '
    r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) '
    r'[0-9]{4} [0-9]{2}:[0-9]{2}:[0-9]{2} GMT'
)


def whole(value, low, high, field):
    if type(value) is not int or not low <= value <= high:
        raise ValueError(field + ' is outside the rehearsal limits')
    return value


def utc_time(value):
    if not isinstance(value, str) or not re.fullmatch(UTC_PATTERN, value):
        raise ValueError('received_at needs an explicit UTC timestamp ending in Z')
    try:
        result = datetime.fromisoformat(value[:-1] + '+00:00')
    except ValueError:
        raise ValueError('received_at is not a calendar timestamp') from None
    if not 1970 <= result.year <= 9998:
        raise ValueError('received_at is outside the rehearsal year range')
    return result


def retry_timing(value, received):
    """Conservative teaching subset, not a general-purpose HTTP-date parser."""
    if isinstance(value, list):
        if len(value) > 4 or any(not isinstance(v, str) or len(v) > 128 for v in value):
            raise ValueError('retry_after is outside the rehearsal limits')
        if len(value) != 1:
            return {'state': 'ambiguous', 'minimum_wait_seconds': None}
        value = value[0]
    if value is None:
        return {'state': 'missing', 'minimum_wait_seconds': None}
    if not isinstance(value, str) or len(value) > 128:
        raise ValueError('retry_after needs text, a short list of values, or null')
    value = value.strip(' \t')
    if re.fullmatch(r'[0-9]+', value):
        digits = value.lstrip('0') or '0'
        if len(digits) > 16 or int(digits) > MAX_SAFE_INTEGER:
            return {'state': 'outside_model_range', 'minimum_wait_seconds': None}
        return {'state': 'delay_seconds', 'minimum_wait_seconds': int(digits)}
    if re.fullmatch(HTTP_DATE_PATTERN, value):
        try:
            target = parsedate_to_datetime(value)
            # Reject calendar normalization, incorrect weekdays and invalid times.
            if format_datetime(target, usegmt=True) != value:
                raise ValueError()
        except (ValueError, TypeError, OverflowError):
            return {'state': 'unrecognized', 'minimum_wait_seconds': None}
        delta = target - received
        # A fractional positive second must not become an early retry.
        seconds = max(0, delta.days * 86400 + delta.seconds + bool(delta.microseconds))
        return {'state': 'http_date', 'minimum_wait_seconds': seconds}
    return {'state': 'unrecognized', 'minimum_wait_seconds': None}


def triage(case):
    if not isinstance(case, dict) or not REQUIRED <= set(case) or not set(case) <= REQUIRED | OPTIONAL:
        raise ValueError('A rehearsal case has unsupported or missing fields')
    method = case['method']
    if not isinstance(method, str) or method not in {'GET', 'HEAD', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'}:
        raise ValueError('method needs a supported uppercase HTTP method')
    status = case['status']
    if status is not None:
        whole(status, 100, 599, 'status')
    received = utc_time(case['received_at'])
    used = whole(case['attempts_used'], 1, 1000, 'attempts_used')
    limit = whole(case['attempt_limit'], 1, 10, 'attempt_limit')
    wait_budget = whole(case['wait_budget_seconds'], 0, 86400, 'wait_budget_seconds')
    read_only = case.get('read_only_confirmed', False)
    if type(read_only) is not bool:
        raise ValueError('read_only_confirmed needs a boolean')
    timing = retry_timing(case.get('retry_after'), received)
    remaining = max(0, limit - used)
    review_at = None
    if status is None:
        decision = 'stop_transport_unknown'
        next_check = 'No HTTP status was recorded. Check the outcome before deciding whether to repeat anything.'
    elif 200 <= status < 300:
        decision = 'inspect_required_result'
        next_check = 'Inspect the exact required record, fields and timestamps. HTTP success alone does not verify a useful result.'
    elif status == 401:
        decision = 'check_credentials'
        next_check = 'Check the selected credential and authentication requirements privately before another request.'
    elif status == 403:
        decision = 'inspect_access_denial'
        next_check = 'Inspect the reported denial and exact request access. This status alone does not identify an exhausted allowance or a required upgrade.'
    elif 300 <= status < 400:
        decision = 'review_redirect'
        next_check = 'Review the destination and credential handling; this rehearsal does not follow redirects.'
    elif status in {429, 503}:
        if method not in {'GET', 'HEAD'} or not read_only:
            decision = 'stop_repeatability_unconfirmed'
            next_check = 'This model only reviews explicitly confirmed read-only GET or HEAD requests.'
        elif remaining <= 0:
            decision = 'stop_attempt_budget'
            next_check = 'The entered total attempt budget is exhausted. It includes the request already made.'
        elif timing['minimum_wait_seconds'] is None:
            decision = 'review_wait_instruction'
            next_check = 'No unambiguous supported wait instruction is available. Review the response and current documentation; do not invent a zero wait.'
        elif timing['minimum_wait_seconds'] > wait_budget:
            decision = 'stop_wait_budget'
            next_check = 'The minimum indicated wait exceeds the entered remaining wait budget. Do not shorten the wait to fit.'
        else:
            decision = 'review_one_read_retry_after_wait'
            review_at = (received + timedelta(seconds=timing['minimum_wait_seconds'])).isoformat().replace('+00:00', 'Z')
            next_check = 'After the indicated wait, review one further read request, its scope and cost. This is a manual decision, not a retry loop or a guarantee of success.'
    elif 500 <= status < 600:
        decision = 'check_service_failure'
        next_check = 'Inspect the service failure and current guidance. This model schedules no request.'
    elif 400 <= status < 500:
        decision = 'inspect_request_failure'
        next_check = 'Inspect the failed request and response meaning before changing or repeating it.'
    else:
        decision = 'inspect_incomplete_response'
        next_check = 'An informational status is not a completed final response.'
    return {
        'method': method,
        'status': status,
        'decision': decision,
        'next_check': next_check,
        'attempts_remaining_under_entered_limit': remaining,
        'retry_timing': timing,
        'earliest_manual_review_at': review_at,
        'useful_output_verified': None,
        'automatic_requests_made': 0,
    }


def report(cases, invented_fixture=None):
    if not isinstance(cases, list) or not 1 <= len(cases) <= MAX_CASES:
        raise ValueError('Supply 1 to 20 rehearsal cases')
    return {
        'format_version': 1,
        'kind': 'first_response_rehearsal',
        'invented_fixture': invented_fixture,
        'input_source': 'built_in_invented_examples' if invented_fixture is True else 'user_supplied_assumptions',
        'cases': [dict(case_number=i, **triage(case)) for i, case in enumerate(cases, 1)],
        'clock_assumption': 'The entered received_at and HTTP-date use an accurate common UTC clock. Clock accuracy is not checked.',
        'parser_scope': 'Decimal delay-seconds up to 2**53-1, or canonical IMF-fixdate with a correct weekday. Obsolete HTTP-date formats are unrecognized in this teaching subset.',
        'budget_scope': 'The caller supplies attempts already used and remaining wait budget. This offline model does not track real attempts or enforce a shared account budget.',
        'API_requests_made': 0,
        'files_written': 0,
    }


def example_cases():
    base = {
        'method': 'GET', 'status': 429,
        'received_at': '2026-01-01T00:00:00Z',
        'attempts_used': 1, 'attempt_limit': 2,
        'wait_budget_seconds': 60, 'read_only_confirmed': True,
        'retry_after': '30',
    }
    changes = [
        {},
        {'retry_after': 'Thu, 01 Jan 2026 00:00:30 GMT', 'received_at': '2026-01-01T00:00:00.000001Z'},
        {'retry_after': None},
        {'retry_after': ['30', '60']},
        {'attempts_used': 2},
        {'wait_budget_seconds': 10},
        {'method': 'POST'},
        {'status': 401, 'retry_after': None},
        {'status': 403, 'retry_after': None},
        {'status': 200, 'retry_after': None},
        {'status': 503, 'retry_after': '15'},
        {'status': None, 'retry_after': None},
    ]
    return [dict(base, **change) for change in changes]


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Repeated JSON fields are ambiguous')
        result[key] = value
    return result


def invalid_constant(value):
    raise ValueError('Nonfinite JSON numbers are not supported')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--example', action='store_true', help='rehearse twelve invented cases')
    source.add_argument('--input', help='read a minimal private JSON case list; - reads stdin')
    args = parser.parse_args(argv)
    try:
        if args.example:
            result = report(example_cases(), invented_fixture=True)
        else:
            if args.input == '-':
                raw = sys.stdin.buffer.read(MAX_BYTES + 1)
            else:
                with Path(args.input).open('rb') as stream:
                    raw = stream.read(MAX_BYTES + 1)
            if len(raw) > MAX_BYTES:
                raise ValueError('Input is too large')
            cases = json.loads(raw.decode('utf-8-sig'), object_pairs_hook=unique_object, parse_constant=invalid_constant)
            result = report(cases)
    except (ValueError, OSError, UnicodeError, RecursionError, TypeError):
        # Do not echo private input, filenames, keys or response bodies.
        parser.exit(2, 'Invalid rehearsal input. Use the minimal case schema in the guide; no request was sent.\n')
    sys.stdout.write(json.dumps(result, indent=2, ensure_ascii=False) + '\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
