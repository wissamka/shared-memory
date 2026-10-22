# Understand the repository

Roaming Shared Memory x-harness gives an AI agent a method and file tools for building a private, portable memory system. The public repository contains reusable instructions, code and fictional examples. Your personal information belongs in the separate vault and optional chat archive you choose during setup.

You can use the system through requests such as “remember this,” “review yesterday's sessions,” “resume the project,” or “write using my approved style guide.” Most users do not need to run the Python tools themselves.

## What happens from installation to everyday use

1. **Install the plugin or standalone skill.** This makes the instructions and helpers available to your AI application. Installation alone does not create a vault or turn on chat collection.
2. **Set up your private memory.** The agent asks which storage you use: OneDrive, Google Drive, another shared drive, or local only. It interviews you about your work, preferences, document style and capture boundaries. Personal questions are optional.
3. **Create or integrate the vault.** The bootstrap tool creates a new folder of linked notes and startup instructions. [Existing-vault integration](existing-vault.md) preserves an established system and adds reviewed connections and helper state; the bootstrap tool will not overwrite it to make setup succeed.
4. **Capture useful information.** The agent records authorized facts, preferences, decisions and source references. It distinguishes what you said from its own suggestions, and preserves uncertainty and conflicting accounts.
5. **Synthesize the captures.** The agent reads pending sources and updates durable topic, project and personal notes. Python tools record which inputs were reviewed, deferred or incorporated into which files.
6. **Use memory in later sessions.** A connected agent reads the startup instructions and relevant notes. Shared storage can carry the files to another device, where access and startup loading still need verification.
7. **Optionally schedule and calibrate voice.** Install a real daily task through the chosen runtime's supported scheduler. Separately, opt into a visible-chat archive and approve examples of your own writing for a style guide.

The skill supplies the workflow. The AI performs the interpretation and writing. Python performs repeatable file operations. Your storage service handles synchronization when configured.

## Vocabulary without the jargon

| Term | Meaning in this project |
|---|---|
| **Skill** | A folder of instructions and supporting resources that an agent reads to carry out a task. It does not run independently. |
| **`SKILL.md`** | The skill's entry point: when to use it, which workflow to follow, and rules to preserve evidence and existing files. |
| **Agent / harness** | The agent is the AI doing the work. The harness is the application running it, such as Codex or Claude Code, with its available tools and permissions. |
| **Plugin** | An installable wrapper around the skill and tools, with metadata the host application understands. This project is an AI-agent plugin, not an Obsidian plugin. |
| **Marketplace catalog** | A small file telling the host where to find this plugin. Being installable from this GitHub catalog does not mean a vendor has reviewed or listed it in its public directory. |
| **Python script** | A text file of executable instructions, ending in `.py`. Python runs it. These helpers use Python 3.10+ and the standard library; some platforms also need a timezone database. |
| **Markdown / vault** | Markdown is readable text with simple formatting and links. A vault is a folder containing those notes, which Obsidian can display and browse. |
| **JSON / YAML** | Structured text formats for configuration and records. JSON is used for captures, receipts and manifests; YAML is used for some display metadata, workflows and note headers. |
| **Provenance** | Where a statement came from, when it applied and who said it, plus a separate record of which assistant later edited the note. Unknown identifiers stay unknown. |
| **Capture / synthesis** | A capture preserves a source or selected discussion. Synthesis turns evidence into organized, sourced knowledge. Saving a capture is not proof that synthesis has happened. |
| **Manifest / receipt** | A manifest lists files or inputs. A receipt records a completed operation. Content hashes help detect changes; they do not prove the truth of a claim or quality of an AI's reasoning. |
| **Corpus / style guide** | The corpus is a selected collection of your own writing. The approved style guide describes how you want new writing to sound and supplies suitable examples. Neither changes the model's weights. |

The public package has **one main skill**, `shared-memory`. Its reference documents describe parts of that skill, not separate running agents. Setup also creates a personal `Procedures/write-in-my-voice/SKILL.md` inside your private vault. That procedure uses your approved preferences and examples; the public package does not contain a particular person's voice.

## Three different places for memory

