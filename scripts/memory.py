#!/usr/bin/env python3
"""Capture sourced memory and keep verifiable per-input review receipts."""
import argparse
from datetime import date, datetime, time, timedelta, timezone
import json
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

from common import create_once, digest, encoded, note, provenance, safe_path, timestamp, within


def config(root):
    return json.loads(within(root, '.memory-state/config.json').read_text(encoding="utf-8"))


def capture(root, data):
    config(root)
    for key in ('source_id', 'source_date', 'session_id', 'harness', 'assistant', 'model',
                'agent', 'chat_reference', 'title', 'text', 'status'):
        if not isinstance(data.get(key), str) or not data[key].strip():
            raise ValueError(f'Missing capture field: {key}')
    if data['status'] not in ('confirmed', 'reported', 'proposed', 'inferred', 'superseded', 'unresolved'):
        raise ValueError('Unsupported claim status')
    timestamp(data['source_date'])
    provenance(data['captured_by'])
    if data['model'] == 'unknown' and not data.get('model_note'):
        raise ValueError('Unknown source model needs model_note')
    identity = digest(data['source_id'].encode())
    path = within(root, f'_Inbox/{identity}.json')
    if path.exists():
        prior = json.loads(path.read_text(encoding="utf-8"))
        # A repeat capture by another editor is still the same source evidence.
        old = {k: v for k, v in prior.items() if k not in ('captured_at', 'captured_by')}
        new = {k: v for k, v in data.items() if k not in ('captured_at', 'captured_by')}
        if old != new:
            raise ValueError('Source ID already has different evidence; use a new correction ID')
        saved = prior
    else:
        saved = {**data, 'captured_at': datetime.now(timezone.utc).isoformat(timespec='seconds')}
        create_once(path, encoded(saved))
    # Also repairs an interrupted capture whose JSON was saved but note was not.
    source_note = within(root, f'Sessions/{identity}.md')
    body = (f'# {saved["title"]}\n\nSource ID: `{saved["source_id"]}`\n\n'
            f'Source event: {saved["source_date"]}; status: {saved["status"]}.\n\n'
            f'Source session: `{saved["session_id"]}`; assistant: {saved["assistant"]}; '
            f'harness: {saved["harness"]}; model: {saved["model"]}; agent: {saved["agent"]}.\n\n'
            f'Conversation reference: {saved["chat_reference"]}. '
            f'Coverage: {saved.get("coverage", "Selected evidence; not a complete session")}.\n\n'
            f'{saved["text"]}\n\n[Capture](../_Inbox/{identity}.json) · [Sessions](Overview.md)\n')
    create_once(source_note, note(body, 'source', saved['title'], saved['captured_by'], saved['captured_at']))
    return {'input_id': identity, 'capture': str(path), 'session_note': str(source_note)}


def reviewed(root):
    result = set()
    for path in sorted(within(root, '.memory-state/receipts').glob('*.json')):
        doc = json.loads(safe_path(path).read_text(encoding="utf-8"))
        result.update(item['input_id'] for item in doc['results'])
    return result


def prepare(root, day=None):
    zone = ZoneInfo(config(root)['timezone'])
    target = date.fromisoformat(day) if day else datetime.now(zone).date() - timedelta(days=1)
    start = datetime.combine(target, time.min, zone)
    end = datetime.combine(target + timedelta(days=1), time.min, zone)
    done = reviewed(root)
    inputs = []
    for path in sorted(within(root, '_Inbox').glob('*.json')):
        raw = safe_path(path).read_bytes()
        source = json.loads(raw)
        if timestamp(source['source_date']) < end and path.stem not in done:
            inputs.append({'input_id': path.stem, 'path': path.relative_to(root).as_posix(),
                           'sha256': digest(raw), 'source_id': source['source_id'],
                           'source_date': source['source_date']})
    manifest = {'version': 1, 'date': target.isoformat(), 'timezone': str(zone),
                'window_start': start.isoformat(), 'window_end': end.isoformat(),
                'inputs': inputs, 'coverage': 'Persisted captures only; verify authorized source inventory separately'}
    run_id = digest(encoded(manifest))
    manifest['run_id'] = run_id
    path = within(root, f'.memory-state/runs/{run_id}.json')
    create_once(path, encoded(manifest))
    return manifest


