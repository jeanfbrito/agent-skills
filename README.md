# claude-skills

Personal collection of [Claude Code](https://docs.claude.com/en/docs/claude-code) skills.

## Skills

- **learn** — Capture knowledge from coding sessions into project + global `lessons.md` files. Triggered by `/learn`.

## Install

Clone and symlink each skill into `~/.claude/skills/`:

```bash
git clone https://github.com/<you>/claude-skills.git ~/Github/claude-skills
ln -s ~/Github/claude-skills/learn ~/.claude/skills/learn
```

Restart Claude Code or start a new session — skills load on startup.

## Layout

Each subdirectory is a self-contained skill with a `SKILL.md` manifest. See [Claude Code skills docs](https://docs.claude.com/en/docs/claude-code/skills).
