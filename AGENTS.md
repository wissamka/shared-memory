# Maintaining this package

This repository is a distributable skill and fictional examples, not a live personal vault. Keep user configuration, transcripts, session IDs, personal contact details, cloud item identifiers and generated vaults outside the repository.

The entry point is SKILL.md. Supporting workflows live in references; executable helpers use Python 3.10+ and the standard library. A timezone database may be needed on Windows. Keep the skill usable when copied as one folder; do not add dependencies on private paths or other skills.

Run `python3 -m unittest discover -s tests -v` and `python3 scripts/check_package.py` after substantive script changes. Use temporary folders and fictional records. Preserve the distinctions between source provenance and edit provenance, a saved prompt and an installed schedule, known captures and complete session coverage, and local readback and cloud synchronization.

Do not overwrite existing vaults or startup files to make a test pass. Do not activate a scheduler, import a person's session history or publish a personal vault while working on this package.
