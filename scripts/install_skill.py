#!/usr/bin/env python3
"""Install this complete skill into selected harnesses. No network or credentials."""
import argparse
import json
from pathlib import Path
import sys

from common import cli_encoding, contains_path, create_once, digest, distribution_roots, encoded, safe_path, same_path

PACKAGE = Path(__file__).resolve().parents[1]
MARKER = '.shared-memory-skill-install.json'


def bundle(source=PACKAGE):
    """Copy only reviewed filenames, independently of Git or working-tree extras."""
    source = Path(source)
    manifest_path = safe_path(source / 'skill-files.json')
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    names = manifest.get('files') if isinstance(manifest, dict) else None
    if (not isinstance(names, list) or not names or
            any(not isinstance(p, str) for p in names) or
            len({p.casefold() for p in names}) != len(names)):
        raise ValueError('Invalid skill distribution manifest')
    if not {'SKILL.md', 'LICENSE', 'skill-files.json'}.issubset(names):
        raise ValueError('Incomplete skill distribution manifest')
    files = {}
    for rel in names:
        if (Path(rel).is_absolute() or '..' in Path(rel).parts or '\\' in rel
                or rel.endswith('.local.json') or any(p.startswith('.') for p in Path(rel).parts)):
            raise ValueError(f'Unsafe distribution filename: {rel}')
        path = safe_path(source / rel)
        if not path.is_file():
            raise ValueError(f'Incomplete skill bundle: {rel}')
        files[rel] = path.read_bytes()
    return files


def default_target(harness, home=None):
    home = Path.home() if home is None else Path(home)
    return home / ('.agents/skills' if harness == 'codex' else '.claude/skills') / 'shared-memory'


def install(targets, apply=False, source=PACKAGE):
    if not targets or any(not Path(p).expanduser().is_absolute() for p in targets):
        raise ValueError('Choose at least one absolute destination (or start with ~)')
    source = safe_path(source)
    files = bundle(source)
    manifest = encoded({'version': 1, 'files': {p: digest(data) for p, data in files.items()}})
    changes = []
    normalized = [safe_path(p) for p in targets]
    if any(same_path(p, q) for i, p in enumerate(normalized) for q in normalized[i+1:]):
        raise ValueError('Duplicate installation destination')
    for root in normalized:
        if any(contains_path(p, root) or contains_path(root, p) for p in distribution_roots(source)):
            raise ValueError('Installation destination must be separate from the downloaded package')
        if any(root != other and (contains_path(other, root) or contains_path(root, other)) for other in normalized):
            raise ValueError('Installation destinations overlap')
        marker = safe_path(root / MARKER)
        if root.exists() and (not root.is_dir() or (any(root.iterdir()) and not marker.is_file())):
            raise ValueError(f'Existing unmanaged skill preserved: {root}')
        if marker.exists() and marker.read_bytes() != manifest:
            raise ValueError(f'Different installed version; preserved: {root}. Use a new folder or review an upgrade.')
        for relative, data in {MARKER: manifest, **files}.items():
            path = safe_path(root / relative)
            if path.exists():
                if not path.is_file() or path.read_bytes() != data:
                    raise ValueError(f'Locally edited installed file preserved: {path}')
            else:
                changes.append((path, data))
    for path, _ in changes:
        if any(parent.exists() and not parent.is_dir() for parent in path.parents):
            raise ValueError(f'Expected directory parent: {path}')
    print(('INSTALL' if apply else 'PREVIEW') + f': {len(changes)} files across {len(normalized)} destination(s)')
    for root in normalized:
        print(root)
    if apply:
        for path, data in changes:
            create_once(path, data)
        print('Skill installed and verified. Start a fresh agent session and ask it to set up shared memory.')
    return changes


def main():
    cli_encoding()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--harness', nargs='+', choices=('codex', 'claude'))
    parser.add_argument('--target', action='append', help='Exact skill folder for another supported harness; may repeat')
    parser.add_argument('--apply', action='store_true', help='Install after reviewing paths; otherwise preview')
    args = parser.parse_args()
    try:
        targets = [default_target(h) for h in (args.harness or [])] + [Path(p).expanduser() for p in (args.target or [])]
        if not targets:
            if not sys.stdin.isatty():
                parser.error('Choose --harness codex/claude or --target; no interactive terminal available')
            print('Install Roaming Shared Memory x-harness for: 1 Codex, 2 Claude Code, 3 Both, 4 Custom folder')
            choice = input('Choose 1–4: ').strip()
            if choice not in ('1', '2', '3', '4'):
                raise ValueError('Choose 1, 2, 3 or 4')
            targets = ([default_target('codex')] if choice == '1' else
                       [default_target('claude')] if choice == '2' else
                       [default_target('codex'), default_target('claude')] if choice == '3' else
                       [Path(input('Exact destination skill folder: ').strip()).expanduser()])
            install(targets)
            if not args.apply and input('Install into these folders? [y/N] ').strip().lower() not in ('y', 'yes'):
                print('No files changed.')
                return 0
            return 0 if install(targets, True) is not None else 1
        if any(not p.is_absolute() for p in targets):
            raise ValueError('Destinations must be absolute or start with ~')
        install(targets, args.apply)
    except (ValueError, OSError, EOFError) as exc:
        print(f'Installation stopped; existing files preserved: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