| Place | What belongs there | What it is used for |
|---|---|---|
| **Curated knowledge vault** | Current preferences, topic notes, project decisions, open questions, procedures and linked source records | Recall, planning and future work |
| **Optional separate chat archive** | Authorized, accessible visible user/assistant discussion, with original wording, metadata, redactions and explicit gaps | Returning to the original discussion |
| **Approved writing corpus and style guide** | Selected owner-authored examples, their approvals, and agreed writing rules | Drafting in the owner's preferred style |

The knowledge vault's `Sessions/` folder contains source records for memory captures; it is not automatically a dump of every chat. The optional archive preserves broader visible discussion within its authorized scope. An assistant reply can be archived, but it does not become an example of the owner's writing.

“Dream mode” is the [daily synthesis workflow](daily-review.md): an agent reviews accessible evidence, resolves or flags conflicts, and updates long-term notes. It is not a background service supplied by these scripts. Saving `Automation/Daily review prompt.md` prepares instructions; installing and observing an actual scheduled task are separate steps.

Writing-style calibration uses the AI you already run. This package does not install a model, require an additional training GPU, fine-tune weights or upload a training dataset.

## Every Python helper

Run commands from the skill folder unless a guide says otherwise. The agent normally supplies the private configuration and provenance files. Keep those files outside this public repository.

### Installation and connections

| File | What it does | When it changes files |
|---|---|---|
| [`install.py`](../install.py) | The convenient front door for standalone installation. It hands the work to `scripts/install_skill.py`; it is not a second installer with different behavior. | With no arguments, asks for destinations and confirmation. Explicit destinations preview unless you add `--apply`. |
| [`scripts/install_skill.py`](../scripts/install_skill.py) | Copies the complete, allowlisted skill into Codex, Claude Code or a chosen skill folder. Records installed file hashes, preserves edited/different installations, and can resume an identical interrupted installation. Makes no network calls. | Same behavior as `install.py`. Creates skill files and an installation record; does not create your memory vault. |
| [`scripts/bootstrap.py`](../scripts/bootstrap.py) | Reads your private setup configuration and creates a new vault: navigation, rules, personal notes, topic folders, source/schedule templates, the canonical shared-memory procedure, your writing procedure, and selected startup connections. Preserves existing managed content on a compatible retry. | Previews by default; `--apply` creates files. It does not install a scheduled job or import chat history. |
| [`scripts/connect_harness.py`](../scripts/connect_harness.py) | Connects an additional tool or device to an existing managed vault by adding a managed block to its startup file and recording the connection. Preserves instructions outside that block. | Previews by default; `--apply` updates the chosen startup file and saves a binding receipt. A matching file does not prove the agent loaded it. |

See [installation](installation.md) and [harness connections](harnesses.md) for configuration and commands.

### Capture, synthesis records and source coverage

| File | What it does | Commands and write behavior |
|---|---|---|
| [`scripts/memory.py`](../scripts/memory.py) | Saves sourced captures, prepares pending inputs for an AI review, checks completion receipts and reports memory state. Also supports forgetting a source or known session. | `capture`, `prepare` and `complete` **write immediately**. `status` inspects records and can create a local operation-lock file. `forget` previews unless `--apply` is supplied. |
| [`scripts/collection.py`](../scripts/collection.py) | Tracks which sources are authorized from which start date and which calendar days have been inventoried. Makes missing/partial collection days visible, separately from captured items waiting for synthesis. | `register` previews unless `--apply`; `pending` reads coverage; `record` **immediately saves** a supplied, agent-verified inventory report. It does not fetch conversations itself. |
| [`scripts/import_sessions.py`](../scripts/import_sessions.py) | Reads explicitly authorized local Codex or Claude JSONL session files and imports recognized visible text as memory captures. Can retry missing collection days and late arrivals. Excludes recognized hidden/system/tool content and reports unsupported or incomplete coverage. | Previews by default; `--apply` writes captures and, when a registered source is supplied, collection records. This is a best-effort local adapter, not an account-wide ChatGPT collector. |

In `memory.py`, `capture` writes an inbox record and readable session note. `prepare` writes a review manifest listing pending inputs, including older unreviewed captures. **The AI then reads the evidence and edits the maintained notes.** `complete` checks input/destination records and saves the receipt; it does not write the synthesis or judge whether the prose is correct. Deferred inputs remain pending.

