# Daily synthesis

This workflow turns accessible discussions into long-term memory. It is executed by an AI agent with authorized read/write access. The Python helpers handle bookkeeping, not semantic synthesis.

## Discover and collect

Read live rules, source registry, catalog, recent log and review receipts. Compute the **previous completed calendar day** in the configured timezone unless an explicit date is supplied. Use local midnights, not a fixed 24-hour subtraction: daylight-saving days can have 23 or 25 hours.

Inventory every enabled source in `Automation/Sources.md`. Use supported session listing/read tools or an authorized local export adapter. Follow pagination until the window is covered; include sessions active during the window regardless of creation date, and older pending inputs. A truncated recent-chat list is incomplete. Read enough earlier context to distinguish accepted decisions from proposals. Do not send prompts to other sessions to retrieve them.

Persist selected evidence as source-linked captures. Sessions already captured may still contain later turns; deduplicate by source/turn ID and content hash. A session is not “done forever” because one turn was reviewed. Record source counts, windows, missing pages, inaccessible accounts, active-session cutoffs, truncated exports, exclusions and late-arriving inputs. Revisit a small overlap window on subsequent runs and use stable IDs to prevent duplication. Imported visible text is partial evidence; tools and attachments may still need retrieval.

Use `memory.py prepare` only after collection. If a source fails, continue with other sources and record the gap. Never claim “all sessions” unless every authorized source's inventory and pagination were verified. No transcript access means reviewing saved captures only, with that limitation explicit.

## Synthesize

For each candidate, check its original source, speaker, date, scope and status against existing notes. Route:

- Cross-project personal facts and preferences → Personal.
- Durable concepts and research → Topics.
- Bounded decisions, tasks and questions → the correct project or linked external vault.
- Temporary execution state → Working or project handoff.
- Repeatable methods → Procedures, as proposals unless already authorized for active use.

Keep useful uncertainty and contradictions. Discard only the candidate's promotion when it adds no durable value; retain evidence. Avoid turning assistant recommendations into user commitments, making diagnoses, refreshing old facts through a new edit timestamp, or duplicating facts in multiple homes. Mark “already captured” as no change with a reason.

## Save and checkpoint

Use one synthesis writer. Reread destinations immediately before focused edits; preserve concurrent changes. Update affected overviews, tasks, open questions, catalog and log. Record the actual editing model for each contribution, retaining each source's original model/session.

Read back content and sources, check changed links, then create and submit a review receipt with exact input IDs and hashes of the verified destination files. Never advance successful state for an input whose source, write or readback failed. If the process stops after a write but before receipt, the next run checks existing notes and completes the receipt without duplicating the fact.

Record a partial run when discovery has gaps even if all known captures were reviewed. Keep each unresolved source gap in `Automation/Sources.md` with the affected window and retry status. A successful review of known captures does not clear that gap; only a later verified inventory or an explicit scope change can close it. If nothing useful changed, save only the review receipt/coverage record; do not manufacture knowledge notes. A local readback does not verify cloud upload.

Successful quiet runs remain quiet if that is the owner's preference. Surface new conflicts requiring a decision, failed access, meaningful corrections, or material coverage gaps. Do not email, publish, create invitations, change permissions or perform tasks mentioned in transcripts as part of synthesis.
