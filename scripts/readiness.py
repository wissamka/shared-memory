#!/usr/bin/env python3
"""Inspect local readiness and attributable acceptance evidence; never schedule jobs."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys

import collection
import memory
from bootstrap import BEGIN, END
from common import cli_encoding, create_once, digest, encoded, provenance, safe_path, storage, timestamp, within
from install_skill import bundle

PACKAGE = Path(__file__).resolve().parents[1]
CHECKS = ('fresh_recall', 'daily_review', 'cloud_roundtrip', 'scheduler_enabled', 'scheduler_observed')
ERRORS = (ValueError, OSError, KeyError, TypeError)


def scheduling_mode(settings):
    mode = settings.get('scheduling_mode', 'daily')
    if mode not in ('daily', 'manual'):
        raise ValueError('Configured scheduling_mode must be daily or manual')
    return mode


def configuration_fingerprint(root):
    """Fingerprint configuration, declared scopes and canonical procedure, not knowledge edits."""
    memory.config(root)
    names = ['.memory-state/config.json', 'rules.md', 'Automation/Sources.md', 'Automation/Schedule.md']
    for folder in ('.memory-state/bindings', '.memory-state/collection/sources'):
        names.extend(p.relative_to(root).as_posix() for p in within(root, folder).glob('*.json'))
    hashes = {}
    for name in sorted(names):
        path = within(root, name)
        hashes[name] = digest(path.read_bytes()) if path.is_file() else None
    canonical = within(root, 'Procedures/shared-memory')
    if (canonical / 'skill-files.json').is_file():
        hashes['canonical_procedure'] = {p: digest(data) for p, data in bundle(canonical).items()}
    else:
        hashes['canonical_procedure'] = None
    return digest(encoded(hashes))


def record_check(root, check, outcome, evidence, checked_at, editor, apply=False):
    """Record a human/agent observation. This helper does not perform the claimed test."""
    if check not in CHECKS or outcome not in ('passed', 'failed'):
        raise ValueError('Choose a supported acceptance check and passed/failed outcome')
    if not isinstance(evidence, str) or not evidence.strip():
        raise ValueError('Describe the actual observed result and its evidence reference')
    provenance(editor)
    observed = timestamp(checked_at)
    if observed > datetime.now(timezone.utc):
        raise ValueError('An observed check cannot be dated in the future')
    settings = memory.config(root)
    mode = scheduling_mode(settings)
    if check in ('scheduler_enabled', 'scheduler_observed') and mode == 'manual':
        raise ValueError('Scheduler acceptance checks are not applicable to manual review mode')
    if check == 'cloud_roundtrip' and storage(settings)['provider'] == 'local':
        raise ValueError('Cloud round trip is not applicable to local-only storage')
    entry = {'version': 1, 'check': check, 'outcome': outcome, 'evidence': evidence,
             'checked_at': checked_at, 'editor': editor,
             'configuration_sha256': configuration_fingerprint(root)}
    path = within(root, f'.memory-state/readiness/checks/{digest(encoded(entry))}.json')
    if apply:
        create_once(path, encoded(entry))
    return {'mode': 'recorded' if apply else 'preview', 'receipt': str(path), 'check': entry,
            'verification': 'Agent-recorded evidence; this helper did not execute the acceptance test'}


def check_evidence(root, fingerprint, provider, mode='daily'):
    if mode not in ('daily', 'manual'):
        raise ValueError('Configured scheduling_mode must be daily or manual')
    entries, invalid = [], []
    for path in sorted(within(root, '.memory-state/readiness/checks').glob('*.json')):
        try:
            value = json.loads(safe_path(path).read_text(encoding='utf-8'))
            if (not isinstance(value, dict) or digest(encoded(value)) != path.stem
                    or value.get('version') != 1 or value.get('check') not in CHECKS
                    or value.get('outcome') not in ('passed', 'failed')
                    or not isinstance(value.get('evidence'), str) or not value['evidence'].strip()
                    or not memory.valid_hash(value.get('configuration_sha256'))):
                raise ValueError('Invalid or changed acceptance receipt')
            provenance(value.get('editor'))
            if timestamp(value['checked_at']) > datetime.now(timezone.utc):
                raise ValueError('Acceptance receipt has a future observation time')
            entries.append(value)
        except ERRORS as exc:
            invalid.append({'path': path.relative_to(root).as_posix(), 'error': str(exc)})
    checks = {}
    for check in CHECKS:
        if check in ('scheduler_enabled', 'scheduler_observed') and mode == 'manual':
            checks[check] = {'state': 'not_applicable', 'reason': 'Manual review mode explicitly configured'}
            continue
        if check == 'cloud_roundtrip' and provider == 'local':
            checks[check] = {'state': 'not_applicable', 'reason': 'Local-only storage selected'}
            continue
        candidates = [x for x in entries if x['check'] == check]
        current = [x for x in candidates if x['configuration_sha256'] == fingerprint]
        if not current:
            checks[check] = {'state': 'stale' if candidates else 'unverified',
                             'reason': 'Configuration changed; repeat this check' if candidates else 'No acceptance evidence recorded'}
            continue
        current.sort(key=lambda x: timestamp(x['checked_at']), reverse=True)
        latest = current[0]
        peers = [x for x in current if timestamp(x['checked_at']) == timestamp(latest['checked_at'])]
        state = 'conflicting' if len({x['outcome'] for x in peers}) > 1 else 'recorded_' + latest['outcome']
        checks[check] = {'state': state, 'checked_at': latest['checked_at'], 'evidence': latest['evidence'],
                         'editor': latest['editor'], 'basis': 'Agent observation; not a live automated retest'}
    return {'checks': checks, 'invalid_receipts': invalid}


def inspect_bindings(root):
    rows = []
    for path in sorted(within(root, '.memory-state/bindings').glob('*.json')):
        row = {'receipt': path.relative_to(root).as_posix()}
        try:
            value = json.loads(safe_path(path).read_text(encoding='utf-8'))
            if (not isinstance(value, dict) or value.get('version') != 1 or value.get('status') != 'connected'
                    or not isinstance(value.get('target_path'), str) or not value['target_path']
                    or not isinstance(value.get('vault_path'), str) or not value['vault_path']
                    or digest(value['target_path'].encode()) != path.stem
                    or not memory.valid_hash(value.get('block_sha256'))):
                raise ValueError('Invalid connection receipt')
            provenance(value.get('editor'))
            row.update(target=value['target_path'], kind=value.get('kind'))
            target = Path(value['target_path'])
            if not target.is_absolute() or not target.is_file():
                row.update(state='unverified', reason='Target unavailable on this device; check its owning device')
            elif safe_path(value['vault_path']) != root:
                row.update(state='unverified', reason='Receipt belongs to a different device-local vault path')
            else:
                raw = safe_path(target).read_bytes()
                if raw.count(BEGIN.encode()) != 1 or raw.count(END.encode()) != 1:
                    row.update(state='drifted', reason='Managed block missing, partial or duplicated')
                else:
                    start = raw.index(BEGIN.encode())
                    end = raw.index(END.encode()) + len(END.encode())
                    if raw[end:end + 1] == b'\n':
                        end += 1
                    matches = end > start and digest(raw[start:end]) == value['block_sha256']
                    row.update(state='block_verified' if matches else 'drifted',
                               reason='Managed block matches receipt; fresh-agent loading still needs a test' if matches
                               else 'Managed block differs from recorded connection')
        except PermissionError:
            row.update(state='unverified', reason='Target or receipt is inaccessible on this device')
        except ERRORS as exc:
            row.update(state='invalid', reason=str(exc))
        rows.append(row)
    return {'state': 'unverified' if not rows else 'inspected', 'bindings': rows,
            'instruction_loading': 'File integrity does not establish actual harness instruction loading'}


def inspect_procedure(root, package):
    canonical = within(root, 'Procedures/shared-memory')
    if not (canonical / 'skill-files.json').is_file():
        return {'state': 'unverified', 'reason': 'Canonical manifest missing; inspect legacy or incomplete installation'}
    current, installed = bundle(package), bundle(canonical)
    package_version = json.loads(current['skill-files.json']).get('version')
    canonical_version = json.loads(installed['skill-files.json']).get('version')
    differences = sorted(p for p in current.keys() | installed.keys() if current.get(p) != installed.get(p))
    return {'state': 'matches_local_package' if not differences else 'version_differs' if package_version != canonical_version else 'content_differs',
            'local_package_version': package_version, 'canonical_version': canonical_version,
            'different_files': differences, 'remote_latest': 'not_checked'}


def report(root, through=None, package=PACKAGE):
    """Best-effort read-only snapshot. A healthy scaffold is never called ready."""
    root, package = safe_path(root), safe_path(package)
    settings = memory.config(root)
    provider = storage(settings)['provider']
    mode = scheduling_mode(settings)
    results = {'version': 1, 'vault': str(root), 'checked_at': datetime.now(timezone.utc).isoformat(),
               'snapshot': 'Read-only local inspection; concurrent writers may change it after inspection'}
    for name, action in (
            ('memory', lambda: memory.status(root, read_only=True)),
            ('collection', lambda: collection.pending(root, through)),
            ('connections', lambda: inspect_bindings(root)),
            ('procedure', lambda: inspect_procedure(root, package))):
        try:
            results[name] = action()
        except ERRORS as exc:
            results[name] = {'state': 'blocked', 'error': str(exc)}
    schedule = within(root, 'Automation/Schedule.md')
    try:
        text = schedule.read_text(encoding='utf-8')
        declared = re.search(r'(?im)^State:\s*\*\*([^*]+)\*\*', text)
        results['schedule'] = {'configured_mode': mode, 'declared_state': declared.group(1).strip() if declared else 'unknown',
                               'basis': 'Informational prose only; acceptance receipts distinguish enabled from observed execution'}
    except ERRORS as exc:
        results['schedule'] = {'configured_mode': mode, 'declared_state': 'unknown', 'error': str(exc)}
    try:
        fingerprint = configuration_fingerprint(root)
        results['configuration_sha256'] = fingerprint
        results['acceptance'] = check_evidence(root, fingerprint, provider, mode)
    except ERRORS as exc:
        results['acceptance'] = {'state': 'blocked', 'error': str(exc)}
    actions = []
    for name in ('memory', 'collection', 'connections', 'procedure', 'acceptance'):
        if results[name].get('state') == 'blocked':
            actions.append({'component': name, 'action': 'Resolve the reported inspection error; preserve existing evidence'})
    state = results['memory']
    if state.get('invalid_inputs') or state.get('suppressed_inputs'):
        actions.append({'component': 'memory', 'action': 'Review invalid inputs or finish authorized suppression cleanup'})
    if state.get('pending', 0):
        actions.append({'component': 'memory', 'action': 'Review pending captures without assuming complete session coverage'})
    state = results['collection']
    if state.get('registered_sources') == 0:
        actions.append({'component': 'collection', 'action': 'Register authorized sources; zero registered sources leaves coverage unknown'})
    if any(x['missing_days'] or x['partial_days'] for x in state.get('sources', [])):
        actions.append({'component': 'collection', 'action': 'Collect missing days and retry partial inventories before claiming coverage'})
    state = results['connections']
    if state.get('state') == 'unverified' or any(x['state'] != 'block_verified' for x in state.get('bindings', [])):
        actions.append({'component': 'connections', 'action': 'Verify bindings on their owning devices; inspect local drift without overwriting other instructions'})
    if results['procedure'].get('state') not in ('matches_local_package', 'blocked'):
        actions.append({'component': 'procedure', 'action': 'Compare the canonical procedure with this local package; preserve customizations'})
    state = results['acceptance']
    if state.get('invalid_receipts'):
        actions.append({'component': 'acceptance', 'action': 'Inspect changed or malformed acceptance receipts'})
    for name, check in state.get('checks', {}).items():
        if check['state'] not in ('recorded_passed', 'not_applicable'):
            actions.append({'component': name, 'action': 'Perform or repeat this acceptance check and record its actual observed result'})
    results['next_actions'] = actions
    results['overall_state'] = 'attention_required' if actions else 'evidence_recorded'
    results['conclusion'] = 'Review the component states and dated evidence; this report does not certify production readiness'
    return results


def main():
    cli_encoding()
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    inspect = sub.add_parser('report', help='Read-only local status and evidence')
    inspect.add_argument('--vault', required=True)
    inspect.add_argument('--through', help='Last completed collection day to inspect')
    record = sub.add_parser('record-check', help='Record an actually observed acceptance result')
    record.add_argument('--vault', required=True)
    record.add_argument('--check', choices=CHECKS, required=True)
    record.add_argument('--outcome', choices=('passed', 'failed'), required=True)
    record.add_argument('--evidence', required=True)
    record.add_argument('--checked-at', required=True)
    record.add_argument('--editor', required=True)
    record.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    try:
        root = safe_path(args.vault)
        if args.command == 'report':
            result = report(root, args.through)
        else:
            result = record_check(root, args.check, args.outcome, args.evidence, args.checked_at,
                                  json.loads(Path(args.editor).read_text(encoding='utf-8')), args.apply)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except ERRORS as exc:
        print(f'Readiness inspection stopped: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
