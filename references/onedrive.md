# Roaming through OneDrive

The user's memory stays in their own private OneDrive folder. The public skill repository contains instructions and fictional templates only.

1. Let the user choose the correct personal or organizational account and existing sync root. A suggested relative folder is `Obsidian/Shared Memory`; never assume a username or organization name.
2. Create the new vault there or carefully integrate an existing vault. Open that folder as a vault in Obsidian. On supported desktops, mark it **Always keep on this device** so local agents can read it offline. [Microsoft Files On-Demand guidance](https://support.microsoft.com/en-us/onedrive/save-disk-space-with-onedrive-files-on-demand-for-windows).
3. Save the OneDrive-relative path in the vault. Keep each machine's absolute path in its own harness startup instructions and private setup configuration. Do not overwrite another machine's binding when the vault syncs.
4. On another device, resolve the same folder and verify the content of a harmless unique test note. Then write a harmless reply there and reread it on the first device. This verifies a round trip at that time; local creation alone does not verify upload.
5. For remote agents, use an authorized OneDrive/SharePoint connector. Resolve the account, drive and actual folder; read rules/schema/index/log contents. Write through supported operations with version checks when available. Recheck permissions on the actual file, not a same-name search result. Never invent cloud URLs or silently create sharing links.

OneDrive sync is not an atomic multi-file transaction or a distributed lock. Designate one writer for synthesis and use unique capture files for independent sessions. If two devices edit the same maintained note, preserve conflict copies and reconcile evidence. Rereading a local file does not prevent a later sync conflict. Keep an independent backup and test restoration.

Obsidian is optional for agents but useful for the owner. Its plugins are not needed by this layout. Sync only what the owner wants to roam; do not put API keys, cookies or account credentials in the vault. Connector access is not created by a Markdown instruction file. When cloud access is unavailable, report the exact route that failed and preserve dated pending updates locally.
