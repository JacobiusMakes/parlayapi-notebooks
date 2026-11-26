"""Exact request-budget arithmetic on entered assumptions. No API or key access."""
import argparse
import csv
import io
import json
import os
from pathlib import Path
import re
import sys
import tempfile

MAX_BYTES = 65536
MAX_JOBS = 100
MAX_SAFE_INTEGER = 2 ** 53 - 1
SCALE = 10 ** 12
LIMITS = {
    'active_minutes': (0, 1440), 'interval_seconds': (1, 86400),
    'sports': (1, 10000), 'requests_per_refresh': (1, 10000),
    'active_windows': (0, 366), 'retry_percent': (0, 1000),
    'consumer_count': (1, 100000),
}
REQUIRED = {'job_id', 'active_minutes', 'interval_seconds', 'sports',
            'requests_per_refresh', 'active_windows', 'retry_percent',
            'credits_per_request'}
ALLOWED = REQUIRED | {'consumer_count', 'start_time'}
EXAMPLE_CSV = '''job_id,active_minutes,interval_seconds,sports,requests_per_refresh,active_windows,retry_percent,credits_per_request,consumer_count,start_time
pregame-board,7,300,2,3,8,5,0.1,2,18:00
event-detail,10,300,1,1,8,0,,1,23:55
'''


def whole(value, field):
    low, high = LIMITS[field]
    if isinstance(value, str) and re.fullmatch(r'[0-9]+', value.strip()):
        digits = value.strip().lstrip('0') or '0'
        if len(digits) <= len(str(high)):
            value = int(digits)
    if type(value) is not int or not low <= value <= high:
        raise ValueError('%s requires a whole number from %s to %s' % (field, low, high))
    return value


def credit_units(value):
    """Represent an entered decimal in trillionths, without float rounding."""
    if value is None or value == '':
        return None
    if not isinstance(value, str):
        raise ValueError('credits_per_request must be decimal text or blank')
    value = value.strip()
    if not value:
        return None
    if not re.fullmatch(r'(?:0|[1-9]\d{0,11})(?:\.\d{1,12})?', value):
        raise ValueError('credits_per_request needs nonnegative decimal text, up to 12 places')
    integer, _, fraction = value.partition('.')
    return int(integer) * SCALE + int(fraction.ljust(12, '0') or '0')


def credit_text(units):
    integer, fraction = divmod(units, SCALE)
    tail = str(fraction).rjust(12, '0').rstrip('0')
    return str(integer) + ('.' + tail if tail else '')


def start_seconds(value):
    if value is None or isinstance(value, str) and not value.strip():
        return None
    if not isinstance(value, str) or not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d', value.strip()):
        raise ValueError('start_time must be HH:MM in a 24-hour clock or blank')
    hours, minutes = map(int, value.strip().split(':'))
    return hours * 3600 + minutes * 60


def parse_jobs_csv(text):
    if not isinstance(text, str) or len(text.encode('utf-8')) > MAX_BYTES:
        raise ValueError('CSV input must be UTF-8 text, at most 65536 bytes')
    reader = csv.reader(io.StringIO(text.lstrip('\ufeff')), strict=True)
    try:
        headers = [name.strip() for name in next(reader)]
    except StopIteration:
        raise ValueError('CSV needs a header and at least one job') from None
    if len(headers) != len(set(headers)):
        raise ValueError('CSV headers must be unique')
    if not REQUIRED <= set(headers) or not set(headers) <= ALLOWED:
        raise ValueError('CSV has missing or unsupported columns; use the supplied template')
    jobs = []
    for row in reader:
        if not row:
            continue
        if len(row) != len(headers):
            raise ValueError('CSV row %s has the wrong number of fields' % (reader.line_num,))
        jobs.append(dict(zip(headers, row)))
        if len(jobs) > MAX_JOBS:
            raise ValueError('Use at most 100 jobs')
    if not jobs:
        raise ValueError('CSV needs at least one job')
    return jobs


