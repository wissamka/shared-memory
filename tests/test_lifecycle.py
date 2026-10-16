import copy
from datetime import datetime, timezone
import json

from helpers import Case, PACKAGE, encoded, memory


class LifecycleTests(Case):
    def test_completed_receipt_remains_replayable_after_note_evolves(self):
        receipt = self.review()
        saved = memory.complete(self.root, receipt)
        destination = self.root / 'Personal/Preferences.md'
        destination.write_bytes(destination.read_bytes() + b'\nAnother sourced update.\n')
        self.assertEqual(saved, memory.complete(self.root, receipt))
        self.assertEqual(saved, memory.complete(self.root, saved))
        self.assertEqual(0, memory.status(self.root)['pending'])

    def test_reviewed_capture_modification_is_detected(self):
        receipt = self.review()
        memory.complete(self.root, receipt)
        capture = next((self.root / '_Inbox').glob('*.json'))
        data = json.loads(capture.read_bytes())
        data['text'] = 'Changed source evidence'
        capture.write_bytes(encoded(data))
        for action in (memory.status, lambda root: memory.prepare(root, '2030-04-03')):
            with self.assertRaisesRegex(ValueError, 'Input changed'):
                action(self.root)

    def test_modified_manifest_cannot_advance_checkpoint(self):
        receipt = self.review()
        path = self.root / f'.memory-state/runs/{receipt["run_id"]}.json'
        manifest = json.loads(path.read_bytes())
        manifest['coverage'] = 'invented complete coverage'
        path.write_bytes(encoded(manifest))
        with self.assertRaisesRegex(ValueError, 'manifest changed'):
            memory.complete(self.root, receipt)
        self.assertFalse((self.root / '.memory-state/receipts').exists())

    def test_receipt_with_missing_results_is_detected(self):
        receipt = self.review()
        saved = memory.complete(self.root, receipt)
        saved['results'] = []
        path = self.root / f'.memory-state/receipts/{receipt["run_id"]}.json'
        path.write_bytes(encoded(saved))
        with self.assertRaisesRegex(ValueError, 'every manifest input'):
            memory.status(self.root)

    def test_late_arrival_and_correction_stay_pending(self):
        receipt = self.review()
        memory.complete(self.root, receipt)
        for source_id, text, date in [('late-arrival', 'Earlier decision', '2030-04-01T12:00:00Z'),
                                       ('correction', 'Two-page briefs now', '2030-04-02T18:00:00Z')]:
            memory.capture(self.root, {**self.data, 'source_id': source_id, 'text': text, 'source_date': date})
        result = memory.prepare(self.root, '2030-04-03')
        self.assertEqual({'late-arrival', 'correction'}, {x['source_id'] for x in result['inputs']})
        self.assertEqual(3, memory.status(self.root)['captured'])
        self.assertEqual(2, memory.status(self.root)['pending'])

    def test_no_change_requires_a_reason_and_records_gap(self):
        receipt = self.review()
        receipt['results'][0].update(outcome='no_change', destinations=[], reason='')
        with self.assertRaises(ValueError):
            memory.complete(self.root, receipt)
        receipt['results'][0]['reason'] = 'Existing preference already contains this source'
        receipt['coverage_gaps'] = ['Other account unavailable; inventory incomplete']
        self.assertEqual('partial', memory.complete(self.root, receipt)['status'])
        self.assertEqual(0, memory.status(self.root)['pending'])

    def test_distinct_source_and_editor_provenance_survive(self):
        self.setup_vault()
        self.data.update(model='fictional-source-model', session_id='fictional-original-session',
                         as_of='2030-03-20', source_locator='fictional-export:42')
        self.data['captured_by'].update(model='fictional-edit-model', session_id='fictional-edit-session')
        result = memory.capture(self.root, self.data)
        note = (self.root / 'Sessions' / (result['input_id'] + '.md')).read_text(encoding='utf-8')
        for expected in ('fictional-source-model', 'fictional-edit-model', 'fictional-original-session',
                         'fictional-edit-session', '2030-03-20', 'fictional-export:42'):
            self.assertIn(expected, note)

    def test_day_boundaries_include_exact_start_exclude_exact_end(self):
        self.setup_vault()
        for key, stamp in [('start', '2030-11-03T00:00:00-04:00'), ('end', '2030-11-04T00:00:00-05:00')]:
            memory.capture(self.root, {**self.data, 'source_id': key, 'source_date': stamp})
        run = memory.prepare(self.root, '2030-11-03')
        start, end = [datetime.fromisoformat(run[k]).astimezone(timezone.utc) for k in ('window_start', 'window_end')]
        self.assertEqual(25 * 3600, (end - start).total_seconds())
        self.assertEqual(['start'], [x['source_id'] for x in run['inputs']])

    def test_empty_review_is_repeatable_and_does_not_create_facts(self):
        self.setup_vault()
        before = (self.root / 'Personal/Preferences.md').read_bytes()
        run = memory.prepare(self.root, '2030-04-02')
        self.assertEqual(run, memory.prepare(self.root, '2030-04-02'))
        receipt = {'run_id': run['run_id'], 'editor': self.editor, 'coverage_gaps': [], 'results': []}
        memory.complete(self.root, receipt)
        self.assertEqual(before, (self.root / 'Personal/Preferences.md').read_bytes())

    def test_malformed_cli_inputs_fail_cleanly(self):
        self.setup_vault()
        bad = self.base / 'bad.json'
        for value in ([], None, 'unexpected'):
            bad.write_bytes(encoded(value))
            for command, flag in [('capture', '--input'), ('complete', '--receipt')]:
                self.cli(PACKAGE / 'scripts/memory.py', command, '--vault', self.root, flag, bad, expected=1)
            self.cli(PACKAGE / 'scripts/bootstrap.py', '--config', bad, expected=1)
        invalid = copy.deepcopy(self.data)
        invalid['source_date'] = 123
        bad.write_bytes(encoded(invalid))
        self.cli(PACKAGE / 'scripts/memory.py', 'capture', '--vault', self.root, '--input', bad, expected=1)

    def test_status_requires_a_real_vault(self):
        self.cli(PACKAGE / 'scripts/memory.py', 'status', '--vault', self.root, expected=1)

    def test_conflicting_success_receipt_preserved(self):
        receipt = self.review()
        memory.complete(self.root, receipt)
        path = self.root / f'.memory-state/receipts/{receipt["run_id"]}.json'
        before = path.read_bytes()
        receipt['results'][0]['reason'] = 'Different story'
        with self.assertRaisesRegex(ValueError, 'different results'):
            memory.complete(self.root, receipt)
        self.assertEqual(before, path.read_bytes())
