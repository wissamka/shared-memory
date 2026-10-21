#!/usr/bin/env python3
"""Connect a new device-local harness to an existing vault without bootstrapping it."""
import argparse
import json
from pathlib import Path
import re
import sys

from bootstrap import BEGIN, END, binding_record, existing_binding, replace_startup, startup
from common import cli_encoding, contains_path, create_once, digest, distribution_roots, encoded, provenance, safe_path, storage, within
from memory import config

PACKAGE = Path(__file__).resolve().parents[1]
KINDS = ('codex', 'claude', 'gemini', 'cursor', 'copilot', 'generic')


def capture_mode(root):
    # Live owner rules take precedence over the historical setup default.
    rules = within(root, 'rules.md').read_text(encoding='utf-8')
    modes = re.findall(r'(?im)^Capture mode:\s*\*\*(explicit|durable)\*\*', rules)
    if len(modes) != 1:
        raise ValueError('Resolve one explicit or durable capture mode in the live rules before connecting')
    return modes[0]


def connect(vault, target, kind, editor, apply=False):
    provenance(editor)
    if kind not in KINDS:
        raise ValueError('Unsupported harness kind')
    if any(not Path(p).expanduser().is_absolute() for p in (vault, target)):
        raise ValueError('Vault and target must be absolute paths (or start with ~)')
    root, path = safe_path(vault), safe_path(target)
    packages = distribution_roots(PACKAGE)
    if any(contains_path(p, root) or contains_path(p, path) for p in packages):
        raise ValueError('Private vault and harness bindings must be outside the distributable package')
    if contains_path(root, path):
        raise ValueError('Harness startup target must be outside the vault')
    settings = config(root)
    storage(settings)
    hook = startup({**settings, 'capture_mode': capture_mode(root)}, root).encode()
    before = path.read_bytes() if path.exists() else None
    if before is not None and (BEGIN.encode() in before or END.encode() in before):
        if before.count(BEGIN.encode()) != 1 or before.count(END.encode()) != 1 or hook not in before:
            raise ValueError(f'Conflicting or partial managed block; preserved: {path}')
        data = before
    else:
        data = (before + b'\n\n' if before is not None else b'') + hook
    identity = digest(str(path).encode())
    record_path = within(root, f'.memory-state/bindings/{identity}.json')
    binding = binding_record(root, path, kind, hook, data, editor)
    prior = existing_binding(record_path, binding)
    if prior is not None:
        # A receipt retains the original connection's editor and whole-file hash.
        # Later unrelated user additions do not invalidate the managed block.
        binding = prior
    for candidate in (path, record_path):
        if any(parent.exists() and not parent.is_dir() for parent in candidate.parents):
            raise ValueError(f'Expected directory parent for: {candidate}')
    result = {'mode': 'applied' if apply else 'preview', 'target': str(path), 'vault': str(root),
              'startup_change': data != before, 'binding_record': str(record_path),
              'instruction_loading': 'unverified; test a fresh harness session'}
    if not apply:
        return result
    # Validate everything above before changing either destination. A write may
    # succeed before the receipt does; repeating the exact connection repairs it.
    if (path.read_bytes() if path.exists() else None) != before:
        raise ValueError('Startup target changed; re-plan connection')
    if data != before:
        if before is None:
            create_once(path, data)
        else:
            replace_startup(path, before, data)
    if prior is None:
        create_once(record_path, encoded(binding))
    if path.read_bytes() != data:
        raise ValueError('Startup readback changed; inspect before claiming connection')
    return result


def main():
    cli_encoding()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--vault', required=True)
    parser.add_argument('--target', required=True)
    parser.add_argument('--kind', required=True, choices=KINDS)
    parser.add_argument('--editor', required=True, help='Private JSON containing actual current editor provenance')
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    try:
        result = connect(args.vault, args.target, args.kind,
                         json.loads(Path(args.editor).read_text(encoding='utf-8')), args.apply)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f'Connection stopped; preserve existing files and retry after review: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
