#!/usr/bin/env python3
"""Opt-in visible-chat archive and owner-approved writing examples; no training or network access."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

from common import (cli_encoding, contains_path, create_once, digest, distribution_roots,
                    encoded, note, provenance, safe_path, timestamp, within)
import suppression
from memory import config as knowledge_config

PACKAGE = Path(__file__).resolve().parents[1]
MARKER = '.voice-archive.json'
IDENTITIES = ('assistant', 'harness', 'model', 'agent', 'session_id', 'chat_reference', 'model_note')


def editor_fields(editor):
    provenance(editor)
    return {key: editor[key] for key in IDENTITIES if key in editor}


def separate(archive, vault):
    if any(contains_path(a, b) or contains_path(b, a) for a, b in [(archive, vault)]):
        raise ValueError('Chat archive and knowledge vault must be separate, non-overlapping directories')
    for package in distribution_roots(PACKAGE):
        if contains_path(package, archive) or contains_path(archive, package):
            raise ValueError('Keep private chat archives outside the distributable skill')


def known(value, field):
    if not isinstance(value, str) or not value.strip() or value.strip().casefold() in ('unknown', 'unavailable'):
        raise ValueError(f'{field} requires a known stable identifier')
    return value


def config(archive):
    archive = safe_path(archive)
    value = json.loads(within(archive, MARKER).read_text(encoding='utf-8'))
    if (not isinstance(value, dict) or value.get('version') != 1 or value.get('kind') != 'visible-chat-archive'
            or not isinstance(value.get('sources'), list) or not value['sources']
            or any(not isinstance(x, str) or not x.strip() for x in value['sources'])
            or len(set(value['sources'])) != len(value['sources'])):
        raise ValueError('Invalid visible-chat archive configuration')
    vault = safe_path(value['knowledge_vault'])
    separate(archive, vault)
    knowledge_config(vault)
    provenance(value['created_by'])
    timestamp(value['created_at'])
    return value


def setup(archive, vault, sources, editor, apply=False):
    archive, vault = safe_path(archive), safe_path(vault)
    separate(archive, vault)
    knowledge_config(vault)
    current_editor = editor_fields(editor)
    if (not isinstance(sources, list) or not sources or any(not isinstance(x, str) or not x.strip() for x in sources)
            or len(set(sources)) != len(sources)):
        raise ValueError('Choose explicit unique source labels for the authorized chat scope')
    desired = {'version': 1, 'kind': 'visible-chat-archive', 'knowledge_vault': str(vault), 'sources': sorted(sources)}
    marker = within(archive, MARKER)
    if marker.exists():
        existing = config(archive)
        if any(existing.get(key) != value for key, value in desired.items()):
            raise ValueError('Different archive configuration; preserve it and review integration')
        return {'mode': 'unchanged', 'archive': str(archive), 'sources': sources}
    if archive.exists() and (not archive.is_dir() or any(archive.iterdir())):
        raise ValueError('Unrecognized nonempty archive; preserve and integrate manually')
    if apply:
        create_once(marker, encoded({**desired, 'created_by': current_editor,
                                    'created_at': datetime.now(timezone.utc).isoformat(timespec='seconds')}))
    return {'mode': 'applied' if apply else 'preview', 'archive': str(archive), 'sources': sources,
            'coverage': 'Only explicitly submitted visible messages; no automatic or universal recording'}


def validate_message(data):
    fields = {'source', 'source_id', 'message_id', 'position', 'role', 'channel', 'source_date',
              'timestamp_note', 'text', 'coverage', 'redactions', 'reviewed_for_secrets', 'captured_by',
              'message_id_note', 'session_id_note', 'capture_message_id', 'capture_session_id', *IDENTITIES}
    if not isinstance(data, dict) or set(data) - fields:
        raise ValueError('Message contains unsupported fields; submit only visible conversation evidence')
    for key in ('source', 'source_id', 'harness'):
        known(data.get(key), key)
    for key in ('message_id', 'session_id'):
        if data.get(key) == 'unknown':
            known(data.get('capture_' + key), 'capture_' + key)
            explanation = data.get(key + '_note')
            if not isinstance(explanation, str) or not explanation.strip():
                raise ValueError(f'Unknown original {key} requires an explicit {key}_note')
        else:
            known(data.get(key), key)
            if 'capture_' + key in data:
                raise ValueError(f'Use the known original {key}; capture IDs are only for unavailable originals')
    if type(data.get('position')) is not int or data['position'] < 0:
        raise ValueError('position must be a stable nonnegative position in the source conversation')
    allowed = {'user': ('user',), 'assistant': ('final', 'commentary')}
    if data.get('role') not in allowed or data.get('channel') not in allowed[data['role']]:
        raise ValueError('Only visible user and assistant final/commentary messages may be archived')
    if data.get('source_date') == 'unknown':
        if not isinstance(data.get('timestamp_note'), str) or not data['timestamp_note'].strip():
            raise ValueError('Unknown timestamps require an explicit explanation')
    else:
        timestamp(data.get('source_date'))
    for key in ('text', 'coverage'):
        if not isinstance(data.get(key), str) or not data[key].strip():
            raise ValueError(f'{key} must be explicit nonempty text')
    if (not isinstance(data.get('redactions'), list)
            or any(not isinstance(x, str) for x in data['redactions']) or data.get('reviewed_for_secrets') is not True):
        raise ValueError('Review/redact secrets before capture and explicitly list redactions (possibly empty)')
    provenance(data)
    provenance(data.get('captured_by'))
    if set(data['captured_by']) - set(IDENTITIES):
        raise ValueError('Capture provenance must not contain extra payloads')
    if 'timestamp_note' in data and not isinstance(data['timestamp_note'], str):
        raise ValueError('timestamp_note must be text')
    return data


def message_key(data):
    # Repeated source/message IDs at different original positions stay distinct;
    # exact overlapping checkpoints retain the same key.
    def original_or_capture(key):
        return ['capture', data['capture_' + key]] if data[key] == 'unknown' else data[key]
    return digest(encoded([data['source'], data['harness'], original_or_capture('session_id'),
                           data['source_id'], original_or_capture('message_id'), data['position']]))


def record(archive, key):
    if not suppression.valid_hash(key):
        raise ValueError('Invalid archived message ID')
    value = json.loads(within(archive, f'Records/{key}.json').read_text(encoding='utf-8'))
    if not isinstance(value, dict) or value.get('version') != 1 or set(value) != {'version', 'message', 'captured_at'}:
        raise ValueError('Invalid archived message record')
    validate_message(value['message'])
    timestamp(value['captured_at'])
    if message_key(value['message']) != key:
        raise ValueError('Archived message identity changed')
    return value


def blocked(archive, data):
    # Existing external archive copies still need voice.forget explicitly.
    vault = safe_path(config(archive)['knowledge_vault'])
    return suppression.is_suppressed(archive, data) or suppression.is_suppressed(vault, data)


def capture(archive, data, apply=False):
    archive = safe_path(archive)
    settings = config(archive)
    validate_message(data)
    if data['source'] not in settings['sources']:
        raise ValueError('Source is outside the archive scope selected by the owner')
    key = message_key(data)
    if blocked(archive, data):
        return {'mode': 'suppressed', 'message_key': key}
    if not apply:
        return {'mode': 'preview', 'message_key': key, 'coverage': data['coverage']}
    with suppression.state_lock(archive):
        if blocked(archive, data):
            return {'mode': 'suppressed', 'message_key': key}
        path = within(archive, f'Records/{key}.json')
        if path.exists():
            saved = record(archive, key)
            prior = {k: v for k, v in saved['message'].items() if k != 'captured_by'}
            incoming = {k: v for k, v in data.items() if k != 'captured_by'}
            if prior != incoming:
                raise ValueError('Message ID/position has different evidence; preserve and resolve the conflict')
        else:
            saved = {'version': 1, 'message': data,
                     'captured_at': datetime.now(timezone.utc).isoformat(timespec='seconds')}
            create_once(path, encoded(saved))
        message = saved['message']
        fallback_notes = '\n'.join(
            f'Original {field}: unknown ({message[field + "_note"]}). '
            f'Capture {field}: `{message["capture_" + field]}` (locally assigned, not a vendor identifier).'
            for field in ('session_id', 'message_id') if message[field] == 'unknown')
        fallback_notes = fallback_notes + '\n\n' if fallback_notes else ''
        body = (f'# {message["role"]} · position {message["position"]}\n\n'
                f'Source: {message["source"]}; session: `{message["session_id"]}`; '
                f'message: `{message["message_id"]}`.\n\n'
                f'{fallback_notes}'
                f'Original timestamp: {message["source_date"]}. '
                f'{message.get("timestamp_note", "")}\n\n'
                f'Coverage: {message["coverage"]}\n\n{message["text"]}\n\n'
                f'[Original metadata and redactions](../Records/{key}.json)\n')
        create_once(within(archive, f'Messages/{key}.md'),
                    note(body, 'visible-message', 'Selected user-visible discussion',
                         message['captured_by'], saved['captured_at']))
    return {'mode': 'saved', 'message_key': key, 'coverage': data['coverage']}


def example(archive, key, attestation, editor, apply=False):
    archive = safe_path(archive)
    config(archive)
    current_editor = editor_fields(editor)
    data = record(archive, key)['message']
    if data['role'] != 'user':
        raise ValueError('Assistant messages are never evidence of the owner\'s writing voice')
    fields = {'owner_authored', 'excludes_pasted_or_quoted', 'authorship_reference', 'context', 'observations'}
    if (not isinstance(attestation, dict) or set(attestation) != fields
            or attestation['owner_authored'] is not True or attestation['excludes_pasted_or_quoted'] is not True):
        raise ValueError('Require explicit owner authorship and exclusion of pasted/quoted/assistant-written text')
    for field in ('authorship_reference', 'context'):
        if not isinstance(attestation[field], str) or not attestation[field].strip():
            raise ValueError('Authorship evidence and writing context must be recorded')
    if (not isinstance(attestation['observations'], list)
            or any(not isinstance(x, str) or not x.strip() for x in attestation['observations'])):
        raise ValueError('Draft observations must be a list of nonempty statements')
    if blocked(archive, data):
        return {'mode': 'suppressed', 'message_key': key}
    value = {'version': 1, 'message_key': key, 'message_sha256': digest(encoded(data)),
             'attestation': attestation, 'status': 'draft', 'editor': current_editor}
    if apply:
        with suppression.state_lock(archive):
            if blocked(archive, data):
                return {'mode': 'suppressed', 'message_key': key}
            if digest(encoded(record(archive, key)['message'])) != value['message_sha256']:
                raise ValueError('Source changed while preparing writing example')
            target = within(archive, f'Corpus/{key}.json')
            if target.exists():
                existing = draft(archive, key)[0]
                if {k: v for k, v in existing.items() if k != 'editor'} != {k: v for k, v in value.items() if k != 'editor'}:
                    raise ValueError('Writing example already has different observations; preserve and review them')
            else:
                create_once(target, encoded(value))
    return {'mode': 'saved' if apply else 'preview', 'message_key': key, 'status': 'draft'}


def draft(archive, key):
    if not suppression.valid_hash(key):
        raise ValueError('Invalid archived message ID')
    value = json.loads(within(archive, f'Corpus/{key}.json').read_text(encoding='utf-8'))
    if (not isinstance(value, dict) or value.get('version') != 1 or value.get('message_key') != key
            or value.get('status') != 'draft' or not suppression.valid_hash(value.get('message_sha256'))):
        raise ValueError('Invalid writing example draft')
    data = record(archive, key)['message']
    if data['role'] != 'user' or digest(encoded(data)) != value['message_sha256']:
        raise ValueError('Writing example source changed or is not user-authored')
    attestation = value.get('attestation', {})
    if attestation.get('owner_authored') is not True or attestation.get('excludes_pasted_or_quoted') is not True:
        raise ValueError('Writing example lacks authorship attestation')
    return value, data


def approve(archive, key, approval_reference, editor, apply=False):
    archive = safe_path(archive)
    config(archive)
    current_editor = editor_fields(editor)
    known(approval_reference, 'Owner approval reference')
    value, data = draft(archive, key)
    if blocked(archive, data):
        return {'mode': 'suppressed', 'message_key': key}
    approval = {'version': 1, 'message_key': key, 'draft_sha256': digest(encoded(value)),
                'owner_approval_reference': approval_reference, 'editor': current_editor}
    if apply:
        with suppression.state_lock(archive):
            if blocked(archive, data):
                return {'mode': 'suppressed', 'message_key': key}
            if digest(encoded(draft(archive, key)[0])) != approval['draft_sha256']:
                raise ValueError('Writing example changed; obtain approval for the revised example')
            target = within(archive, f'Approvals/{key}.json')
            if target.exists():
                existing = json.loads(target.read_text(encoding='utf-8'))
                if {k: v for k, v in existing.items() if k != 'editor'} != {k: v for k, v in approval.items() if k != 'editor'}:
                    raise ValueError('Different approval already exists; preserve and inspect it')
            else:
                create_once(target, encoded(approval))
    return {'mode': 'saved' if apply else 'preview', 'message_key': key, 'status': 'approved' if apply else 'draft'}


def corpus(archive):
    archive = safe_path(archive)
    config(archive)
    result = []
    for path in sorted(within(archive, 'Approvals').glob('*.json')):
        approval = json.loads(safe_path(path).read_text(encoding='utf-8'))
        value, data = draft(archive, path.stem)
        if (not isinstance(approval, dict) or approval.get('version') != 1
                or approval.get('message_key') != path.stem or approval.get('draft_sha256') != digest(encoded(value))):
            raise ValueError('Writing example approval no longer matches its draft')
        known(approval.get('owner_approval_reference'), 'Owner approval reference')
        provenance(approval.get('editor'))
        if not blocked(archive, data):
            result.append({'message_key': path.stem, 'text': data['text'], 'source_id': data['source_id'],
                           'session_id': data['session_id'], 'source_date': data['source_date'],
                           **{key: data[key] for key in ('message_id', 'message_id_note', 'session_id_note',
                                                        'capture_message_id', 'capture_session_id') if key in data},
                           'context': value['attestation']['context'], 'observations': value['attestation']['observations']})
    return {'examples': result, 'purpose': 'Owner-approved writing examples and observations; no model training'}


def forget_plan(archive, selected):
    inputs, _ = suppression.cleanup_history(archive, selected)
    for path in sorted(within(archive, 'Records').glob('*.json')):
        if suppression.matches(selected, record(archive, path.stem)['message']):
            inputs.add(path.stem)
    files = []
    for key in sorted(inputs):
        for relative in (f'Approvals/{key}.json', f'Corpus/{key}.json', f'Messages/{key}.md', f'Records/{key}.json'):
            path = within(archive, relative)
            if path.exists():
                files.append({'path': relative, 'sha256': digest(path.read_bytes())})
    return {'suppression': selected, 'message_keys': sorted(inputs), 'files': files,
            'other_stores_require_review': True,
            'limitations': 'Knowledge notes, voice guide, other archives, chat provider history and cloud/backups '
                          'require separate scoped review; no deletion outside this archive is performed.'}


def forget(archive, editor, source_id=None, session_id=None, harness=None, apply=False):
    archive = safe_path(archive)
    config(archive)
    current_editor = editor_fields(editor)
    selected = suppression.selector(source_id, session_id, harness)
    suppression.entries(archive)
    if not apply:
        return {'mode': 'preview', **forget_plan(archive, selected)}
    with suppression.state_lock(archive):
        plan = forget_plan(archive, selected)
        suppression.save(archive, selected, current_editor)
        suppression.save_cleanup(archive, selected, plan['message_keys'], [])
        for item in plan['files']:
            path = within(archive, item['path'])
            if digest(path.read_bytes()) != item['sha256']:
                raise ValueError('Archive changed; suppression remains active, inspect and retry')
            path.unlink()
        return {'mode': 'applied', **plan}


def main():
    cli_encoding()
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ('setup', 'capture', 'example', 'approve', 'corpus', 'forget'):
        cmd = sub.add_parser(name)
        cmd.add_argument('--archive', required=True)
        if name != 'corpus':
            cmd.add_argument('--apply', action='store_true')
        if name in ('setup', 'example', 'approve', 'forget'):
            cmd.add_argument('--editor', required=True)
        if name == 'setup':
            cmd.add_argument('--vault', required=True)
            cmd.add_argument('--sources', required=True, help='Private JSON file containing approved source labels')
        elif name == 'capture':
            cmd.add_argument('--input', required=True)
        elif name == 'example':
            cmd.add_argument('--message-key', required=True)
            cmd.add_argument('--attestation', required=True)
        elif name == 'approve':
            cmd.add_argument('--message-key', required=True)
            cmd.add_argument('--approval-reference', required=True)
        elif name == 'forget':
            scope = cmd.add_mutually_exclusive_group(required=True)
            scope.add_argument('--source-id')
            scope.add_argument('--session-id')
            cmd.add_argument('--harness')
    args = parser.parse_args()
    def read(path):
        return json.loads(Path(path).read_text(encoding='utf-8'))
    try:
        if args.command == 'setup':
            result = setup(args.archive, args.vault, read(args.sources), read(args.editor), args.apply)
        elif args.command == 'capture':
            result = capture(args.archive, read(args.input), args.apply)
        elif args.command == 'example':
            result = example(args.archive, args.message_key, read(args.attestation), read(args.editor), args.apply)
        elif args.command == 'approve':
            result = approve(args.archive, args.message_key, args.approval_reference, read(args.editor), args.apply)
        elif args.command == 'corpus':
            result = corpus(args.archive)
        else:
            result = forget(args.archive, read(args.editor), args.source_id, args.session_id, args.harness, args.apply)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f'Voice operation stopped; existing evidence preserved: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
