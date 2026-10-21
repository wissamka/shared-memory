import json
import re
from urllib.parse import unquote
import zipfile

from helpers import Case, PACKAGE, digest, encoded
from check_package import check
from install_skill import bundle


class PackageTests(Case):
    def test_zip_install_to_vault_to_review_using_only_packaged_files(self):
        archive = self.base / 'shared-memory.zip'
        with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as output:
            for name, data in bundle().items():
                output.writestr('shared-memory/' + name, data)
        extracted = self.base / 'extracted'
        with zipfile.ZipFile(archive) as source:
            source.extractall(extracted)
        downloaded = extracted / 'shared-memory'
        installed = self.base / 'installed skill'
        self.cli(downloaded / 'install.py', '--target', installed, '--apply')
        setup = self.base / 'setup.json'
        self.c['storage'] = {'provider': 'google-drive', 'relative_path': 'Obsidian/Shared Memory'}
        self.c['harness_targets'] = [
            {'kind': kind, 'path': str(self.base / kind / filename)} for kind, filename in
            [('codex', 'AGENTS.md'), ('claude', 'CLAUDE.md'), ('gemini', 'GEMINI.md'),
             ('cursor', 'AGENTS.md'), ('copilot', '.github/copilot-instructions.md')]]
        setup.write_bytes(encoded(self.c))
        self.cli(installed / 'scripts/bootstrap.py', '--config', setup, '--apply')
        canonical = self.root / 'Procedures/shared-memory'
        self.cli(canonical / 'scripts/bootstrap.py', '--config', setup, '--apply')
        source = self.base / 'capture.json'
        source.write_bytes(encoded(self.data))
        saved = json.loads(self.cli(canonical / 'scripts/memory.py', 'capture', '--vault', self.root,
                                    '--input', source).stdout)
        manifest = json.loads(self.cli(canonical / 'scripts/memory.py', 'prepare', '--vault', self.root,
                                       '--date', '2030-04-02').stdout)
        # A fixture simulates the semantic agent. This is a file-workflow test,
        # not evidence of LLM synthesis quality or a live harness loading rules.
        destination = self.root / 'Personal/Preferences.md'
        destination.write_bytes(destination.read_bytes() +
            f'\nOne-page briefs. [Source](../Sessions/{saved["input_id"]}.md)\n'.encode())
        receipt = {'run_id': manifest['run_id'], 'editor': self.editor, 'coverage_gaps': [], 'results': [
            {'input_id': saved['input_id'], 'outcome': 'promoted', 'reason': 'Preference in fixture saved',
             'destinations': [{'path': 'Personal/Preferences.md', 'sha256': digest(destination.read_bytes())}]}]}
        receipt_path = self.base / 'receipt.json'
        receipt_path.write_bytes(encoded(receipt))
        self.cli(canonical / 'scripts/memory.py', 'complete', '--vault', self.root, '--receipt', receipt_path)
        status = json.loads(self.cli(canonical / 'scripts/memory.py', 'status', '--vault', self.root).stdout)
        self.assertEqual(1, status['reviewed'])
        self.assertEqual(0, status['pending'])
        repeat = json.loads(self.cli(canonical / 'scripts/memory.py', 'prepare', '--vault', self.root,
                                     '--date', '2030-04-02').stdout)
        self.assertEqual([], repeat['inputs'])
        for target in self.c['harness_targets']:
            from pathlib import Path
            text = Path(target['path']).read_text(encoding='utf-8')
            self.assertIn('google-drive', text)
            self.assertIn('Obsidian/Shared Memory', text)
        schedule = (self.root / 'Automation/Schedule.md').read_text(encoding='utf-8')
        self.assertIn('**prepared**', schedule)
        self.assertIn('Observed unattended run: pending', schedule)
        self.check_links(self.root)

    def check_links(self, root):
        for path in root.rglob('*.md'):
            for ref in re.findall(r'\]\(([^)]+)\)', path.read_text(encoding='utf-8')):
                ref = ref.strip('<>').split('#', 1)[0]
                if ref and not re.match(r'^[a-z]+:', ref) and not ref.startswith('/'):
                    self.assertTrue((path.parent / unquote(ref)).exists(), f'{path.name}: {ref}')

    def test_generated_vault_links_resolve(self):
        self.setup_vault()
        self.check_links(self.root)

    def test_every_helper_has_working_help_without_side_effects(self):
        for script in ('bootstrap.py', 'memory.py', 'import_sessions.py', 'install_skill.py',
                       'collection.py', 'connect_harness.py', 'readiness.py', 'voice.py'):
            self.cli(PACKAGE / 'scripts' / script, '--help')
        self.assertFalse(self.root.exists())

    def test_package_syntax_links_and_private_data_heuristics(self):
        self.assertEqual([], check())

    def test_storage_interview_and_installer_are_in_distributable(self):
        files = bundle()
        self.assertIn('install.py', files)
        for name in ('SKILL.md', 'references/interview.md', 'references/shared-storage.md'):
            for choice in ('OneDrive', 'Google Drive', 'local'):
                self.assertIn(choice, files[name].decode())
        example = json.loads(files['assets/config.example.json'])
        self.assertEqual('local', example['storage']['provider'])
        self.assertNotIn('onedrive_relative_path', example)
