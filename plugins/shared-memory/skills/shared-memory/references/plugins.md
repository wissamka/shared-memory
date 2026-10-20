# Plugin installation and updates

Shared Memory AI Second Brain is distributed through this project's GitHub marketplace. It is a file-based skill plugin: no server, credentials or background collector are bundled. Installation adds the workflow to your agent. The guided setup then chooses storage, creates your private vault, connects authorized sources and verifies scheduling separately.

## ChatGPT desktop / Codex

With a recent Codex CLI:

```sh
codex plugin marketplace add wissamka/shared-memory
codex plugin add shared-memory@shared-memory
```

Open Plugins in the desktop app, or `/plugins` in Codex, to inspect the installed plugin. If it does not appear immediately, restart the app. Choose its setup action or ask: “Use Shared Memory AI Second Brain to set up my memory.” Select the plugin/skill explicitly if your interface requires it.

This adds our GitHub marketplace. It does not mean the plugin has been accepted into OpenAI's reviewed public directory. A browser-only ChatGPT session without authorized durable file access cannot create a local vault; use an environment with that access. Account, workspace and client-version restrictions can affect plugin availability.

## Claude Code

In Claude Code:

```text
/plugin marketplace add wissamka/shared-memory
/plugin install shared-memory@shared-memory
```

Start a fresh session, then invoke `/shared-memory:shared-memory` and ask it to set up your memory. Terminal equivalents are `claude plugin marketplace add wissamka/shared-memory` and `claude plugin install shared-memory@shared-memory`.

The release also contains `shared-memory.plugin`, a ZIP of the same plugin for interfaces that support local plugin uploads. File-format packaging alone does not establish compatibility with every Cowork version; use the documented Claude Code route unless upload/install has been verified in your client.

## What setup still needs

Choose OneDrive, Google Drive, another shared drive or local storage; give the agent an authorized writable location. It asks about capture scope, exclusions, personal preferences and the agent tools you use. Python 3.10+ runs the file helpers; a timezone database may be needed on Windows. The agent can perform equivalent checked file operations where Python is unavailable.

No vault, session collection, cloud access, or daily task is activated merely by installing this plugin. The installing agent must record what was created, which sources it could access, whether a real schedule was installed, and the results of [acceptance checks](acceptance.md).

## Updates have two parts

First update the plugin through its host:

```sh
codex plugin marketplace upgrade shared-memory
codex plugin add shared-memory@shared-memory
```

For Claude, use `claude plugin marketplace update shared-memory`, then `claude plugin update shared-memory@shared-memory`. Restart the agent to load the updated package.

Second, ask the updated plugin: “Review and upgrade the shared-memory procedure in my existing vault, preserving my notes and local customizations.”

The vault has its own canonical copy at `Procedures/shared-memory`. A host update does **not** replace that copy. Compare its `skill-files.json` version and file contents with the updated plugin; absence of that manifest means a legacy installation. Do not rerun bootstrap expecting an upgrade: it deliberately preserves existing files.

The agent must:

1. Read the current vault rules and identify the existing canonical procedure.
2. Back up that procedure outside the plugin checkout, in a private location.
3. Compare old and new package files, retaining any owner customization for explicit reconciliation. Use the last installed release as a baseline when available; never assume an edited file is disposable.
4. Apply only reviewed procedure-file updates. Do not replace personal notes, sources, preferences, startup bindings, logs or schedules with generated defaults.
5. Check links, run a harmless capture/recall check, and record the applied version and remaining gaps in the vault log. Keep the backup for rollback.

This is currently an agent-guided upgrade, not an automatic migration tool. A legacy vault or locally customized procedure needs that review. Keep the old procedure available until validation succeeds.

## Removal

Use the host's plugin uninstall action (`codex plugin remove shared-memory@shared-memory` or `claude plugin uninstall shared-memory@shared-memory`). Remove the marketplace separately if you no longer want its catalog.

Uninstalling the plugin leaves your private vault, existing startup bindings and scheduled job in place. Ask the agent to disable the actual scheduled task and remove only the shared-memory managed blocks if you want to stop using the system entirely. Keep or delete your vault according to your own retention choice; plugin removal never authorizes deleting it.

## Maintainer packaging

Edit the root skill and its allowlisted resources, not the generated plugin copy. `skill-files.json` is the reviewed distribution file list and version. Bump its version for a release, then run:

```sh
python3 scripts/build_plugin.py
python3 scripts/build_plugin.py --check
python3 scripts/build_plugin.py --check --archive dist/shared-memory.plugin
```

The build includes only listed files and fails on unexpected files in the generated plugin directory. Both plugin hosts use `plugins/shared-memory/skills/shared-memory`; manifests and both marketplace catalogs stay in Git. Continuous integration checks that the generated copy matches the source.

No npm package is required. The standalone Python installer remains an offline fallback. Skills-CLI installation is not yet a verified route for this release.

Standards checked against [OpenAI plugin packaging](https://developers.openai.com/plugins/build/plugins), [Claude plugin reference](https://code.claude.com/docs/en/plugins-reference) and [Claude marketplaces](https://code.claude.com/docs/en/plugin-marketplaces). Admission to their reviewed public directories is a separate submission/review process.
