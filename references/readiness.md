# Inspect installation readiness

Run a read-only local report after setup, before declaring installation complete, and when recovering from failures:

```sh
python3 scripts/readiness.py report --vault /absolute/path/vault
```

An optional `--through YYYY-MM-DD` selects the last calendar day whose collection coverage should be checked. Otherwise the report uses the previous completed day in the vault timezone. The report is a best-effort snapshot while other writers may be active. It does not change files, run a model, contact a cloud account or activate a scheduler.

It combines:

- Captured, reviewed and pending input counts, including invalid inputs and suppressed evidence still awaiting cleanup. These are persisted captures, not proof that every chat was discovered.
- Registered source inventories, missing days, partial days and suggested overlap days. No registered sources means coverage is unknown.
- Recorded device bindings. It compares the managed block with its receipt; unrelated startup edits are allowed. Missing or inaccessible paths on another device remain unverified. A matching block does not prove a fresh agent loaded it.
- The canonical procedure's version and allowlisted contents compared with the local package running this report. Differences may be customizations requiring review. The report does not check GitHub or claim to know the newest remote release.
- Dated acceptance evidence for fresh-session recall, a real daily review, the selected cloud round trip, scheduler settings and an observed unattended execution. A local-only vault marks cloud testing not applicable. When `.memory-state/config.json` explicitly selects `scheduling_mode: "manual"`, both scheduler checks are not applicable; fresh recall, an actual review and the other applicable checks remain required. Missing/legacy scheduling mode defaults to `daily`. Prose in the schedule note cannot change that choice.

`overall_state: attention_required` means inspect `next_actions` and the detailed component states. `evidence_recorded` means the listed local checks and recorded observations have no outstanding flags; it is not a certification of production readiness or continuous service health. A populated folder or saved daily prompt never proves a working installation.

## Record an observed acceptance check

After actually performing a harmless [acceptance check](acceptance.md), record its result with the current editor's provenance and an evidence reference. The helper stores the observation; it does not perform or independently verify the test. Do not run this merely to clear a readiness warning.

```sh
python3 scripts/readiness.py record-check --vault /absolute/path/vault \
  --check fresh_recall --outcome passed \
  --evidence "Fresh test session retrieved the fictional preference and cited its saved source; reference: private acceptance note" \
  --checked-at 2030-04-02T12:00:00+00:00 \
  --editor /absolute/path/editor.local.json
```

This previews the receipt. Replace the fictional timestamp and evidence with the actual observation, then add `--apply` to save. Future timestamps and missing evidence are rejected. Outcomes are `passed` or `failed`; checks are:

| Check | Required observation |
|---|---|
| `fresh_recall` | A fresh harness session reads current instructions, retrieves the harmless preference and cites its original source. |
| `daily_review` | An actual agent review reads authorized evidence, synthesizes or explains no change, saves and rereads notes, and records the review outcome. |
| `cloud_roundtrip` | A harmless note and reply survive a round trip through the chosen second device or authenticated connector. Local readback alone is insufficient. |
| `scheduler_enabled` | The supported scheduler returns and rereads an enabled task, its identifier, host, timezone, scope and next run. |
| `scheduler_observed` | Scheduler history and saved outputs prove an actual unattended execution. A prepared prompt, enabled task or manually invoked run is insufficient. |

Receipts are immutable, content-addressed files in `.memory-state/readiness/checks/`. They retain the check, outcome, time, evidence and actual assistant/harness/model/agent/session provenance. Keep evidence private and never place credentials in it. Repeating an identical receipt is harmless; a changed observation creates another receipt. The newest observation for a check is shown; conflicting outcomes at the same time remain flagged.

Evidence is tied to a fingerprint of configuration, live rules, source declarations, connection receipts, schedule settings and the canonical procedure. Changing these marks old evidence stale; repeat the affected acceptance checks after the changes. Ordinary knowledge/profile edits and daily collection attempts do not invalidate configuration evidence. The fingerprint is deliberately conservative: even an informational edit to a fingerprinted file can require a new check. Finish configuration edits before recording results.

Readiness never treats `scheduler_enabled` as proof of `scheduler_observed`. Recording either scheduler check is rejected while manual review mode is configured. Existing historical receipts are preserved if the owner switches to manual review; the current report marks those checks not applicable without claiming that an old job was disabled. Changing the mode does not create, enable or disable any scheduler. Schedule prose is displayed as a declaration only. Historical passed checks retain their actual dates and are not a guarantee that credentials, devices or external services remain available today.
