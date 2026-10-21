import json
import os
from pathlib import Path
import shutil
import stat
from unittest.mock import patch

from helpers import Case, PACKAGE, bootstrap, encoded
import connect_harness


class ConnectionTests(Case):
    def target(self):
        return self.base / 'new-device' / 'CLAUDE.md'

    def connect(self, target=None, apply=True):
        return connect_harness.connect(self.root, target or self.target(), 'claude', self.editor, apply)

    def test_preview_then_bind_preserves_profile_fingerprint_and_startup(self):
        self.setup_vault()
        target = self.target()
        target.parent.mkdir()
        original = b'# Existing instructions\r\nPreserve exact bytes.\r\n'
        target.write_bytes(original)
        snapshots = {p: p.read_bytes() for p in (self.root / 'Personal').glob('*.md')}
        marker = self.root / bootstrap.MARKER
        marker_before = marker.read_bytes()
        preview = self.connect(apply=False)
        self.assertEqual(original, target.read_bytes())
        self.assertFalse(Path(preview['binding_record']).exists())
        applied = self.connect()
        self.assertTrue(target.read_bytes().startswith(original))
        binding = json.loads(Path(applied['binding_record']).read_bytes())
        self.assertEqual('connected', binding['status'])
        self.assertEqual(self.editor, binding['editor'])
        self.assertEqual(str(self.root), binding['vault_path'])
        self.assertEqual(marker_before, marker.read_bytes())
        self.assertEqual(snapshots, {p: p.read_bytes() for p in snapshots})
        self.assertIn('unverified', applied['instruction_loading'])

    def test_repeat_preserves_new_user_text_and_original_binding_receipt(self):
        self.setup_vault()
        applied = self.connect()
        target = self.target()
        record = Path(applied['binding_record'])
        original_receipt = record.read_bytes()
        target.write_bytes(target.read_bytes() + b'\nNew unrelated rule.\n')
        before = target.read_bytes()
        self.editor = {**self.editor, 'session_id': 'another-fictional-editor-session'}
        repeated = self.connect()
        self.assertFalse(repeated['startup_change'])
        self.assertEqual(before, target.read_bytes())
        self.assertEqual(original_receipt, record.read_bytes())

    def test_roamed_vault_new_local_path_uses_live_rules_without_bootstrap(self):
        self.setup_vault()
        old_root = self.root
        self.root = self.base / 'another-device' / 'same-roamed-vault'
        shutil.copytree(old_root, self.root)
        rules = self.root / 'rules.md'
        rules.write_text(rules.read_text().replace('Capture mode: **durable**', 'Capture mode: **explicit**'), encoding='utf-8')
        marker = (self.root / bootstrap.MARKER).read_bytes()
        self.connect()
        text = self.target().read_text(encoding='utf-8')
        self.assertIn(str(self.root), text)
        self.assertNotIn(str(old_root), text)
        self.assertIn('Capture mode: explicit.', text)
        self.assertEqual(marker, (self.root / bootstrap.MARKER).read_bytes())

    def test_rejects_conflicting_or_partial_blocks_without_mutation(self):
        self.setup_vault()
        target = self.target()
        target.parent.mkdir()
        for content in (bootstrap.BEGIN + '\ninterrupted',
                        bootstrap.BEGIN + '\nAnother vault.\n' + bootstrap.END,
                        bootstrap.END):
            target.write_text(content, encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'Conflicting or partial'):
                self.connect()
            self.assertEqual(content, target.read_text(encoding='utf-8'))
        self.assertFalse((self.root / '.memory-state/bindings').exists())

    def test_rejects_vault_package_relative_and_symlink_targets(self):
        self.setup_vault()
        for target in (self.root / 'AGENTS.md', PACKAGE / 'fictional-binding.md', Path('relative.md')):
            with self.assertRaises(ValueError):
                self.connect(target)
        other = self.base / 'do-not-touch.md'
        other.write_text('Keep me', encoding='utf-8')
        symlink = self.base / 'symlink.md'
        try:
            symlink.symlink_to(other)
        except OSError:
            self.skipTest('Platform does not grant symlink creation')
        with self.assertRaises(ValueError):
            self.connect(symlink)
        self.assertEqual('Keep me', other.read_text(encoding='utf-8'))

    def test_ambiguous_live_capture_mode_requires_review(self):
        self.setup_vault()
        rules = self.root / 'rules.md'
        rules.write_bytes(rules.read_bytes() + b'\nCapture mode: **explicit**\n')
        with self.assertRaisesRegex(ValueError, 'Resolve one'):
            self.connect()
        self.assertFalse(self.target().exists())

    def test_failed_receipt_is_recoverable_without_duplicate_startup(self):
        self.setup_vault()
        real_create = connect_harness.create_once

        def failure(path, data):
            if 'bindings' in path.parts:
                raise OSError('Synthetic disk failure at binding receipt')
            return real_create(path, data)

        with patch('connect_harness.create_once', side_effect=failure):
            with self.assertRaises(OSError):
                self.connect()
        startup = self.target().read_bytes()
        result = self.connect()
        self.assertEqual(startup, self.target().read_bytes())
        self.assertTrue(Path(result['binding_record']).exists())
        self.assertEqual(1, startup.count(bootstrap.BEGIN.encode()))

    def test_malformed_binding_record_blocks_before_startup_change(self):
        self.setup_vault()
        planned = self.connect(apply=False)
        record = Path(planned['binding_record'])
        record.parent.mkdir(parents=True)
        record.write_bytes(encoded({'version': 1}))
        with self.assertRaisesRegex(ValueError, 'Different existing binding'):
            self.connect()
        self.assertFalse(self.target().exists())

    def test_atomic_startup_failure_before_replace_leaves_original_then_retries(self):
        target = self.base / 'AGENTS.md'
        original = b'# Original\nNever remove this.\n'
        target.write_bytes(original)
        self.c['harness_targets'] = [{'kind': 'codex', 'path': str(target)}]
        with patch('bootstrap.os.replace', side_effect=OSError('Synthetic interrupted publish')):
            with self.assertRaises(OSError):
                self.setup_vault()
        self.assertEqual(original, target.read_bytes())
        self.assertEqual([], list(self.base.glob('.memory-startup-*')))
        self.setup_vault()
        self.assertTrue(target.read_bytes().startswith(original))
        self.assertEqual(1, target.read_bytes().count(bootstrap.BEGIN.encode()))

    def test_failure_after_atomic_replace_retries_without_duplicate(self):
        target = self.base / 'AGENTS.md'
        target.write_bytes(b'Keep this.\n')
        self.c['harness_targets'] = [{'kind': 'codex', 'path': str(target)}]
        original_replace = os.replace

        def fail_after(source, destination):
            original_replace(source, destination)
            raise OSError('Synthetic interruption after rename')

        with patch('bootstrap.os.replace', side_effect=fail_after):
            with self.assertRaises(OSError):
                self.setup_vault()
        completed = target.read_bytes()
        self.setup_vault()
        self.assertEqual(completed, target.read_bytes())
        self.assertEqual(1, completed.count(bootstrap.BEGIN.encode()))

    def test_concurrent_startup_edit_during_temp_write_is_preserved(self):
        target = self.base / 'AGENTS.md'
        target.write_bytes(b'Original.\n')

        def concurrent_change(_fd):
            target.write_bytes(b'Other user edit.\n')

        with patch('bootstrap.os.fsync', side_effect=concurrent_change):
            with self.assertRaisesRegex(ValueError, 'Target changed'):
                bootstrap.replace_startup(target, b'Original.\n', b'Original.\nNew block.\n')
        self.assertEqual(b'Other user edit.\n', target.read_bytes())
        self.assertEqual([], list(self.base.glob('.memory-startup-*')))

    def test_startup_replacement_preserves_existing_mode(self):
        if os.name == 'nt':
            self.skipTest('POSIX mode semantics are unavailable on Windows')
        target = self.base / 'AGENTS.md'
        target.write_bytes(b'Original.\n')
        target.chmod(0o640)
        bootstrap.replace_startup(target, b'Original.\n', b'Original.\nNew block.\n')
        self.assertEqual(0o640, stat.S_IMODE(target.stat().st_mode))

    def test_connection_cli_preview_apply_and_clean_failures(self):
        self.setup_vault()
        editor = self.base / 'editor.local.json'
        editor.write_bytes(encoded(self.editor))
        args = ['--vault', self.root, '--target', self.target(), '--kind', 'claude', '--editor', editor]
        self.cli(PACKAGE / 'scripts/connect_harness.py', *args)
        self.assertFalse(self.target().exists())
        self.cli(PACKAGE / 'scripts/connect_harness.py', *args, '--apply')
        self.assertTrue(self.target().exists())
        editor.write_bytes(encoded([]))
        self.cli(PACKAGE / 'scripts/connect_harness.py', *args, '--apply', expected=1)

    def test_initial_bootstrap_records_bindings_and_repairs_only_missing_receipt(self):
        target = self.target()
        self.c['harness_targets'] = [{'kind': 'claude', 'path': str(target)}]
        self.setup_vault()
        records = list((self.root / '.memory-state/bindings').glob('*.json'))
        self.assertEqual(1, len(records))
        record = json.loads(records[0].read_bytes())
        self.assertEqual(str(target), record['target_path'])
        self.assertEqual(self.editor, record['editor'])
        original = target.read_bytes()
        records[0].unlink()
        self.setup_vault()
        self.assertEqual(original, target.read_bytes())
        self.assertTrue(records[0].exists())
        self.assertFalse(self.connect()['startup_change'])
