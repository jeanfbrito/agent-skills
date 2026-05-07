# Jira CLI Skill — Claude Code + Hermes

Two versions of the same skill:

| Directory | For | Setup |
|-----------|-----|-------|
| `./` (root files) | Claude Code (macOS) | Keychain + Homebrew |
| `hermes/` | Hermes (Linux) | Binary download + `local-config.yml` |

## Files

| File | Purpose |
|------|---------|
| `SKILL.md` | Skill definition (Claude Code version) |
| `setup.sh` | Installer for jira-cli (macOS — Homebrew + Keychain) |
| `jira-env.sh` | Env helper (macOS — reads from Keychain) |
| `hermes/SKILL.md` | Skill definition (Hermes version) |
| `hermes/setup.sh` | Installer for jira-cli (Linux — binary download) |
| `hermes/jira-env.sh` | Env helper (Linux — reads from `local-config.yml`) |
| `hermes/local-config.yml.example` | Template for manual Hermes config |
| `hermes/scripts/` | Support scripts |

## Hermes install

```bash
# One-shot interactive
~/.hermes-icarus/skills/atlassian/jira/setup.sh
```

See `hermes/README.md` for full instructions.

## Claude Code (macOS) install

```bash
./setup.sh
```
