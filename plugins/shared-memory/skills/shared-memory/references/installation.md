# Installation

## Install the skill into an agent

Prefer the [native plugin route](plugins.md) for public installation. The following installer is the offline/standalone fallback. If this skill was loaded from an installed plugin, skip installation and proceed to the interview and private-vault bootstrap.

Run `python3 install.py` from the downloaded package (Windows: `py install.py`). The interactive installer asks for Codex, Claude Code, both or a custom folder, previews destinations and offers to install. It copies the full skill with its dependencies; no manual copy-paste is needed. For scripted use, run `python3 install.py --harness codex claude --apply`, or supply one or more `--target` absolute skill folders. Without `--apply`, explicit destinations are previewed only.

The installer preserves nonempty unmanaged folders, edited files and different versions. An identical rerun repairs missing files and resumes interrupted installation. To upgrade, review the new version and the old folder's changes, then select a new folder or make a deliberate replacement outside this helper; it never silently deletes an existing skill. It requires Python 3.10+ but no third-party packages. Install `tzdata` separately if vault bootstrap needs a timezone database on your platform.

Start a fresh harness session to load the skill, then run the interview before creating the vault.

## Bootstrap the private vault

Use the interview to fill a private JSON configuration **outside the skill repository**. The example in `assets/config.example.json` is fictional and must be adapted. No network call or account configuration is made by the bootstrap script.

Required fields: `preferred_name`, `role`, `goal`, `timezone` (IANA name), absolute `vault_path`, and `provenance` with `assistant`, `harness`, `model`, `agent`, `session_id`, `chat_reference`, `model_note`. Unknown identities must be literal `unknown` with explanation, never invented.

Set `storage` from the interview: `{ "provider": "google-drive", "relative_path": "Obsidian/Shared Memory" }` is one example. Supported providers are `onedrive`, `google-drive`, `dropbox`, `icloud`, `network-share`, `other` and `local`. The bundled example is explicitly local-only; it is not a recommendation over the person's existing service. For shared storage, resolve the actual mounted/synced root before setting `vault_path`; see [shared storage](shared-storage.md). The old `onedrive_relative_path` field remains supported for existing configurations but is not used for new setups. Conflicting old/new storage settings are rejected.

Optional: `topics`, `communication_preferences`, `document_preferences`, `voice_rules`, `voice_sources`, `approval_rules`, `excluded_data`, `capture_mode` (`explicit` or `durable`), `daily_time`, `scheduling_mode` (`daily` or `manual`), and `harness_targets`. Set `manual` when the owner declines an unattended schedule; otherwise `daily` prepares scheduling instructions without installing a job. Existing configs without this field retain daily preparation.

Each harness target has `kind` and an absolute `path` to an instruction file. Supported kinds: `codex`, `claude`, `gemini`, `cursor`, `copilot`, `generic`. Choose the actual supported startup location from [harnesses.md](harnesses.md), not a guessed global filename. Paths are local device bindings; keep private configuration off GitHub. Cross-device installations use their own bindings to the same shared-drive-relative vault.

```sh
python3 scripts/bootstrap.py --config /absolute/path/setup.local.json
python3 scripts/bootstrap.py --config /absolute/path/setup.local.json --preview
python3 scripts/bootstrap.py --config /absolute/path/setup.local.json --apply
```

