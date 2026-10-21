# Completeness audit

**Shared Memory AI Second Brain — 2026-10-20**

Four independent reviews examined the package from product management, skill development, adversarial QA and competitive analysis perspectives. The audited baseline was version **0.2.0**, commit `f1fdbfc643da01a013699ebd2452e018d0137b1c`.

This is a baseline assessment with a remediation checkpoint. New safeguards have passed local regression checks; baseline findings below remain historical evidence, not a claim that the same code is still present. No item is release-verified merely because implementation exists. See the [roadmap](roadmap.md) for priorities and acceptance criteria, and the [verification record](verification.md) for completed checks.

## Release assessment

The package is suitable for explicitly limited early access. It provides the requested structure and agent workflows, but it has not demonstrated a complete dependable unattended memory loop. The highest priorities are persistent forgetting, honest collection coverage after downtime, safe review/recovery, and evidence that fresh agents and a real schedule use the memory correctly.

Agent-led synthesis is an intentional design choice. A separate database, embedding service or always-running server is not necessary to address the identified gaps.

## Requirements coverage

“Implemented” identifies a shipped file/helper capability, not proof of every real installation. “Agent-guided” means a documented workflow that the host agent must execute. “Unverified” means required live evidence is absent, rather than a demonstrated failure.

| User outcome | Baseline status | What exists / what remains |
|---|---|---|
| Organized Obsidian-compatible topics, projects, personal memory and navigation | Implemented | Bootstrap creates Markdown structure and links. Ongoing navigation maintenance remains agent-guided. See [schema](../references/schema.md). |
| Traceable sessions, sources, dates and editing models | Implemented + agent-guided | Capture and receipt helpers preserve identities/hashes; agents must verify semantic attribution and citations. Source and editor provenance remain distinct. |
| “Remember,” “store,” “correct,” “resume,” and profile inspection | Agent-guided; live recall unverified | [Operations](../references/operations.md) specify immediate promotion, correction and recall. The baseline lacked a fresh-agent demonstration; a bounded independent exercise is now recorded in verification. |
| Forget information and prevent it returning | Agent-guided; enforcement missing | Deletion scope is documented, but capture/import does not enforce the suppression registry. |
| Optional personal and document-style interview | Implemented workflow | [Interview](../references/interview.md) covers explicit preferences, optional samples, scope and privacy. No psychological inference or model training is claimed. |
| OneDrive, Google Drive, other shared storage or local-only choice | Implemented choice; access agent-guided; roaming unverified | [Storage guidance](../references/shared-storage.md) requires actual location and round-trip verification. Choosing a provider does not implement its synchronization. |
| Native plugin installation | Implemented and package-tested | Codex and Claude marketplace lifecycle tests are recorded. Reviewed vendor-directory admission and Cowork upload compatibility are not established. |
| Connect multiple harnesses/devices | Initial bindings implemented; later connection manual | Startup blocks exist, but changing bootstrap targets/path fails the identical-config check. A separate bind/rebind operation is missing. |
| Daily synthesis and scheduling | Agent-guided; observed execution unverified | Prompt and schedule receipt distinguish prepared, enabled, tested and observed. The installer does not itself run a model or activate a job. |
| Missed-day recovery | Partial implementation | Already saved captures catch up. Durable inventory state for days never collected is missing. |
| Safe retries, partial progress and readiness | Partial implementation | Hash validation and exact receipt replay exist. Overlapping receipts, blocked inputs, malformed pending files and interrupted startup appends need stronger handling. |
| Updates and removal | Host lifecycle implemented; vault lifecycle manual | Canonical-procedure upgrades and full system disconnection require separate reviewed steps. |

## Confirmed gaps and defects

Evidence locations refer to the baseline above; line numbers may change during remediation. “Missing safeguard” and “manual workflow” are distinguished from undocumented failures.

