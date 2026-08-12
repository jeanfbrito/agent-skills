# claude-skills

Personal collection of [Claude Code](https://docs.claude.com/en/docs/claude-code) skills.

## Skills

- **learn** — Capture knowledge from coding sessions into project + global `lessons.md` files. Triggered by `/learn`.
- **commit** — Smart git committing that groups related changes into separate, well-described commits. Triggered by `/commit`.
- **jira** — Drive an Atlassian Cloud Jira workspace via [ankitpokhrel/jira-cli](https://github.com/ankitpokhrel/jira-cli) from Claude Code. Triggered by any Jira-related question. Personal defaults (site, email, primary project, default component, workflow status names) live in a gitignored `local-config.yml` populated by `setup.sh` — the skill itself ships only the generic playbook. A Linux-adapted variant for Hermes lives in `jira/hermes/`.
- **grok-build** — Delegate coding tasks to xAI's Grok CLI (`grok`) running headless: implement, review, or diagnose code with verification patterns, session resume, and worktree isolation. Triggered by "use grok", "ask grok", "grok this". Requires the `grok` binary installed and authenticated (`grok login`).
- **postmortem** — Write a post-mortem after a challenging task: full timeline including failed attempts, root causes, customer-safe framing rules, and durable lesson extraction into AGENTS.md and memory. Triggered by `/postmortem`, "write a post-mortem", "document what we learned".

## Commands

- **ticket** — Ticket/task workflow. Triggered by `/ticket`.

## Install

Clone once, then symlink each skill into `~/.claude/skills/` and each command into `~/.claude/commands/` — symlinks mean a `git pull` updates everything, but only if every machine points at the SAME clone:

```bash
git clone https://github.com/jeanfbrito/agent-skills.git ~/Github/agent-skills
mkdir -p ~/.claude/skills ~/.claude/commands
ln -s ~/Github/agent-skills/learn ~/.claude/skills/learn
ln -s ~/Github/agent-skills/commit ~/.claude/skills/commit
ln -s ~/Github/agent-skills/jira ~/.claude/skills/jira
ln -s ~/Github/agent-skills/grok-build ~/.claude/skills/grok-build
ln -s ~/Github/agent-skills/postmortem ~/.claude/skills/postmortem
ln -s ~/Github/agent-skills/commands/ticket.md ~/.claude/commands/ticket.md
```

For the **jira** skill, also run the one-time setup to install jira-cli, store your API token in macOS Keychain, and capture per-user defaults into `local-config.yml` (gitignored):

```bash
~/.claude/skills/jira/setup.sh
```

Restart Claude Code or start a new session — skills load on startup.

## Layout

Each subdirectory is a self-contained skill with a `SKILL.md` manifest. See [Claude Code skills docs](https://docs.claude.com/en/docs/claude-code/skills).
