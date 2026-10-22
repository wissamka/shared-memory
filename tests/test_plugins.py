import json
from pathlib import Path
from unittest.mock import patch
import zipfile

from helpers import Case, PACKAGE, bootstrap, encoded
import build_plugin
import install_skill
import readiness


class PluginTests(Case):
    def test_setup_entrypoint_survives_relocation_and_reaches_bundled_workflow(self):
        plugin = self.base / 'Relocated plugin with spaces'
        for name, data in build_plugin.plugin_files().items():
            target = plugin / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        manifest = json.loads((plugin / 'plugin.json').read_bytes())
        entry = plugin / manifest['extensions']['com.openai']['onboardingSkill']
        self.assertEqual(plugin / 'skills/setup/SKILL.md', entry)
        self.assertEqual(install_skill.bundle()['assets/setup-skill.md'], entry.read_bytes())
        for relative in ('../shared-memory/SKILL.md', '../shared-memory/references/setup.md'):
            self.assertIn(relative, entry.read_text(encoding='utf-8'))
            target = (entry.parent / relative).resolve()
            self.assertTrue(target.is_relative_to(plugin.resolve()))
            self.assertTrue(target.is_file())

    def test_packaged_setup_preserves_two_startup_files_and_exposes_unfinished_job(self):
        targets = [self.base / '.codex/AGENTS.md', self.base / '.claude/CLAUDE.md']
        originals = [b'Existing coding rules.\n', b'Existing writing rules.\n']
        for target, original in zip(targets, originals):
            target.parent.mkdir(parents=True)
            target.write_bytes(original)
        config = self.base / 'setup.json'
        config.write_bytes(encoded({**self.c, 'scheduling_mode': 'daily', 'harness_targets': [
            {'kind': kind, 'path': str(target)} for kind, target in zip(('codex', 'claude'), targets)]}))
        script = build_plugin.PLUGIN / 'skills/shared-memory/scripts/bootstrap.py'
        self.cli(script, '--config', config, '--apply')
        before = [p.read_bytes() for p in targets]
        self.cli(script, '--config', config, '--apply')
        for target, original, applied in zip(targets, originals, before):
            self.assertTrue(applied.startswith(original))
            self.assertEqual(applied, target.read_bytes())
            self.assertEqual(1, applied.count(b'<!-- shared-memory:start -->'))
        result = readiness.report(self.root)
        self.assertEqual('attention_required', result['overall_state'])
        self.assertEqual(2, len(result['connections']['bindings']))
        self.assertTrue(all(x['state'] == 'block_verified' for x in result['connections']['bindings']))
        for check in ('fresh_recall', 'scheduler_enabled', 'scheduler_observed'):
            self.assertEqual('unverified', result['acceptance']['checks'][check]['state'])

    def source_copy(self):
        source = self.base / 'Package'
        for name, data in install_skill.bundle().items():
            path = source / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        return source

    def test_generated_plugin_matches_source_and_bootstraps(self):
        self.quiet(build_plugin.build, check=True)
        plugin = build_plugin.PLUGIN
        portable = json.loads((plugin / 'plugin.json').read_bytes())
        claude = json.loads((plugin / '.claude-plugin/plugin.json').read_bytes())
        self.assertEqual(portable['version'], claude['version'])
        self.assertEqual('shared-memory', portable['name'])
        self.assertTrue((plugin / portable['extensions']['com.openai']['onboardingSkill']).is_file())
        config = self.base / 'setup.json'
        config.write_bytes(encoded(self.c))
        self.cli(plugin / 'skills/shared-memory/scripts/bootstrap.py', '--config', config, '--apply')
        self.assertTrue((self.root / 'Personal/Profile.md').is_file())
        self.assertEqual(install_skill.bundle()['SKILL.md'],
                         (self.root / 'Procedures/shared-memory/SKILL.md').read_bytes())

    def test_unlisted_private_file_not_distributed_by_any_path(self):
        source = self.source_copy()
        (source / 'assets/setup.local.json').write_text('{"private": "fictional sentinel"}')
        (source / 'reports/private-draft.md').write_text('fictional private draft')
        self.assertNotIn('assets/setup.local.json', install_skill.bundle(source))
        self.assertNotIn('reports/private-draft.md', install_skill.bundle(source))
        self.assertFalse(any('setup.local' in p for p in build_plugin.plugin_files(source)))
        installed = self.base / 'installed'
        self.quiet(install_skill.install, [installed], True, source)
        with patch.object(bootstrap, 'PACKAGE', source):
            self.setup_vault()
        for target in (installed, self.root / 'Procedures/shared-memory'):
            self.assertFalse((target / 'assets/setup.local.json').exists())
            self.assertFalse((target / 'reports/private-draft.md').exists())

    def test_distribution_manifest_rejects_missing_and_unsafe_paths(self):
        source = self.source_copy()
        manifest = json.loads((source / 'skill-files.json').read_bytes())
        for invalid in ('../outside.md', 'assets/setup.local.json', '.env', 'missing.md'):
            (source / 'skill-files.json').write_bytes(encoded({**manifest, 'files': [*manifest['files'], invalid]}))
            with self.assertRaises(ValueError):
                install_skill.bundle(source)

    def test_case_alias_cannot_put_private_content_in_package(self):
        source = self.source_copy()
        alias = source.with_name('package')
        if not alias.exists() or not alias.samefile(source):
            self.skipTest('Requires a case-insensitive filesystem')
        with patch.object(bootstrap, 'PACKAGE', source):
            self.c['vault_path'] = str(alias / 'private-vault')
            with self.assertRaises(ValueError):
                bootstrap.plan(self.c)
            self.c['vault_path'] = str(self.root)
            self.c['harness_targets'] = [{'kind': 'codex', 'path': str(alias / 'AGENTS.md')}]
            with self.assertRaises(ValueError):
                bootstrap.plan(self.c)
        with self.assertRaises(ValueError):
            self.quiet(install_skill.install, [alias / 'nested'], True, source)
        self.assertFalse((source / 'private-vault').exists())
        self.assertFalse((source / 'AGENTS.md').exists())

    def test_archive_contains_only_plugin_files_and_is_reproducible(self):
        first, second = self.base / 'first.plugin', self.base / 'second.plugin'
        self.quiet(build_plugin.build, check=True, archive=first)
        self.quiet(build_plugin.build, check=True, archive=second)
        self.assertEqual(first.read_bytes(), second.read_bytes())
        with zipfile.ZipFile(first) as archive:
            self.assertEqual(set(build_plugin.plugin_files()), set(archive.namelist()))
            self.assertTrue(all(not n.startswith('/') and '..' not in Path(n).parts for n in archive.namelist()))
        with self.assertRaises(ValueError):
            self.quiet(build_plugin.build, archive=first)

    def test_nested_plugin_protects_outer_distribution_and_checkout(self):
        outer = self.base / 'public-checkout'
        (outer / '.git').mkdir(parents=True)
        plugin = outer / 'plugins/shared-memory'
        for name, data in build_plugin.plugin_files().items():
            path = plugin / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        skill = plugin / 'skills/shared-memory'
        for vault in (plugin / 'private-vault', outer / 'private-vault'):
            config = self.base / 'setup.json'
            config.write_bytes(encoded({**self.c, 'vault_path': str(vault)}))
            self.cli(skill / 'scripts/bootstrap.py', '--config', config, '--apply', expected=1)
            self.assertFalse(vault.exists())
        config.write_bytes(encoded({**self.c, 'harness_targets': [
            {'kind': 'codex', 'path': str(outer / 'AGENTS.md')}]}))
        self.cli(skill / 'scripts/bootstrap.py', '--config', config, '--apply', expected=1)
        self.assertFalse((outer / 'AGENTS.md').exists())
        self.assertFalse(self.root.exists())
        with self.assertRaises(ValueError):
            self.quiet(install_skill.install, [outer / 'nested-skill'], True, skill)
