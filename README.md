# agent-skills

Personal collection of [Claude Code](https://docs.claude.com/en/docs/claude-code)
skills. Each folder is one skill with a `SKILL.md` manifest. The manifest's
`description` lists the phrases that trigger the skill. The body has the full
procedure.

## Skills

### Git and pull requests

| Skill | What it does | Notes |
| --- | --- | --- |
| [commit](commit/SKILL.md) | Groups related changes into separate commits, each with its own message. | |
| [pr-description](pr-description/SKILL.md) | Drafts a PR title and body in the house style (Summary, What changed, Verification with real numbers) from the diff and the checks that ran. | Draft-first. Uses `shared/tone.md`. |
| [babysit](babysit/SKILL.md) | Works on an open PR until every check is green. A watch script polls checks and review bots. The model triages each batch, fixes and pushes. It stops when a human reviewer comments. | Runs in its own worktree. Optional `local-config.yml`. |
| [pr-triage](pr-triage/SKILL.md) | Weekly triage of the repo's open PRs: what blocks your own PRs, review drafts for third-party PRs, duplicate checks for bot PRs. | Draft-first. Keeps head SHAs in `local-state.json`. |
| [branch-triage](branch-triage/SKILL.md) | Sorts a remote's branches into merged and open, and deletes merged ones after you confirm the list. | |
| [worktree-gc](worktree-gc/SKILL.md) | Finds worktrees, branches and stashes left by merged or abandoned work. An audit script classifies each one first. | Deletes only what you confirm. |

### Tickets, reports and team communication

| Skill | What it does | Notes |
| --- | --- | --- |
| [jira](jira/SKILL.md) | Drives Jira through [jira-cli](https://github.com/ankitpokhrel/jira-cli): JQL, tickets, sprints, and `jira-link-pr` to link a PR to its ticket. | Run `setup.sh` once. Linux variant in `jira/hermes/`. |
| [why](why/SKILL.md) | Finds why code, a setting or a behavior is the way it is, from git history, PRs and every connected source. Grades each claim. | |
| [postmortem](postmortem/SKILL.md) | Writes a post-mortem after a hard task, extracts the lessons, and drafts the write-up and team summary. | Draft-first. Uses `shared/tone.md`. |
| [weekly-digest](weekly-digest/SKILL.md) | Drafts a short weekly update in impact language from real sources (ledger, PRs, git, Jira). | Draft-first. Uses `shared/tone.md`. |
| [proposal](proposal/SKILL.md) | Drafts a one-page technical proposal backed by evidence from the project. | Draft-first. Uses `shared/tone.md`. |

### Daily routine

| Skill | What it does | Notes |
| --- | --- | --- |
| [good-morning](good-morning/SKILL.md) | Builds the day plan from Jira, Rocket.Chat, GitHub and the ledgers, ranked on a fixed ladder, with one main focus. | Read-only. Setup in `good-morning/README.md`. |
| [good-night](good-night/SKILL.md) | Collects what you did today and drafts the closing note that good-morning reads next. Optional wellbeing check-in. | Local only. Setup in `good-night/README.md`. |

### Agents and skills

| Skill | What it does | Notes |
| --- | --- | --- |
| [learn](learn/SKILL.md) | Saves lessons from a session into `lessons.md` files, or into the skill that missed them. | |
| [update-skill](update-skill/SKILL.md) | Creates or updates a skill in this repo with the repo's conventions (frontmatter, absolute paths, README, symlink). | |
| [skill-checkup](skill-checkup/SKILL.md) | Grades the skills against recent session history and drafts `SKILL.md` edits. | Local HTML report. |
| [awesomeness-incremental-loop](awesomeness-incremental-loop/SKILL.md) | Runs an endless improvement loop against a project's reference material. One subagent per cycle, a journal and a trail on disk, step backs on stalls, and a blind critic at the done gate. | Never pushes. Guides in `references/` and `senses/`. |
| [grok-build](grok-build/SKILL.md) | Hands coding tasks to the Grok CLI in headless mode, with verification and worktree isolation. | Needs `grok login`. |
| [asd-ste100](asd-ste100/SKILL.md) | Rewrites English in Simplified Technical English. `scripts/ste-lint.py` checks the text. | Installs alone: `npx skills add jeanfbrito/agent-skills -s asd-ste100 -g`. |

### Machine and measurement

| Skill | What it does | Notes |
| --- | --- | --- |
| [disk-cleanup](disk-cleanup/SKILL.md) | Frees disk space on macOS. It measures first and cleans caches that rebuild themselves. It restarts a hung Docker before the prune, and asks before it touches your files. | |
| [benchmark-checklist](benchmark-checklist/SKILL.md) | Checks a performance number before you report it or act on it. | |

### Design and game development

| Skill | What it does | Notes |
| --- | --- | --- |
| [one-page-design](one-page-design/SKILL.md) | Draws one printable diagram of one design idea. `fit-check.sh` fails on a second page or a broken layout rule. | Writes `designs/`. Does not commit. |
| [procedural-animation](procedural-animation/SKILL.md) | Reference corpus for character and procedural animation (IK, foot sliding, springs, motion matching). | Self-contained. |
| [mixamo-download](mixamo-download/SKILL.md) | Searches Mixamo and downloads clips through your logged-in Chrome session. | You approve each download list. |

### Moved

- **yt-transcript** now lives in `~/Github/yt2txt` (`skill/yt-transcript`). Its
  `./install.sh` installs the CLIs and links the skill.

## Commands

- **ticket** (`commands/ticket.md`): the ticket and task workflow, `/ticket`.

## Conventions

- Cross-file references use absolute paths (`~/Github/agent-skills/...`),
  because the skills are installed as symlinks. `asd-ste100` is the exception:
  it uses paths relative to its own folder, so it works wherever it is
  installed.
- A skill that writes text for other people loads
  [`shared/tone.md`](shared/tone.md) and shows the draft before it sends
  anything.
- Per-user settings and state live in a gitignored `local-config.yml` (or
  `local-state.json`) next to the skill.

## Install

Clone once, then link the skills into `~/.claude/skills/`. Symlinks let a
`git pull` update every skill. Point every machine at the same clone.

```bash
git clone https://github.com/jeanfbrito/agent-skills.git ~/Github/agent-skills
mkdir -p ~/.claude/skills ~/.claude/commands
for d in ~/Github/agent-skills/*/; do
  [ -f "$d/SKILL.md" ] && ln -sfn "${d%/}" ~/.claude/skills/"$(basename "$d")"
done
ln -sfn ~/Github/agent-skills/commands/ticket.md ~/.claude/commands/ticket.md
```

To install one skill only:
`ln -s ~/Github/agent-skills/<name> ~/.claude/skills/<name>`.

The **jira** skill also needs a one-time setup. It installs jira-cli, stores
the API token in the macOS Keychain and writes `local-config.yml`:

```bash
~/.claude/skills/jira/setup.sh
```

Skills load when a session starts. Restart Claude Code or start a new session.

## Credits

- **skill-checkup** is adapted from
  [warpdotdev/common-skills](https://github.com/warpdotdev/common-skills)
  `skill-doctor` (MIT License).
- **benchmark-checklist** and **why** are adapted from
  [cursor/plugins](https://github.com/cursor/plugins) `pstack` (MIT License).
- **asd-ste100** is vendored from
  [danyuchn/asd-ste100-skill](https://github.com/danyuchn/asd-ste100-skill)
  (MIT License). The local changes are in `asd-ste100/UPSTREAM.md`.
- **one-page-design** uses Stone Librande's GDC 2010 one-page design tests.
- **awesomeness-incremental-loop** is adapted from the gauntlet loop.
- **pr-description** replaces the `pr` skill from `mattpocock/skills`.

See `THIRD_PARTY_NOTICES.md` for the license texts.
