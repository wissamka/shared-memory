import copy
import json

from helpers import Case, encoded, memory
from common import digest


class PartialReviewTests(Case):
    def partial(self):
        self.setup_vault()
        first = memory.capture(self.root, {**self.data, 'source_id': 'fictional-good'})
        second = memory.capture(self.root, {**self.data, 'source_id': 'fictional-needs-source'})
        run = memory.prepare(self.root, '2030-04-02')
        note = self.root / 'Personal/Preferences.md'
        note.write_bytes(note.read_bytes() + b'\nFictional preference, source: fictional-good.\n')
        receipt = {'run_id': run['run_id'], 'editor': self.editor, 'coverage_gaps': [], 'results': [
            {'input_id': first['input_id'], 'outcome': 'promoted', 'reason': 'Saved fictional sourced preference',
             'destinations': [{'path': 'Personal/Preferences.md', 'sha256': digest(note.read_bytes())}]},
            {'input_id': second['input_id'], 'outcome': 'deferred', 'reason': 'Original attachment unavailable; retry access',
             'destinations': []}]}
        return receipt, first, second

    def test_success_and_deferred_checkpoint_separately_then_finish(self):
        receipt, first, second = self.partial()
        saved = memory.complete(self.root, receipt)
        self.assertEqual('partial', saved['status'])
        self.assertEqual({first['input_id']}, memory.reviewed(self.root))
        self.assertEqual(1, memory.status(self.root)['pending'])
        self.assertEqual(1, memory.status(self.root)['reviewed'])
        remaining = memory.prepare(self.root, '2030-04-02')
        self.assertEqual([second['input_id']], [x['input_id'] for x in remaining['inputs']])
        finished = {'run_id': remaining['run_id'], 'editor': self.editor, 'coverage_gaps': [], 'results': [
            {'input_id': second['input_id'], 'outcome': 'no_change', 'reason': 'Original source checked; no durable information',
             'destinations': []}]}
        self.assertEqual('reviewed', memory.complete(self.root, finished)['status'])
        self.assertEqual(0, memory.status(self.root)['pending'])
        self.assertEqual(2, memory.status(self.root)['reviewed'])
        self.assertEqual(saved, memory.complete(self.root, receipt))

    def test_all_deferred_can_retry_same_day_and_prepare_is_stable(self):
        receipt, _, _ = self.partial()
        for result in receipt['results']:
            result.update(outcome='deferred', reason='Fictional source access blocked', destinations=[])
        memory.complete(self.root, receipt)
        retry = memory.prepare(self.root, '2030-04-02')
        self.assertNotEqual(receipt['run_id'], retry['run_id'])
        self.assertEqual([receipt['run_id']], retry['retry_after'])
        self.assertEqual(retry, memory.prepare(self.root, '2030-04-02'))
        next_receipt = {**receipt, 'run_id': retry['run_id']}
        memory.complete(self.root, next_receipt)
        retry_again = memory.prepare(self.root, '2030-04-02')
        self.assertNotEqual(retry['run_id'], retry_again['run_id'])
        self.assertEqual(2, len(retry_again['retry_after']))
        final = copy.deepcopy(next_receipt)
        final['run_id'] = retry_again['run_id']
        for item in final['results']:
            item.update(outcome='no_change', reason='Fictional source verified; no durable change')
        memory.complete(self.root, final)
        self.assertEqual(0, memory.status(self.root)['pending'])

    def test_deferred_requires_reason_and_rejects_destinations(self):
        receipt, _, _ = self.partial()
        bad = copy.deepcopy(receipt)
        bad['results'][1]['reason'] = ' '
        with self.assertRaisesRegex(ValueError, 'reason'):
            memory.complete(self.root, bad)
        bad = copy.deepcopy(receipt)
        bad['results'][1]['destinations'] = bad['results'][0]['destinations']
        with self.assertRaisesRegex(ValueError, 'Deferred'):
            memory.complete(self.root, bad)
        self.assertEqual(0, memory.status(self.root)['reviewed'])

    def test_partial_receipt_replay_does_not_recheck_evolved_destination(self):
        receipt, _, _ = self.partial()
        saved = memory.complete(self.root, receipt)
        note = self.root / 'Personal/Preferences.md'
        note.write_bytes(note.read_bytes() + b'\nLater legitimate edit.\n')
        self.assertEqual(saved, memory.complete(self.root, receipt))
        changed = copy.deepcopy(receipt)
        changed['results'][1].update(outcome='no_change', reason='Different result')
        with self.assertRaisesRegex(ValueError, 'different results'):
            memory.complete(self.root, changed)

    def test_stale_manifest_cannot_reacknowledge_success_even_as_deferred(self):
        receipt, _, _ = self.partial()
        stale = memory.prepare(self.root, '2030-04-03')
        memory.complete(self.root, receipt)
        stale_receipt = copy.deepcopy(receipt)
        stale_receipt['run_id'] = stale['run_id']
        for item in stale_receipt['results']:
            item.update(outcome='deferred', reason='Stale worker waiting', destinations=[])
        with self.assertRaisesRegex(ValueError, 'Stale review'):
            memory.complete(self.root, stale_receipt)

    def test_deferred_source_hash_and_partial_status_tampering_detected(self):
        receipt, _, second = self.partial()
        saved = memory.complete(self.root, receipt)
        path = self.root / '.memory-state/receipts' / (receipt['run_id'] + '.json')
        path.write_bytes(encoded({**saved, 'status': 'reviewed'}))
        with self.assertRaisesRegex(ValueError, 'Invalid receipt status'):
            memory.status(self.root)
        path.write_bytes(encoded(saved))
        source = self.root / '_Inbox' / (second['input_id'] + '.json')
        data = json.loads(source.read_bytes())
        data['text'] = 'Altered fictional source'
        source.write_bytes(encoded(data))
        with self.assertRaisesRegex(ValueError, 'Input changed'):
            memory.prepare(self.root, '2030-04-03')

    def test_unverified_success_destination_still_blocks_entire_checkpoint(self):
        receipt, _, _ = self.partial()
        note = self.root / 'Personal/Preferences.md'
        note.write_bytes(note.read_bytes() + b'\nUnverified concurrent edit.\n')
        with self.assertRaisesRegex(ValueError, 'Destination missing or changed'):
            memory.complete(self.root, receipt)
        self.assertEqual(0, memory.status(self.root)['reviewed'])

    def test_forgetting_deferred_source_preserves_suppression_and_reopens_mixed_success(self):
        receipt, first, second = self.partial()
        memory.complete(self.root, receipt)
        memory.forget(self.root, self.editor, source_id='fictional-needs-source', apply=True)
        remaining = memory.prepare(self.root, '2030-04-03')
        self.assertEqual([first['input_id']], [x['input_id'] for x in remaining['inputs']])
        self.assertEqual('suppressed', memory.capture(self.root, {**self.data, 'source_id': 'fictional-needs-source'})['status'])
        self.assertFalse((self.root / '_Inbox' / (second['input_id'] + '.json')).exists())
