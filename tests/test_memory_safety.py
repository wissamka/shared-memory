import json
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

from helpers import Case, PACKAGE, encoded, memory
from common import digest
import suppression


class MemorySafetyTests(Case):
    def make_receipt(self, run):
        return {'run_id': run['run_id'], 'editor': self.editor, 'coverage_gaps': [], 'results': [
            {'input_id': item['input_id'], 'outcome': 'no_change', 'reason': 'Fictional source checked',
             'destinations': []} for item in run['inputs']]}

    def test_forget_preview_is_read_only_and_reports_maintained_notes(self):
        receipt = self.review()
        memory.complete(self.root, receipt)
        before = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        plan = memory.forget(self.root, self.editor, source_id=self.data['source_id'])
        self.assertEqual('preview', plan['mode'])
        self.assertEqual(4, len(plan['files']))
        self.assertTrue(plan['maintained_notes_require_review'])
        self.assertIn('Personal/Preferences.md', plan['notes_to_review'])
        after = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        self.assertEqual(before, after)

    def test_forget_suppresses_reimport_and_preserves_maintained_notes(self):
        receipt = self.review()
        memory.complete(self.root, receipt)
        destination = self.root / 'Personal/Preferences.md'
        original_note = destination.read_bytes()
        first = memory.forget(self.root, self.editor, source_id=self.data['source_id'], apply=True)
        self.assertEqual(4, len(first['removed']))
        self.assertTrue(suppression.is_suppressed(self.root, self.data))
        blocked = memory.capture(self.root, self.data)
        self.assertEqual('suppressed', blocked['status'])
        self.assertFalse((self.root / f'_Inbox/{blocked["input_id"]}.json').exists())
        self.assertFalse((self.root / f'Sessions/{blocked["input_id"]}.md').exists())
        self.assertEqual(original_note, destination.read_bytes())
        self.assertEqual(0, memory.status(self.root)['captured'])
        self.assertEqual([], memory.prepare(self.root, '2030-04-02')['inputs'])

    def test_tombstones_are_idempotent_hashes_without_payload_or_extra_metadata(self):
        self.setup_vault()
        memory.capture(self.root, self.data)
        first = memory.forget(self.root, {**self.editor, 'extra': 'forgotten-payload'},
                              source_id=self.data['source_id'], apply=True)
        tombstone = next((self.root / '.memory-state/suppressions').glob('*.json'))
        before = tombstone.read_bytes()
        repeated = memory.forget(self.root, {**self.editor, 'agent': 'another-editor'},
                                 source_id=self.data['source_id'], apply=True)
        self.assertEqual(before, tombstone.read_bytes())
        self.assertEqual(first['suppression_id'], repeated['suppression_id'])
        self.assertEqual([], repeated['removed'])
        for path in (self.root / '.memory-state').rglob('*.json'):
            saved = path.read_text(encoding='utf-8')
            self.assertNotIn(self.data['source_id'], saved)
            self.assertNotIn(self.data['text'], saved)
            self.assertNotIn('forgotten-payload', saved)

    def test_session_suppression_is_scoped_and_blocks_later_turns(self):
        self.setup_vault()
        second = {**self.data, 'source_id': 'fictional-second-turn'}
        other_harness = {**self.data, 'source_id': 'fictional-other-harness', 'harness': 'Other harness'}
        other_session = {**self.data, 'source_id': 'fictional-other-session', 'session_id': 'other-session'}
        for data in (self.data, second, other_harness, other_session):
            memory.capture(self.root, data)
        memory.forget(self.root, self.editor, session_id=self.data['session_id'],
                      harness=self.data['harness'], apply=True)
        self.assertTrue(suppression.is_suppressed(self.root, second))
        self.assertTrue(suppression.is_suppressed(self.root, {**second, 'source_id': 'later-turn'}))
        self.assertFalse(suppression.is_suppressed(self.root, other_harness))
        self.assertFalse(suppression.is_suppressed(self.root, other_session))
        self.assertEqual(2, memory.status(self.root)['captured'])
        self.assertEqual('suppressed', memory.capture(self.root, {**second, 'source_id': 'later-turn'})['status'])

    def test_unknown_session_cannot_suppress_unrelated_unknown_sources(self):
        self.setup_vault()
        for session_id, harness in [('unknown', 'Codex'), ('session', 'unknown'), ('session', '')]:
            with self.assertRaises(ValueError):
                memory.forget(self.root, self.editor, session_id=session_id, harness=harness, apply=True)
        self.assertFalse((self.root / '.memory-state/suppressions').exists())

    def test_mixed_run_forget_retains_other_source_and_returns_it_to_pending(self):
        self.setup_vault()
        memory.capture(self.root, self.data)
        other = memory.capture(self.root, {**self.data, 'source_id': 'fictional-unaffected'})
        run = memory.prepare(self.root, '2030-04-02')
        memory.complete(self.root, self.make_receipt(run))
        memory.forget(self.root, self.editor, source_id=self.data['source_id'], apply=True)
        state = memory.status(self.root)
        self.assertEqual((1, 0, 1), (state['captured'], state['reviewed'], state['pending']))
        self.assertTrue(Path(other['capture']).exists())
        self.assertEqual([other['input_id']], [x['input_id'] for x in memory.prepare(self.root, '2030-04-02')['inputs']])

    def test_interrupted_forget_never_promotes_residuals_and_retries(self):
        self.setup_vault()
        captured = memory.capture(self.root, self.data)
        unlink = Path.unlink
        failed = False

        def fail_once(path, *args, **kwargs):
            nonlocal failed
            if path.suffix == '.md' and path.parent.name == 'Sessions' and not failed:
                failed = True
                raise OSError('Simulated interruption')
            return unlink(path, *args, **kwargs)

        with patch.object(Path, 'unlink', fail_once):
            with self.assertRaises(OSError):
                memory.forget(self.root, self.editor, session_id=self.data['session_id'],
                              harness=self.data['harness'], apply=True)
        self.assertTrue(Path(captured['capture']).exists())
        self.assertEqual('suppressed', memory.capture(self.root, self.data)['status'])
        self.assertEqual([], memory.prepare(self.root, '2030-04-02')['inputs'])
        self.assertFalse(memory.status(self.root)['healthy'])
        memory.forget(self.root, self.editor, session_id=self.data['session_id'],
                      harness=self.data['harness'], apply=True)
        self.assertFalse(Path(captured['session_note']).exists())
        self.assertFalse(Path(captured['capture']).exists())
        self.assertTrue(memory.status(self.root)['healthy'])

    def test_old_manifest_cannot_complete_after_suppression_only(self):
        self.setup_vault()
        memory.capture(self.root, self.data)
        run = memory.prepare(self.root, '2030-04-02')
        with suppression.state_lock(self.root):
            suppression.save(self.root, suppression.selector(source_id=self.data['source_id']), self.editor)
        with self.assertRaisesRegex(ValueError, 'suppressed'):
            memory.complete(self.root, self.make_receipt(run))

    def test_stale_overlap_rejected_and_exact_replay_remains_valid(self):
        self.setup_vault()
        memory.capture(self.root, self.data)
        first = memory.prepare(self.root, '2030-04-02')
        memory.capture(self.root, {**self.data, 'source_id': 'fictional-later'})
        second = memory.prepare(self.root, '2030-04-02')
        receipt = self.make_receipt(second)
        done = memory.complete(self.root, receipt)
        with self.assertRaisesRegex(ValueError, 'Stale review'):
            memory.complete(self.root, self.make_receipt(first))
        self.assertEqual(done, memory.complete(self.root, receipt))
        self.assertEqual(1, len(list((self.root / '.memory-state/receipts').glob('*.json'))))

    def test_local_operation_lock_blocks_another_process_then_releases(self):
        self.setup_vault()
        script = ('import sys; from pathlib import Path; '
                  'sys.path.insert(0, sys.argv[1]); import memory; '
                  'memory.status(Path(sys.argv[2]))')
        command = [sys.executable, '-c', script, str(PACKAGE / 'scripts'), str(self.root)]
        with suppression.state_lock(self.root):
            blocked = subprocess.run(command, capture_output=True, text=True, timeout=10)
        self.assertNotEqual(0, blocked.returncode)
        self.assertIn('Another local memory operation', blocked.stderr)
        self.assertEqual(0, subprocess.run(command, capture_output=True, timeout=10).returncode)

    def test_status_validates_every_pending_capture_without_counting_corruption(self):
        self.setup_vault()
        good = memory.capture(self.root, self.data)
        (self.root / '_Inbox/broken.json').write_text('[]', encoding='utf-8')
        malformed = {**self.data, 'source_id': 'fictional-invalid', 'source_date': 'no date'}
        (self.root / f'_Inbox/{digest(malformed["source_id"].encode())}.json').write_bytes(encoded(malformed))
        (self.root / '_Inbox/bad-json.json').write_text('{', encoding='utf-8')
        state = memory.status(self.root)
        self.assertEqual((1, 1), (state['captured'], state['pending']))
        self.assertEqual(3, len(state['invalid_inputs']))
        self.assertFalse(state['healthy'])
        self.assertTrue(Path(good['capture']).exists())
        with self.assertRaises((ValueError, KeyError)):
            memory.prepare(self.root, '2030-04-02')

    def test_corrupted_suppression_state_fails_closed_even_with_empty_inbox(self):
        self.setup_vault()
        folder = self.root / '.memory-state/suppressions'
        folder.mkdir()
        (folder / 'broken.json').write_text('{}', encoding='utf-8')
        with self.assertRaises(ValueError):
            memory.capture(self.root, self.data)
        with self.assertRaises(ValueError):
            memory.prepare(self.root, '2030-04-02')
        with self.assertRaises(ValueError):
            memory.status(self.root)

    def test_cli_forget_defaults_to_preview(self):
        self.setup_vault()
        item = memory.capture(self.root, self.data)
        editor = self.base / 'editor.json'
        editor.write_bytes(encoded(self.editor))
        args = ('forget', '--vault', self.root, '--source-id', self.data['source_id'], '--editor', editor)
        preview = self.cli(PACKAGE / 'scripts/memory.py', *args)
        self.assertEqual('preview', json.loads(preview.stdout)['mode'])
        self.assertTrue(Path(item['capture']).exists())
        applied = self.cli(PACKAGE / 'scripts/memory.py', *args, '--apply')
        self.assertEqual('applied', json.loads(applied.stdout)['mode'])
        self.assertFalse(Path(item['capture']).exists())
