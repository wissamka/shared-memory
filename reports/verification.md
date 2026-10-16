# Verification record — 2026-10-16

Four distinct local test passes were completed using fictional records and temporary folders. The final regression suite contains **64 tests**; all passed, including a run with ASCII as the inherited pipe encoding to check that the CLIs explicitly emit UTF-8.

| Pass | Checks | Result |
|---|---|---|
| 1. Installation | 13 tests: all seven storage choices, legacy configuration, direct installer, interactive accept/cancel, multi-target preflight, existing edits, interrupted setup and rerun from the vault's canonical skill copy | Passed |
| 2. Memory lifecycle | 12 tests: capture provenance, corrections, late arrivals, 25-hour day, historical receipt replay, changed evidence, manifest/receipt consistency, no-change review and malformed CLI input | Passed |
| 3. Failure and recovery | 12 tests: failed flush, unsupported file publication, competing writers, missing input, symlink, malformed exports, model changes, duplicate/reformatted exports and unknown sessions | Passed |
| 4. Packaged use and regression | 5 package tests, then all 64 tests including the original 22: ZIP extraction → direct skill installation → vault bootstrap → capture → simulated sourced synthesis → receipt → repeat review; all five harness files and generated links checked | Passed |

Reproduce the focused passes with `python3 -m unittest discover -s tests -p test_installation.py -v`, then the same command for `test_lifecycle.py`, `test_resilience.py`, and `test_package.py`. Run the full suite with `python3 -m unittest discover -s tests -v`. Package syntax, links and privacy-pattern checks pass with `python3 scripts/check_package.py`; the skill-format validator also passed.

## Defects addressed

- Setup can resume from the installed canonical skill, preserving edited notes and repairing missing files.
- Replaying an identical completed review remains valid after a destination note evolves.
- Modified source captures, changed manifests and incomplete stored receipts are detected instead of silently hiding pending work.
- Interrupted writes do not leave truncated final files; competing content is preserved.
- Copied or reformatted exports with known session IDs deduplicate, while repeated identical turns and model changes remain distinct.
- Invalid input shapes produce actionable failures, and Unicode works in redirected CLI output.

## Privacy review

Reviewed the distributable files, example data, tracked Git history and commit author metadata. Examples use fictional identities, source IDs and preferences. Private vaults, setup files, transcripts, account/drive identifiers, personal paths and credentials are excluded. Commit authors use a generic contributor identity. Automated scans check personal identifiers, private paths, email addresses, credentials, conversation links and cloud-item links; literal scanner patterns are reviewed separately from real values.

Before public publication, also inspect repository metadata, all remote branches/tags, issues, releases, workflow logs and artifacts. GitHub account ownership and the repository URL are intentionally visible when a repository is public. Pattern checks complement review; they are not a universal secret detector. Recheck future contributions and generated archives before distribution.

## Limits of this verification

The tests verify file behavior and review bookkeeping. The synthesis step uses a fictional fixture; it is not an evaluation of a model's semantic synthesis. No person's live history was imported. No actual shared-drive round trip, fresh agent instruction loading, or unattended scheduler execution was performed by these tests. Those remain per-installation checks in [acceptance.md](../references/acceptance.md). Network filesystems that cannot perform exclusive hard-link publication fail safely and need an equivalent supported write route.

The repository workflow runs the full suite on Linux, macOS and Windows with Python 3.10. Consult the workflow result for the exact revision being installed.
