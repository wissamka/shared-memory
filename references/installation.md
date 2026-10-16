# Installation

## Install the skill into an agent

Run `python3 install.py` from the downloaded package (Windows: `py install.py`). The interactive installer asks for Codex, Claude Code, both or a custom folder, previews destinations and offers to install. It copies the full skill with its dependencies; no manual copy-paste is needed. For scripted use, run `python3 install.py --harness codex claude --apply`, or supply one or more `--target` absolute skill folders. Without `--apply`, explicit destinations are previewed only.

The installer preserves nonempty unmanaged folders, edited files and different versions. An identical rerun repairs missing files and resumes interrupted installation. To upgrade, review the new version and the old folder's changes, then select a new folder or make a deliberate replacement outside this helper; it never silently deletes an existing skill. It requires Python 3.10+ but no third-party packages. Install `tzdata` separately if vault bootstrap needs a timezone database on your platform.

Start a fresh harness session to load the skill, then run the interview before creating the vault.

## Bootstrap the private vault

Use the interview to fill a private JSON configuration **outside the skill repository**. The example in `assets/config.example.json` is fictional and must be adapted. No network call or account configuration is made by the bootstrap script.

Required fields: `preferred_name`, `role`, `goal`, `timezone` (IANA name), absolute `vault_path`, and `provenance` with `assistant`, `harness`, `model`, `agent`, `session_id`, `chat_reference`, `model_note`. Unknown identities must be literal `unknown` with explanation, never invented.

Set `storage` from the interview: `{ "provider": "google-drive", "relative_path": "Obsidian/Shared Memory" }` is one example. Supported providers are `onedrive`, `google-drive`, `dropbox`, `icloud`, `network-share`, `other` and `local`. The bundled example is explicitly local-only; it is not a recommendation over the person's existing service. For shared storage, resolve the actual mounted/synced root before setting `vault_path`; see [shared storage](shared-storage.md). The old `onedrive_relative_path` field remains supported for existing configurations but is not used for new setups. Conflicting old/new storage settings are rejected.

Optional: `topics`, `communication_preferences`, `document_preferences`, `voice_rules`, `voice_sources`, `approval_rules`, `excluded_data`, `capture_mode` (`explicit` or `durable`), `daily_time`, and `harness_targets`.

Each harness target has `kind` and an absolute `path` to an instruction file. Supported kinds: `codex`, `claude`, `gemini`, `cursor`, `copilot`, `generic`. Choose the actual supported startup location from [harnesses.md](harnesses.md), not a guessed global filename. Paths are local device bindings; keep private configuration off GitHub. Cross-device installations use their own bindings to the same shared-drive-relative vault.

```sh
python3 scripts/bootstrap.py --config /absolute/path/setup.local.json
python3 scripts/bootstrap.py --config /absolute/path/setup.local.json --preview
python3 scripts/bootstrap.py --config /absolute/path/setup.local.json --apply
```

The script refuses unrelated nonempty vaults, symlinked destinations, invalid topics, conflicting managed blocks and overlapping targets. The complete plan is checked before writes. Existing startup text stays intact; new managed instructions are appended. Repeating the same setup preserves edited notes. Interrupted setup leaves a manifest so the identical configuration can resume. There is no destructive reset flag. It does not migrate existing vaults or update a previously installed skill version automatically.

After bootstrap, open `00-Hub.md` in Obsidian using “Open folder as vault.” Complete `Automation/Sources.md`, [scheduling](scheduling.md), and [acceptance checks](acceptance.md). Generated examples or “pending” markers do not count as completed verification.

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

`capture` saves an immutable content-checked inbox record and a linked session-source note. The agent still promotes meaningful facts into maintained notes and updates log/catalog. Duplicate identical source IDs are no-ops; changed content under the same ID is a conflict and must be represented as a correction with a new source ID.

`prepare` selects every unreviewed capture before the end of the chosen local calendar day, including older missed inputs. It saves a manifest under `.memory-state/runs/`. It does not discard future inputs or advance a checkpoint. Its output explicitly limits coverage to persisted captures; inspect the source registry and discover other authorized sessions before creating the final manifest.

After the agent reads sources, synthesizes notes, checks links and rereads destinations, it writes a receipt JSON. The receipt contains `run_id`, `editor` (current provenance), `coverage_gaps` (list), and `results` with one `input_id`, `outcome` (`promoted` or `no_change`), nonempty `reason`, and `destinations` for each successfully reviewed input. A destination is `{ "path": "Personal/Preferences.md", "sha256": "<hash of saved file>" }`. Promoted inputs require destinations. The agent must semantically verify the claim and citations; matching bytes alone do not prove correctness.

```sh
python3 scripts/memory.py complete --vault /absolute/path/vault --receipt /absolute/path/receipt.local.json
python3 scripts/memory.py status --vault /absolute/path/vault
```

Incomplete receipts, missing/changed inputs, out-of-vault paths and missing/changed destinations fail without marking any input reviewed. A receipt with coverage gaps can acknowledge its reviewed captures but remains partial; undiscovered sessions are not declared reviewed. Retrying a failed run is safe. Per-input receipts prevent duplicate promotion; the semantic agent must also compare existing notes.

Saved review manifests are content-checked, and reviewed captures are checked against their original hashes. A changed or missing source stops status/preparation instead of silently dropping evidence. Restore unintended corruption or follow the authorized forgetting procedure. An identical completed receipt can be replayed after a destination note evolves; its hash records the historical review, not a permanent freeze of that note.

## Optional local conversation import

The agent should prefer a supported session-list/read interface, follow pagination, and capture only authorized durable material. When explicitly authorized to import **visible conversation text** from a selected local source tree, use:

```sh
python3 scripts/import_sessions.py --kind codex --source /authorized/session/folder --vault /absolute/path/vault --date 2030-04-02 --editor /absolute/path/editor.local.json
```

This previews counts. Add `--apply` to save. `--kind claude` supports Claude Code JSONL transcripts. These are best-effort adapters for observed local formats, not stable vendor APIs. Codex imports user and final assistant text; Claude imports user/assistant text blocks. Both skip system/developer messages, tool payloads, internal analysis and thinking. Malformed records and unrecognized message channels produce coverage gaps; non-message telemetry is ignored. They examine message timestamps across files, so a session created last week but used today is included. Any attachments, tool evidence and omitted channels need separate authorized retrieval. Copy the returned gaps into `Automation/Sources.md` for later retry; the importer does not update that registry. Do not run this against a whole account unless the user authorized that scope; source roots are mandatory, never auto-discovered. No automatic secret redaction is claimed. Check exclusions before importing.

With a known session ID, import identity survives JSON reformatting, inserted telemetry and copied exports. The first source locator is retained. Without a session ID, identity is scoped to the source file's absolute path; record that gap and review possible duplicates after moving unknown-session exports. Do not combine overlapping partial exports of identical timestamp/content turns without checking them.
