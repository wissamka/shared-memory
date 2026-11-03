#!/usr/bin/env python3
"""Read a personal Markdown task list and compute its local-calendar reminder windows."""
import argparse
from datetime import date, datetime, timedelta
import json
from pathlib import Path
import re
import sys
from zoneinfo import ZoneInfo

from common import cli_encoding, safe_path, within


def cells(line):
    body = line.strip().removeprefix('|')
    if body.endswith('|') and not body.endswith(r'\|'):
        body = body[:-1]
    return [cell.strip().replace(r'\|', '|') for cell in
            re.split(r'(?<!\\)\|', body)]


def visible_lines(text):
    """Keep line positions while excluding fenced examples."""
    # Fenced examples may contain plausible-looking tasks. Only read live tables.
    lines = []
    fence = ''
    for line in text.splitlines():
        stripped = line.lstrip()
        if fence:
            candidate = stripped.rstrip()
            if len(candidate) >= len(fence) and set(candidate) == {fence[0]}:
                fence = ''
            lines.append('')
        elif (opening := re.match(r'^(`{3,}|~{3,})', stripped)):
            fence = opening.group(1)
            lines.append('')
        else:
            lines.append(line)
    return lines


def personal_tasks(text):
    """Accept repeated Markdown task tables, including an existing two-section list."""
    lines = visible_lines(text)
    found = False
    tasks = []
    for index, line in enumerate(lines[:-1]):
        if '|' not in line:
            continue
        header = [name.casefold() for name in cells(line)]
        if not {'task', 'status', 'due'}.issubset(header):
            continue
        separator = cells(lines[index + 1])
        if len(separator) != len(header) or not all(re.fullmatch(r':?-{3,}:?', cell) for cell in separator):
            raise ValueError(f'Invalid task table header at line {index + 1}')
        if len(set(header)) != len(header):
            raise ValueError(f'Duplicate task column at line {index + 1}')
        found = True
        for number in range(index + 2, len(lines)):
            if '|' not in lines[number]:
                break
            row = cells(lines[number])
            if len(row) != len(header):
                raise ValueError(f'Invalid task row at line {number + 1}')
            data = dict(zip(header, row))
            status = data['status'].casefold()
            if status in {'done', 'closed', 'complete', 'completed', 'cancelled', 'canceled'}:
                continue
            if status not in {'open', 'open (recurring)', 'in progress', 'waiting', 'blocked'} or not data['task']:
                raise ValueError(f'Unrecognized task or status at line {number + 1}')
            due = data['due']
            approximate = due.startswith('~')
            if approximate:
                due = due[1:].strip()
            if due in {'', '-', '—'} and not approximate:
                due = None
            elif not re.fullmatch(r'\d{4}-\d{2}-\d{2}', due):
                raise ValueError(f'Expected YYYY-MM-DD at line {number + 1}')
            else:
                date.fromisoformat(due)
            item = {'task': data['task'], 'due': due}
            if approximate:
                item['approximate'] = True
            tasks.append(item)
    if not found:
        raise ValueError('Personal task table requires Task, Status and Due columns')
    return tasks


def agenda(tasks, period, today):
    if period == 'weekly':
        start = today + timedelta(days=7 - today.weekday())
        end = start + timedelta(days=6)
    else:
        start, end = today, today + timedelta(days=1)
    result = {'period': period, 'start': start.isoformat(), 'end': end.isoformat(), 'upcoming': []}
    if period == 'weekly':
        result.update(overdue=[], undated=[])
    for item in sorted(tasks, key=lambda row: (row['due'] or '', row['task'].casefold())):
        due = item['due']
        if due and result['start'] <= due <= result['end']:
            result['upcoming'].append(item)
        elif period == 'weekly' and due is None:
            result['undated'].append(item)
        elif period == 'weekly' and due < today.isoformat():
            result['overdue'].append(item)
    return result


def main():
    cli_encoding()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--vault', required=True)
    parser.add_argument('--personal-list', default='My Tasks.md', help='Canonical vault-relative personal task note')
    parser.add_argument('--period', choices=['daily', 'weekly'], required=True)
    parser.add_argument('--on', type=date.fromisoformat, help='Local reference date (defaults to today)')
    args = parser.parse_args()
    try:
        root = safe_path(args.vault)
        config = json.loads(within(root, '.memory-state/config.json').read_text(encoding='utf-8'))
        zone = ZoneInfo(config['timezone'])
        today = args.on or datetime.now(zone).date()
        tasks = personal_tasks(within(root, args.personal_list).read_text(encoding='utf-8'))
        print(json.dumps(agenda(tasks, args.period, today), ensure_ascii=False, indent=2))
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f'Personal agenda unavailable: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
