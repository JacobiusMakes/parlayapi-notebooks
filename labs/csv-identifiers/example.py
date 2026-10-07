#!/usr/bin/env python3
"""Original fictional teaching example. No API calls, feed rows, or real people."""
import csv
import io

INPUT = '''participant_id,label,observation,observation_state
000123,Fictional Harbor Player,,unknown
9007199254740993,Fictional Ridge Player,,observed_empty
004200,Fictional Valley Player,0,observed
'''
EXPECTED = '''SYNTHETIC EXAMPLE : fictional IDs and records
GOOD ID: '000123'
GOOD ID: '9007199254740993'
GOOD ID: '004200'
GOOD observation 000123: None (unknown)
GOOD observation 9007199254740993: '' (observed_empty)
GOOD observation 004200: '0' (observed)
BAD numeric import: '000123' -> '123'
BAD float import: '9007199254740993' -> '9007199254740992'
RAW CSV ambiguity: None and '' both write as ''
STATE COLUMN: 'unknown' and 'observed_empty' remain distinct
'''

def render():
    rows = list(csv.DictReader(io.StringIO(INPUT)))
    lines = ['SYNTHETIC EXAMPLE : fictional IDs and records']
    for row in rows:
        lines.append(f"GOOD ID: {row['participant_id']!r}")
    for row in rows:
        state = row['observation_state']
        value = None if state == 'unknown' else row['observation']
        lines.append(f"GOOD observation {row['participant_id']}: {value!r} ({state})")
    lines.append(f"BAD numeric import: {rows[0]['participant_id']!r} -> {str(int(rows[0]['participant_id']))!r}")
    lines.append(f"BAD float import: {rows[1]['participant_id']!r} -> {str(int(float(rows[1]['participant_id'])))!r}")
    raw = io.StringIO()
    csv.writer(raw, lineterminator='\n').writerow([None, ''])
    if next(csv.reader(io.StringIO(raw.getvalue()))) != ['', '']:
        raise RuntimeError('Unexpected CSV blank-field behavior')
    lines.append("RAW CSV ambiguity: None and '' both write as ''")
    lines.append("STATE COLUMN: 'unknown' and 'observed_empty' remain distinct")
    return '\n'.join(lines) + '\n'

if __name__ == '__main__':
    output = render()
    if output != EXPECTED:
        raise SystemExit('Literal expected output mismatch')
    print(output, end='')
