# Vault schema and evidence

The generated vault uses plain Markdown and normal links, readable in Obsidian without plugins.

| Location | Purpose |
|---|---|
| `00-Hub.md`, `index.md` | Human navigation and maintained-page catalog |
| `AGENTS.md`, `rules.md` | Shared schema and owner-approved operating rules |
| `log.md` | Append-only attributable change history |
| `Personal/` | Profile, communication, document preferences and voice |
| `Topics/<topic>/Overview.md` | Durable subject knowledge; add substantive notes as needed |
| `Projects/` | Bounded objectives, decisions, tasks and open questions |
| `People/` | Relevant, authorized relationship context |
| `Sessions/` | Human-readable discussion records and source pointers |
| `RAW/` | Original evidence, preserved during ordinary maintenance |
| `_Inbox/` | Content-addressed captures awaiting synthesis |
| `Working/` | Handoff, unresolved conflicts and pending writes |
| `Procedures/` | Shared-memory skill and owner-specific writing procedure |
| `Automation/` | Source registry, scheduling receipt and daily review prompt |
| `.memory-state/` | Private machine-readable manifests and review receipts |

Use personal memory for cross-project facts and preferences. Keep detailed project knowledge in its own home, linking rather than copying. Separate vaults are appropriate when audiences or permissions differ; folders alone do not enforce access boundaries.

## Two kinds of provenance

**Claim provenance:** source identifier or URL, source/event date, effective/as-of date, speaker/author, status (`confirmed`, `reported`, `proposed`, `inferred`, `superseded`, `unresolved`) and assumptions. A session may contain both user statements and assistant suggestions; attribute them separately. A stable session ID plus turn/message identifier is useful even without a clickable conversation URL.

**Edit provenance:** every maintained page has `updated`, `last_edited_by`, `last_edited_harness`, `last_edited_model`, `last_edited_agent`, `last_edited_session_id`, `last_edited_chat`. Use an ISO timestamp with timezone offset. Record `last_edited_model_note` when unavailable. Original source/author fields remain intact. A later editing model does not become the author of earlier claims.

The operation log records the same identities, affected notes, evidence, changes, assumptions, open conflicts, and what was verified. Keep per-contribution model changes. Do not falsely label all work with a runtime's default model.

## Conflict and freshness rules

First check whether scope, dates, units or proposal-versus-decision status explain a disagreement. Otherwise preserve both accounts and their sources. Add an unresolved-conflict notice to affected notes and link `Working/Conflicts.md`. Ask a specific question when a decision depends on resolving it. Record the user's resolution and effective date; keep the former account as superseded. A newer file timestamp does not prove a newer fact.

## Expansion and maintenance

Search existing notes before adding a section. Create a topic overview only for a useful recurring subject. Link it from hub/catalog and link every new maintained note from an overview or catalog. Update decisions, open questions and current tasks when facts change. Keep verbatim source text in RAW or a source record, not duplicated across every synthesis page.

Log entries use `## [ISO timestamp] operation | title`. Operations include setup, capture, ingest, query, correction, decision, review, lint and forget. Routine maintenance preserves historical entries. Forgetting may require a separately scoped redaction of historical/source copies; keep only a non-sensitive audit notice.
