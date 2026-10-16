#!/usr/bin/env python3
"""Best-effort visible-text JSONL import from an explicitly authorized source tree."""
import argparse
from datetime import date, datetime, time, timedelta
import json
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

from common import digest, provenance, safe_path, timestamp
from memory import capture, config


def text_blocks(content, allowed):
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ''
    return '\n'.join(item['text'] for item in content if isinstance(item, dict)
                     and item.get('type') in allowed and isinstance(item.get('text'), str))


def extract(path, kind, start, end, editor):
    records, gaps = [], []
    session, model = 'unknown', 'unknown'
    visible_records = 0
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
                session = payload.get('id') or 'unknown'
                continue
            if event.get('type') == 'turn_context':
                model = payload.get('model') or 'unknown'
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
            if not content and payload.get('content'):
                gaps.append(f'{path.name}:{line_number}: message has no supported text; inspect attachments/format')
            source_model = model if role == 'assistant' else 'unknown'
        else:
            role = event.get('type')
            message = event.get('message', {})
            if not isinstance(message, dict) or role not in ('user', 'assistant') or event.get('isMeta'):
                continue
            content = text_blocks(message.get('content'), ('text',))
            session = event.get('sessionId') or session
            source_model = message.get('model', 'unknown') if role == 'assistant' else 'unknown'
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
        # Stable across reruns and copied files; distinct line positions preserve repeated turns.
        source_id = f'{kind}:{session}:{line_number}:{digest(line.encode())}'
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


def collect(kind, source, root, day, editor, apply=False):
    provenance(editor)
    source = safe_path(source)
    if not source.is_dir():
        raise ValueError('Source must be the explicitly authorized directory')
    zone = ZoneInfo(config(root)['timezone'])
    target = date.fromisoformat(day)
    start = datetime.combine(target, time.min, zone)
    end = datetime.combine(target + timedelta(days=1), time.min, zone)
    count, gaps = 0, []
    paths = sorted(source.rglob('*.jsonl'))
    if not paths:
        gaps.append('No JSONL files found; source coverage unverified')
    for path in paths:
        try:
            safe_path(path)
            records, missing = extract(path, kind, start, end, editor)
            gaps.extend(missing)
            for record in records:
                if apply:
                    capture(root, record)
                count += 1
        except (ValueError, OSError) as exc:
            gaps.append(f'{path.name}: {exc}')
    return {'mode': 'applied' if apply else 'preview', 'files_examined': len(paths),
            'visible_messages': count, 'window_start': start.isoformat(), 'window_end': end.isoformat(),
            'coverage_gaps': gaps, 'coverage': 'Selected local JSONL tree and recognized visible text only'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kind', choices=('codex', 'claude'), required=True)
    parser.add_argument('--source', required=True)
    parser.add_argument('--vault', required=True)
    parser.add_argument('--date', required=True)
    parser.add_argument('--editor', required=True)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    try:
        result = collect(args.kind, args.source, safe_path(args.vault), args.date,
                         json.loads(Path(args.editor).read_text(encoding="utf-8")), args.apply)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 2 if result['coverage_gaps'] else 0
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f'Import stopped; preserve pending inputs: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
