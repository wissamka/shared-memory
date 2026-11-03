from unittest.mock import patch
from helpers import Case
from archive_tasks import transfer
from common import digest
from task_agenda import personal_tasks

HEADER = '| Task | Status | Due | Added | Done | Notes |\n|---|---|---|---|---|---|\n'
AGENT = '| Task | Status | Owner | Outcome | Created | Closed |\n|---|---|---|---|---|---|\n'
FINISHED = '| Call supplier | Done | ~2030-01-03 | 2030-01-01 | 2030-01-03 | owner confirmed |'
PROOF = '| Inspect drawings | Done | Example agent | [Proof](drawing.md) | 2030-01-01 | 2030-01-03 |'


class CompletedTaskTests(Case):
    def setUp(self):
        super().setUp()
        self.setup_vault()
        self.agent = self.root / 'Task List.md'
        self.personal = self.root / 'My Tasks.md'
        self.history = self.root / 'Completed Task List.md'
        self.agent.write_text(AGENT + PROOF + '\n| Inspect site | Open (recurring) | Team | Weekly | | |\n', encoding='utf-8')
        self.personal.write_text(HEADER + FINISHED + '\n| Plan a trip | Open | | | | |\n', encoding='utf-8')

    def move(self, mode, sha=None):
        return transfer(self.root, self.agent.name, self.personal.name, self.history.name, mode, sha)

    def test_verified_migration_preserves_fields_and_keeps_only_active_rows(self):
        originals = [p.read_bytes() for p in (self.agent, self.personal, self.history)]
        self.assertEqual({'Agent': 1, 'Personal': 1}, self.move('preview')['completed'])
        self.assertEqual(originals, [p.read_bytes() for p in (self.agent, self.personal, self.history)])
        self.assertEqual(2, self.move('apply')['removed'])
        history = self.history.read_text(encoding='utf-8')
        for text in (FINISHED, PROOF, 'Agent ·', 'Personal ·'):
            self.assertIn(text, history)
        self.assertNotIn(PROOF, self.agent.read_text(encoding='utf-8'))
        self.assertNotIn(FINISHED, self.personal.read_text(encoding='utf-8'))
        self.assertIn('Open (recurring)', self.agent.read_text(encoding='utf-8'))
        self.assertEqual(['Plan a trip'], [t['task'] for t in personal_tasks(self.personal.read_text(encoding='utf-8'))])

    def test_copy_crash_retry_and_partial_source_prune_do_not_duplicate_history(self):
        result = self.move('copy')
        self.assertEqual(2, result['copied'])
        self.assertIn(PROOF, self.agent.read_text(encoding='utf-8'))
        self.assertEqual(0, self.move('copy')['copied'])
        # Another resume already pruned the first list.
        self.agent.write_bytes(b''.join(line for line in self.agent.read_bytes().splitlines(keepends=True)
                                        if line.rstrip(b'\r\n') != PROOF.encode()))
        self.assertEqual(1, self.move('prune', result['archive_sha256'])['removed'])
        self.assertEqual(0, self.move('apply')['removed'])
        self.assertEqual(1, self.history.read_text(encoding='utf-8').count(FINISHED))

    def test_shared_storage_needs_provider_hash_and_stops_on_tampering(self):
        import json
        cfg = self.root / '.memory-state/config.json'
        data = json.loads(cfg.read_bytes())
        data['storage']['provider'] = 'onedrive'
        cfg.write_text(json.dumps(data), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'cloud readback'):
            self.move('apply')
        sha = self.move('copy')['archive_sha256']
        original = self.personal.read_bytes()
        self.history.write_bytes(self.history.read_bytes().replace(b'owner confirmed', b'changed'))
        with self.assertRaises(ValueError):
            self.move('prune', sha)
        self.assertEqual(original, self.personal.read_bytes())

    def test_changed_completion_after_copy_is_not_removed(self):
        sha = self.move('copy')['archive_sha256']
        changed = self.agent.read_bytes().replace(b'Inspect drawings', b'Inspect revised drawings')
        self.agent.write_bytes(changed)
        with self.assertRaisesRegex(ValueError, 'incomplete'):
            self.move('prune', sha)
        self.assertEqual(changed, self.agent.read_bytes())
        self.assertIn(FINISHED, self.personal.read_text(encoding='utf-8'))

    def test_duplicate_titles_checkbox_and_fenced_example(self):
        self.agent.write_text('## Notes\n- [x] Verified design\n- [ ] Verify shipment\n\n```md\n' +
                              AGENT + PROOF + '\n```\n', encoding='utf-8')
        self.personal.write_text(HEADER + (FINISHED + '\n') * 2, encoding='utf-8')
        self.assertEqual(3, self.move('apply')['removed'])
        self.assertEqual(2, self.history.read_text(encoding='utf-8').count(FINISHED))
        self.assertIn(PROOF, self.agent.read_text(encoding='utf-8'))
        self.assertIn('- [ ] Verify shipment', self.agent.read_text(encoding='utf-8'))
        self.assertNotIn('- [x] Verified design', self.agent.read_text(encoding='utf-8'))

    def test_empty_active_lists_do_not_open_archive(self):
        self.move('apply')
        from pathlib import Path
        read = Path.read_bytes
        def checked_read(path):
            self.assertNotEqual(path, self.history)
            return read(path)
        with patch.object(Path, 'read_bytes', checked_read):
            self.assertEqual(0, self.move('preview')['removed'])

    def test_invalid_table_and_alias_safely_preserve_inputs(self):
        original = self.history.read_bytes()
        self.agent.write_text(AGENT + '| wrong | Done |\n', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'Invalid task row'):
            self.move('apply')
        with self.assertRaisesRegex(ValueError, 'distinct'):
            transfer(self.root, self.agent.name, self.personal.name, self.agent.name, 'copy')
        self.assertEqual(original, self.history.read_bytes())

    def test_kept_rows_retain_crlf_and_original_bytes(self):
        prefix = AGENT.replace('\n', '\r\n').encode()
        keep = '| Café | Waiting | Team | Pending | | |\r\n'.encode()
        self.agent.write_bytes(prefix + PROOF.encode() + b'\r\n' + keep)
        self.move('apply')
        self.assertEqual(prefix + keep, self.agent.read_bytes())
