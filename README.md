# claude-skills

Personal collection of [Claude Code](https://docs.claude.com/en/docs/claude-code) skills.

## Skills

- **learn** — Capture knowledge from coding sessions into project + global `lessons.md` files. Triggered by `/learn`.
- **commit** — Smart git committing that groups related changes into separate, well-described commits. Triggered by `/commit`.
- **jira** — Drive an Atlassian Cloud Jira workspace via [ankitpokhrel/jira-cli](https://github.com/ankitpokhrel/jira-cli) from Claude Code. Triggered by any Jira-related question. Personal defaults (site, email, primary project, default component, workflow status names) live in a gitignored `local-config.yml` populated by `setup.sh` — the skill itself ships only the generic playbook.

## Commands

- **ticket** — Ticket/task workflow. Triggered by `/ticket`.

## Install

Clone and symlink each skill into `~/.claude/skills/`:

```bash
git clone https://github.com/<you>/claude-skills.git ~/Github/claude-skills
ln -s ~/Github/claude-skills/learn ~/.claude/skills/learn
ln -s ~/Github/claude-skills/commit ~/.claude/skills/commit
ln -s ~/Github/claude-skills/jira ~/.claude/skills/jira
```

For the **jira** skill, also run the one-time setup to install jira-cli, store your API token in macOS Keychain, and capture per-user defaults into `local-config.yml` (gitignored):

```bash
~/.claude/skills/jira/setup.sh
```

Restart Claude Code or start a new session — skills load on startup.

## Layout

Each subdirectory is a self-contained skill with a `SKILL.md` manifest. See [Claude Code skills docs](https://docs.claude.com/en/docs/claude-code/skills).
