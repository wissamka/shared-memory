import json
from pathlib import Path

from helpers import Case, PACKAGE, encoded
import collection
import connect_harness
import readiness


class ReadinessTests(Case):
    def save_check(self, check='fresh_recall', outcome='passed', evidence='Fictional acceptance observation; no real account used.', apply=True):
        return readiness.record_check(self.root, check, outcome, evidence, '2020-04-02T12:00:00Z', self.editor, apply)

    def snapshot(self):
        return {p.relative_to(self.root).as_posix(): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}

    def test_report_is_read_only_and_fresh_scaffold_is_not_ready(self):
        self.setup_vault()
        before = self.snapshot()
        result = readiness.report(self.root, '2030-04-02')
        self.assertEqual(before, self.snapshot())
        self.assertFalse((self.root / '.memory-state/operation.lock').exists())
        self.assertEqual('attention_required', result['overall_state'])
        self.assertEqual(0, result['collection']['registered_sources'])
        self.assertEqual('unverified', result['acceptance']['checks']['fresh_recall']['state'])
        self.assertEqual('not_applicable', result['acceptance']['checks']['cloud_roundtrip']['state'])
        self.assertEqual('prepared', result['schedule']['declared_state'])
        self.assertEqual('unverified', result['acceptance']['checks']['scheduler_observed']['state'])

    def test_record_preview_and_immutable_repeat_with_provenance(self):
        self.setup_vault()
        preview = self.save_check(apply=False)
        self.assertFalse(Path(preview['receipt']).exists())
        first = self.save_check()
        again = self.save_check()
        self.assertEqual(first['receipt'], again['receipt'])
        self.assertEqual(1, len(list((self.root / '.memory-state/readiness/checks').glob('*.json'))))
        check = readiness.report(self.root, '2030-04-02')['acceptance']['checks']['fresh_recall']
        self.assertEqual('recorded_passed', check['state'])
        self.assertEqual(self.editor, check['editor'])
        self.assertIn('not a live automated', check['basis'])

    def test_configuration_change_stales_evidence_but_knowledge_edit_does_not(self):
        self.setup_vault()
        self.save_check()
        profile = self.root / 'Personal/Profile.md'
        profile.write_bytes(profile.read_bytes() + b'\nFictional project preference.\n')
        self.assertEqual('recorded_passed', readiness.report(self.root, '2030-04-02')['acceptance']['checks']['fresh_recall']['state'])
        rules = self.root / 'rules.md'
        rules.write_bytes(rules.read_bytes() + b'\nChanged permission scope.\n')
        self.assertEqual('stale', readiness.report(self.root, '2030-04-02')['acceptance']['checks']['fresh_recall']['state'])

    def test_enabled_schedule_is_not_an_observed_run_even_when_prose_claims_it(self):
        self.setup_vault()
        schedule = self.root / 'Automation/Schedule.md'
        schedule.write_text('State: **observed**.\n', encoding='utf-8')
        self.save_check('scheduler_enabled')
        result = readiness.report(self.root, '2030-04-02')
        self.assertEqual('observed', result['schedule']['declared_state'])
        self.assertEqual('recorded_passed', result['acceptance']['checks']['scheduler_enabled']['state'])
        self.assertEqual('unverified', result['acceptance']['checks']['scheduler_observed']['state'])

    def test_binding_ignores_unrelated_edits_but_detects_block_drift(self):
        self.setup_vault()
        target = self.base / 'AGENTS.md'
        connect_harness.connect(self.root, target, 'codex', self.editor, True)
        original = target.read_bytes()
        target.write_bytes(b'Unrelated prefix.\n' + original + b'\nUnrelated suffix.\n')
        self.assertEqual('block_verified', readiness.report(self.root, '2030-04-02')['connections']['bindings'][0]['state'])
        target.write_bytes(target.read_bytes().replace(b'Canonical vault', b'Changed vault'))
        self.assertEqual('drifted', readiness.report(self.root, '2030-04-02')['connections']['bindings'][0]['state'])
        target.unlink()
        self.assertEqual('unverified', readiness.report(self.root, '2030-04-02')['connections']['bindings'][0]['state'])

    def test_foreign_device_binding_is_unverified_not_corrupt(self):
        self.setup_vault()
        target = self.base / 'AGENTS.md'
        result = connect_harness.connect(self.root, target, 'codex', self.editor, True)
        path = Path(result['binding_record'])
        record = json.loads(path.read_bytes())
        record['vault_path'] = str(self.base / 'another-device' / 'vault')
        path.write_bytes(encoded(record))
        self.assertEqual('unverified', readiness.report(self.root, '2030-04-02')['connections']['bindings'][0]['state'])

    def test_missing_and_partial_source_days_remain_visible(self):
        self.setup_vault()
        collection.register(self.root, 'fictional-source', 'manual', '2030-04-01', self.editor, True)
        collection.record(self.root, 'fictional-source', '2030-04-01',
                          {'mode': 'applied', 'coverage_gaps': ['Fictional source inaccessible']}, self.editor)
        state = readiness.report(self.root, '2030-04-02')['collection']
        self.assertEqual(1, state['registered_sources'])
        self.assertEqual(['2030-04-02'], state['sources'][0]['missing_days'])
        self.assertEqual('2030-04-01', state['sources'][0]['partial_days'][0]['date'])

    def test_malformed_capture_and_tampered_acceptance_receipt_reported(self):
        self.setup_vault()
        (self.root / '_Inbox/broken.json').write_bytes(b'not JSON')
        check = self.save_check()
        path = Path(check['receipt'])
        value = json.loads(path.read_bytes())
        value['outcome'] = 'failed'
        path.write_bytes(encoded(value))
        result = readiness.report(self.root, '2030-04-02')
        self.assertFalse(result['memory']['healthy'])
        self.assertEqual(1, len(result['memory']['invalid_inputs']))
        self.assertEqual(1, len(result['acceptance']['invalid_receipts']))
        self.assertEqual('unverified', result['acceptance']['checks']['fresh_recall']['state'])

    def test_canonical_drift_is_local_comparison_not_latest_remote_claim(self):
        self.setup_vault()
        initial = readiness.report(self.root, '2030-04-02')['procedure']
        self.assertEqual('matches_local_package', initial['state'])
        self.assertEqual('not_checked', initial['remote_latest'])
        canonical = self.root / 'Procedures/shared-memory/SKILL.md'
        canonical.write_bytes(canonical.read_bytes() + b'\nOwner customization.\n')
        state = readiness.report(self.root, '2030-04-02')['procedure']
        self.assertEqual('content_differs', state['state'])
        self.assertIn('SKILL.md', state['different_files'])

    def test_rejects_missing_evidence_future_times_and_local_cloud_check(self):
        self.setup_vault()
        with self.assertRaises(ValueError):
            self.save_check(evidence='   ')
        with self.assertRaises(ValueError):
            self.save_check('cloud_roundtrip')
        with self.assertRaises(ValueError):
            readiness.record_check(self.root, 'fresh_recall', 'passed', 'Fictional', '2999-04-02T00:00:00Z', self.editor, True)
        with self.assertRaises(ValueError):
            readiness.record_check(self.root, 'fresh_recall', 'passed', 'Fictional', '2020-04-02', self.editor, True)

    def test_conflicting_same_time_outcomes_and_later_failure_are_visible(self):
        self.setup_vault()
        self.save_check()
        self.save_check(outcome='failed', evidence='Fictional contradictory observation.')
        state = readiness.report(self.root, '2030-04-02')['acceptance']['checks']['fresh_recall']
        self.assertEqual('conflicting', state['state'])
        readiness.record_check(self.root, 'fresh_recall', 'failed', 'Fictional later failed recall.',
                               '2020-04-03T12:00:00Z', self.editor, True)
        state = readiness.report(self.root, '2030-04-02')['acceptance']['checks']['fresh_recall']
        self.assertEqual('recorded_failed', state['state'])

    def test_readiness_cli_has_read_only_report_and_record_preview(self):
        self.setup_vault()
        self.cli(PACKAGE / 'scripts/readiness.py', 'report', '--vault', self.root, '--through', '2030-04-02')
        editor = self.base / 'editor.local.json'
        editor.write_bytes(encoded(self.editor))
        self.cli(PACKAGE / 'scripts/readiness.py', 'record-check', '--vault', self.root, '--check', 'fresh_recall',
                 '--outcome', 'passed', '--evidence', 'Fictional observation only', '--checked-at',
                 '2020-04-02T12:00:00Z', '--editor', editor)
        self.assertFalse((self.root / '.memory-state/readiness/checks').exists())

    def test_manual_mode_makes_only_scheduler_checks_not_applicable(self):
        self.setup_vault()
        config = self.root / '.memory-state/config.json'
        value = json.loads(config.read_bytes())
        value['scheduling_mode'] = 'manual'
        config.write_bytes(encoded(value))
        result = readiness.report(self.root, '2030-04-02')
        self.assertEqual('manual', result['schedule']['configured_mode'])
        for key in ('scheduler_enabled', 'scheduler_observed'):
            self.assertEqual('not_applicable', result['acceptance']['checks'][key]['state'])
            with self.assertRaisesRegex(ValueError, 'not applicable'):
                self.save_check(key)
        for key in ('fresh_recall', 'daily_review'):
            self.assertEqual('unverified', result['acceptance']['checks'][key]['state'])
        self.assertEqual(0, result['collection']['registered_sources'])
        self.assertEqual('attention_required', result['overall_state'])

    def test_legacy_daily_is_not_overridden_by_manual_schedule_prose(self):
        self.setup_vault()
        config = self.root / '.memory-state/config.json'
        value = json.loads(config.read_bytes())
        value.pop('scheduling_mode', None)
        config.write_bytes(encoded(value))
        (self.root / 'Automation/Schedule.md').write_text('State: **manual**.\n', encoding='utf-8')
        result = readiness.report(self.root, '2030-04-02')
        self.assertEqual('daily', result['schedule']['configured_mode'])
        for key in ('scheduler_enabled', 'scheduler_observed'):
            self.assertEqual('unverified', result['acceptance']['checks'][key]['state'])

    def test_manual_mode_preserves_old_scheduler_evidence_and_rejects_invalid_mode(self):
        self.setup_vault()
        receipt = self.save_check('scheduler_enabled')
        original = Path(receipt['receipt']).read_bytes()
        config = self.root / '.memory-state/config.json'
        value = json.loads(config.read_bytes())
        value['scheduling_mode'] = 'manual'
        config.write_bytes(encoded(value))
        result = readiness.report(self.root, '2030-04-02')
        self.assertEqual('not_applicable', result['acceptance']['checks']['scheduler_enabled']['state'])
        self.assertEqual(original, Path(receipt['receipt']).read_bytes())
        value['scheduling_mode'] = 'unexpected'
        config.write_bytes(encoded(value))
        with self.assertRaisesRegex(ValueError, 'scheduling_mode'):
            readiness.report(self.root, '2030-04-02')
        with self.assertRaisesRegex(ValueError, 'scheduling_mode'):
            self.save_check('scheduler_enabled')
