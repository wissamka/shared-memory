# Capture, recall and correction

## Remember this / store this

Resolve “this” from the current conversation. If clear, save immediately within the owner's capture scope; do not require a second approval. If there are two plausible referents, ask a focused clarification. Check `Personal/Preferences.md` and `rules.md` for excluded material.

1. Read the live schema, catalog and destination. Identify whether the item is a personal preference, knowledge, project decision, proposal, question or task.
2. Capture the source with original session/turn identifiers, speaker, source date, status and relevant caveats. Use `scripts/memory.py capture --vault … --input …` for immutable JSON captures; schema is in [installation.md](installation.md).
3. Update the appropriate maintained note in the same session. Explicit requests to remember a preference must reach Personal/Preferences.md now, not wait silently in the inbox until tomorrow. If its home is uncertain, save in the inbox and say so.
4. Link the session/source, update navigation and log, read back, and report the destination briefly. A capture is not independent verification of its contents.

At meaningful milestones, save a session record: goal, useful facts/decisions with attribution, outputs, unresolved questions and next action. Save task state in Working/Handoff.md or a project handoff. Do not record hidden reasoning. A summary must disclose omitted or unavailable portions of the conversation.

## Recall and resume

Find the current canonical note via the catalog, inspect its sources and unresolved conflicts, then answer with links. For “what do you know about me?”, show relevant profile/preferences, distinguish explicit statements from inferred patterns, and invite correction without inventing a fuller biography. For a resumed project, verify current output paths and next action; avoid treating an old handoff as completed work.

## Correct this

Record the exact correction, source, date and scope. Amend all relevant maintained views and mark the prior statement superseded. Preserve history and raw sources. An explicit correction in the current conversation is already sufficient evidence of the user's changed preference or intent.

## Forget this

Stop using the identified information immediately. Resolve ambiguous scope before deletion. A single fact may share a source with unrelated material: do not expand a narrow request into deleting a whole conversation without authority. Raw-source preservation is a routine-maintenance convention, not a reason to ignore an authorized privacy deletion.

For an authorized whole captured source, preview the helper plan:

```sh
python3 scripts/memory.py forget --vault /absolute/path/vault --source-id fictional-source --editor /absolute/path/editor.local.json
```

Add `--apply` once the concrete scope is authorized. To suppress a whole session, use `--session-id fictional-session --harness Codex` instead of `--source-id`; the harness and session together define the scope. The private editor JSON contains actual current provenance, as described in [installation](installation.md).

The helper saves hashed suppression before cleanup, removes matching capture/source records and dependent manifests/receipts, and lists known maintained destinations for separate review. Capture, preparation and the JSONL importer enforce this machine-readable suppression; a note in `Automation/Sources.md` alone is not enforcement. Existing suppression remains active after an interrupted cleanup, so inspect the result and retry the same authorized operation. A copied export with stable source/session identity remains suppressed; this is not semantic detection of the same fact under an unrelated new identity.

The agent must separately remove/redact authorized content from maintained notes, derived summaries, indexes, logs, optional transcript archives and voice corpora. Search beyond the helper's known destinations: it does not discover every paraphrase or edit maintained prose. For a narrow fact, review the source and its other contents before selecting a source-level action. Do not pretend a modified capture still has its original hash. Mixed review receipts invalidated during cleanup make their other inputs pending again; compare existing notes before re-reviewing them.

Read back affected files and verify a repeat import does not restore suppressed sources. Leave only a non-sensitive notice; do not repeat forgotten content in logs or examples. Explain any retained external chat history, cloud versions, backups or inaccessible copies. Suppression is not complete erasure, and no automatic unsuppress operation is provided.

## Personalization during ordinary work

Record direct feedback with its context: chat, technical report, article or business document. Promote repeated observations only as proposed rules until the owner endorses them. Do not generalize frustration in one moment into a personality label. The writing procedure uses current approved rules and selected examples, and never invents experience to imitate a style. Follow [voice calibration](voice.md) for an optional owner-message corpus and reviewed style guide. A full visible-chat archive is a separate, optional source store with its own scope, retention and coverage; it does not replace curated memory or grant access to unavailable conversations.
