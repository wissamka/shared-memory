#!/usr/bin/env python3
"""Record bounded source inventories and expose uncollected calendar days."""
import argparse
from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

from common import cli_encoding, create_once, digest, encoded, provenance, safe_path, within
from memory import config


def source_key(source_id):
    if not isinstance(source_id, str) or not source_id.strip():
        raise ValueError('A source ID is required')
    return digest(source_id.encode())


def load_source(root, source_id):
    config(root)
    value = json.loads(within(root, f'.memory-state/collection/sources/{source_key(source_id)}.json').read_text(encoding='utf-8'))
    if (not isinstance(value, dict) or value.get('version') != 1
            or value.get('source_id') != source_id or value.get('kind') not in ('codex', 'claude', 'manual')):
        raise ValueError('Invalid collection source')
    date.fromisoformat(value['since'])
    provenance(value['editor'])
    return value


def register(root, source_id, kind, since, editor, apply=False):
    config(root)
    provenance(editor)
    key = source_key(source_id)
    date.fromisoformat(since)
    if kind not in ('codex', 'claude', 'manual'):
        raise ValueError('Unsupported collection kind')
    path = within(root, f'.memory-state/collection/sources/{key}.json')
    value = {'version': 1, 'source_id': source_id, 'kind': kind, 'since': since, 'editor': editor}
    if path.exists():
        prior = load_source(root, source_id)
        if any(prior[k] != value[k] for k in ('source_id', 'kind', 'since')):
            raise ValueError('Source scope differs; preserve its history and register a distinct source ID')
        return {'mode': 'unchanged', 'source': prior}
    if apply:
        create_once(path, encoded(value))
    return {'mode': 'applied' if apply else 'preview', 'source': value}


def record(root, source_id, day, report, editor):
    source = load_source(root, source_id)
    target = date.fromisoformat(day)
    if target < date.fromisoformat(source['since']):
        raise ValueError('Collection day precedes the registered scope')
    provenance(editor)
    if not isinstance(report, dict):
        raise ValueError('Collection report must be an object')
    gaps = report.get('coverage_gaps')
    if not isinstance(gaps, list) or any(not isinstance(x, str) for x in gaps):
        raise ValueError('Collection gaps must be an explicit list')
    if report.get('mode') != 'applied':
        raise ValueError('A preview is not a completed collection')
    # This is an inventory of the declared source, not all chats or all content.
    entry = {'version': 1, 'source_id': source_id, 'date': day,
             'status': 'partial' if gaps else 'collected', 'coverage_gaps': gaps,
             'coverage': report.get('coverage', 'Declared source only'),
             'collected_at': datetime.now(timezone.utc).isoformat(), 'editor': editor}
    for key in ('files_examined', 'visible_messages', 'saved_messages', 'skipped_suppressed'):
        value = report.get(key, 0)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise ValueError('Collection counts must be nonnegative integers')
        entry[key] = value
    identifier = digest(encoded(entry))
    create_once(within(root, f'.memory-state/collection/attempts/{identifier}.json'), encoded(entry))
    return entry


