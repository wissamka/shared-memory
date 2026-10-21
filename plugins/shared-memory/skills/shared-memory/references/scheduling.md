# Install and verify daily scheduling

Daily review (also called dream mode) is the agent workflow in [daily-review.md](daily-review.md). Scheduling is a separate persistent trigger for that workflow, and is part of setup when the owner asks for it. Use the current harness's supported scheduler and schema; do not write proprietary internal scheduler files. Check for an existing task by purpose and vault before creating one. Update the existing task instead of duplicating it. Keep the public skill independent of private automation IDs.

Establish the timezone, review time, selected runtime, source scope and notification preference. A reasonable proposal is 02:00 local time for the previous day, with missed-day catch-up. This is a proposal until selected; do not invent the owner's preference. Show the generated prompt and scope, then use authorization already given rather than asking again unnecessarily.

## Codex desktop

Discover the supported automation-management tool. If available, create a thread heartbeat for this installed vault unless the owner requests a standalone scheduled project. Use the tool's exact schema for its schedule and timezone; confirm the resolved next run. Do not hand-edit automation configuration files. Record actual task ID, execution host, enabled status, timezone, next run and the saved prompt in `Automation/Schedule.md`. Read the result back. A local task depends on its host's availability and access; verify those conditions in the installed version.

## Claude / Cowork

Use a persistent Desktop scheduled task or supported cloud routine. Session-scoped `/loop` is insufficient for an unattended daily service. Desktop tasks need the machine available; cloud routines need a cloud-accessible vault and configured connectors. Inspect the current supported scheduling surface and verify the task after creation. Do not assume Claude Code and Cowork share identical tools, access or scheduling behavior. [Claude scheduling documentation](https://code.claude.com/docs/en/scheduled-tasks).

## Other runtimes

Use their documented persistent scheduler if available. A generic operating-system scheduler is appropriate only when the owner has selected an installed noninteractive agent command, its credentials/usage arrangement, working directory, permissions, timeout, logs and execution host. Configure it through that scheduler's supported interface; test the same unattended command before enabling recurrence. Do not silently fall back to GitHub Actions or send a private vault to a public repository.

If the environment has no persistent scheduler or write access, keep the fully rendered prompt and setup state as **prepared / blocked**, state exactly what is missing, and give the user the concrete next action. Do not label the installation complete or the task scheduled.

## Prompt and receipt

The installer renders `Automation/Daily review prompt.md` from `assets/daily-prompt.md`. Its runtime must read the live source registry and schema every run, plan missing/partial registered collection days as well as older pending captures, preserve provenance, verify saves and record collection and review coverage separately. Source start dates bound authorized history; a daily trigger does not authorize backfilling the whole account. Exclude email/publication or other unrelated actions.

Use these states in `Automation/Schedule.md`:

1. **Prepared** — prompt and desired settings exist.
2. **Enabled** — scheduler returned and read back an actual task ID and settings.
3. **Tested** — a real run read a harmless source, synthesized it, saved, reread and produced a receipt.
4. **Observed** — the scheduler's run history confirms an unattended scheduled execution.

Include last test/run times and failures. Never infer tested or observed from enabled. Avoid duplicate schedules across devices: choose one synthesis writer; all devices may create unique captures. A roaming schedule document is a receipt, not an executable roaming job. Use [readiness](readiness.md) to expose absent or stale execution evidence. A passing file-helper test or prepared prompt does not establish a live unattended run.

For manual-only installations, set `scheduling_mode: "manual"` in the private bootstrap configuration. No scheduler is required and readiness marks scheduler checks not applicable; manual synthesis and fresh recall still require verification. Changing modes in an existing vault is a reviewed update to its private `.memory-state/config.json` and `Automation/Schedule.md`, not a bootstrap reset.
