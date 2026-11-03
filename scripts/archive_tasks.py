#!/usr/bin/env python3
"""Copy verified completions to history, then remove only their verified source rows."""
import argparse
from collections import Counter
from contextlib import nullcontext
from pathlib import Path
import json
import os
import re
import sys
from urllib.parse import quote

from bootstrap import replace_startup
from common import cli_encoding, create_once, digest, encoded, safe_path, same_path, within
from memory import config
from suppression import state_lock
from task_agenda import cells, visible_lines


def completed_entries(raw, source_name, archive_dir, lane):
    original = raw.decode('utf-8').splitlines(keepends=True)
    lines = visible_lines(raw.decode('utf-8'))
    entries = {}
    counts = Counter()
    heading = ''
    relative = Path(os.path.relpath(source_name, archive_dir)).as_posix()

    def add(index, payload):
        # Identical rows within one migration represent separate recorded tasks.
        key = (heading, payload)
        counts[key] += 1
        ident = digest(encoded([lane, source_name.as_posix(), heading, payload, counts[key]]))
        marker = f'<!-- completed-task:{ident} -->'
        label = f'{lane} · [source list]({quote(relative)})'
        if heading:
            label += ' · ' + heading
        block = f'{marker}\n{label}\n\n{payload}\n<!-- end-completed-task:{ident} -->'
        entries[index] = (marker, block)

    index = 0
    while index < len(lines):
        line = lines[index]
        if line.startswith('#'):
            heading = line.lstrip('#').strip()
        if re.match(r'^[-*+] \[[xX]\] \S', line):
            if index + 1 < len(lines) and lines[index + 1].startswith((' ', '\t')):
                raise ValueError('Nested checklist needs a reviewed move including its children')
            add(index, line)
        header = [cell.casefold() for cell in cells(line)] if '|' in line else []
        if not {'task', 'status'}.issubset(header):
            index += 1
            continue
        if len(set(header)) != len(header) or index + 1 >= len(lines):
            raise ValueError(f'Ambiguous task table at line {index + 1}')
        separator = lines[index + 1]
        if len(cells(separator)) != len(header) or not all(re.fullmatch(r':?-{3,}:?', x) for x in cells(separator)):
            raise ValueError(f'Invalid task table at line {index + 1}')
        index += 2
        while index < len(lines) and '|' in lines[index]:
            row = cells(lines[index])
            if len(row) != len(header):
                raise ValueError(f'Invalid task row at line {index + 1}')
            status = row[header.index('status')].split(' · ', 1)[0].strip().casefold()
            if status in {'done', 'completed', 'complete', 'closed'}:
                add(index, '\n'.join((line, separator, lines[index])))
            index += 1
    return entries, ''.join(line for i, line in enumerate(original) if i not in entries).encode()


def transfer(root, agent_list, personal_list, archive, mode='preview', verified_hash=None):
    root = safe_path(root)
    settings = config(root)
    paths = [within(root, name) for name in (agent_list, personal_list, archive)]
    if any(same_path(path, other) for index, path in enumerate(paths) for other in paths[index + 1:]):
        raise ValueError('The two active lists and the archive must be distinct')
    if mode == 'apply' and settings.get('storage', {}).get('provider') != 'local':
        raise ValueError('Shared storage requires --copy, cloud readback, then --prune with the verified hash')
    target = paths[-1]
    with nullcontext() if mode == 'preview' else state_lock(root):
        sources = []
        blocks = []
        counts = {}
        for path, lane in zip(paths[:2], ('Agent', 'Personal')):
            raw = path.read_bytes()
            entries, after = completed_entries(raw, path.relative_to(root), target.parent.relative_to(root), lane)
            if path.parent != target.parent and any(re.search(r'\]\((?![a-zA-Z][a-zA-Z0-9+.-]*:|/|#)', block.split('\n\n', 1)[1]) for _, block in entries.values()):
                raise ValueError('Review and rebase relative links before moving entries between folders')
            counts[lane] = len(entries)
            sources.append((path, raw, after))
            blocks.extend(entries.values())
        result = {'mode': mode, 'completed': counts, 'copied': 0, 'removed': 0}
        if not blocks:
            return result
        before = target.read_bytes() if target.exists() else None
        history = (before or b'').decode('utf-8')
        missing = []
        for marker, block in blocks:
            if marker not in history:
                missing.append(block)
            elif history.count(marker) != 1 or block not in history:
                raise ValueError('Archive receipt differs from source content. Both copies preserved.')
        result['to_copy'] = len(missing)
        if mode == 'preview':
            return result
        if mode == 'prune':
            if before is None or not verified_hash or digest(before) != verified_hash or missing:
                raise ValueError('Archive is incomplete or differs from verified hash. Active lists preserved.')
        elif missing:
            if before is None:
                history = '# Completed Task List\n\nOn-demand history of finished agent and personal tasks.\n'
            output = (history + '\n\n' + '\n\n'.join(missing) + '\n').encode()
            if before is None:
                create_once(target, output)
            else:
                replace_startup(target, before, output)
            before = output
            result['copied'] = len(missing)
        if target.read_bytes() != before:
            raise ValueError('Archive changed during verification. Active lists preserved.')
        result['archive_sha256'] = digest(before)
        if mode in {'prune', 'apply'}:
            for path, initial, after in sources:
                if initial != after:
                    if target.read_bytes() != before:
                        raise ValueError('Archive changed. Recheck before pruning remaining rows.')
                    replace_startup(path, initial, after)
                    result['removed'] += counts['Agent' if path == paths[0] else 'Personal']
        return result


def main():
    cli_encoding()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--vault', required=True)
    parser.add_argument('--agent-list', default='Task List.md')
    parser.add_argument('--personal-list', default='My Tasks.md')
    parser.add_argument('--archive', default='Completed Task List.md')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--copy', dest='mode', action='store_const', const='copy')
    group.add_argument('--prune', dest='mode', action='store_const', const='prune')
    group.add_argument('--apply', dest='mode', action='store_const', const='apply')
    parser.add_argument('--verified-archive-sha256')
    args = parser.parse_args()
    try:
        print(json.dumps(transfer(args.vault, args.agent_list, args.personal_list, args.archive,
                                  args.mode or 'preview', args.verified_archive_sha256), indent=2))
    except (OSError, ValueError, KeyError) as exc:
        print(f'Task archive stopped: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
