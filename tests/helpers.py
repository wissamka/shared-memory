import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

PACKAGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE / 'scripts'))
import bootstrap
import memory
from common import digest, encoded


class Case(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.root = self.base / 'Shared Memory — café'
        self.c = json.loads((PACKAGE / 'assets/config.example.json').read_text(encoding='utf-8'))
        self.c['vault_path'] = str(self.root)
        self.c['timezone'] = 'America/New_York'
        self.editor = self.c['provenance']
        self.data = json.loads((PACKAGE / 'assets/capture.example.json').read_text(encoding='utf-8'))

    def quiet(self, function, *args, **kwargs):
        with contextlib.redirect_stdout(io.StringIO()):
            return function(*args, **kwargs)

    def setup_vault(self):
        self.quiet(bootstrap.install, self.c, apply=True)

    def review(self):
        self.setup_vault()
        item = memory.capture(self.root, self.data)
        run = memory.prepare(self.root, '2030-04-02')
        destination = self.root / 'Personal/Preferences.md'
        destination.write_bytes(destination.read_bytes() + b'\nOne-page briefs. Source: fictional-session-1:turn-3:preference.\n')
        return {'run_id': run['run_id'], 'editor': self.editor, 'coverage_gaps': [], 'results': [
            {'input_id': item['input_id'], 'outcome': 'promoted', 'reason': 'Preference saved with source',
             'destinations': [{'path': 'Personal/Preferences.md', 'sha256': digest(destination.read_bytes())}]}]}

    def cli(self, script, *args, expected=0):
        result = subprocess.run([sys.executable, str(script), *map(str, args)], cwd=self.base,
                                capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(expected, result.returncode, result.stdout + result.stderr)
        self.assertNotIn('Traceback', result.stderr)
        return result