The script refuses unrelated nonempty vaults, symlinked destinations, invalid topics, conflicting managed blocks and overlapping targets. The complete plan is checked before writes. Existing startup text stays intact; new managed instructions are appended. Repeating the same setup preserves edited notes. Interrupted setup leaves a manifest so the identical configuration can resume. Existing startup files are published as complete replacements after checking their prior bytes; a legacy partial/conflicting block is preserved for reviewed recovery, not guessed away. There is no destructive reset flag. It does not migrate existing vaults or update a previously installed skill version automatically. Use [connect an additional harness](harnesses.md#connect-an-additional-local-harness) for a new device/target after setup.

After bootstrap, open `00-Hub.md` in Obsidian using “Open folder as vault.” Complete `Automation/Sources.md`, register authorized collection sources below, follow [scheduling](scheduling.md), and run [acceptance checks](acceptance.md). Offer the optional separate chat archive and owner-message style corpus through [voice calibration](voice.md), then consult [readiness](readiness.md). Generated examples or “pending” markers do not count as completed verification.

## Capture format and helper

Use a private JSON file like `assets/capture.example.json`. Fields:

- `source_id`: stable unique message/turn/capture identifier; a correction gets a new ID.
- `source_date`: offset-aware ISO timestamp of the source event.
- `session_id`, `harness`, `assistant`, `model`, `agent`, `chat_reference`: original source provenance; use unknown when unavailable.
- `title`, `text`, `status`: visible evidence or attributed summary, with reported/proposed/etc. status.
- `captured_by`: the current editor provenance object. Source model and capture model can differ.
- Optional `source_locator`, `as_of`, `coverage`, `model_note`.

```sh
python3 scripts/memory.py capture --vault /absolute/path/vault --input /absolute/path/capture.local.json
python3 scripts/memory.py prepare --vault /absolute/path/vault --date 2030-04-02
```

`capture` saves an immutable content-checked inbox record and a linked session-source note. The agent still promotes meaningful facts into maintained notes and updates log/catalog. Duplicate identical source IDs are no-ops; changed content under the same ID is a conflict and must be represented as a correction with a new source ID. Suppressed sources return a suppressed result rather than being recreated; see [forgetting](operations.md#forget-this).

`prepare` selects every unreviewed capture before the end of the chosen local calendar day, including older missed inputs. It saves a manifest under `.memory-state/runs/`. It does not discard future inputs or advance a checkpoint. Its output explicitly limits coverage to persisted captures; inspect the source registry and discover other authorized sessions before creating the final manifest.

After the agent reads sources, synthesizes notes, checks links and rereads destinations, it writes a receipt JSON. The receipt contains `run_id`, `editor` (current provenance), `coverage_gaps` (list), and `results` with one `input_id`, `outcome` (`promoted`, `no_change` or `deferred`), nonempty `reason`, and `destinations` for every manifest input. Use `deferred` with a reason and no destinations for work that cannot yet be completed. A destination is `{ "path": "Personal/Preferences.md", "sha256": "<hash of saved file>" }`. Promoted inputs require destinations. The agent must semantically verify the claim and citations; matching bytes alone do not prove correctness.

```sh
python3 scripts/memory.py complete --vault /absolute/path/vault --receipt /absolute/path/receipt.local.json
python3 scripts/memory.py status --vault /absolute/path/vault
```

Incomplete receipts, missing/changed inputs, out-of-vault paths and missing/changed destinations fail without marking any input reviewed. Every input must be accounted for; successful items are checkpointed while explicit `deferred` items remain pending. A later prepare includes those pending items in a new immutable attempt, even on the same day. A receipt with discovery gaps or deferred items remains partial; undiscovered sessions are not declared reviewed. Do not label an unresolved input `no_change` to bypass this requirement.

Completion rejects a new run overlapping inputs owned by another completed run; reconcile notes and prepare again. Exact same-run replay remains valid. Local serialization protects helper state changes, but is not a distributed lock; keep one synthesis writer. Receipt ownership prevents conflicting acknowledgements, not duplicate prose written by an agent, so compare existing notes before retrying.

`status` distinguishes valid pending inputs, suppressed leftovers and malformed pending files. It does not certify source coverage, cloud sync or a schedule; use [readiness](readiness.md) for the broader evidence report. Malformed pending files remain preserved and can still block preparation until reviewed recovery; they are not silently skipped.

Saved review manifests are content-checked, and reviewed captures are checked against their original hashes. A changed or missing source stops status/preparation instead of silently dropping evidence. Restore unintended corruption or follow the authorized forgetting procedure. An identical completed receipt can be replayed after a destination note evolves; its hash records the historical review, not a permanent freeze of that note.

## Optional local conversation import

The agent should prefer a supported session-list/read interface, follow pagination, and capture only authorized durable material. When explicitly authorized to import **visible conversation text** from a selected local source tree, use:

```sh
python3 scripts/import_sessions.py --kind codex --source /authorized/session/folder --vault /absolute/path/vault --date 2030-04-02 --editor /absolute/path/editor.local.json
```

This previews counts. Add `--apply` to save. `--kind claude` supports Claude Code JSONL transcripts. These are best-effort adapters for observed local formats, not stable vendor APIs. Codex imports user and final assistant text; Claude imports user/assistant text blocks. Both skip system/developer messages, tool payloads, internal analysis and thinking. Malformed records, unrecognized message channels and unsupported visible-content blocks produce coverage gaps, including mixed recognized/unknown content. Known hidden/tool blocks remain excluded; non-message telemetry is ignored. They examine message timestamps across files, so a session created last week but used today is included. Any attachments, tool evidence and omitted channels need separate authorized retrieval. Mirror actionable gaps in `Automation/Sources.md` for later retry. With `--source-id`, applied imports also persist per-day coverage in the registered collection ledger; the importer does not rewrite the Markdown registry. Do not run this against a whole account unless the user authorized that scope; source roots are mandatory, never auto-discovered. No automatic secret redaction is claimed. Check exclusions before importing.

With a known session ID, import identity survives JSON reformatting, inserted telemetry and copied exports. The first source locator is retained. Without a session ID, identity is scoped to the source file's absolute path; record that gap and review possible duplicates after moving unknown-session exports. Do not combine overlapping partial exports of identical timestamp/content turns without checking them.


## Register collection and catch-up

Choose a stable private source name, its authorized account/folder scope, and the earliest date the owner permits collecting. Record the actual path/access route in `Automation/Sources.md`; registration itself does not grant access or discover sources.

```sh
python3 scripts/collection.py register --vault /absolute/path/vault --source-id example-codex --kind codex --since 2030-04-01 --editor /absolute/path/editor.local.json
python3 scripts/collection.py register --vault /absolute/path/vault --source-id example-codex --kind codex --since 2030-04-01 --editor /absolute/path/editor.local.json --apply
python3 scripts/collection.py pending --vault /absolute/path/vault --through 2030-04-03
python3 scripts/import_sessions.py --kind codex --source /authorized/session/folder --source-id example-codex --catch-up --vault /absolute/path/vault --date 2030-04-03 --editor /absolute/path/editor.local.json
```

The import command previews missing/partial days plus the default one-day late-arrival overlap. Add `--apply` to save captures and collection attempts. `--since YYYY-MM-DD` instead of `--catch-up` explicitly selects a date range ending on `--date`; it must still be authorized. Do not combine `--since` and `--catch-up`. Registration kind must match the importer, and the agent must verify that each use of the source name refers to the same real account/path scope. Changed scope needs a distinct source registration, not erasing old gaps.

Use bounded date windows for large backlogs. A recorded day means the declared selected source was inventoried to the reported extent; it never establishes access to every chat. Missing and partial days remain in the plan until a later successful inventory. A review receipt only advances synthesis bookkeeping, not collection coverage.

For supported connector/API sources, register `--kind manual`, inventory the declared window through the authorized interface and use `collection.py record --vault … --source-id … --date … --report … --editor …` after verifying it. The private report JSON needs `mode: "applied"`, explicit `coverage_gaps: []` or actual gap strings, and an accurate `coverage` description. Optional nonnegative integer counts are `files_examined`, `visible_messages`, `saved_messages`, and `skipped_suppressed`. A preview cannot be recorded as completed. These receipts depend on the agent's truthful inventory; the helper does not query or verify a connector itself.
