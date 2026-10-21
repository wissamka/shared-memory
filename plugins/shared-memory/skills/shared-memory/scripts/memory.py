#!/usr/bin/env python3
"""Capture sourced memory and keep verifiable per-input review receipts."""
import argparse
from contextlib import nullcontext
from datetime import date, datetime, time, timedelta, timezone
import json
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

from common import cli_encoding, create_once, digest, encoded, note, provenance, safe_path, timestamp, within
import suppression
from suppression import is_suppressed, state_lock


def config(root):
    value = json.loads(within(root, '.memory-state/config.json').read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get('version') != 1 or not isinstance(value.get('timezone'), str):
        raise ValueError('Invalid vault configuration')
    ZoneInfo(value['timezone'])
    return value


def validate_capture(data):
    if not isinstance(data, dict):
        raise ValueError('Capture must be an object')
    for key in ('source_id', 'source_date', 'session_id', 'harness', 'assistant', 'model',
                'agent', 'chat_reference', 'title', 'text', 'status'):
        if not isinstance(data.get(key), str) or not data[key].strip():
            raise ValueError(f'Missing capture field: {key}')
    if data['status'] not in ('confirmed', 'reported', 'proposed', 'inferred', 'superseded', 'unresolved'):
        raise ValueError('Unsupported claim status')
    timestamp(data['source_date'])
    provenance(data['captured_by'])
    provenance(data)
    if 'captured_at' in data:
        timestamp(data['captured_at'])
    return data


def load_capture(root, path):
    raw = safe_path(path).read_bytes()
    data = validate_capture(json.loads(raw))
    if digest(data['source_id'].encode()) != path.stem:
        raise ValueError('Invalid captured source identity')
    return data, raw


def capture(root, data):
    config(root)
    validate_capture(data)
    with state_lock(root):
        if is_suppressed(root, data):
            return {'status': 'suppressed', 'input_id': digest(data['source_id'].encode())}
        return _capture(root, data)


def _capture(root, data):
    identity = digest(data['source_id'].encode())
    path = within(root, f'_Inbox/{identity}.json')
    if path.exists():
        prior = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(prior, dict):
            raise ValueError('Invalid existing capture; preserve and inspect it')
        # A repeat capture by another editor is still the same source evidence.
        old = {k: v for k, v in prior.items() if k not in ('captured_at', 'captured_by', 'source_locator')}
        new = {k: v for k, v in data.items() if k not in ('captured_at', 'captured_by', 'source_locator')}
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
            f'Source locator: {saved.get("source_locator", "not supplied")}. '
            f'As of: {saved.get("as_of", "not supplied")}. '
            f'Model note: {saved.get("model_note", "not supplied")}.\n\n'
            f'{saved["text"]}\n\n[Capture](../_Inbox/{identity}.json) · [Sessions](Overview.md)\n')
    create_once(source_note, note(body, 'source', saved['title'], saved['captured_by'], saved['captured_at']))
    return {'input_id': identity, 'capture': str(path), 'session_note': str(source_note)}


def valid_hash(value):
    return isinstance(value, str) and len(value) == 64 and all(ch in '0123456789abcdef' for ch in value)


def load_manifest(root, run_id):
    if not valid_hash(run_id):
        raise ValueError('Invalid run ID')
    doc = json.loads(within(root, f'.memory-state/runs/{run_id}.json').read_text(encoding='utf-8'))
    if (not isinstance(doc, dict) or doc.get('version') != 1 or doc.get('run_id') != run_id
            or digest(encoded({k: v for k, v in doc.items() if k != 'run_id'})) != run_id):
        raise ValueError('Review manifest changed; restore evidence or prepare a new review')
    if not isinstance(doc.get('inputs'), list):
        raise ValueError('Invalid manifest inputs')
    seen = set()
    for item in doc['inputs']:
        if not isinstance(item, dict) or not isinstance(item.get('source_id'), str):
            raise ValueError('Invalid manifest input')
        key = item['input_id']
        if (not valid_hash(key) or key in seen or not valid_hash(item['sha256'])
                or key != digest(item['source_id'].encode()) or item['path'] != f'_Inbox/{key}.json'):
            raise ValueError('Invalid manifest input')
        seen.add(key)
    return doc