def complete(root, receipt):
    provenance(receipt.get('editor'))
    run_id = receipt.get('run_id', '')
    if len(run_id) != 64 or any(ch not in '0123456789abcdef' for ch in run_id):
        raise ValueError('Invalid run ID')
    manifest = json.loads(within(root, f'.memory-state/runs/{run_id}.json').read_text(encoding="utf-8"))
    expected = {item['input_id']: item for item in manifest['inputs']}
    results = receipt.get('results', [])
    if not isinstance(results, list) or any(not isinstance(x, dict) for x in results):
        raise ValueError('results must be a list of objects')
    ids = [item.get('input_id') for item in results]
    if len(set(ids)) != len(ids) or set(ids) != set(expected):
        raise ValueError('Receipt must account for every manifest input exactly once; unfinished work stays pending')
    gaps = receipt.get('coverage_gaps')
    if not isinstance(gaps, list) or any(not isinstance(x, str) for x in gaps):
        raise ValueError('coverage_gaps must be an explicit list')
    for result in results:
        item = expected[result['input_id']]
        if digest(within(root, item['path']).read_bytes()) != item['sha256']:
            raise ValueError('Input changed or disappeared; review again')
        if result.get('outcome') not in ('promoted', 'no_change') or not isinstance(result.get('reason'), str) or not result['reason'].strip():
            raise ValueError('Each input needs a successful outcome and reason')
        destinations = result.get('destinations', [])
        if not isinstance(destinations, list):
            raise ValueError('destinations must be a list')
        if result['outcome'] == 'promoted' and not destinations:
            raise ValueError('Promoted inputs need verified destinations')
        for destination in destinations:
            path = within(root, destination['path'])
            if path.suffix != '.md' or digest(path.read_bytes()) != destination['sha256']:
                raise ValueError('Destination missing or changed; read back before checkpointing')
    saved = {**receipt, 'status': 'partial' if gaps else 'reviewed',
             'date': manifest['date'], 'coverage': manifest['coverage']}
    path = within(root, f'.memory-state/receipts/{run_id}.json')
    if path.exists():
        prior = json.loads(path.read_text(encoding="utf-8"))
        if {k: v for k, v in prior.items() if k != 'completed_at'} != saved:
            raise ValueError('Receipt already exists with different results; preserve history')
        return prior
    saved['completed_at'] = datetime.now(timezone.utc).isoformat(timespec='seconds')
    create_once(path, encoded(saved))
    return saved


def status(root):
    done = reviewed(root)
    all_inputs = {p.stem for p in within(root, '_Inbox').glob('*.json')}
    return {'captured': len(all_inputs), 'reviewed': len(all_inputs & done),
            'pending': len(all_inputs - done), 'coverage': 'Persisted captures only'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ('capture', 'prepare', 'complete', 'status'):
        cmd = sub.add_parser(name)
        cmd.add_argument('--vault', required=True)
        if name == 'capture':
            cmd.add_argument('--input', required=True)
        elif name == 'prepare':
            cmd.add_argument('--date')
        elif name == 'complete':
            cmd.add_argument('--receipt', required=True)
    args = parser.parse_args()
    try:
        root = safe_path(args.vault)
        if args.command == 'capture':
            output = capture(root, json.loads(Path(args.input).read_text(encoding="utf-8")))
        elif args.command == 'prepare':
            output = prepare(root, args.date)
        elif args.command == 'complete':
            output = complete(root, json.loads(Path(args.receipt).read_text(encoding="utf-8")))
        else:
            output = status(root)
        print(json.dumps(output, indent=2, ensure_ascii=False))
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f'Memory operation failed; no review checkpoint advanced: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