| ID | Priority / classification | Finding and user impact | Baseline evidence |
|---|---|---|---|
| C01 | Must — missing privacy safeguard | Reimporting a forgotten source recreates its capture and session note. A prose suppression registry is not enforced. Reproduced with fictional data by development and QA reviews. | [Operations](../references/operations.md), lines 24–26; [importer](../scripts/import_sessions.py), lines 123–126. |
| C02 | Must — missing collection capability | Catch-up handles persisted captures, but there is no durable per-source inventory history for uncollected outage days. A single-day import behaves as requested; the missing feature is the daily collection contract. | [Daily review](../references/daily-review.md), lines 7–13; [importer](../scripts/import_sessions.py), lines 105–131. |
| C03 | Must — receipt defect | Two overlapping prepared runs can both acknowledge the same input with different outcomes. Exact replay of one run is safe, but per-input ownership across runs is not enforced. Reproduced. | [Memory helper](../scripts/memory.py), lines 121–132 and 162–180. |
| C04 | Must — partial-progress limitation | One unresolved input prevents checkpointing all successful inputs in the same manifest. This is documented all-or-nothing behavior, but unsuitable for a persistent queue with independently blocked items. Reproduced. | [Memory helper](../scripts/memory.py), lines 96–107; [installation](../references/installation.md), lines 55–62. |
| C05 | Must — coverage defect | A Claude export containing recognized text plus unsupported visible content can omit the latter with no coverage gap. Known hidden/tool content must remain excluded. Reproduced. | [Importer](../scripts/import_sessions.py), lines 65–74; [installation](../references/installation.md), line 74. |
| C06 | Must — readiness/integrity gap | Status only counts captures/reviews. Invalid pending JSON can count as valid work while preparation aborts. No single report combines source gaps, scheduler evidence, bindings, roaming and package drift. | [Memory helper](../scripts/memory.py), lines 142–147 and 184–189; [bootstrap](../scripts/bootstrap.py), lines 148–160. |
| C07 | Should — missing lifecycle automation | Adding a harness or changing a device-local path changes the original setup fingerprint and requires manual integration. Do not loosen bootstrap validation to regenerate an existing vault. | [Bootstrap](../scripts/bootstrap.py), lines 225–230; [harnesses](../references/harnesses.md), lines 3–16. |
| C08 | Must — startup recovery defect | An interrupted direct append can leave a partial managed block that identical setup refuses to repair. The original prefix survives, but the general resume promise is too broad. Reproduced. | [Bootstrap](../scripts/bootstrap.py), lines 259–261 and 293–296; [installation](../references/installation.md), line 31. |
| C09 | Should — manual upgrade gap | A host plugin update does not update the canonical procedure used by an existing vault. Safe manual instructions exist; deterministic drift reporting, customization handling and rollback do not. | [Plugin lifecycle](../references/plugins.md), lines 48–60. |
| C10 | Should — guided lifecycle gaps | Plugin uninstall leaves startup bindings and scheduled work. Full disconnection, source repair and sync-conflict recovery need clearer guided operations and verification. Existing documentation discloses the uninstall behavior. | [Plugin lifecycle](../references/plugins.md), lines 64–66; [shared storage](../references/shared-storage.md), line 30. |

## Remediation checkpoint

Implemented and locally regression-tested; live installation evidence is tracked separately:

- **C01:** whole-source or harness/session forgetting previews scope, writes hashed suppression before cleanup, invalidates affected receipts/manifests and blocks repeat helper ingestion. Maintained prose, optional archives/corpora and external copies still require scoped agent review. Suppression does not recognize arbitrary paraphrases under unrelated identities.
- **C02/C05:** registered collection starts, per-day attempts and missing/partial-day catch-up exist; importer reports unsupported visible-content gaps and enforces suppression. Source access and account/path scope still depend on the authorized runtime and agent verification.
- **C03/C06:** new overlapping review completion is rejected; status distinguishes invalid pending records and suppressed leftovers. The read-only evidence/readiness report combines source inventory, bindings, procedure drift and attributable acceptance observations. Corrupt sources remain preserved; fail-safe preparation can still be blocked by an invalid input.
- **C04:** explicit deferred outcomes allow successful inputs to checkpoint while unresolved work stays pending; same-day retries preserve immutable receipt history. Invalid or missing source evidence still blocks certification until repaired.
- **C07/C08:** a helper connects a new local harness target to an existing vault, and startup edits use checked complete-file publication. Conflicting old bindings and ambiguous legacy partial blocks require reviewed integration; automatic move/rebind is not claimed.
- **Optional archive and voice workflow:** the interview now offers a separate accessible visible-chat archive and an owner-message corpus. Main setup remains usable without these choices; style rules/examples need approval and no model training is claimed.

**Still open:** C09 canonical-procedure upgrade/rollback; C10 complete disconnection and broader recovery; broader model, cloud and unattended-scheduler evidence below. See [roadmap](roadmap.md).