Forgetting first records a hashed suppression entry so the same source/session cannot be reimported through these helpers. It then removes the targeted captures and affected review records. The agent must separately review derived notes, the optional archive and external copies. This is not automatic erasure from every service or backup. See [operations](operations.md) and [daily review](daily-review.md).

### Voice and installation checks

| File | What it does | Commands and write behavior |
|---|---|---|
| [`scripts/voice.py`](../scripts/voice.py) | Manages an optional separate visible-chat archive, selected owner-authored examples and their approvals. Preserves source metadata and gaps. Supplies approved examples for an agent to use when maintaining the style guide. | `setup`, `capture`, `example`, `approve` and `forget` preview unless `--apply`. `corpus` reads eligible approved examples. No model training or network calls. |
| [`scripts/readiness.py`](../scripts/readiness.py) | Reports capture integrity, source coverage, startup connections, canonical-procedure differences and recorded acceptance checks. Keeps missing evidence visible. | `report` is read-only. `record-check` previews unless `--apply`, then saves an observation the operator actually made. It does not itself test cloud sync, run a fresh agent or install a schedule. |

The voice workflow distinguishes “this message was archived,” “this is my own writing,” and “I approve this as an example.” A stored example must pass those separate steps before it belongs in the approved corpus. See [voice and archive](voice.md) and [readiness](readiness.md).

### Internal libraries and maintainer tools

