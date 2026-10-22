# Connect an existing memory vault

Use this workflow when someone already has an Obsidian or Markdown memory system. The goal is to connect the skill to the existing knowledge, rules and writing voice. Do not rerun new-vault bootstrap against a populated unrelated directory. There is no automatic migration or reset flag.

This is a reviewed, agent-guided integration. The owner must authorize the target vault and startup-file changes. Reuse answers and authorization already supplied; ask only about missing scope or material choices.

Follow the [complete setup workflow](setup.md) around this integration. Offer startup-file connections and daily/manual review, then perform the authorized changes in the same setup. Reuse an identified existing schedule; do not leave the owner to discover a separate scheduling step.

## Inspect and map before editing

1. Resolve the real vault and storage provider. Read its live schema, rules, index, recent log, relevant preference notes and any writing procedure. Identify separate project vaults and chat archives; preserve their boundaries.
2. Inspect installed skills/plugins and existing startup files. Reuse an installed copy when appropriate; avoid installing both a plugin and standalone copy of the same skill in one host. A global installation applies to that user's host configuration, not every machine or account.
3. Check for `.memory-state/config.json`, an existing canonical `Procedures/shared-memory`, and any `<!-- shared-memory:start -->` block. Existing managed state means a reviewed connection or upgrade, not a second adoption. Preserve differing or partial records for reconciliation.
4. Prepare a private integration map with the exact canonical locations for profile, preferences, voice, topics/projects, sources, log and index. Compare source content before inferring that two pages duplicate each other. Existing facts retain their original dates and attribution.
5. Preview additions and focused edits. Save copies and content hashes of files that will change to an owner-authorized private backup location. Never store that backup, the map or personal configuration in the public package.

## Add support without replacing the schema

Use checked, create-only writes for new files, preflight the whole list for collisions, and re-read existing files immediately before focused edits. An interrupted integration must compare each intended file and resume only when compatible; do not overwrite a different file merely because the name matches.

| Location | Integration rule |
|---|---|
| `AGENTS.md`, `rules.md`, `index.md`, `log.md` | Preserve the existing schema and history. Add a small integration pointer, catalog entries and an attributable log entry where appropriate. If the vault uses other names, create reviewed routing files only where no conflicting file exists. |
| `Working/Shared memory integration.md` | Suggested home for the private map, source authorization, added files, acceptance evidence and remaining gaps. Link it from the existing index/hub. The owner may choose a different documented location. |
| `Procedures/shared-memory/` | Copy the complete reviewed allowlist into an empty destination. If a canonical procedure already exists, use the [upgrade workflow](plugins.md#updates-have-two-parts), preserving local changes. |
| `Personal/Profile.md`, `Personal/Preferences.md`, `Personal/Voice.md` | If the vault already stores these elsewhere, optional compatibility notes should contain links and routing instructions, not duplicated personal facts or invented defaults. Preserve existing files with these names. |
| `Procedures/write-in-my-voice/SKILL.md` | If the owner already has a canonical voice skill, create a small delegate to it only when this path is empty. Preserve the existing skill and its evidence; do not recalibrate it from scratch or overwrite it with the public template. |
| `.memory-state/config.json` | Create a minimal runtime configuration only if no managed configuration exists. Choose actual timezone, storage, capture scope and scheduling intent; do not copy fictional identity values. |
| `_Inbox/`, `Sessions/` | The helpers use these paths for content-addressed captures and source notes. Inspect existing files first. Unrelated JSON inside `_Inbox/` needs review because the memory helper expects its capture format. Keep the existing files until a separately authorized resolution is clear. Provide a readable `Sessions/Overview.md` when absent, since new source notes link to it. |
| `Automation/Sources.md`, `Automation/Schedule.md`, `Automation/Daily review prompt.md` | Reuse existing schedules and scope. Add accurate records/prompts only where absent. A prepared prompt does not enable a job. If no existing task is found, report it as unverified rather than creating a duplicate. |

The minimal runtime configuration has this shape; these values are examples, not installation choices:

```json
{
  "version": 1,
  "timezone": "Etc/UTC",
  "storage": {"provider": "local", "relative_path": ""},
  "capture_mode": "explicit",
  "scheduling_mode": "daily"
}
```

`daily` records scheduling intent and keeps scheduler acceptance checks pending; it does not activate a task. Use `manual` only when the owner selects review on request. Capture mode follows the owner's existing authorization. The connection helper reads one unambiguous line in live `rules.md`: `Capture mode: **explicit**` or `Capture mode: **durable**`. If the rules already express that choice elsewhere, add an attributable machine-readable line after confirming consistency. Do not silently override an existing restriction.

Do not fabricate `.shared-memory-install.json` to bypass bootstrap's protection. An adopted vault can use the memory and connection helpers without claiming it was created by bootstrap. Keep the adoption plan and evidence in the private integration map instead.

## Connect the chosen hosts

Install the native plugin globally for each authorized user account, or use the standalone installer for hosts without that route. Then run the [connection helper](harnesses.md#connect-an-additional-local-harness) from the installed package against the real vault and actual supported startup files. Preview first and apply within the owner's authorization.

The helper preserves instructions outside its managed block and records a binding. If another block conflicts, compare its meaning and preserve a backup before any separately reviewed replacement. Global setup must not erase project-specific rules, publication boundaries or other existing instructions.

The standard startup block reads `Personal/Preferences.md` and `Procedures/write-in-my-voice/SKILL.md`. Verify those paths lead to the owner's actual canonical sources, either directly or through reviewed pointer notes. Add instructions in the live vault rules to read the integration map before applying the package's example schema. A pointer is a route to evidence, not a new source for the underlying fact.

## Prove the integration works

1. Compare the existing notes with the pre-integration hashes. Report every intended change; investigate any unexpected change before proceeding.
2. Run the read-only readiness report from the installed package. Zero registered collection sources means unknown coverage, not a complete history.
3. Capture one harmless real decision or preference already authorized for retention, with truthful provenance. Perform a manual sourced synthesis into its existing canonical note and record the receipt. This proves that the helper can work with the old layout; it does not prove unattended execution.
4. In a fresh session for each connected host, ask it to identify the vault and retrieve a harmless existing preference with its source. Do not count a binding receipt or this setup agent's current context as fresh-session recall. Record any host that has not been tested.
5. For shared storage, verify actual cloud contents and another-device access as needed. A local readback does not prove roaming. Reuse and inspect an existing scheduler if one is identified; leave actual scheduling/observed-run gaps explicit otherwise.

Save a completion record listing the installed package version, hosts, preserved sources, actual acceptance checks, pending tests and rollback location. Installing this workflow does not authorize a historical chat import, training upload or publication of the private vault.
