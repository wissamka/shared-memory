# Release readiness roadmap

**2026-10-20 — baseline: version 0.2.0, commit `f1fdbfc`.**

This roadmap follows the [four-perspective completeness audit](completeness-audit.md). “Implemented under validation” means code or workflow exists but acceptance/release validation has not yet established every outcome. “In progress” means work has begun. The baseline remains early access until the relevant gates have evidence. This file does not authorize activating a person's scheduler or importing private histories for testing.

## Must: trustworthy core behavior

| Work | Status | Observable acceptance |
|---|---|---|
| **Persistent forgetting** (C01) | Locally regression-tested | Forget a fictional captured source, then import the same/copied export and attempt direct capture. Forgotten evidence stays excluded; unrelated inputs survive; suppression state contains no forgotten payload. Derived-note redaction and external-history limits are reported separately. Interrupted cleanup can resume. |
| **Durable collection coverage and catch-up** (C02) | Locally regression-tested | After three uncollected days, the next bounded collection plan includes every authorized missing window. Failed sources keep their gaps; other sources advance. Retries deduplicate. Daylight-saving boundaries and late arrivals remain correct. |
| **Per-input receipt ownership** (C03) | Locally regression-tested | A stale overlapping run cannot certify an already-owned input. Same-run exact replay remains valid; conflicting work stays recoverable. |
| **Partial progress inside blocked batches** (C04) | Locally verified | A two-input review with one blocked item checkpoints only the successful item, leaves the other pending and later completes it without duplicate claims. Explicit deferred outcomes now preserve that distinction, including same-day all-deferred retries. |
| **Truthful import omissions** (C05) | Locally regression-tested | Unknown and mixed visible-content formats produce safe coverage warnings; recognized text survives. Hidden reasoning, system messages and tool payloads never enter captures. Gaps remain visible until resolved or explicitly excluded. |
| **Readiness and integrity report** (C06) | Locally verified | A new vault reports no configured sources and only a prepared schedule. Zero pending captures never implies full coverage. Invalid inputs, source windows, bindings, version drift and missing live tests have concrete next steps; unknown checks stay unknown. |
| **Recoverable startup-file edits** (C08) | Locally regression-tested | Faults before/during/after an edit cannot leave an undetected truncated startup file. Proven owned work can resume; original instructions and concurrent edits survive; ambiguous partial blocks produce a preserved conflict and a recovery step. |
| **Independent real-agent acceptance** | Bounded local exercise passed; broader evaluation open | An agent following installed instructions captures a fictional preference and sources; a new session recalls it, applies a correction, preserves conflicts and proposal status, respects exclusions and ignores source-embedded instructions. Save reviewable outcomes and score claims/citations, not wording alone. |
| **Observed schedule and roaming evidence** | Pending authorized test environment | Read back an enabled supported task, run a harmless manual test, then independently observe an unattended execution and receipt. Complete a second-route note/reply round trip for each provider claimed as verified. If unavailable, publish that limit explicitly. |

## Should: easy ongoing use

| Work | Status | Observable acceptance |
|---|---|---|
| **Connect another harness/device** (C07) | New-target connection locally regression-tested; conflicting rebind remains manual | Connect an existing edited vault to a new target using its device-local path without rerunning bootstrap or changing personal notes. Preserve unrelated startup text; repeat safely; reject customized owned blocks with a reviewable conflict. |
| **Reviewed canonical-procedure upgrade** (C09) | Planned | Compare installed baseline, local customizations and new allowlisted package; preview changes, back up privately, preserve conflicts and support rollback. Notes, owner rules and schedules remain untouched. Version drift is visible until reconciled. |
| **Stop/disconnect workflow** (C10) | Planned | Disable/read back the actual selected task, remove only owned startup blocks and keep the vault. Clearly distinguish uninstalling a plugin from stopping collection. Unsupported actions produce specific manual steps. |
| **Recovery guidance** (C10) | Planned | Diagnose damaged sources, pending writes, stale locks and sync-conflict copies; preserve evidence; provide scoped reversible recovery. Never mark a conflict resolved merely because a local read succeeded. |
| **What changed and why** | Planned | One view links recent promoted knowledge, proposed preferences awaiting approval, conflicts and superseded decisions to their sources. A forget notice does not repeat deleted content. |
| **Retrieval evaluation at useful size** | Planned | In a larger fictional vault, retrieve the correct relevant source with bounded context, show conflicting evidence and abstain when absent. Start with existing catalog/lexical navigation. |

## Optional archive and approved voice calibration

The next increment also includes an optional separate archive of accessible visible chat and a private corpus of owner-authored messages. Local helper and workflow integration are tested; owner calibration remains installation-specific. Acceptance requires visible wording/order and legitimate repeats, explicit gaps, secret/internal-content exclusions, separate owner versus assistant/quoted authorship, scoped retention/forgetting, approved style rules/examples and a fresh evaluated sample. Declining these options must leave main setup usable. This is style adaptation through instructions and examples, not model training.

## Later: optional growth

- **Scoped lifecycle capture:** supported hooks may request bounded checkpoints, with explicit-only mode, exclusions, visible status and opt-out. Installation alone must not activate broad transcript collection.
- **Compatibility and migration:** publish tested versus guide-only harness/storage routes; add selected existing-vault import/export and optional retrieval integrations when users need them.
- **Distribution:** pursue reviewed vendor directories and verify additional skills installers. An npm package is not required to deliver the current workflow.

## Release gate and evidence

1. Close each claimed deterministic fix with a regression that reproduces the baseline issue and proves preservation of unrelated data.
2. Run the full test suite, package/privacy checks and generated-plugin validation. Keep all fixtures fictional and generated vaults outside the distributable package.
3. Record actual agent, storage and scheduler acceptance separately from unit tests. A receipt or hash proves bookkeeping, not semantic correctness or cloud synchronization.
4. Update the public verification record with the exact tested revision and remaining limitations. Do not mark this roadmap complete based only on implementation or increasing test counts.
5. After publishing an authorized push or release, monitor workflows for that exact commit through completion, inspect failures and verify corrections. Report missing or unverifiable checks explicitly.

No new server, required database or embedding stack is planned. The objective is dependable portable memory with clear scope and evidence.
