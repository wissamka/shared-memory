import json
from pathlib import Path
import sys
from unittest.mock import patch

from helpers import Case, PACKAGE, bootstrap, encoded
import install_skill


class InstallationTests(Case):
    def test_manual_only_setup_does_not_request_scheduling(self):
        self.c['scheduling_mode'] = 'manual'
        self.setup_vault()
        state = json.loads((self.root / '.memory-state/config.json').read_bytes())
        self.assertEqual('manual', state['scheduling_mode'])
        schedule = (self.root / 'Automation/Schedule.md').read_text(encoding='utf-8')
        handoff = (self.root / 'Working/Handoff.md').read_text(encoding='utf-8')
        self.assertIn('**manual**', schedule)
        self.assertNotIn('next run: pending', schedule)
        self.assertNotIn('requested daily schedule', handoff)
        self.c['scheduling_mode'] = 'invented'
        with self.assertRaises(ValueError):
            bootstrap.validate(self.c)

    def test_every_storage_provider_reaches_generated_files(self):
        for provider in ('onedrive', 'google-drive', 'dropbox', 'icloud', 'network-share', 'other', 'local'):
            with self.subTest(provider=provider):
                self.c['storage'] = {'provider': provider, 'relative_path': 'Obsidian/Memory' if provider != 'local' else ''}
                files = bootstrap.build(self.c, self.root, '2030-04-02T00:00:00Z')
                state = json.loads(files['.memory-state/config.json'])
                self.assertEqual(self.c['storage'], state['storage'])
                self.assertIn(provider, bootstrap.startup(self.c, self.root))
                for name in ('Automation/Daily review prompt.md', 'Automation/Startup instructions.md'):
                    self.assertIn(f'`{provider}`', files[name].decode())
                    self.assertNotIn('OneDrive-relative', files[name].decode())

    def test_legacy_onedrive_configuration_and_conflict(self):
        del self.c['storage']
        self.c['onedrive_relative_path'] = 'Obsidian/Memory'
        bootstrap.validate(self.c)
        self.assertIn('Storage provider: `onedrive`', bootstrap.startup(self.c, self.root))
        self.c['storage'] = {'provider': 'google-drive', 'relative_path': 'Obsidian/Memory'}
        with self.assertRaises(ValueError):
            bootstrap.plan(self.c)
        self.assertFalse(self.root.exists())

    def test_invalid_storage_shapes_and_relative_paths(self):
        for value in ([], 'google-drive', {'provider': 'unsupported'}, {'provider': 'local', 'relative_path': []}):
            self.c['storage'] = value
            with self.assertRaises(ValueError):
                bootstrap.validate(self.c)
        self.c['storage'] = {'provider': 'local'}
        self.c['vault_path'] = 'relative-vault'
        with self.assertRaises(ValueError):
            bootstrap.plan(self.c)

    def test_canonical_copy_can_resume_setup(self):
        self.setup_vault()
        profile = self.root / 'Personal/Profile.md'
        profile.write_bytes(profile.read_bytes() + b'\nKeep this edit.\n')
        missing = self.root / 'Topics/Work/Overview.md'
        missing.unlink()
        setup = self.base / 'setup.json'
        setup.write_bytes(encoded(self.c))
        self.cli(self.root / 'Procedures/shared-memory/scripts/bootstrap.py', '--config', setup, '--apply')
        self.assertIn(b'Keep this edit.', profile.read_bytes())
        self.assertTrue(missing.exists())

    def test_install_preview_then_multiple_targets_and_repeat(self):
        targets = [self.base / 'codex skills/shared-memory', self.base / 'claude skills/shared-memory']
        self.quiet(install_skill.install, targets)
        self.assertTrue(all(not p.exists() for p in targets))
        self.quiet(install_skill.install, targets, True)
        expected = install_skill.bundle()
        for target in targets:
            self.assertEqual(expected, {name: (target / name).read_bytes() for name in expected})
            self.assertFalse((target / '.git').exists())
            self.assertFalse((target / 'tests').exists())
        self.assertEqual([], self.quiet(install_skill.install, targets, True))

    def test_default_harness_destinations(self):
        self.assertEqual(self.base / '.agents/skills/shared-memory', install_skill.default_target('codex', self.base))
        self.assertEqual(self.base / '.claude/skills/shared-memory', install_skill.default_target('claude', self.base))

    def test_installer_repairs_interruption(self):
        target = self.base / 'skill'
        changes = self.quiet(install_skill.install, [target])
        marker, data = changes[0]
        target.mkdir()
        marker.write_bytes(data)
        self.quiet(install_skill.install, [target], True)
        self.assertEqual((PACKAGE / 'SKILL.md').read_bytes(), (target / 'SKILL.md').read_bytes())

    def test_installer_preserves_edits_and_unmanaged_folders(self):
        target = self.base / 'skill'
        self.quiet(install_skill.install, [target], True)
        skill = target / 'SKILL.md'
        skill.write_bytes(b'Owner edits')
        with self.assertRaises(ValueError):
            self.quiet(install_skill.install, [target], True)
        self.assertEqual(b'Owner edits', skill.read_bytes())
        other = self.base / 'unmanaged'
        other.mkdir()
        (other / 'keep').write_bytes(b'Original')
        with self.assertRaises(ValueError):
            self.quiet(install_skill.install, [other], True)
        self.assertEqual(['keep'], [p.name for p in other.iterdir()])

    def test_installer_preflights_all_destinations(self):
        target = self.base / 'new'
        invalid = self.base / 'invalid'
        invalid.write_bytes(b'Existing file')
        with self.assertRaises(ValueError):
            self.quiet(install_skill.install, [target, invalid], True)
        self.assertFalse(target.exists())

    def test_installer_rejects_overlap_and_relative_destinations(self):
        for paths in ([PACKAGE], [PACKAGE / 'child'], [self.base, self.base / 'child'],
                      [self.base, self.base], [Path('relative')], []):
            with self.assertRaises(ValueError):
                self.quiet(install_skill.install, paths)

    def test_interactive_installer_can_cancel_or_accept(self):
        target = self.base / 'interactive'
        with patch.object(sys, 'argv', ['install.py']), patch('sys.stdin.isatty', return_value=True):
            with patch('builtins.input', side_effect=['4', str(target), 'n']):
                self.assertEqual(0, self.quiet(install_skill.main))
            self.assertFalse(target.exists())
            with patch('builtins.input', side_effect=['4', str(target), 'yes']):
                self.assertEqual(0, self.quiet(install_skill.main))
            self.assertTrue((target / 'SKILL.md').exists())

    def test_installer_cli_and_no_terminal_error(self):
        target = self.base / 'cli-skill'
        self.cli(PACKAGE / 'install.py', '--target', target)
        self.assertFalse(target.exists())
        self.cli(PACKAGE / 'install.py', '--target', target, '--apply')
        self.assertTrue((target / 'scripts/bootstrap.py').exists())
        self.cli(PACKAGE / 'install.py', expected=2)

    def test_package_cannot_be_harness_binding(self):
        self.c['harness_targets'] = [{'kind': 'codex', 'path': str(PACKAGE / 'AGENTS.md')}]
        with self.assertRaises(ValueError):
            bootstrap.plan(self.c)
        self.assertFalse(self.root.exists())
