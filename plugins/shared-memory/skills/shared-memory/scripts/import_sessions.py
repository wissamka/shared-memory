#!/usr/bin/env python3
"""Best-effort visible-text JSONL import from an explicitly authorized source tree."""
import argparse
from datetime import date, datetime, time, timedelta
import json
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

from common import cli_encoding, digest, encoded, provenance, safe_path, timestamp
from memory import capture, config
from collection import load_source, pending, record as record_collection
from suppression import is_suppressed


def text_blocks(content, allowed):
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ''
    return '\n'.join(item['text'] for item in content if isinstance(item, dict)
                     and item.get('type') in allowed and isinstance(item.get('text'), str))


def unsupported_content(content, allowed):
    """Flag missing visible text without ever extracting reasoning or tool data."""
    if isinstance(content, str):
        return False
    if not isinstance(content, list):
        return True
    excluded = {'thinking', 'redacted_thinking', 'tool_use', 'tool_result'}
    return any(not isinstance(item, dict) or
               (item.get('type') not in excluded and
                (item.get('type') not in allowed or not isinstance(item.get('text'), str)))
               for item in content)


def extract(path, kind, start, end, editor):
    records, gaps = [], []
    session, model = 'unknown', 'unknown'
    visible_records = 0
    occurrences = {}

    def identifier(value):
        return value if isinstance(value, str) and value.strip() else 'unknown'
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except (ValueError, TypeError):
            gaps.append(f'{path.name}:{line_number}: malformed JSON; coverage uncertain')
            continue
        if not isinstance(event, dict):
            gaps.append(f'{path.name}:{line_number}: unsupported record shape')
            continue
        payload = event.get('payload', {})
        payload = payload if isinstance(payload, dict) else {}
        if kind == 'codex':
            if event.get('type') == 'session_meta':
                session = identifier(payload.get('id'))
                model = 'unknown'
                continue
            if event.get('type') == 'turn_context':
                model = identifier(payload.get('model'))
                continue
            if event.get('type') != 'response_item' or payload.get('type') != 'message':
                continue
            role = payload.get('role')
            if role not in ('user', 'assistant'):
                continue
            if role == 'assistant' and payload.get('channel') != 'final':
                if payload.get('channel') not in ('analysis', 'commentary'):
                    gaps.append(f'{path.name}:{line_number}: assistant channel unrecognized; omitted')
                continue  # Never extract analysis, tool messages or uncertain channels.
            content = text_blocks(payload.get('content'), ('input_text', 'output_text', 'text'))
            if unsupported_content(payload.get('content'), ('input_text', 'output_text', 'text')):
                gaps.append(f'{path.name}:{line_number}: unsupported visible content; inspect attachments/format')
            source_model = model if role == 'assistant' else 'unknown'
        else:
            role = event.get('type')
            message = event.get('message', {})
            if not isinstance(message, dict) or role not in ('user', 'assistant') or event.get('isMeta'):
                continue
            content = text_blocks(message.get('content'), ('text',))
            if unsupported_content(message.get('content'), ('text',)):
                gaps.append(f'{path.name}:{line_number}: unsupported visible content; inspect attachments/format')
            session = identifier(event.get('sessionId')) if event.get('sessionId') else session
            source_model = identifier(message.get('model')) if role == 'assistant' else 'unknown'
        if not content.strip():
            continue
        visible_records += 1
        try:
            stamp = timestamp(event['timestamp'])
        except (KeyError, ValueError, TypeError):
            gaps.append(f'{path.name}:{line_number}: visible message has no usable timestamp')
            continue
        if not start <= stamp < end:
            continue
        # Semantic identity survives JSON formatting, telemetry insertion and copied
        # exports. An occurrence counter preserves truly identical repeated turns.
        scope = session if session != 'unknown' else 'file-' + digest(str(path.resolve()).encode())
        if session == 'unknown':
            gaps.append(f'{path.name}:{line_number}: session ID unavailable; identity scoped to source file')
        signature = digest(encoded([kind, scope, stamp.isoformat(), role, content, source_model]))
        occurrences[signature] = occurrences.get(signature, 0) + 1
        source_id = f'{kind}:{scope}:{signature}:{occurrences[signature]}'
        records.append({'source_id': source_id, 'source_date': stamp.isoformat(),
                        'session_id': session, 'harness': 'Codex' if kind == 'codex' else 'Claude Code',
                        'assistant': ('Codex' if kind == 'codex' else 'Claude') if role == 'assistant' else 'user',
                        'model': source_model, 'model_note': 'User message: no generation model' if role == 'user'
                        else ('Exact model unavailable in this record' if source_model == 'unknown' else 'Read from source record'),
                        'agent': 'unknown', 'chat_reference': 'unavailable',
                        'source_locator': f'{path}:{line_number}', 'title': f'{role} message — {stamp.date()}',
                        'text': content, 'status': 'reported', 'captured_by': editor,
                        'coverage': 'Visible text only; system, tools, reasoning and attachments omitted'})
    if not visible_records:
        gaps.append(f'{path.name}: no recognized visible messages; format or coverage unverified')
    return records, gaps


