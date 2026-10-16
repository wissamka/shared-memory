from datetime import datetime, timezone
import json
import os
from unittest.mock import patch

from helpers import Case, PACKAGE, encoded, memory
from common import create_once
from import_sessions import collect, extract
import install_skill


class ResilienceTests(Case):
    def events(self):
        return [
            {'type': 'session_meta', 'payload': {'id': 'fictional-export-session'}},
            {'type': 'turn_context', 'payload': {'model': 'fictional-model-a'}},
            {'type': 'response_item', 'timestamp': '2030-04-02T12:00:00Z',
             'payload': {'type': 'message', 'role': 'assistant', 'channel': 'final',
                         'content': [{'type': 'output_text', 'text': 'Visible answer'}]}}
        ]

    def export(self, path, events, **kwargs):
        path.write_text('\n'.join(json.dumps(x, **kwargs) for x in events), encoding='utf-8')

    def test_failed_flush_never_publishes_partial_final_file(self):
        target = self.base / 'atomic.json'
        with patch('common.os.fsync', side_effect=OSError('simulated disk full')):
            with self.assertRaises(OSError):
                create_once(target, b'Complete record')
        self.assertFalse(target.exists())
        self.assertEqual([], list(self.base.glob('.memory-write-*')))
        self.assertTrue(create_once(target, b'Complete record'))

    def test_unsupported_publish_fails_without_partial_file(self):
        target = self.base / 'atomic.json'
        with patch('common.os.link', side_effect=OSError('operation unsupported')):
            with self.assertRaises(OSError):
                create_once(target, b'Complete record')
        self.assertFalse(target.exists())
        self.assertEqual([], list(self.base.glob('.memory-write-*')))

    def test_concurrent_creator_is_preserved(self):
        target = self.base / 'atomic.json'
        link = os.link

        def race(source, destination):
            target.write_bytes(b'Other writer')
            link(source, destination)

        with patch('common.os.link', side_effect=race):
            with self.assertRaisesRegex(ValueError, 'Concurrent content differs'):
                create_once(target, b'My record')
        self.assertEqual(b'Other writer', target.read_bytes())
        self.assertEqual([], list(self.base.glob('.memory-write-*')))

    def test_concurrent_identical_creator_is_idempotent(self):
        target = self.base / 'atomic.json'
        link = os.link

        def race(source, destination):
            target.write_bytes(b'Same record')
            link(source, destination)

        with patch('common.os.link', side_effect=race):
            self.assertFalse(create_once(target, b'Same record'))
        self.assertEqual(b'Same record', target.read_bytes())

    def test_import_deduplicates_copies_reformatted_json_and_telemetry(self):
        self.setup_vault()
        source = self.base / 'exports'
        source.mkdir()
        events = self.events()
        self.export(source / 'original.jsonl', events)
        first = collect('codex', source, self.root, '2030-04-02', self.editor, True)
        self.assertEqual([], first['coverage_gaps'])
        self.export(source / 'copied.jsonl', [events[0], {'type': 'telemetry'}, *events[1:]],
                    sort_keys=True, separators=(',', ':'))
        second = collect('codex', source, self.root, '2030-04-02', self.editor, True)
        self.assertEqual([], second['coverage_gaps'])
        self.assertEqual(1, memory.status(self.root)['captured'])
        capture = json.loads(next((self.root / '_Inbox').glob('*.json')).read_bytes())
        self.assertIn('original.jsonl:3', capture['source_locator'])

    def test_distinct_identical_turns_are_retained(self):
        self.setup_vault()
        source = self.base / 'exports'
        source.mkdir()
        events = self.events()
        self.export(source / 'repeat.jsonl', [*events, events[-1]])
        collect('codex', source, self.root, '2030-04-02', self.editor, True)
        self.assertEqual(2, memory.status(self.root)['captured'])

    def test_model_changes_are_preserved_per_record(self):
        path = self.base / 'model-switch.jsonl'
        events = self.events()
        self.export(path, [*events, {'type': 'turn_context', 'payload': {'model': 'fictional-model-b'}}, events[-1]])
        records, gaps = extract(path, 'codex', datetime(2030, 4, 2, tzinfo=timezone.utc),
                                datetime(2030, 4, 3, tzinfo=timezone.utc), self.editor)
        self.assertEqual([], gaps)
        self.assertEqual(['fictional-model-a', 'fictional-model-b'], [x['model'] for x in records])

    def test_unknown_sessions_in_different_files_do_not_collapse(self):
        self.setup_vault()
        source = self.base / 'exports'
        source.mkdir()
        for name in ('one', 'two'):
            self.export(source / (name + '.jsonl'), self.events()[1:])
        result = collect('codex', source, self.root, '2030-04-02', self.editor, True)
        self.assertEqual(2, memory.status(self.root)['captured'])
        self.assertEqual(2, len(result['coverage_gaps']))

    def test_malformed_metadata_and_timestamp_report_gaps(self):
        self.setup_vault()
        source = self.base / 'exports'
        source.mkdir()
        events = self.events()
        events[0]['payload']['id'] = []
        events[1]['payload']['model'] = {}
        malformed = {**events[-1], 'timestamp': 42}
        self.export(source / 'bad.jsonl', [*events, malformed, []])
        result = collect('codex', source, self.root, '2030-04-02', self.editor, True)
        self.assertEqual(1, memory.status(self.root)['captured'])
        self.assertEqual(3, len(result['coverage_gaps']))

    def test_missing_source_and_changed_input_prevent_completion(self):
        receipt = self.review()
        item = next((self.root / '_Inbox').glob('*.json'))
        before = item.read_bytes()
        item.unlink()
        with self.assertRaises(OSError):
            memory.complete(self.root, receipt)
        item.write_bytes(before + b' ')
        with self.assertRaises(ValueError):
            memory.complete(self.root, receipt)
        self.assertFalse((self.root / '.memory-state/receipts').exists())

    def test_existing_symlink_inside_install_destination_rejected(self):
        target = self.base / 'skill'
        self.quiet(install_skill.install, [target], True)
        script = target / 'scripts/memory.py'
        script.unlink()
        external = self.base / 'external.py'
        external.write_bytes(b'Keep external')
        try:
            script.symlink_to(external)
        except OSError:
            self.skipTest('Platform does not grant symlink creation')
        with self.assertRaises(ValueError):
            self.quiet(install_skill.install, [target], True)
        self.assertEqual(b'Keep external', external.read_bytes())

    def test_invalid_capture_file_is_not_silently_ignored(self):
        self.setup_vault()
        path = self.root / '_Inbox/broken.json'
        path.write_bytes(encoded([]))
        self.cli(PACKAGE / 'scripts/memory.py', 'prepare', '--vault', self.root, '--date', '2030-04-02', expected=1)