def validate_results(root, receipt, manifest, destinations=False):
    provenance(receipt.get('editor'))
    expected = {item['input_id']: item for item in manifest['inputs']}
    results = receipt.get('results', [])
    if not isinstance(results, list) or any(not isinstance(x, dict) for x in results):
        raise ValueError('results must be a list of objects')
    ids = [item.get('input_id') for item in results]
    if any(not valid_hash(key) for key in ids) or len(set(ids)) != len(ids) or set(ids) != set(expected):
        raise ValueError('Receipt must account for every manifest input exactly once; unfinished work stays pending')
    gaps = receipt.get('coverage_gaps')
    if not isinstance(gaps, list) or any(not isinstance(x, str) for x in gaps):
        raise ValueError('coverage_gaps must be an explicit list')
    for result in results:
        item = expected[result['input_id']]
        if digest(within(root, item['path']).read_bytes()) != item['sha256']:
            raise ValueError('Input changed or disappeared; review again')
        if result.get('outcome') not in ('promoted', 'no_change', 'deferred') or not isinstance(result.get('reason'), str) or not result['reason'].strip():
            raise ValueError('Each input needs a supported outcome and reason')
        targets = result.get('destinations', [])
        if not isinstance(targets, list) or any(not isinstance(x, dict) for x in targets):
            raise ValueError('destinations must be a list of objects')
        if result['outcome'] == 'promoted' and not targets:
            raise ValueError('Promoted inputs need verified destinations')
        if result['outcome'] == 'deferred' and targets:
            raise ValueError('Deferred inputs cannot claim verified destinations')
        for destination in targets:
            path = within(root, destination['path'])
            if path.suffix != '.md' or not valid_hash(destination.get('sha256')):
                raise ValueError('Invalid destination path or hash')
            if destinations and digest(path.read_bytes()) != destination['sha256']:
                raise ValueError('Destination missing or changed; read back before checkpointing')


def receipt_status(receipt):
    return 'partial' if receipt['coverage_gaps'] or any(x['outcome'] == 'deferred' for x in receipt['results']) else 'reviewed'


def reviewed(root):
    result = set()
    for path in sorted(within(root, '.memory-state/receipts').glob('*.json')):
        doc = json.loads(safe_path(path).read_text(encoding="utf-8"))
        if not isinstance(doc, dict) or doc.get('run_id') != path.stem:
            raise ValueError('Invalid saved receipt')
        manifest = load_manifest(root, path.stem)
        validate_results(root, doc, manifest)
        if doc.get('status') != receipt_status(doc):
            raise ValueError('Invalid receipt status')
        result.update(item['input_id'] for item in doc['results'] if item['outcome'] != 'deferred')
    return result


def prepare(root, day=None):
    config(root)
    with state_lock(root):
        return _prepare(root, day)


def _prepare(root, day=None):
    suppression.entries(root)
    zone = ZoneInfo(config(root)['timezone'])
    target = date.fromisoformat(day) if day else datetime.now(zone).date() - timedelta(days=1)
    start = datetime.combine(target, time.min, zone)
    end = datetime.combine(target + timedelta(days=1), time.min, zone)
    done = reviewed(root)
    inputs = []
    for path in sorted(within(root, '_Inbox').glob('*.json')):
        source, raw = load_capture(root, path)
        if is_suppressed(root, source):
            continue
        if timestamp(source['source_date']) < end and path.stem not in done:
            inputs.append({'input_id': path.stem, 'path': path.relative_to(root).as_posix(),
                           'sha256': digest(raw), 'source_id': source['source_id'],
                           'source_date': source['source_date']})
    manifest = {'version': 1, 'date': target.isoformat(), 'timezone': str(zone),
                'window_start': start.isoformat(), 'window_end': end.isoformat(),
                'inputs': inputs, 'coverage': 'Persisted captures only; verify authorized source inventory separately'}
    pending_ids = {item['input_id'] for item in inputs}
    retry_after = []
    for path in sorted(within(root, '.memory-state/receipts').glob('*.json')):
        receipt = json.loads(safe_path(path).read_text(encoding='utf-8'))
        if any(item['outcome'] == 'deferred' and item['input_id'] in pending_ids for item in receipt['results']):
            retry_after.append(path.stem)
    if retry_after:
        # All-deferred work can be retried on the same day without changing an
        # immutable receipt. Prepare remains deterministic until another attempt
        # is checkpointed; earlier successful inputs are already excluded above.
        manifest['retry_after'] = retry_after
    run_id = digest(encoded(manifest))
    manifest['run_id'] = run_id
    path = within(root, f'.memory-state/runs/{run_id}.json')
    create_once(path, encoded(manifest))
    return manifest