def collect(kind, source, root, day, editor, apply=False, source_id=None):
    provenance(editor)
    source = safe_path(source)
    if not source.is_dir():
        raise ValueError('Source must be the explicitly authorized directory')
    zone = ZoneInfo(config(root)['timezone'])
    target = date.fromisoformat(day)
    if kind not in ('codex', 'claude'):
        raise ValueError('Unsupported source kind')
    if source_id is not None:
        registered = load_source(root, source_id)
        if registered['kind'] != kind or target < date.fromisoformat(registered['since']):
            raise ValueError('Import does not match the registered source scope')
    start = datetime.combine(target, time.min, zone)
    end = datetime.combine(target + timedelta(days=1), time.min, zone)
    count, saved, suppressed, gaps = 0, 0, 0, []
    paths = sorted(source.rglob('*.jsonl'))
    if not paths:
        gaps.append('No JSONL files found; source coverage unverified')
    for path in paths:
        try:
            safe_path(path)
            records, missing = extract(path, kind, start, end, editor)
            gaps.extend(missing)
            for record in records:
                count += 1
                if is_suppressed(root, record):
                    suppressed += 1
                    continue
                if apply:
                    result = capture(root, record)
                    if result.get('status') == 'suppressed':
                        suppressed += 1
                    else:
                        saved += 1
        except (ValueError, OSError, KeyError, TypeError) as exc:
            gaps.append(f'{path.name}: {exc}')
    result = {'mode': 'applied' if apply else 'preview', 'files_examined': len(paths),
            'visible_messages': count, 'window_start': start.isoformat(), 'window_end': end.isoformat(),
            'saved_messages': saved, 'skipped_suppressed': suppressed,
            'coverage_gaps': gaps, 'coverage': 'Selected local JSONL tree and recognized visible text only'}
    if source_id is not None and apply:
        result['collection_status'] = record_collection(root, source_id, day, result, editor)['status']
    return result


def collect_days(kind, source, root, through, editor, apply=False, source_id=None,
                 since=None, catch_up=False):
    end = date.fromisoformat(through)
    if catch_up:
        if not source_id or since:
            raise ValueError('Catch-up requires a registered source ID and cannot combine with --since')
        registered = load_source(root, source_id)
        if registered['kind'] != kind:
            raise ValueError('Source kind differs from its registration')
        rows = pending(root, through)['sources']
        days = next(row['next_dates'] for row in rows if row['source_id'] == source_id)
    else:
        first = date.fromisoformat(since) if since else end
        if first > end:
            raise ValueError('Start date must not follow the end date')
        days = [(first + timedelta(days=n)).isoformat() for n in range((end - first).days + 1)]
    reports = [{'date': day, **collect(kind, source, root, day, editor, apply, source_id)} for day in days]
    return {'mode': 'applied' if apply else 'preview', 'days': reports,
            'coverage_gaps': [f'{row["date"]}: {gap}' for row in reports for gap in row['coverage_gaps']],
            'coverage': 'Registered bounded source only; review receipts do not replace collection evidence'}


def main():
    cli_encoding()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kind', choices=('codex', 'claude'), required=True)
    parser.add_argument('--source', required=True)
    parser.add_argument('--vault', required=True)
    parser.add_argument('--date', required=True)
    parser.add_argument('--since', help='Include every date from this day through --date')
    parser.add_argument('--source-id', help='Registered collection source; persist coverage on apply')
    parser.add_argument('--catch-up', action='store_true', help='Retry missing/partial days and late-arrival overlap')
    parser.add_argument('--editor', required=True)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    try:
        editor = json.loads(Path(args.editor).read_text(encoding='utf-8'))
        if args.since or args.catch_up:
            result = collect_days(args.kind, args.source, safe_path(args.vault), args.date,
                                  editor, args.apply, args.source_id, args.since, args.catch_up)
        else:
            result = collect(args.kind, args.source, safe_path(args.vault), args.date,
                             editor, args.apply, args.source_id)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 2 if result['coverage_gaps'] else 0
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f'Import stopped; preserve pending inputs: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