def pending(root, through=None, overlap_days=1):
    zone = ZoneInfo(config(root)['timezone'])
    end = date.fromisoformat(through) if through else datetime.now(zone).date() - timedelta(days=1)
    if not isinstance(overlap_days, int) or not 0 <= overlap_days <= 31:
        raise ValueError('Overlap must be between 0 and 31 days')
    sources = {}
    for path in sorted(within(root, '.memory-state/collection/sources').glob('*.json')):
        raw = json.loads(safe_path(path).read_text(encoding='utf-8'))
        if not isinstance(raw, dict) or source_key(raw.get('source_id')) != path.stem:
            raise ValueError('Invalid collection source filename')
        source = load_source(root, raw['source_id'])
        sources[source['source_id']] = source
    attempts = {}
    for path in sorted(within(root, '.memory-state/collection/attempts').glob('*.json')):
        value = json.loads(safe_path(path).read_text(encoding='utf-8'))
        if not isinstance(value, dict) or digest(encoded(value)) != path.stem:
            raise ValueError('Collection attempt changed; inspect it before continuing')
        if value.get('version') != 1 or value.get('source_id') not in sources:
            raise ValueError('Collection attempt has no registered source')
        day = date.fromisoformat(value['date'])
        if day < date.fromisoformat(sources[value['source_id']]['since']):
            raise ValueError('Collection attempt precedes the registered scope')
        provenance(value['editor'])
        gaps = value.get('coverage_gaps')
        if not isinstance(gaps, list) or any(not isinstance(x, str) for x in gaps):
            raise ValueError('Invalid collection gaps')
        for field in ('files_examined', 'visible_messages', 'saved_messages', 'skipped_suppressed'):
            count = value.get(field)
            if not isinstance(count, int) or isinstance(count, bool) or count < 0:
                raise ValueError('Invalid collection count')
        if value.get('status') not in ('partial', 'collected'):
            raise ValueError('Invalid collection status')
        if value.get('status') != ('partial' if value.get('coverage_gaps') else 'collected'):
            raise ValueError('Collection status disagrees with gaps')
        stamp = datetime.fromisoformat(value['collected_at'])
        if stamp.tzinfo is None:
            raise ValueError('Collection time needs an offset')
        key = (value['source_id'], day)
        if key not in attempts or stamp > attempts[key][0]:
            attempts[key] = (stamp, value)
    rows = []
    for source_id, source in sorted(sources.items()):
        first = date.fromisoformat(source['since'])
        missing, partial, overlap = [], [], []
        for n in range(max(0, (end - first).days + 1)):
            day = first + timedelta(days=n)
            last = attempts.get((source_id, day))
            if not last:
                missing.append(day.isoformat())
            elif last[1]['status'] == 'partial':
                partial.append({'date': day.isoformat(), 'gaps': last[1]['coverage_gaps']})
            elif overlap_days and day > end - timedelta(days=overlap_days):
                overlap.append(day.isoformat())
        rows.append({'source_id': source_id, 'kind': source['kind'], 'since': source['since'],
                     'missing_days': missing, 'partial_days': partial, 'overlap_days': overlap,
                     'next_dates': sorted(set(missing + [x['date'] for x in partial] + overlap))})
    return {'through': end.isoformat(), 'timezone': str(zone), 'registered_sources': len(rows),
            'sources': rows, 'coverage': 'Declared source inventories only; no sources means coverage is unknown'}


def main():
    cli_encoding()
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    add = sub.add_parser('register')
    add.add_argument('--vault', required=True)
    add.add_argument('--source-id', required=True)
    add.add_argument('--kind', choices=('codex', 'claude', 'manual'), required=True)
    add.add_argument('--since', required=True)
    add.add_argument('--editor', required=True)
    add.add_argument('--apply', action='store_true')
    report = sub.add_parser('pending')
    report.add_argument('--vault', required=True)
    report.add_argument('--through')
    report.add_argument('--overlap-days', type=int, default=1)
    save = sub.add_parser('record', help='Record an agent-verified inventory of a declared source')
    save.add_argument('--vault', required=True)
    save.add_argument('--source-id', required=True)
    save.add_argument('--date', required=True)
    save.add_argument('--report', required=True)
    save.add_argument('--editor', required=True)
    args = parser.parse_args()
    try:
        root = safe_path(args.vault)
        if args.command == 'register':
            result = register(root, args.source_id, args.kind, args.since,
                              json.loads(Path(args.editor).read_text(encoding='utf-8')), args.apply)
        elif args.command == 'pending':
            result = pending(root, args.through, args.overlap_days)
        else:
            result = record(root, args.source_id, args.date,
                            json.loads(Path(args.report).read_text(encoding='utf-8')),
                            json.loads(Path(args.editor).read_text(encoding='utf-8')))
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f'Collection operation stopped: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
