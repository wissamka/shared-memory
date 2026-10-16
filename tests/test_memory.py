import contextlib
import copy
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import bootstrap
import memory
from common import digest, encoded
from import_sessions import collect


class MemoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name).resolve()
        self.root = self.base / 'Vault with spaces'
        package = Path(__file__).resolve().parents[1]
        self.c = json.loads((package / 'assets/config.example.json').read_text())
        self.c['vault_path'] = str(self.root)
        self.c['timezone'] = 'America/New_York'
        self.editor = self.c['provenance']
        self.data = json.loads((package / 'assets/capture.example.json').read_text())

    def tearDown(self):
        self.temp.cleanup()

    def install(self):
        with contextlib.redirect_stdout(io.StringIO()):
            bootstrap.install(self.c, apply=True)

    def test_preview_has_no_side_effects(self):
        with contextlib.redirect_stdout(io.StringIO()):
            bootstrap.install(self.c)
        self.assertFalse(self.root.exists())

    def test_bootstrap_preserves_startup_and_edited_notes(self):
        hook = self.base / 'agent-home/AGENTS.md'
        hook.parent.mkdir()
        hook.write_bytes(b'# Existing\r\nKeep this exactly.\r\n')
        original = hook.read_bytes()
        self.c['harness_targets'] = [{'kind': 'codex', 'path': str(hook)}]
        self.install()
        saved = hook.read_bytes()
        self.assertTrue(saved.startswith(original))
        profile = self.root / 'Personal/Profile.md'
        profile.write_text(profile.read_text() + '\nUser update.\n')
        self.install()
        self.assertEqual(saved, hook.read_bytes())
        self.assertIn('User update.', profile.read_text())

    def test_nonempty_unrelated_vault_rejected(self):
        self.root.mkdir()
        (self.root / 'keep.md').write_text('Original')
        with self.assertRaises(ValueError):
            self.install()
        self.assertEqual(['keep.md'], [p.name for p in self.root.iterdir()])

    def test_conflicting_hook_preflight_writes_nothing(self):
        hook = self.base / 'CLAUDE.md'
        hook.write_text(bootstrap.BEGIN + '\nother setup\n' + bootstrap.END)
        self.c['harness_targets'] = [{'kind': 'claude', 'path': str(hook)}]
        with self.assertRaises(ValueError):
            self.install()
        self.assertFalse(self.root.exists())

    def test_overlapping_paths_rejected(self):
        self.c['harness_targets'] = [{'kind': 'codex', 'path': str(self.base / 'target')},
                                    {'kind': 'claude', 'path': str(self.base / 'target/CLAUDE.md')}]
        with self.assertRaises(ValueError):
            self.install()
        self.assertFalse(self.root.exists())

    def test_topic_traversal_and_reserved_names_rejected(self):
        for topic in ('../escape', 'A/B', 'CON', 'COM1', 'Topic '):
            self.c['topics'] = [topic]
            with self.assertRaises(ValueError):
                bootstrap.plan(self.c)

    def test_changed_config_rejected(self):
        self.install()
        self.c['preferred_name'] = 'Another user'
        with self.assertRaises(ValueError):
            self.install()

    def test_interrupted_setup_resumes(self):
        root, changes = bootstrap.plan(self.c)
        marker, _, content = changes[0]
        root.mkdir()
        marker.write_bytes(content)
        self.install()
        self.assertTrue((root / '00-Hub.md').exists())

    def test_symlink_target_rejected(self):
        other = self.base / 'outside'
        other.mkdir()
        try:
            self.root.symlink_to(other, target_is_directory=True)
        except OSError:
            self.skipTest('Platform does not grant symlink creation')
        with self.assertRaises(ValueError):
            self.install()
        self.assertEqual([], list(other.iterdir()))

    def test_unknown_model_requires_explanation(self):
        self.editor['model_note'] = ''
        with self.assertRaises(ValueError):
            self.install()

    def test_capture_duplicate_and_conflict(self):
        self.install()
        first = memory.capture(self.root, self.data)
        repeated = copy.deepcopy(self.data)
        repeated['captured_by']['session_id'] = 'another-capture-session'
        self.assertEqual(first, memory.capture(self.root, repeated))
        repeated['text'] = 'Changed preference'
        with self.assertRaises(ValueError):
            memory.capture(self.root, repeated)
        self.assertEqual(1, memory.status(self.root)['captured'])

    def test_capture_repairs_missing_source_note(self):
        self.install()
        first = memory.capture(self.root, self.data)
        Path(first['session_note']).unlink()
        memory.capture(self.root, self.data)
        self.assertTrue(Path(first['session_note']).exists())

    def test_daily_window_handles_dst_and_old_pending(self):
        self.install()
        old = copy.deepcopy(self.data)
        old['source_date'] = '2030-03-01T01:00:00-05:00'
        memory.capture(self.root, old)
        future = copy.deepcopy(old)
        future.update(source_id='future', source_date='2030-03-11T00:00:00-04:00')
        memory.capture(self.root, future)
        result = memory.prepare(self.root, '2030-03-10')
        start = datetime.fromisoformat(result['window_start']).astimezone(timezone.utc)
        end = datetime.fromisoformat(result['window_end']).astimezone(timezone.utc)
        self.assertEqual(23 * 3600, (end - start).total_seconds())
        self.assertEqual(1, len(result['inputs']))
        self.assertEqual('2030-03-01T01:00:00-05:00', result['inputs'][0]['source_date'])

    def setup_review(self):
        self.install()
        item = memory.capture(self.root, self.data)
        run = memory.prepare(self.root, '2030-04-02')
        destination = self.root / 'Personal/Preferences.md'
        # Mimic an agent's verified, source-attributed synthesis; no model invoked.
        destination.write_text(destination.read_text() + '\nDecision briefs: one page. Source: fictional-session-1:turn-3:preference.\n')
        return {'run_id': run['run_id'], 'editor': self.editor, 'coverage_gaps': [], 'results': [
            {'input_id': item['input_id'], 'outcome': 'promoted', 'reason': 'Explicit preference saved',
             'destinations': [{'path': 'Personal/Preferences.md', 'sha256': digest(destination.read_bytes())}]}]}

    def test_review_receipt_retry_and_no_duplicate_pending(self):
        receipt = self.setup_review()
        first = memory.complete(self.root, receipt)
        self.assertEqual(first, memory.complete(self.root, receipt))
        self.assertEqual(0, memory.status(self.root)['pending'])
        self.assertEqual([], memory.prepare(self.root, '2030-04-03')['inputs'])

    def test_missing_or_changed_destination_keeps_pending(self):
        receipt = self.setup_review()
        (self.root / 'Personal/Preferences.md').write_text('Concurrent edit')
        with self.assertRaises(ValueError):
            memory.complete(self.root, receipt)
        self.assertEqual(1, memory.status(self.root)['pending'])

    def test_partial_receipt_cannot_skip_input(self):
        receipt = self.setup_review()
        receipt['results'] = []
        with self.assertRaises(ValueError):
            memory.complete(self.root, receipt)
        self.assertEqual(1, memory.status(self.root)['pending'])

    def test_destination_traversal_rejected(self):
        receipt = self.setup_review()
        receipt['results'][0]['destinations'][0]['path'] = '../outside.md'
        with self.assertRaises(ValueError):
            memory.complete(self.root, receipt)

    def test_coverage_gap_preserved_as_partial(self):
        receipt = self.setup_review()
        receipt['coverage_gaps'] = ['Other authorized account unavailable']
        result = memory.complete(self.root, receipt)
        self.assertEqual('partial', result['status'])
        self.assertEqual(receipt['coverage_gaps'], result['coverage_gaps'])

    def test_unknown_outcome_or_unverified_promotion_rejected(self):
        receipt = self.setup_review()
        receipt['results'][0]['destinations'] = []
        with self.assertRaises(ValueError):
            memory.complete(self.root, receipt)

    def test_local_import_filters_reasoning_and_old_session_creation(self):
        self.install()
        source = self.base / 'exports'
        source.mkdir()
        lines = [
            {'type': 'session_meta', 'payload': {'id': 'fictional-old-session'}, 'timestamp': '2030-03-01T00:00:00Z'},
            {'type': 'turn_context', 'payload': {'model': 'example-exact-model'}},
            {'type': 'response_item', 'timestamp': '2030-04-02T12:00:00Z', 'payload': {'type': 'message', 'role': 'user', 'content': [{'type': 'input_text', 'text': 'Remember my brief format.'}]}},
            {'type': 'response_item', 'timestamp': '2030-04-02T12:00:01Z', 'payload': {'type': 'message', 'role': 'assistant', 'channel': 'analysis', 'content': [{'type': 'output_text', 'text': 'PRIVATE REASONING'}]}},
            {'type': 'response_item', 'timestamp': '2030-04-02T12:00:02Z', 'payload': {'type': 'message', 'role': 'assistant', 'channel': 'final', 'content': [{'type': 'output_text', 'text': 'Preference saved.'}]}},
            {'type': 'response_item', 'timestamp': '2030-04-02T12:00:03Z', 'payload': {'type': 'message', 'role': 'system', 'content': [{'type': 'input_text', 'text': 'SYSTEM CONTENT'}]}}
        ]
        (source / 'old-session.jsonl').write_text('\n'.join(json.dumps(x) for x in lines))
        preview = collect('codex', source, self.root, '2030-04-02', self.editor)
        self.assertEqual(2, preview['visible_messages'])
        self.assertEqual(0, memory.status(self.root)['captured'])
        collect('codex', source, self.root, '2030-04-02', self.editor, apply=True)
        saved = '\n'.join(p.read_text() for p in (self.root / '_Inbox').glob('*.json'))
        self.assertNotIn('PRIVATE REASONING', saved)
        self.assertNotIn('SYSTEM CONTENT', saved)
        self.assertIn('example-exact-model', saved)
        self.assertEqual(2, memory.status(self.root)['captured'])

    def test_claude_import_ignores_tool_results_and_thinking(self):
        self.install()
        source = self.base / 'exports'
        source.mkdir()
        events = [{'type': 'assistant', 'sessionId': 'fictional-session', 'timestamp': '2030-04-02T12:00:00Z',
                   'message': {'model': 'example-model', 'content': [{'type': 'thinking', 'thinking': 'HIDDEN'},
                                                                  {'type': 'text', 'text': 'Visible answer'}]}},
                  {'type': 'user', 'timestamp': '2030-04-02T12:00:00Z', 'message': {'content': [{'type': 'tool_result', 'content': 'TOOL SECRET'}]}}]
        (source / 'session.jsonl').write_text('\n'.join(json.dumps(x) for x in events) + '\n{broken')
        report = collect('claude', source, self.root, '2030-04-02', self.editor, True)
        self.assertEqual(1, report['visible_messages'])
        self.assertTrue(report['coverage_gaps'])
        saved = '\n'.join(p.read_text() for p in (self.root / '_Inbox').glob('*.json'))
        self.assertNotIn('HIDDEN', saved)
        self.assertNotIn('TOOL SECRET', saved)


if __name__ == '__main__':
    unittest.main()