def audit_jobs(jobs):
    if not isinstance(jobs, list) or not 1 <= len(jobs) <= MAX_JOBS:
        raise ValueError('Supply 1 to 100 job objects')
    rows, seen, total_requests, known_units, unpriced = [], set(), 0, 0, []
    for index, job in enumerate(jobs, 1):
        if not isinstance(job, dict) or not REQUIRED <= set(job) or not set(job) <= ALLOWED:
            raise ValueError('Job %s has missing or unsupported fields' % index)
        ident = job['job_id']
        if not isinstance(ident, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,63}', ident):
            raise ValueError('job_id needs 1 to 64 letters, digits, dots, underscores or hyphens')
        if ident in seen:
            raise ValueError('Job %s repeats an earlier job_id' % index)
        seen.add(ident)
        values = {field: whole(job.get(field, 1), field) for field in LIMITS}
        start = start_seconds(job.get('start_time'))
        unit = credit_units(job['credits_per_request'])
        seconds = values['active_minutes'] * 60
        interval = values['interval_seconds']
        polls = (seconds + interval - 1) // interval
        base = polls * values['sports'] * values['requests_per_refresh'] * values['active_windows']
        reserve = (base * values['retry_percent'] + 99) // 100
        planned = base + reserve
        total_requests += planned
        if total_requests > MAX_SAFE_INTEGER:
            raise ValueError('Request total exceeds portable exact JSON integer storage; reduce the scenario')
        estimate = None if unit is None else planned * unit
        if unit is None:
            unpriced.append(ident)
        else:
            known_units += estimate
        markers = []
        for poll in range(min(polls, 12)):
            offset = poll * interval
            marker = {'offset_seconds': offset}
            if start is not None:
                absolute = start + offset
                marker['day_offset'] = absolute // 86400
                clock = absolute % 86400
                marker['clock_label'] = '%02d:%02d:%02d' % (clock // 3600, clock // 60 % 60, clock % 60)
            markers.append(marker)
        rows.append({
            'job_id': ident, 'assumptions': values,
            'start_time_label': None if start is None else '%02d:%02d' % (start // 3600, start // 60 % 60),
            'polls_per_window': polls, 'base_requests': base,
            'additional_retry_requests': reserve, 'planned_requests': planned,
            'credits_per_request': None if unit is None else credit_text(unit),
            'estimated_credits': None if estimate is None else credit_text(estimate),
            'poll_markers': markers, 'omitted_markers': max(0, polls - 12),
            'last_poll_offset_seconds': (polls - 1) * interval if polls else None,
        })
    return {
        'format_version': 1, 'kind': 'request_budget_assumptions',
        'jobs': rows, 'planned_requests': total_requests,
        'known_estimated_credit_subtotal': credit_text(known_units),
        'total_estimated_credits': None if unpriced else credit_text(known_units),
        'unpriced_job_ids': unpriced,
        'boundary_rule': 'Each nonempty window includes its initial poll and excludes its end.',
        'window_rule': 'active_windows counts complete repetitions, including windows crossing midnight.',
        'sharing_rule': 'Each row is one upstream job. consumer_count records its readers and does not multiply requests.',
        'clock_rule': 'Clock labels use a relative 24-hour day. They do not schedule calendar dates or timezone transitions.',
        'sample_rule': 'At most 12 poll markers per window; totals cover every modeled poll.',
        'unit_cost_validation': 'Entered assumptions only; verify exact request costs in current documentation.',
        'actual_credit_usage': 'not_observed', 'api_requests_made': 0,
    }


def format_table(report):
    lines = ['Job | Planned requests | Entered unit credits | Estimated credits',
             '--- | ---: | ---: | ---:']
    for row in report['jobs']:
        unit = 'unknown' if row['credits_per_request'] is None else row['credits_per_request']
        estimate = 'unknown' if row['estimated_credits'] is None else row['estimated_credits']
        lines.append('%s | %s | %s | %s' % (row['job_id'], row['planned_requests'], unit, estimate))
    total = report['total_estimated_credits']
    lines += ['', 'Planned requests: %s' % report['planned_requests'],
              'Known estimated credit subtotal: ' + report['known_estimated_credit_subtotal'],
              'Total estimated credits: ' + ('unknown' if total is None else total)]
    return '\n'.join(lines) + '\n'


def write_new_file(destination, text):
    """Publish a complete owner-only file without replacing an existing path."""
    destination = Path(destination)
    temp_name = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=destination.parent,
                                         prefix='.budget-', delete=False) as f:
            temp_name = f.name
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.link(temp_name, destination)
    finally:
        if temp_name is not None:
            Path(temp_name).unlink()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--example', action='store_true', help='use the invented teaching CSV')
    source.add_argument('--input', help='read a private CSV file; use - for stdin')
    parser.add_argument('--format', choices=['json', 'table'], default='json')
    parser.add_argument('--output', help='create a new file; existing paths are never replaced')
    args = parser.parse_args(argv)
    try:
        if args.example:
            text = EXAMPLE_CSV
        else:
            if args.input == '-':
                raw = sys.stdin.buffer.read(MAX_BYTES + 1)
            else:
                with Path(args.input).open('rb') as f:
                    raw = f.read(MAX_BYTES + 1)
            if len(raw) > MAX_BYTES:
                raise ValueError('CSV input exceeds 65536 bytes')
            text = raw.decode('utf-8-sig')
        report = audit_jobs(parse_jobs_csv(text))
        report['invented_fixture'] = True if args.example else None
        report['input_source'] = 'built_in_invented_example' if args.example else 'user_supplied_assumptions'
        rendered = json.dumps(report, indent=2, ensure_ascii=False) + '\n' if args.format == 'json' else format_table(report)
        if args.output:
            write_new_file(args.output, rendered)
        else:
            sys.stdout.write(rendered)
    except (ValueError, OSError, UnicodeError, csv.Error) as error:
        parser.exit(2, 'Budget input/output error: %s\n' % error)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
