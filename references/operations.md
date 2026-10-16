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

Stop using the identified information immediately. Resolve ambiguous scope before deletion. Remove/redact it from active notes, derived summaries, captures and pending inputs within the authorized scope; inspect related notes so the next daily run does not reintroduce it. Explain where immutable originals, external chat history, OneDrive version history and backups may retain copies. Do not promise complete erasure outside available control. Add a non-sensitive suppression identifier in `Automation/Sources.md` for future ingestion and a minimal log notice; do not repeat the forgotten content in the notice. Raw-source preservation is a routine-maintenance convention, not a reason to ignore an authorized privacy deletion.

## Personalization during ordinary work

Record direct feedback with its context: chat, technical report, article or business document. Promote repeated observations only as proposed rules until the owner endorses them. Do not generalize frustration in one moment into a personality label. The writing procedure uses current approved rules and selected examples, and never invents experience to imitate a style.
