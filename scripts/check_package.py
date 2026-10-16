#!/usr/bin/env python3
"""Check package links, parse Python, and flag common private-data patterns."""
import ast
from pathlib import Path
import re
import sys
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]


def check(root=ROOT):
    problems = []
    files = [p for p in root.rglob('*') if p.is_file() and not any(
        part in ('.git', '.venv', '__pycache__', 'private', 'dist', 'pending-memory') for part in p.relative_to(root).parts)]
    for path in files:
        if path.suffix not in ('.md', '.py', '.json', '.yaml', '.yml'):
            continue
        content = path.read_text()
        if path.suffix == '.py':
            try:
                ast.parse(content)
            except SyntaxError as exc:
                problems.append(f'{path.relative_to(root)}: {exc}')
        if path.suffix == '.md':
            for ref in re.findall(r'\]\(([^)]+)\)', content):
                ref = ref.strip('<>').split('#', 1)[0]
                if not ref or re.match(r'^[a-z]+:', ref) or ref.startswith('/'):
                    continue
                if not (path.parent / unquote(ref)).exists():
                    problems.append(f'{path.relative_to(root)}: missing link {ref}')
        # Heuristics only; review files and version history before publication.
        patterns = [r'/Users/[^/\s`]+/', r'/home/[^/\s`]+/',
                    r'(?i)[a-z0-9._%+-]+@(?:gmail|hotmail|outlook)\.com',
                    r'(?i)(?:sk-proj-|ghp_)[A-Za-z0-9_-]{20,}',
                    r'codex://threads/[0-9a-f-]{20,}',
                    r'(?i)https://onedrive\.live\.com[^\s)]*[?&](?:cid|id)=']
        if path.name != 'check_package.py':
            for pattern in patterns:
                if re.search(pattern, content):
                    problems.append(f'{path.relative_to(root)}: review potential private data ({pattern})')
    return problems


if __name__ == '__main__':
    errors = check()
    print('\n'.join(errors) if errors else 'Package checks passed: links, Python syntax, common private-data patterns.')
    sys.exit(bool(errors))