## Evidence still needed

A bounded actual-agent exercise passed after remediation; see [verification](verification.md). It is distinct from native autoload, cloud and unattended-run acceptance.

These are validation gaps, not claims that the underlying operation fails:

- **Broader real agent use:** the bounded fictional exercise now covers sourced synthesis, independent explicit startup loading, recall, correction, proposal status, hostile source instructions and scoped forgetting. Native automatic loading, excluded-data scenarios, conflict-resolution breadth and writing-style quality still need broader evaluation.
- **Actual roaming:** a harmless note written through one selected storage route, independently read and replied to through the other route, then read back. Verify each claimed provider separately.
- **Persistent scheduling:** create/read back an actual supported task, distinguish a manual test from an observed unattended run, and demonstrate recovery after an inaccessible source or host.
- **Useful retrieval:** find relevant evidence in a larger fictional vault, preserve contradictory accounts and abstain when no source exists. More files and successful hashes do not establish answer quality.

At the audited baseline, the **70-test suite**, package checks and generated-plugin checks passed locally. Independent QA repeated one nominal scripted workflow and eight edge scenarios in fresh fictional environments. Scripted note edits and a fresh Python process are not fresh-LLM recall. No live personal history, cloud account or scheduler was used in that audit. Earlier platform and native installer evidence is in [verification](verification.md).

## Competitive context

Official documentation was reviewed on 2026-10-20. This is a capability comparison, not an independent performance, privacy or deletion-guarantee benchmark. No pricing or adoption comparisons are asserted.

| Alternative | Relevant documented capability | Implication for this package |
|---|---|---|
| Basic Memory | Markdown as source of truth, MCP access, lifecycle capture and visible capture/checkpoint status. [Overview](https://docs.basicmemory.com/start-here/what-is-basic-memory), [capture](https://docs.basicmemory.com/integrations/harness-capture). | Closest direct alternative. Portable Markdown alone is not a unique claim; readiness and capture visibility are reasonable expectations. |
| Mem0 | Application memory infrastructure with scoped create/read/update/delete and history, using a library or service. [OSS overview](https://github.com/mem0ai/mem0/blob/main/docs/open-source/overview.mdx), [REST operations](https://github.com/mem0ai/mem0/blob/main/docs/open-source/features/rest-api.mdx). | Useful lifecycle primitives; adopting comparable infrastructure is not necessary for a plain-file skill. |
| OpenMemory | The current repository describes selected session transfer among local coding harnesses; automatic synchronization is listed as future work. [Current README](https://github.com/mem0ai/openmemory/blob/main/README.md). | Session migration and curated durable knowledge solve different parts of continuity. Do not combine older MCP marketing with current features without verification. |
| Letta | Current documentation includes git-backed memory, working-style initialization, dreaming and memory diagnostics. Shared repositories have runtime-specific scope. [Memory](https://docs.letta.com/configuration/memory), [shared repositories](https://docs.letta.com/concepts/shared-memory). | Strong integrated experience and diagnostics; this skill can retain its independence from a particular agent platform. |
| Supermemory | Profiles, memory-review controls and previewable forgetting; a filesystem interface synchronizes to its service. [Review](https://supermemory.ai/docs/recall/memory-review), [forgetting](https://supermemory.ai/docs/recall/memory-operations), [filesystem](https://supermemory.ai/docs/smfs/overview). | Reviewable changes and clear forget-versus-delete semantics matter. A filesystem view does not establish service-independent ownership. |
| Smart Connections | Obsidian-native semantic related-note retrieval with local embeddings by default; chat is a separate plugin. [Official repository](https://github.com/brianpetro/obsidian-smart-connections). | Potential optional companion. Rebuilding Obsidian chat or embeddings would distract from the core memory workflow. |

The defensible positioning is: **a dependency-light setup and maintenance skill for readable memory in storage the owner chooses, with approved working preferences, traceable evidence and checks that show what actually works.** Do not claim unique invention of portable memory, universal chat access, full erasure or superior recall without evidence.

## Scope boundaries

The next increment should strengthen the existing file-based approach. It does not need a proprietary cloud service, mandatory embeddings, an always-on universal recorder, enterprise access control, psychological profiling or an educational course. Optional capture hooks, interoperability and additional distribution routes can follow demonstrated demand and explicit collection consent.
