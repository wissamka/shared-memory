import json
from pathlib import Path
from unittest.mock import patch

from helpers import Case, PACKAGE, encoded, memory
import suppression
import voice


class VoiceTests(Case):
    def setUp(self):
        super().setUp()
        self.setup_vault()
        self.archive = self.base / 'Visible chats'
        self.message = {'source': 'selected-personal-chats', 'source_id': 'fictional-source-message',
                        'message_id': 'fictional-message', 'position': 3, 'role': 'user', 'channel': 'user',
                        'source_date': '2030-04-02T12:00:00Z', 'text': 'I prefer plain verbs and specific examples.',
                        'coverage': 'Selected visible message; earlier conversation unavailable',
                        'redactions': [], 'reviewed_for_secrets': True,
                        'assistant': 'user', 'harness': 'Codex', 'model': 'unknown', 'agent': 'unknown',
                        'session_id': 'fictional-voice-session', 'chat_reference': 'unavailable',
                        'model_note': 'Human-authored message; no generation model', 'captured_by': self.editor}
        self.attestation = {'owner_authored': True, 'excludes_pasted_or_quoted': True,
                            'authorship_reference': 'Owner confirmed authorship in selected turn',
                            'context': 'Brief business explanation', 'observations': ['Use plain verbs.']}

    def ready(self):
        return voice.setup(self.archive, self.root, ['selected-personal-chats'], self.editor, apply=True)

    def approved(self):
        self.ready()
        key = voice.capture(self.archive, self.message, apply=True)['message_key']
        voice.example(self.archive, key, self.attestation, self.editor, apply=True)
        voice.approve(self.archive, key, 'fictional-owner-approval-turn', self.editor, apply=True)
        return key

    def unknown_identity(self, **changes):
        return {**self.message, 'session_id': 'unknown', 'message_id': 'unknown',
                'session_id_note': 'Chat interface does not expose its original conversation ID',
                'message_id_note': 'Chat interface does not expose original message IDs',
                'capture_session_id': 'capture-session-one', 'capture_message_id': 'capture-message-one',
                **changes}

    def test_unavailable_original_ids_stay_unknown_and_capture_ids_are_labeled(self):
        self.ready()
        message = self.unknown_identity()
        key = voice.capture(self.archive, message, apply=True)['message_key']
        saved = voice.record(self.archive, key)['message']
        self.assertEqual(message, saved)
        self.assertEqual('unknown', saved['session_id'])
        self.assertEqual('unknown', saved['message_id'])
        rendered = (self.archive / f'Messages/{key}.md').read_text(encoding='utf-8')
        self.assertIn('session: `unknown`', rendered)
        self.assertIn('not a vendor identifier', rendered)
        voice.example(self.archive, key, self.attestation, self.editor, apply=True)
        voice.approve(self.archive, key, 'owner-approval-reference', self.editor, apply=True)
        evidence = voice.corpus(self.archive)['examples'][0]
        self.assertEqual('unknown', evidence['session_id'])
        self.assertEqual('unknown', evidence['message_id'])
        self.assertEqual('capture-session-one', evidence['capture_session_id'])

    def test_capture_ids_keep_overlap_idempotent_and_distinct_unknown_sessions_separate(self):
        self.ready()
        message = self.unknown_identity()
        first = voice.capture(self.archive, message, apply=True)
        self.assertEqual(first, voice.capture(self.archive, message, apply=True))
        other = voice.capture(self.archive, self.unknown_identity(capture_session_id='capture-session-two'), apply=True)
        repeated = voice.capture(self.archive, self.unknown_identity(position=4), apply=True)
        self.assertEqual(3, len({first['message_key'], other['message_key'], repeated['message_key']}))
        self.assertEqual(3, len(list((self.archive / 'Records').glob('*.json'))))

    def test_unknown_original_ids_require_notes_and_stable_capture_ids(self):
        self.ready()
        for field in ('capture_session_id', 'capture_message_id', 'session_id_note', 'message_id_note'):
            data = self.unknown_identity()
            del data[field]
            with self.assertRaises(ValueError):
                voice.capture(self.archive, data, apply=True)
        with self.assertRaises(ValueError):
            voice.capture(self.archive, self.unknown_identity(capture_session_id='unknown'), apply=True)
        with self.assertRaises(ValueError):
            voice.capture(self.archive, {**self.message, 'capture_message_id': 'unused-confusing-id'}, apply=True)

    def test_known_ids_keep_previous_identity_and_cannot_collide_with_capture_ids(self):
        expected = memory.digest(encoded([self.message['source'], self.message['harness'], self.message['session_id'],
                                          self.message['source_id'], self.message['message_id'], self.message['position']]))
        self.assertEqual(expected, voice.message_key(self.message))
        self.assertNotEqual(expected, voice.message_key(self.unknown_identity(
            capture_session_id=self.message['session_id'], capture_message_id=self.message['message_id'])))

    def test_forget_unknown_session_is_rejected_and_source_forget_preserves_other_captures(self):
        self.ready()
        first = self.unknown_identity()
        second = self.unknown_identity(source_id='another-source-retention-key', capture_session_id='capture-session-two')
        one = voice.capture(self.archive, first, apply=True)['message_key']
        two = voice.capture(self.archive, second, apply=True)['message_key']
        with self.assertRaises(ValueError):
            voice.forget(self.archive, self.editor, session_id='unknown', harness='Codex', apply=True)
        voice.forget(self.archive, self.editor, source_id=first['source_id'], apply=True)
        self.assertFalse((self.archive / f'Records/{one}.json').exists())
        self.assertTrue((self.archive / f'Records/{two}.json').exists())
        self.assertEqual('suppressed', voice.capture(self.archive, first, apply=True)['mode'])
        self.assertEqual('saved', voice.capture(self.archive, second, apply=True)['mode'])

    def test_setup_is_opt_in_and_repeated_setup_preserves_archive(self):
        plan = voice.setup(self.archive, self.root, ['selected-personal-chats'], self.editor)
        self.assertEqual('preview', plan['mode'])
        self.assertFalse(self.archive.exists())
        self.ready()
        key = voice.capture(self.archive, self.message, apply=True)['message_key']
        before = (self.archive / f'Records/{key}.json').read_bytes()
        self.assertEqual('unchanged', self.ready()['mode'])
        self.assertEqual(before, (self.archive / f'Records/{key}.json').read_bytes())
        with self.assertRaises(ValueError):
            voice.setup(self.archive, self.root, ['different-source'], self.editor, apply=True)

    def test_archive_must_be_separate_from_vault_and_distribution(self):
        for path in (self.root, self.root / 'chat archive', self.base, PACKAGE / 'private-archive'):
            with self.assertRaises(ValueError):
                voice.setup(path, self.root, ['source'], self.editor, apply=True)
        self.archive.mkdir()
        (self.archive / 'existing.txt').write_text('preserve', encoding='utf-8')
        with self.assertRaises(ValueError):
            self.ready()
        self.assertEqual('preserve', (self.archive / 'existing.txt').read_text())

    def test_missing_or_wrong_knowledge_vault_is_rejected(self):
        wrong = self.base / 'not-a-vault'
        wrong.mkdir()
        with self.assertRaises(OSError):
            voice.setup(self.archive, wrong, ['source'], self.editor, apply=True)
        self.ready()
        (self.root / '.memory-state/config.json').unlink()
        with self.assertRaises(OSError):
            voice.capture(self.archive, self.message, apply=True)

    def test_symlink_archive_and_nested_record_targets_are_rejected(self):
        target = self.base / 'external'
        target.mkdir()
        try:
            self.archive.symlink_to(target, target_is_directory=True)
        except OSError:
            self.skipTest('Symlinks unavailable')
        with self.assertRaises(ValueError):
            self.ready()
        self.archive.unlink()
        self.ready()
        (self.archive / 'Records').symlink_to(target, target_is_directory=True)
        with self.assertRaises(ValueError):
            voice.capture(self.archive, self.message, apply=True)
        self.assertEqual([], list(target.iterdir()))

    def test_visible_scope_roles_channels_and_secret_attestation(self):
        self.ready()
        bad = [
            {**self.message, 'role': 'system'}, {**self.message, 'role': 'tool'},
            {**self.message, 'role': 'assistant', 'channel': 'analysis'},
            {**self.message, 'role': 'assistant', 'channel': 'tool'},
            {**self.message, 'source': 'unapproved-account'},
            {**self.message, 'reviewed_for_secrets': False},
            {**self.message, 'hidden_payload': 'must never be persisted'},
            {**self.message, 'captured_by': {**self.editor, 'raw_logs': 'must never be persisted'}},
        ]
        for item in bad:
            with self.assertRaises(ValueError):
                voice.capture(self.archive, item, apply=True)
        self.assertFalse((self.archive / 'Records').exists())
        assistant = {**self.message, 'role': 'assistant', 'channel': 'commentary'}
        self.assertEqual('saved', voice.capture(self.archive, assistant, apply=True)['mode'])

    def test_unknown_time_is_explicit_and_original_wording_is_preserved(self):
        self.ready()
        message = {**self.message, 'source_date': 'unknown', 'timestamp_note': 'Not exposed by source interface',
                   'text': 'First line.\n\nRepeated: yes.\nRepeated: yes.\n[REDACTED: credential]',
                   'redactions': ['Credential replaced with a label before capture']}
        key = voice.capture(self.archive, message, apply=True)['message_key']
        saved = voice.record(self.archive, key)
        self.assertEqual(message, saved['message'])
        self.assertIn(message['text'], (self.archive / f'Messages/{key}.md').read_text(encoding='utf-8'))
        with self.assertRaises(ValueError):
            voice.capture(self.archive, {**self.message, 'source_date': 'unknown'}, apply=True)

    def test_exact_overlap_deduplicates_but_repeated_ids_at_new_position_survive(self):
        self.ready()
        first = voice.capture(self.archive, self.message, apply=True)
        retry = voice.capture(self.archive, {**self.message, 'captured_by': {**self.editor, 'agent': 'another-agent'}}, apply=True)
        self.assertEqual(first, retry)
        second = voice.capture(self.archive, {**self.message, 'position': 4}, apply=True)
        self.assertNotEqual(first['message_key'], second['message_key'])
        self.assertEqual(2, len(list((self.archive / 'Records').glob('*.json'))))
        with self.assertRaises(ValueError):
            voice.capture(self.archive, {**self.message, 'text': 'Changed text under same ID'}, apply=True)

    def test_interrupted_capture_repairs_missing_markdown_without_replacing_evidence(self):
        self.ready()
        key = voice.capture(self.archive, self.message, apply=True)['message_key']
        source = self.archive / f'Records/{key}.json'
        before = source.read_bytes()
        rendered = self.archive / f'Messages/{key}.md'
        rendered.unlink()
        voice.capture(self.archive, self.message, apply=True)
        self.assertEqual(before, source.read_bytes())
        self.assertTrue(rendered.exists())

    def test_voice_corpus_rejects_assistant_text_and_unattested_or_quoted_samples(self):
        self.ready()
        assistant = {**self.message, 'role': 'assistant', 'channel': 'final'}
        key = voice.capture(self.archive, assistant, apply=True)['message_key']
        with self.assertRaises(ValueError):
            voice.example(self.archive, key, self.attestation, self.editor, apply=True)
        user_key = voice.capture(self.archive, {**self.message, 'position': 5}, apply=True)['message_key']
        for change in ({'owner_authored': False}, {'excludes_pasted_or_quoted': False}, {'authorship_reference': ''}):
            with self.assertRaises(ValueError):
                voice.example(self.archive, user_key, {**self.attestation, **change}, self.editor, apply=True)
        self.assertEqual([], voice.corpus(self.archive)['examples'])

    def test_draft_observations_are_inactive_until_exact_owner_approval(self):
        self.ready()
        key = voice.capture(self.archive, self.message, apply=True)['message_key']
        voice.example(self.archive, key, self.attestation, self.editor, apply=True)
        self.assertEqual([], voice.corpus(self.archive)['examples'])
        preview = voice.approve(self.archive, key, 'fictional-owner-approval-turn', self.editor)
        self.assertEqual('draft', preview['status'])
        self.assertEqual([], voice.corpus(self.archive)['examples'])
        voice.approve(self.archive, key, 'fictional-owner-approval-turn', self.editor, apply=True)
        examples = voice.corpus(self.archive)['examples']
        self.assertEqual(1, len(examples))
        self.assertEqual(self.message['text'], examples[0]['text'])
        self.assertEqual(self.attestation['observations'], examples[0]['observations'])
        sample = self.archive / f'Corpus/{key}.json'
        value = json.loads(sample.read_bytes())
        value['attestation']['observations'].append('An unapproved new rule')
        sample.write_bytes(encoded(value))
        with self.assertRaisesRegex(ValueError, 'approval'):
            voice.corpus(self.archive)

    def test_knowledge_forget_hides_corpus_but_does_not_claim_archive_deletion(self):
        key = self.approved()
        memory.forget(self.root, self.editor, source_id=self.message['source_id'], apply=True)
        self.assertEqual([], voice.corpus(self.archive)['examples'])
        self.assertTrue((self.archive / f'Records/{key}.json').exists())
        self.assertEqual('suppressed', voice.capture(self.archive, self.message, apply=True)['mode'])

    def test_archive_forget_preview_apply_and_reimport_suppression(self):
        key = self.approved()
        plan = voice.forget(self.archive, self.editor, source_id=self.message['source_id'])
        self.assertEqual('preview', plan['mode'])
        self.assertEqual(4, len(plan['files']))
        self.assertTrue(plan['other_stores_require_review'])
        self.assertEqual(1, len(voice.corpus(self.archive)['examples']))
        voice.forget(self.archive, self.editor, source_id=self.message['source_id'], apply=True)
        self.assertFalse((self.archive / f'Records/{key}.json').exists())
        self.assertFalse((self.archive / f'Messages/{key}.md').exists())
        self.assertEqual([], voice.corpus(self.archive)['examples'])
        self.assertEqual('suppressed', voice.capture(self.archive, self.message, apply=True)['mode'])
        self.assertEqual([], voice.forget(self.archive, self.editor, source_id=self.message['source_id'], apply=True)['files'])
        for path in (self.archive / '.memory-state').rglob('*.json'):
            self.assertNotIn(self.message['source_id'], path.read_text(encoding='utf-8'))
            self.assertNotIn(self.message['text'], path.read_text(encoding='utf-8'))

    def test_session_forget_removes_repeated_ids_and_leaves_other_sessions(self):
        self.ready()
        for position in (3, 4):
            voice.capture(self.archive, {**self.message, 'position': position}, apply=True)
        other = {**self.message, 'session_id': 'another-session'}
        keep = voice.capture(self.archive, other, apply=True)['message_key']
        voice.forget(self.archive, self.editor, session_id=self.message['session_id'], harness='Codex', apply=True)
        self.assertEqual([keep + '.json'], [p.name for p in (self.archive / 'Records').glob('*.json')])
        self.assertEqual('suppressed', voice.capture(self.archive, {**self.message, 'position': 6}, apply=True)['mode'])

    def test_interrupted_forget_blocks_corpus_and_resumes(self):
        key = self.approved()
        unlink = Path.unlink
        def fail(path, *args, **kwargs):
            if path.parent.name == 'Messages':
                raise OSError('Simulated interruption')
            return unlink(path, *args, **kwargs)
        with patch.object(Path, 'unlink', fail):
            with self.assertRaises(OSError):
                voice.forget(self.archive, self.editor, source_id=self.message['source_id'], apply=True)
        self.assertEqual([], voice.corpus(self.archive)['examples'])
        self.assertEqual('suppressed', voice.capture(self.archive, self.message, apply=True)['mode'])
        voice.forget(self.archive, self.editor, source_id=self.message['source_id'], apply=True)
        self.assertFalse((self.archive / f'Messages/{key}.md').exists())

    def test_cli_setup_and_capture_default_to_preview(self):
        editor = self.base / 'editor.json'
        sources = self.base / 'sources.json'
        message = self.base / 'message.json'
        editor.write_bytes(encoded(self.editor))
        sources.write_bytes(encoded(['selected-personal-chats']))
        message.write_bytes(encoded(self.message))
        command = ('setup', '--archive', self.archive, '--vault', self.root, '--sources', sources, '--editor', editor)
        self.assertEqual('preview', json.loads(self.cli(PACKAGE / 'scripts/voice.py', *command).stdout)['mode'])
        self.assertFalse(self.archive.exists())
        self.cli(PACKAGE / 'scripts/voice.py', *command, '--apply')
        self.assertEqual('preview', json.loads(self.cli(PACKAGE / 'scripts/voice.py', 'capture', '--archive', self.archive,
                                                       '--input', message).stdout)['mode'])
        self.assertFalse((self.archive / 'Records').exists())
