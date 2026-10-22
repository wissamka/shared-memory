# Complete first-run setup

Treat setup as one installation workflow, from interview through working memory. Do the authorized work in this conversation. Do not hand the owner a list of commands, a generated daily prompt or a reminder to request scheduling later when supported tools can finish it now.

Plugin installation makes the skills available. Codex exposes a setup action; Claude Code exposes `/shared-memory:setup`. A host may require the owner to launch that conversation once. This package does not silently run install hooks, grant itself access or start jobs before the owner's choices. After setup, ordinary conversation and “remember this” use the startup instructions; no repeated skill invocation is required in a connected host that loads them.

## 1. Discover and ask

Reuse answers and authorization already supplied. Read the [interview](interview.md), inspect the available host tools and known installed state, then ask only missing choices, at most three short questions at a time:

1. **Storage:** “Do you already use OneDrive, Google Drive, another shared-drive service, or local storage only? Should I connect an existing vault or create a new one?” Resolve the actual accessible location; do not assume a provider or machine path.
2. **Agents and capture:** “Which tools should use this memory, globally or only in this project? May I append a memory section to their startup instructions? Should I retain useful decisions as we work or only what you explicitly ask me to remember?” Inspect the actual supported files before proposing them. Ask about source accounts/projects, prospective collection start date and exclusions; do not equate daily synthesis with permission to import all history.
3. **Daily review:** “Would you like automatic daily synthesis or review only when asked?” If daily, ask for time/timezone, execution host and notification preference. Propose 02:00 for the previous local day only as an option. Explain which machine must be available. Inspect existing tasks for this vault and purpose before proposing a new one.

Quick setup needs only the operational choices plus a preferred name or alias and a short communication preference. Offer the deeper document/voice interview after the working connection. Missing optional biography, writing samples or archive consent must not block core setup. An existing vault's preferences remain authoritative.

## 2. Present the concrete plan, then apply

Show the exact vault, startup-file paths and appended block, source scope, and any existing task to update or new task to create, including the rendered prompt, schedule and timezone. Ask for missing authorization; reuse approval already given. If a supported tool needs a separate platform approval, explain that requirement and finish independent work while it is pending.

Use [installation](installation.md) for a new vault or [existing-vault integration](existing-vault.md) for an established one. Keep private plans and configuration outside the public package. Read existing startup files immediately before editing. Use bootstrap's `harness_targets` or [connect_harness.py](../scripts/connect_harness.py) to append one managed block and verify it. Preserve all surrounding instructions. A matching block is already connected; a conflicting/partial block needs reviewed reconciliation, not a second block. Back up reviewed changes privately. Never overwrite the whole startup file with a template or alter unrelated instructions.

Connect every selected host that is accessible, and name each inaccessible host as pending. A global plugin and a global startup binding are separate steps. On another device resolve its own paths to the same vault. Do not create a second vault to get around missing access.

## 3. Finish collection and scheduling

Register the chosen sources and start date using [collection setup](installation.md#register-collection-and-catch-up). Verify the scheduler's access route, not just this conversation's access. When the owner selects summaries only, register that selected summary source and explain that its coverage is limited; do not substitute raw session import. Keep optional full transcripts and a voice corpus separate and opt-in.

For daily mode, follow [scheduling](scheduling.md) **during setup**: inspect matching tasks, update the identified task or create one when absence is verified, and read its settings back. Do not stop at saving a prompt or tell the owner to ask another question to activate the approved job. If more than one matching task exists, show the candidates and resolve ownership before changing one. Never enable one writer per harness for the same vault. Leave unrelated jobs intact.

Record the real provider, task identifier, execution host, timezone, next run, prompt and source scope in `Automation/Schedule.md`. Use the supported run-now/test action when available, inspect its result and save evidence. A manual review in this conversation is useful but cannot prove the scheduled runtime's access. If a run-now action is unavailable, leave first scheduled execution pending and identify its expected time. Use the scheduler's native result/notification mechanism; do not create a separate monitor without authorization.

For manual mode, record that explicit choice in configuration and the schedule note. Do not turn failed daily setup into manual mode merely to clear checks. No scheduler/write access means a specific blocker, not a completed daily installation. Never work around it by changing permissions, inventing a task ID, using a session-only loop, or publishing private memory to a repository.

## 4. Test before handing over

Run [acceptance checks](acceptance.md) with a harmless item the owner permits saving: capture, sourced synthesis, saved-content readback, then fresh-session recall in each selected accessible host. Test storage through the actual cloud route when shared storage was chosen. Preserve provenance and source dates. Do not count this setup conversation's context as recall, a local read as cloud sync, or a simulated scheduler as a real job.

Run [readiness](readiness.md), record only observed results and resolve failures within scope. Keep a private `Automation/Setup.md` checklist with each requested component, selected scope, status, evidence/date, missing access and next action. Link it from the vault index. Re-read this checklist and live state when setup resumes; avoid duplicate vaults, sources, startup blocks or schedules. The checklist is a navigation record, not proof by itself.

Use explicit completion language:

| State | What the owner should hear |
|---|---|
| Awaiting a choice or access | Name the exact question/blocker and what is already applied. Keep setup incomplete. |
| Connected and tested; first scheduled run pending | Report working interactive memory and verified schedule settings separately. Name the next run; do not claim unattended synthesis has passed. |
| All requested checks observed | Report the vault, connected hosts, source scope, verified run and how to use memory normally. No further setup commands needed. |
| Manual mode selected and tested | Report working memory with review on request; no daily task promised. |

At handover, show a short component checklist rather than merely “installed.” Include where the instructions were appended, how to change/disable the schedule, remaining coverage limits and any restart/new session needed. Readiness evidence is dated, not a guarantee of continuous service.