def complete(root, receipt):
    config(root)
    with state_lock(root):
        return _complete(root, receipt)


def _complete(root, receipt):
    if not isinstance(receipt, dict):
        raise ValueError('Receipt must be an object')
    run_id = receipt.get('run_id', '')
    manifest = load_manifest(root, run_id)
    validate_results(root, receipt, manifest)
    for item in manifest['inputs']:
        source, _ = load_capture(root, within(root, item['path']))
        if is_suppressed(root, source):
            raise ValueError('Review includes suppressed evidence; finish forgetting and prepare a new review')
    saved = {k: v for k, v in receipt.items() if k != 'completed_at'}
    saved.update({'status': receipt_status(receipt),
                  'date': manifest['date'], 'coverage': manifest['coverage']})
    path = within(root, f'.memory-state/receipts/{run_id}.json')
    if path.exists():
        prior = json.loads(path.read_text(encoding="utf-8"))
        if {k: v for k, v in prior.items() if k != 'completed_at'} != saved:
            raise ValueError('Receipt already exists with different results; preserve history')
        return prior
    if reviewed(root) & {item['input_id'] for item in manifest['inputs']}:
        raise ValueError('Stale review overlaps a completed run; reconcile notes and prepare a new review')
    validate_results(root, receipt, manifest, destinations=True)
    saved['completed_at'] = datetime.now(timezone.utc).isoformat(timespec='seconds')
    create_once(path, encoded(saved))
    return saved


def status(root, read_only=False):
    """Inspect captures; read_only is a best-effort snapshot without creating a lock."""
    config(root)
    with nullcontext() if read_only else state_lock(root):
        suppression.entries(root)
        done = reviewed(root)
        all_inputs, suppressed, invalid = set(), [], []
        for path in sorted(within(root, '_Inbox').glob('*.json')):
            try:
                source, _ = load_capture(root, path)
            except (ValueError, OSError, KeyError, TypeError) as exc:
                invalid.append({'path': path.relative_to(root).as_posix(), 'error': str(exc)})
                continue
            if is_suppressed(root, source):
                suppressed.append(path.relative_to(root).as_posix())
            else:
                all_inputs.add(path.stem)
        return {'captured': len(all_inputs), 'reviewed': len(all_inputs & done),
                'pending': len(all_inputs - done), 'coverage': 'Persisted captures only',
                'invalid_inputs': invalid, 'suppressed_inputs': suppressed,
                'healthy': not invalid and not suppressed}


