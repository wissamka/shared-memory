#!/usr/bin/env python3
"""Build or verify the public plugin from explicitly listed, portable skill files."""
import argparse
import json
from pathlib import Path
import sys
import zipfile

from common import cli_encoding, encoded, safe_path
from install_skill import bundle

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / 'plugins/shared-memory'
REPO = 'https://github.com/wissamka/shared-memory'


def plugin_files(source=ROOT):
    skill = bundle(source)
    version = json.loads(skill['skill-files.json'])['version']
    identity = {
        'name': 'shared-memory', 'version': version,
        'description': 'Build a personal memory vault with sourced notes, preferences and daily review.',
        'author': {'name': 'Shared Memory contributors'},
        'homepage': REPO, 'repository': REPO, 'license': 'MIT',
        'keywords': ['memory', 'obsidian', 'productivity'],
    }
    portable = {
        '$schema': 'https://agent-plugins.org/schemas/1.0.0/plugin.schema.json', **identity,
        'extensions': {'com.openai': {
            'onboardingSkill': './skills/shared-memory/SKILL.md',
            'interface': {
                'displayName': 'Shared Memory AI Second Brain',
                'shortDescription': 'Personal memory across agents, sessions and devices',
                'developerName': 'Shared Memory contributors',
                'category': 'Productivity', 'capabilities': ['Read', 'Write'],
                'websiteURL': REPO,
                'defaultPrompt': ['Set up my shared memory. Ask which shared drive I use and how I like to work.'],
            },
        }},
    }
    return {
        'plugin.json': encoded(portable),
        '.claude-plugin/plugin.json': encoded(identity),
        'LICENSE': skill['LICENSE'],
        **{'skills/shared-memory/' + p: data for p, data in skill.items()},
    }


def build(check=False, archive=None):
    files = plugin_files()
    actual = {p.relative_to(PLUGIN).as_posix() for p in PLUGIN.rglob('*')
              if p.is_file() and '__pycache__' not in p.parts}
    unexpected = actual - files.keys()
    if unexpected:
        raise ValueError('Unexpected plugin files; review and remove explicitly: ' + ', '.join(sorted(unexpected)))
    differences = [name for name, data in files.items()
                   if not (PLUGIN / name).is_file() or (PLUGIN / name).read_bytes() != data]
    if check and differences:
        raise ValueError('Generated plugin differs; run build_plugin.py: ' + ', '.join(differences))
    if not check:
        for name in differences:
            path = safe_path(PLUGIN / name)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(files[name])
    if archive:
        archive = safe_path(archive)
        if archive.exists():
            raise ValueError('Archive already exists; choose a new output')
        archive.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(archive, 'x', zipfile.ZIP_DEFLATED) as output:
            for name, data in sorted(files.items()):
                info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                output.writestr(info, data)
    print(f'Plugin {"verified" if check else "built"}: {len(files)} allowlisted files.')


def main():
    cli_encoding()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--archive', help='Optional new ZIP/.plugin archive path')
    args = parser.parse_args()
    try:
        build(args.check, args.archive)
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
