import json
from datetime import datetime, timezone

from helpers import Case, digest, encoded, memory
from collection import pending, record, register
from import_sessions import collect, collect_days, extract


class CollectionTests(Case):
    def source(self):
        self.setup_vault()
        source = self.base / 'exports'
        source.mkdir()
        records = [{'type': 'session_meta', 'payload': {'id': 'fictional-outage-session'}}]
        for day in range(1, 5):
            records.append({'type': 'response_item', 'timestamp': f'2030-04-0{day}T12:00:00Z',
                            'payload': {'type': 'message', 'role': 'user',
                                        'content': [{'type': 'input_text', 'text': f'Decision on day {day}'}]}})
        (source / 'events.jsonl').write_text('\n'.join(json.dumps(x) for x in records), encoding='utf-8')
        register(self.root, 'fictional-local', 'codex', '2030-04-01', self.editor, True)
        return source

    def test_register_preview_has_no_side_effect_and_empty_registry_is_unknown(self):
        self.setup_vault()
        register(self.root, 'fictional-local', 'codex', '2030-04-01', self.editor)
        self.assertFalse((self.root / '.memory-state/collection').exists())
        self.assertEqual(0, pending(self.root, '2030-04-04')['registered_sources'])

    def test_catch_up_collects_uncaptured_outage_days_without_duplicates(self):
        source = self.source()
        collect('codex', source, self.root, '2030-04-01', self.editor, True, 'fictional-local')
        row = pending(self.root, '2030-04-04')['sources'][0]
        self.assertEqual(['2030-04-02', '2030-04-03', '2030-04-04'], row['missing_days'])
        output = collect_days('codex', source, self.root, '2030-04-04', self.editor, True,
                              'fictional-local', catch_up=True)
        self.assertEqual(3, len(output['days']))
        self.assertEqual(4, memory.status(self.root)['captured'])
        repeat = collect_days('codex', source, self.root, '2030-04-04', self.editor, True,
                              'fictional-local', catch_up=True)
        self.assertEqual(['2030-04-04'], [x['date'] for x in repeat['days']])
        self.assertEqual(4, memory.status(self.root)['captured'])

    def test_preview_does_not_advance_collection_and_partial_window_stays_pending(self):
        source = self.source()
        collect('codex', source, self.root, '2030-04-01', self.editor, False, 'fictional-local')
        self.assertEqual(['2030-04-01'], pending(self.root, '2030-04-01')['sources'][0]['missing_days'])
        path = source / 'events.jsonl'
        original = path.read_text(encoding='utf-8')
        path.write_text(original + '\n{broken', encoding='utf-8')
        collect('codex', source, self.root, '2030-04-01', self.editor, True, 'fictional-local')
        self.assertEqual('2030-04-01', pending(self.root, '2030-04-01')['sources'][0]['partial_days'][0]['date'])
        path.write_text(original, encoding='utf-8')
        collect('codex', source, self.root, '2030-04-01', self.editor, True, 'fictional-local')
        self.assertEqual([], pending(self.root, '2030-04-01')['sources'][0]['partial_days'])

    def test_review_completion_does_not_clear_uncollected_day(self):
        self.source()
        run = memory.prepare(self.root, '2030-04-03')
        memory.complete(self.root, {'run_id': run['run_id'], 'editor': self.editor,
                                   'coverage_gaps': [], 'results': []})
        self.assertEqual(3, len(pending(self.root, '2030-04-03')['sources'][0]['missing_days']))

    def test_changed_scope_wrong_adapter_and_preview_record_rejected(self):
        source = self.source()
        with self.assertRaises(ValueError):
            register(self.root, 'fictional-local', 'codex', '2030-04-02', self.editor, True)
        with self.assertRaises(ValueError):
            collect('claude', source, self.root, '2030-04-02', self.editor, True, 'fictional-local')
        with self.assertRaises(ValueError):
            record(self.root, 'fictional-local', '2030-04-02', {'mode': 'preview', 'coverage_gaps': []}, self.editor)

    def test_tampered_attempt_rejected(self):
        source = self.source()
        collect('codex', source, self.root, '2030-04-01', self.editor, True, 'fictional-local')
        path = next((self.root / '.memory-state/collection/attempts').glob('*.json'))
        value = json.loads(path.read_bytes())
        value['status'] = 'partial'
        path.write_bytes(encoded(value))
        with self.assertRaisesRegex(ValueError, 'changed'):
            pending(self.root, '2030-04-01')

    def test_forgotten_session_stays_suppressed_during_repeated_collection(self):
        source = self.source()
        collect('codex', source, self.root, '2030-04-01', self.editor, True, 'fictional-local')
        memory.forget(self.root, self.editor, session_id='fictional-outage-session', harness='Codex', apply=True)
        result = collect_days('codex', source, self.root, '2030-04-04', self.editor, True,
                              'fictional-local', since='2030-04-01')
        self.assertEqual(4, sum(day['skipped_suppressed'] for day in result['days']))
        self.assertEqual(0, memory.status(self.root)['captured'])
        self.assertFalse(list((self.root / '_Inbox').glob('*.json')))

    def test_correct_hash_does_not_make_invalid_attempt_schema_valid(self):
        source = self.source()
        collect('codex', source, self.root, '2030-04-01', self.editor, True, 'fictional-local')
        path = next((self.root / '.memory-state/collection/attempts').glob('*.json'))
        original = json.loads(path.read_bytes())
        path.unlink()
        for change in ({'coverage_gaps': 'not a list'}, {'saved_messages': -1}, {'date': '2030-03-31'}):
            value = {**original, **change}
            invalid = path.with_name(digest(encoded(value)) + '.json')
            invalid.write_bytes(encoded(value))
            with self.assertRaises(ValueError):
                pending(self.root, '2030-04-01')
            invalid.unlink()

    def test_claude_mixed_supported_and_unknown_blocks_keep_text_and_report_gap(self):
        path = self.base / 'mixed.jsonl'
        path.write_text(json.dumps({'type': 'assistant', 'sessionId': 'fictional',
                        'timestamp': '2030-04-02T12:00:00Z', 'message': {'content': [
                            {'type': 'text', 'text': 'Visible decision'},
                            {'type': 'future_visible_block', 'value': 'not parsed'},
                            {'type': 'thinking', 'thinking': 'HIDDEN'},
                            {'type': 'tool_result', 'content': 'TOOL'}]}}), encoding='utf-8')
        records, gaps = extract(path, 'claude', datetime(2030, 4, 2, tzinfo=timezone.utc),
                                datetime(2030, 4, 3, tzinfo=timezone.utc), self.editor)
        self.assertEqual(['Visible decision'], [x['text'] for x in records])
        self.assertEqual(1, len(gaps))
        self.assertIn('unsupported visible content', gaps[0])

    def test_codex_mixed_content_also_reports_unknown_shape(self):
        source = self.source()
        path = source / 'events.jsonl'
        event = {'type': 'response_item', 'timestamp': '2030-04-02T12:00:00Z', 'payload': {
            'type': 'message', 'role': 'user', 'content': [{'type': 'input_text', 'text': 'Keep text'}, {'type': 'input_image'}]}}
        path.write_text(json.dumps(event), encoding='utf-8')
        result = collect('codex', source, self.root, '2030-04-02', self.editor, True, 'fictional-local')
        self.assertTrue(any('unsupported visible' in x for x in result['coverage_gaps']))
        self.assertEqual(1, memory.status(self.root)['captured'])
