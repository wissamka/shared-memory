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