def _forget_plan(root, selected):
    suppression.entries(root)  # Corrupt suppression state must not be bypassed.
    inputs, runs = suppression.cleanup_history(root, selected)
    if selected['scope'] == 'source':
        inputs.add(selected['source_hash'])
    for path in sorted(within(root, '_Inbox').glob('*.json')):
        source, _ = load_capture(root, path)
        if suppression.matches(selected, source):
            inputs.add(path.stem)
    for path in sorted(within(root, '.memory-state/runs').glob('*.json')):
        manifest = load_manifest(root, path.stem)
        if inputs & {item['input_id'] for item in manifest['inputs']}:
            runs.add(path.stem)
    notes = set()
    for path in sorted(within(root, '.memory-state/receipts').glob('*.json')):
        doc = json.loads(safe_path(path).read_text(encoding='utf-8'))
        if (not isinstance(doc, dict) or not valid_hash(path.stem) or doc.get('run_id') != path.stem
                or not isinstance(doc.get('results'), list)):
            raise ValueError('Invalid receipt; inspect before forgetting')
        for item in doc['results']:
            if not isinstance(item, dict) or not valid_hash(item.get('input_id')):
                raise ValueError('Invalid receipt result; inspect before forgetting')
            if item['input_id'] in inputs:
                runs.add(path.stem)
                for destination in item.get('destinations', []):
                    path_in_vault = within(root, destination['path'])
                    notes.add(path_in_vault.relative_to(root).as_posix())
    # Remove receipts before source files so interruption never leaves a receipt
    # that points at a capture this operation has already deleted.
    paths = ([f'.memory-state/receipts/{key}.json' for key in sorted(runs)]
             + [f'.memory-state/runs/{key}.json' for key in sorted(runs)]
             + [f'Sessions/{key}.md' for key in sorted(inputs)]
             + [f'_Inbox/{key}.json' for key in sorted(inputs)])
    files = []
    for relative in paths:
        path = within(root, relative)
        if path.exists():
            if not path.is_file():
                raise ValueError('Expected a file in forgetting scope')
            files.append({'path': relative, 'sha256': digest(path.read_bytes())})
    return {'suppression': selected, 'input_ids': sorted(inputs), 'run_ids': sorted(runs),
            'files': files, 'maintained_notes_require_review': True, 'notes_to_review': sorted(notes),
            'limitations': 'Maintained notes, indexes, logs, external histories and backups need separate scoped review; '
                          'removing a mixed review receipt makes its other inputs pending again.'}


def forget(root, editor, source_id=None, session_id=None, harness=None, apply=False):
    """Preview or suppress then remove only identified evidence and bookkeeping.

    An explicit owner instruction authorizes --apply; this helper does not decide
    what a natural-language forgetting request refers to or edit maintained prose.
    """
    config(root)
    provenance(editor)
    selected = suppression.selector(source_id, session_id, harness)
    if not apply:
        return {'mode': 'preview', **_forget_plan(root, selected)}
    with state_lock(root):
        plan = _forget_plan(root, selected)
        suppression.save(root, selected, editor)
        suppression.save_cleanup(root, selected, plan['input_ids'], plan['run_ids'])
        removed = []
        for item in plan['files']:
            path = within(root, item['path'])
            if digest(path.read_bytes()) != item['sha256']:
                raise ValueError('Forgetting target changed; suppression remains active, inspect and retry')
            path.unlink()
            removed.append(item['path'])
        return {'mode': 'applied', **plan, 'removed': removed,
                'suppression_id': suppression.suppression_id(selected)}


def main():
    cli_encoding()
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ('capture', 'prepare', 'complete', 'status', 'forget'):
        cmd = sub.add_parser(name)
        cmd.add_argument('--vault', required=True)
        if name == 'capture':
            cmd.add_argument('--input', required=True)
        elif name == 'prepare':
            cmd.add_argument('--date')
        elif name == 'complete':
            cmd.add_argument('--receipt', required=True)
        elif name == 'forget':
            identities = cmd.add_mutually_exclusive_group(required=True)
            identities.add_argument('--source-id')
            identities.add_argument('--session-id')
            cmd.add_argument('--harness')
            cmd.add_argument('--editor', required=True)
            cmd.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    try:
        root = safe_path(args.vault)
        if args.command == 'capture':
            output = capture(root, json.loads(Path(args.input).read_text(encoding="utf-8")))
        elif args.command == 'prepare':
            output = prepare(root, args.date)
        elif args.command == 'complete':
            output = complete(root, json.loads(Path(args.receipt).read_text(encoding="utf-8")))
        elif args.command == 'forget':
            output = forget(root, json.loads(Path(args.editor).read_text(encoding='utf-8')),
                            args.source_id, args.session_id, args.harness, args.apply)
        else:
            output = status(root)
        print(json.dumps(output, indent=2, ensure_ascii=False))
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f'Memory operation failed; no review checkpoint advanced: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
