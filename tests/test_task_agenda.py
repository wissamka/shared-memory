from datetime import date
from pathlib import Path
import json

from helpers import Case, PACKAGE
from task_agenda import agenda, personal_tasks

TABLE = '| Task | Status | Due | Added | Done | Notes |\n|---|---|---|---|---|---|\n'


def row(name, due='', status='Open'):
    return f'| {name} | {status} | {due} | | | |\n'


class TaskAgendaTests(Case):
    def test_installed_harnesses_share_two_lists_and_can_resume(self):
        self.c['harness_targets'] = [
            {'kind': kind, 'path': str(self.base / kind / filename)}
            for kind, filename in [('codex', 'AGENTS.md'), ('claude', 'CLAUDE.md')]]
        self.setup_vault()
        for target in self.c['harness_targets']:
            self.assertIn('task routes', Path(target['path']).read_text(encoding='utf-8'))
        manual = (self.root / 'AGENTS.md').read_text(encoding='utf-8')
        self.assertIn('Task%20List.md', manual)
        self.assertIn('My%20Tasks.md', manual)
        agency = self.root / 'Task List.md'
        personal = self.root / 'My Tasks.md'
        agency.write_text(agency.read_text(encoding='utf-8') + row('Agent work', '2031-11-02'), encoding='utf-8')
        personal.write_text(personal.read_text(encoding='utf-8').replace(TABLE, TABLE + row('Personal work', '2031-11-02')), encoding='utf-8')
        self.setup_vault()
        result = self.cli(self.root / 'Procedures/shared-memory/scripts/task_agenda.py', '--vault', self.root,
                          '--period', 'daily', '--on', '2031-11-02')
        self.assertEqual(['Personal work'], [x['task'] for x in json.loads(result.stdout)['upcoming']])

    def test_approximate_dates_retain_the_qualifier_in_the_digest(self):
        tasks = personal_tasks(TABLE + row('Review estimate', '~2030-12-31'))
        item = agenda(tasks, 'daily', date(2030, 12, 30))['upcoming'][0]
        self.assertTrue(item['approximate'])
        self.assertEqual('2030-12-31', item['due'])

    def test_old_bootstrap_does_not_create_shadow_lists_on_upgrade(self):
        self.setup_vault()
        marker = self.root / '.shared-memory-install.json'
        state = json.loads(marker.read_text(encoding='utf-8'))
        state['files'].remove('My Tasks.md')
        marker.write_text(json.dumps(state), encoding='utf-8')
        established = self.root / 'Custom'
        established.mkdir()
        (self.root / 'My Tasks.md').rename(established / 'My Tasks.md')
        with self.assertRaisesRegex(ValueError, 'guided task-list upgrade'):
            self.setup_vault()
        self.assertFalse((self.root / 'My Tasks.md').exists())
        self.assertTrue((established / 'My Tasks.md').exists())

    def test_daily_covers_today_and_tomorrow_and_skips_closed(self):
        tasks = personal_tasks(TABLE + row('Past', '2030-12-30') + row('Today', '2030-12-31') +
                               row('Tomorrow', '2031-01-01') + row('Later', '2031-01-02') +
                               row('Completed', '2030-12-31', 'Done') + row('Undated'))
        result = agenda(tasks, 'daily', date(2030, 12, 31))
        self.assertEqual(['Today', 'Tomorrow'], [x['task'] for x in result['upcoming']])
        self.assertNotIn('undated', result)

    def test_sunday_previews_monday_through_sunday_and_separates_other_items(self):
        tasks = personal_tasks(TABLE + row('Overdue', '2026-10-31') + row('Today', '2026-11-01') +
                               row('Monday', '2026-11-02') + row('Sunday', '2026-11-08') +
                               row('Beyond', '2026-11-09') + row('No date') +
                               '\n## Done\n\n' + TABLE + row('Closed', '2026-11-03', 'Done'))
        result = agenda(tasks, 'weekly', date(2026, 11, 1))
        self.assertEqual(('2026-11-02', '2026-11-08'), (result['start'], result['end']))
        self.assertEqual(['Monday', 'Sunday'], [x['task'] for x in result['upcoming']])
        self.assertEqual(['Overdue'], [x['task'] for x in result['overdue']])
        self.assertEqual(['No date'], [x['task'] for x in result['undated']])

    def test_mapped_custom_folder_preserved_and_bad_input_is_not_an_empty_digest(self):
        self.setup_vault()
        folder = self.root / 'Command Center'
        folder.mkdir()
        note = folder / 'Personal actions.md'
        note.write_text(TABLE + row(r'Review A\|B', '2030-03-10'), encoding='utf-8')
        args = ('--vault', self.root, '--period', 'daily', '--on', '2030-03-10',
                '--personal-list', 'Command Center/Personal actions.md')
        helper = PACKAGE / 'scripts/task_agenda.py'
        before = note.read_bytes()
        self.assertEqual('Review A|B', json.loads(self.cli(helper, *args).stdout)['upcoming'][0]['task'])
        self.assertEqual(before, note.read_bytes())
        note.write_text(TABLE + row('Broken date', 'next Friday'), encoding='utf-8')
        self.assertIn('YYYY-MM-DD', self.cli(helper, *args, expected=1).stderr)
        self.assertIn('relative path', self.cli(helper, '--vault', self.root, '--period', 'daily',
                      '--personal-list', '../outside.md', expected=1).stderr)

    def test_two_day_windows_cross_weekend_leap_day_and_dst_dates(self):
        cases = [('2026-11-06', '2026-11-07'), ('2028-02-28', '2028-02-29'),
                 ('2026-03-08', '2026-03-09'), ('2026-11-01', '2026-11-02')]
        for start, end in cases:
            with self.subTest(start=start):
                result = agenda(personal_tasks(TABLE + row('Due', end)), 'daily', date.fromisoformat(start))
                self.assertEqual(end, result['end'])
                self.assertEqual(['Due'], [item['task'] for item in result['upcoming']])

    def test_week_preview_crosses_year_and_excludes_following_monday(self):
        data = TABLE + row('First', '2030-12-30') + row('Last', '2031-01-05') + row('Later', '2031-01-06')
        result = agenda(personal_tasks(data), 'weekly', date(2030, 12, 29))
        self.assertEqual(('2030-12-30', '2031-01-05'), (result['start'], result['end']))
        self.assertEqual(['First', 'Last'], [item['task'] for item in result['upcoming']])

    def test_real_note_edits_move_rescheduled_and_completed_items_out_of_daily_digest(self):
        self.setup_vault()
        path = self.root / 'My Tasks.md'
        helper = self.root / 'Procedures/shared-memory/scripts/task_agenda.py'
        args = ('--vault', self.root, '--period', 'daily', '--on', '2030-07-08')
        def due_titles():
            return [item['task'] for item in json.loads(self.cli(helper, *args).stdout)['upcoming']]
        path.write_text(TABLE + row('A', '2030-07-08') + row('B', '2030-07-09'), encoding='utf-8')
        self.assertEqual(['A', 'B'], due_titles())
        path.write_text(TABLE + row('A', '2030-07-08', 'Done') + row('B', '2030-07-10'), encoding='utf-8')
        self.assertEqual([], due_titles())

    def test_all_closed_empty_and_undated_only_lists(self):
        for contents in [TABLE, TABLE + row('Finished', '2030-01-01', 'Done'),
                         TABLE + row('Dropped', '2030-01-01', 'Cancelled')]:
            result = agenda(personal_tasks(contents), 'weekly', date(2030, 1, 1))
            self.assertFalse(any(result[key] for key in ('upcoming', 'overdue', 'undated')))
        tasks = personal_tasks(TABLE + row('Waiting for a date'))
        self.assertFalse(agenda(tasks, 'daily', date(2030, 1, 1))['upcoming'])
        self.assertEqual(tasks, agenda(tasks, 'weekly', date(2030, 1, 1))['undated'])

    def test_compact_markdown_preserves_trailing_empty_cells_and_optional_outer_pipes(self):
        data = 'Task|Status|Due|Notes\n---|---|---|---\nReview|Open|| |\n'
        self.assertEqual([{'task': 'Review', 'due': None}], personal_tasks(data))
        data = '|Task|Status|Due|Added|Done|Notes|\n|---|---|---|---|---|---|\n|Review|Open|||||\n'
        self.assertEqual([{'task': 'Review', 'due': None}], personal_tasks(data))

    def test_fenced_examples_do_not_generate_reminders(self):
        for fence in ('```', '~~~~'):
            with self.subTest(fence=fence):
                note = fence + 'markdown\n' + TABLE + row('Example', '2030-01-01') + fence + '\n\n' + TABLE + row('Real')
                self.assertEqual(['Real'], [item['task'] for item in personal_tasks(note)])

    def test_invalid_data_never_looks_like_a_successful_empty_digest(self):
        for contents in ['# Missing list', TABLE + row('Impossible', '2030-02-30'),
                         TABLE + row('Unknown state', '', 'Mystery'), TABLE + '| Short | Open |\n',
                         TABLE + row('Invalid approximate date', '~')]:
            with self.subTest(contents=contents), self.assertRaises(ValueError):
                personal_tasks(contents)

    def test_default_day_uses_owner_timezone_when_utc_date_differs(self):
        from contextlib import redirect_stdout
        from datetime import datetime, timezone
        from io import StringIO
        import sys
        from unittest.mock import patch
        import task_agenda

        self.c['timezone'] = 'America/Los_Angeles'
        self.setup_vault()
        class FixedClock(datetime):
            @classmethod
            def now(cls, zone):
                return datetime(2030, 1, 1, 2, 30, tzinfo=timezone.utc).astimezone(zone)

        output = StringIO()
        with patch.object(task_agenda, 'datetime', FixedClock), redirect_stdout(output), \
                patch.object(sys, 'argv', ['agenda', '--vault', str(self.root), '--period', 'daily']):
            self.assertEqual(0, task_agenda.main())
        self.assertEqual('2029-12-31', json.loads(output.getvalue())['start'])
