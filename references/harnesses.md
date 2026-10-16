# Harness startup adapters

Use one canonical vault. Each device gets a small instruction block pointing to its actual local path plus the same shared-drive-relative locator. Read the canonical rules on every memory-dependent session; do not maintain independent personal facts in each harness file.

| Harness | Entry point | Scope / verification |
|---|---|---|
| Codex | `AGENTS.md` in the project, or `~/.codex/AGENTS.md` / actual CODEX_HOME | Check overrides and project hierarchy; verify a fresh session reads it. Skill discovery can use `~/.agents/skills/shared-memory`. |
| Claude Code | Project `CLAUDE.md` or `~/.claude/CLAUDE.md` | Generated prose routes to canonical instructions; avoids fragile absolute `@` imports containing spaces. Check loaded memory in the current version. |
| Gemini CLI | Project `GEMINI.md` or `~/.gemini/GEMINI.md` | Verify with `/memory show` or supported equivalent. |
| Cursor | Project `AGENTS.md` | Global User Rules are configured through Cursor settings, not an invented global file. |
| GitHub Copilot | Project `.github/copilot-instructions.md` | Scope depends on the Copilot surface; verify instruction loading and file access there. |
| ChatGPT, Grok and other interfaces | Supported project/system instructions or explicitly supplied startup text | Do not invent `GROK.md` autoload behavior. The app must have file or connector access and actually read the files. |

The installer emits generic startup instructions under `Automation/Startup instructions.md` and can append a managed block to selected files via `harness_targets`. It refuses differing existing managed blocks. Preserve unrelated instructions. Attaching a vault folder does not itself load the rules or grant write permission.

A global path such as `/Users/...` cannot be used unchanged on Windows or a cloud worker. Resolve the configured cloud-relative locator through the authenticated connector and read content, not just metadata. Verify a write/readback if editing is intended. Unavailable connectors are reported, with pending changes kept in an authorized local workspace.

Check supported behavior when installing; products evolve. Reference documentation:

- [Codex AGENTS.md](https://developers.openai.com/codex/guides/agents-md)
- [Codex skills](https://developers.openai.com/codex/skills)
- [Claude memory](https://code.claude.com/docs/en/memory)
- [Gemini context files](https://geminicli.com/docs/cli/gemini-md/)
- [Cursor rules](https://cursor.com/docs/rules)
- [Copilot repository instructions](https://docs.github.com/en/copilot/customizing-copilot/adding-repository-custom-instructions-for-github-copilot)
