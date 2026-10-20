# Choose storage and verify roaming

Ask which service the person already uses: **OneDrive, Google Drive, another shared-drive solution, or local storage only**. Reuse a known answer. Never assume a paid service, a particular account, or a sync-root name. The public skill repository contains instructions and fictional templates; the private vault belongs in the person's chosen storage.

## Resolve the chosen service

| Choice | What to establish |
|---|---|
| OneDrive | Personal or organizational account, actual synced root, and a folder kept available offline. Use **Always keep on this device** where supported. |
| Google Drive | Correct account and My Drive/shared-drive location, actual Drive for desktop path, and streaming or mirroring mode. Streamed folders need explicit offline availability; mirrored files are stored locally. |
| Dropbox or another sync service | Actual local sync root, account, offline settings and a supported connector if remote access is needed. |
| iCloud Drive | Actual local folder and download/pinning behavior on this device. Test accessibility on each intended operating system. |
| Network share / NAS | Mounted path, read/write permissions, reconnect behavior and whether offline access exists. A mounted share is not automatically an offline copy. |
| Local only | A private local folder. Mark cross-device roaming unavailable unless the owner later chooses and verifies a sharing route. |

Provider details can change: consult current vendor guidance when installing. See [Microsoft Files On-Demand](https://support.microsoft.com/en-us/onedrive/save-disk-space-with-onedrive-files-on-demand-for-windows) and [Google streaming, mirroring and offline access](https://support.google.com/drive/answer/13401938?hl=en).

Set `storage.provider` to `onedrive`, `google-drive`, `dropbox`, `icloud`, `network-share`, `other`, or `local`. Set `storage.relative_path` to the vault's path within the chosen shared root, such as `Obsidian/Shared Memory`; leave it empty for local-only storage. For `other`, record the service name and access route in `Automation/Sources.md`. Keep account/drive identifiers in private configuration or the source registry, never in the public skill.

## Install and test

1. Resolve the real existing local root or mount. The file helpers accept a local filesystem path; they do not sign in, install a sync client, create a cloud account, or verify upload. Do not create a same-name local directory and imply it is synced.
2. Choose a new vault folder or integrate an existing vault carefully. Open the actual folder in Obsidian. Ensure files are downloaded and readable before starting local setup.
3. Keep each device's absolute path in its own harness startup file and private setup configuration. The shared relative locator can roam, but one device's absolute path must not replace another device's binding. Confirm the correct account when multiple accounts contain similar folders.
4. Write a harmless unique test note. Read it on the second device or through the intended authenticated connector. Write a reply there and read it back on the first device. Record time, devices/routes and result. Local readback alone does not verify cloud upload.
5. If only connector access is available, use the supported connector's read/write operations and the schema to create or integrate the vault. The Python bootstrap requires a local folder. Do not create a disconnected local twin and claim installation in the cloud. If no authorized write route is available, preserve a dated pending setup and report that gap.

Use conditional/versioned writes where supported. Resolve the actual account and folder; do not trust a same-name search result or invent cloud URLs. Creating shared links or changing access permissions requires its own user authorization.

File synchronization is not an atomic multi-file transaction or a distributed lock. Designate one synthesis writer, use unique captures for independent sessions, preserve conflict copies, and reconcile against sources. The helpers use an exclusive local hard-link publish to avoid partially written final files; a filesystem without that operation fails safely and needs an agent-supported equivalent conditional write. This does not claim distributed concurrency protection. Keep an independent backup and test restoration.

Obsidian and its plugins are optional for agents. Exclude credentials from every storage option. Connector access is not created by an instruction file. When access fails, record the failed route and keep dated pending updates without claiming that they were saved to the vault.