| File | What it does | Who uses it / write behavior |
|---|---|---|
| [`scripts/common.py`](../scripts/common.py) | Shared functions for paths, UTF-8 text, JSON, content hashes, provenance, timezones and checked file creation. Avoids repeating those rules in every helper. | Imported by other scripts; not a user command. Its file functions write only when called by the owning operation. No network or model calls. |
| [`scripts/suppression.py`](../scripts/suppression.py) | Shared functions for hashed forget records, suppression checks, cleanup records and a local operation lock. Helps keep forgotten sources out of later imports and corpus selection. | Imported by memory and archive tools; not a user command. Callers control changes. The lock coordinates one local filesystem, not multiple cloud-connected devices. |
| [`scripts/check_package.py`](../scripts/check_package.py) | Checks relative Markdown file links, parses Python syntax and flags common private-data patterns in package files. | Maintainers run it before publishing. It reads files and reports problems. It is a heuristic check, not a guarantee that all private information has been detected. |
| [`scripts/build_plugin.py`](https://github.com/wissamka/shared-memory/blob/main/scripts/build_plugin.py) | Builds the generated plugin copy and manifests from the distribution list; can create a `.plugin`/ZIP archive. Available in the full repository, not the standalone skill bundle. | **Writes the generated plugin when run normally.** `--check` verifies without changing that copy. Adding `--archive PATH` creates a new archive, even with `--check`. It does not publish to GitHub or a marketplace. |

There is no universal preview switch. In particular, memory capture/review commands and collection-record saving write immediately, while the builder normally writes generated files. Use the table and the relevant workflow guide before invoking a command. The eight operational scripts with command interfaces support `--help`; the two internal libraries and package checker are not general-purpose command interfaces.

## Map of the other repository files

Links to maintainer-only files below open GitHub because those files are intentionally absent from an installed standalone skill.

| File or folder | Purpose |
|---|---|
| [`README.md`](../README.md) | Public introduction, installation routes, examples and development checks. |
| [`SKILL.md`](../SKILL.md) | Instructions the agent loads; routes requests to the appropriate reference workflow. |
| [`AGENTS.md`](https://github.com/wissamka/shared-memory/blob/main/AGENTS.md) | Instructions for agents developing this public package, including fictional test data and keeping private vault data out of the repo. Distinct from the startup files created for a user. |
| [`agents/openai.yaml`](../agents/openai.yaml) | Skill display name, short description and default prompt. Despite the folder name, this does not define or start subagents. |
| [`skill-files.json`](../skill-files.json) | Package version and explicit distribution allowlist. Installers, bootstrap and plugin builds use it to decide which files to copy. |
| [`assets/config.example.json`](../assets/config.example.json) | Fictional setup configuration showing the required storage, identity, preference and harness settings. Make your real copy outside the repo. |
| [`assets/capture.example.json`](../assets/capture.example.json) | Fictional sourced-capture format, including discussion and editor provenance. |
| [`assets/daily-prompt.md`](../assets/daily-prompt.md) | Reusable prompt for the reviewing agent. A prompt is not an installed schedule. |
| [`assets/setup-skill.md`](../assets/setup-skill.md) | Source for the plugin's dedicated `skills/setup/SKILL.md` entry point. Codex's setup action and Claude's `/shared-memory:setup` use it to run the same complete setup workflow. |
| [`references/`](#reference-reading-map) | Detailed workflows and formats; use the reading map below. |
| [`reports/verification.md`](../reports/verification.md) | Recorded tests and their limits. A dated record of verification, not continuous monitoring. |
| [`reports/completeness-audit.md`](../reports/completeness-audit.md) | Product, skill-development, QA and market review findings, fixes and remaining gaps. |
| [`reports/roadmap.md`](../reports/roadmap.md) | Remaining improvements and acceptance work. |
| [`tests/`](#every-test-file) | Automated checks using fictional data and temporary folders. They are development tools, not parts of your memory. |
| [`.agents/plugins/marketplace.json`](https://github.com/wissamka/shared-memory/blob/main/.agents/plugins/marketplace.json) | Codex marketplace catalog pointing to the plugin directory. |
| [`.claude-plugin/marketplace.json`](https://github.com/wissamka/shared-memory/blob/main/.claude-plugin/marketplace.json) | Claude marketplace catalog pointing to the same plugin directory. |
| [`plugins/shared-memory/plugin.json`](https://github.com/wissamka/shared-memory/blob/main/plugins/shared-memory/plugin.json) | Generated portable plugin identity, version and OpenAI onboarding/display metadata. |
| [`plugins/shared-memory/.claude-plugin/plugin.json`](https://github.com/wissamka/shared-memory/blob/main/plugins/shared-memory/.claude-plugin/plugin.json) | Generated Claude plugin manifest. |
| [`plugins/shared-memory/skills/shared-memory/`](https://github.com/wissamka/shared-memory/tree/main/plugins/shared-memory/skills/shared-memory) | Generated copy of the allowlisted skill. Edit root sources, then rebuild; do not maintain this as a separate implementation. The plugin also includes a copy of the license. |
| [`.github/workflows/checks.yml`](https://github.com/wissamka/shared-memory/blob/main/.github/workflows/checks.yml) | GitHub checks on pushes and pull requests: unit tests, package checks and generated-plugin consistency on Linux, macOS and Windows. |
| [`.gitignore`](https://github.com/wissamka/shared-memory/blob/main/.gitignore) | Excludes typical local/private configuration, generated vaults, archives and caches from normal Git additions. Not a complete privacy control; review the distribution allowlist and actual published files. |
| [`.gitattributes`](https://github.com/wissamka/shared-memory/blob/main/.gitattributes) | Keeps text line endings consistent across platforms. |
| [`LICENSE`](../LICENSE) | MIT terms for using and redistributing this package. |

Release downloads include `shared-memory.zip` for the standalone skill and `shared-memory.plugin` for clients that support that plugin archive format. Local `dist/` build outputs are not tracked source. A full repository checkout also contains maintainer tools and tests that the installed skill intentionally omits.

### Reference reading map

| Guide | Read it for |
|---|---|
| [This repository guide](repository-guide.md) | Concepts, every Python file and the package map |
| [Plugin installation](plugins.md) | Native installation, host updates, removal and maintainer packaging |
| [Vault installation](installation.md) | Private configuration, bootstrap and setup validation |
| [Existing vault](existing-vault.md) | Reusing established notes, preferences and voice without replacing the vault |
| [Complete setup](setup.md) | Asking for choices, appending startup instructions, configuring the selected daily job, testing, and resuming unfinished setup |
| [Interview](interview.md) | Questions about work, preferences, documents, voice, privacy and storage |
| [Schema](schema.md) | Vault folders, note metadata, evidence and conflict handling |
| [Operations](operations.md) | Remember, retrieve, correct, forget and inspect personal memory |
| [Daily review](daily-review.md) | Collection, catch-up, synthesis, review receipts and failure recovery |
| [Scheduling](scheduling.md) | Installing a real supported task and verifying its operation |
| [Shared storage](shared-storage.md) | Provider choice, access, roaming, sync and concurrent-write limits |
| [Harnesses](harnesses.md) | Startup instructions and connecting another tool/device |
| [Voice](voice.md) | Separate chat archive, owner-authored corpus, approval and style calibration |
| [Readiness](readiness.md) | Local status and recording actual acceptance evidence |
| [Acceptance](acceptance.md) | Live checks for recall, review, storage and scheduler behavior |

### Every test file

These Python files run through `python3 -m unittest discover -s tests -v` in a full checkout. They create fictional temporary fixtures and simulate failure cases. Passing tests does not establish a particular user's cloud synchronization, model quality or unattended scheduler operation.

| File | What it checks |
|---|---|
| [`tests/helpers.py`](https://github.com/wissamka/shared-memory/blob/main/tests/helpers.py) | Shared fictional records, temporary-folder setup and command helpers for the test suite; not a separate feature. |
| [`tests/test_memory.py`](https://github.com/wissamka/shared-memory/blob/main/tests/test_memory.py) | Core setup, capture, provenance, review receipts, time boundaries and local-import filtering. |
| [`tests/test_installation.py`](https://github.com/wissamka/shared-memory/blob/main/tests/test_installation.py) | Storage choices, installer previews, path protection, interrupted installs and preservation of edits. |
| [`tests/test_connections.py`](https://github.com/wissamka/shared-memory/blob/main/tests/test_connections.py) | Startup connections, existing instructions, concurrent edits, atomic replacement and binding recovery. |
| [`tests/test_collection.py`](https://github.com/wissamka/shared-memory/blob/main/tests/test_collection.py) | Source registration, missed-day catch-up, coverage records, suppression and malformed inventories. |
| [`tests/test_lifecycle.py`](https://github.com/wissamka/shared-memory/blob/main/tests/test_lifecycle.py) | Repeated reviews, evolving notes, changed source evidence, provenance, late arrivals and damaged receipts. |
| [`tests/test_memory_safety.py`](https://github.com/wissamka/shared-memory/blob/main/tests/test_memory_safety.py) | Forgetting, blocked reimports, stale review manifests, interrupted cleanup and local locking. |
| [`tests/test_partial_reviews.py`](https://github.com/wissamka/shared-memory/blob/main/tests/test_partial_reviews.py) | Successful and deferred inputs in the same review, retries and invalid completion records. |
| [`tests/test_readiness.py`](https://github.com/wissamka/shared-memory/blob/main/tests/test_readiness.py) | Read-only reporting, unknown coverage, procedure/binding drift and stale or invalid acceptance evidence. |
| [`tests/test_resilience.py`](https://github.com/wissamka/shared-memory/blob/main/tests/test_resilience.py) | Failure recovery, interrupted file operations, malformed records and import edge cases. |
| [`tests/test_voice.py`](https://github.com/wissamka/shared-memory/blob/main/tests/test_voice.py) | Archive scope, visible-content rules, authorship, approvals, changed examples and forgetting. |
| [`tests/test_package.py`](https://github.com/wissamka/shared-memory/blob/main/tests/test_package.py) | Standalone ZIP installation through a simulated review, links, helper interfaces and packaging checks. |
| [`tests/test_plugins.py`](https://github.com/wissamka/shared-memory/blob/main/tests/test_plugins.py) | Plugin/source consistency, reproducible archives, distribution boundaries and exclusion of unlisted files. |

## What the package can and cannot establish

The helpers provide local validation and bookkeeping. The agent and user still need to verify that the chosen environment can access the right sources, that a fresh session actually reads its startup instructions, and that a scheduled review runs with durable access. A source registry with no pending captures is not proof that every conversation was collected.

A shared-drive folder does not grant an AI access to an account, prove synchronization, or coordinate simultaneous edits on different devices. Use one synthesis writer and verify a real round trip when roaming matters. The Python helpers operate on local filesystem paths; connector-only setups need the agent's authorized connector workflow and equivalent checks.

Updating the installed plugin also does not automatically update `Procedures/shared-memory` inside an existing vault. That canonical copy may have owner customizations and needs a reviewed upgrade. Removing the plugin leaves the private vault, startup connections and scheduled task in place until separately addressed. See [plugin lifecycle](plugins.md) and the [remaining roadmap](../reports/roadmap.md).
