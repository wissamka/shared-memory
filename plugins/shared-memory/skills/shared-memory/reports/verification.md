# Documentation release — version 0.3.1

Validated on October 21, 2026. This release adds a beginner's repository guide and README overview, routes explanation requests from the skill entry point, and includes the guide in standalone and plugin distributions. Runtime Python behavior is unchanged.

- All **151 automated tests passed** locally, including installation from the bundled files and generated-plugin consistency.
- Package link, Python syntax and common private-data-pattern checks passed; the skill-format validator passed.
- A file-inventory check confirmed that the guide describes all **26 Python files**: 13 implementation/maintenance files and 13 test/support files. Script command and write-behavior descriptions were checked against their implementations.
- The generated plugin includes the same guide as the standalone skill. Maintainer-only file links open GitHub so they remain usable from an installed skill without the full checkout.

These checks validate the documentation and packaging update. They add no new claim of live cloud synchronization, native startup loading, unattended scheduling or writing-quality acceptance. See the exact published revision's [GitHub checks](https://github.com/wissamka/shared-memory/actions) for platform results.

---

# Reliability and optional voice archive — version 0.3.0

Local validation on October 20, 2026 used fictional records and isolated temporary directories. Four distinct passes completed after integrating the audit fixes:

| Pass | Coverage | Result |
|---|---|---|
| 1. Privacy and review safety | Source/session suppression, interrupted forgetting, stale reviews, deferred outcomes and approved voice evidence | 41 tests passed |
| 2. Collection and readiness | Missed days, partial inventories, reimport suppression, evidence staleness, binding drift and manual scheduling mode | 25 tests passed |
| 3. Installation and recovery | Storage choices, new harnesses, atomic startup edits, interrupted writes and source formats | 40 tests passed |
| 4. Complete packaged regression | Full suite, including standalone ZIP installation, canonical procedure, generated plugin and all prior behavior | **151 tests passed** |

Package link/syntax/private-pattern checks, generated-plugin equality and skill-format validation also passed. The package still uses Python 3.10+ and the standard library; the external skill-format validator's YAML parser is a test-tool dependency only.

The fixes enforce hashed suppression before cleanup, keep collection coverage separate from review completion, reject stale overlapping receipts, allow explicit deferred inputs, surface malformed inputs, and preserve existing startup text during new harness connections. The new read-only readiness report shows what was inspected and what is supported only by dated agent observations. Explicit manual-only setups do not require scheduler checks.

The optional separate chat archive preserves selected visible messages and truthful provenance. When an interface hides original identifiers, those remain unknown and separate stable capture identifiers support overlap handling. Only author-attested user messages can become draft writing examples; exact owner approval activates them. Known knowledge-vault suppressions immediately exclude matching examples; deleting archive copies still requires its scoped cleanup. No model training, training export or service upload is implemented.

An actual agent created a fictional local installation, promoted sourced preferences/project status and completed a manual daily review. A separate agent with no inherited conversation read the generated startup file, recalled the preference with sources, kept an unapproved project unapproved despite a supplier memo containing hostile instructions, saved an explicit format correction, and performed scoped forgetting. Same-source reimport returned suppressed; three unrelated original captures stayed byte-identical. Invalidating the affected mixed review receipt correctly returned remaining inputs to pending.

That exercise found manual-only scheduling placeholders and one missing voice-reference file in an intermediate bundle snapshot. Explicit manual mode and final allowlist integration fixed those issues; regression/package link checks cover the final bundle. The exercise verifies independent explicit instruction loading, not native automatic startup loading across every harness. It does not establish all-provider capture, every shared-drive service, an observed unattended schedule, large-vault retrieval quality or owner-specific voice calibration. Test artifacts stayed private and fictional.

The [completeness audit](completeness-audit.md) and [roadmap](roadmap.md) retain remaining work: reviewed automatic canonical-procedure upgrades/rollback, complete disconnection/recovery, and broader real-installation acceptance. Malformed or missing source evidence still blocks review certification until repaired. Cloud synchronization and distributed concurrent writes are not established by these local tests.

---

# Plugin distribution — version 0.2.0

The native plugin package uses the portable Agent Plugins manifest, a Claude compatibility manifest, and separate Codex/Claude GitHub marketplace catalogs. Both hosts discover the same bundled skill. Plugin files are generated from a reviewed filename list; continuous integration rejects a stale generated copy.

Validation on October 19, 2026:

- Full suite: **70 tests passed** on macOS, including packaged bootstrap, reproducible archive, ignored private-file exclusion and case-alias separation.
- Codex CLI **0.162.1**, isolated unauthenticated profile: local marketplace registration, install, enabled inventory, update to a synthetic next version, uninstall and catalog removal passed.
- Claude Code **2.1.226**, isolated unauthenticated profile: the same lifecycle passed. Native component inspection found one `shared-memory` skill, zero hooks, zero agents and zero MCP servers. Native plugin and marketplace validation passed.
- Test profiles and fictional private memory remained separate; plugin removal preserved the fictional memory. Existing user plugin settings, real vaults and schedulers were not used.
- Explicit distribution filenames now govern both standalone installation and the canonical vault copy. A misplaced ignored local JSON file and private draft were excluded in regression tests.
- Filesystem identity checks now reject existing case aliases of the public package during vault creation, harness binding and standalone installation.

Native installer tests exercise package loading and updates, not model synthesis. A host update still requires a separate reviewed update of the canonical procedure in an existing vault. The documented upgrade is agent-guided; automatic migration, fresh model-driven recall, real cloud synchronization and observed unattended daily review remain unverified. Public directory admission and Cowork upload compatibility are not claimed. The earlier four-pass record below remains historical evidence.

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
