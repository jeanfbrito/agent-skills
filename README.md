# agent-skills

Personal collection of [Claude Code](https://docs.claude.com/en/docs/claude-code)
skills. Each folder is one skill with a `SKILL.md` manifest. The manifest's
`description` lists the phrases that trigger the skill. The body has the full
procedure.

## Skills

### Git and pull requests

| Skill | What it does | Notes |
| --- | --- | --- |
| [commit](commit/SKILL.md) | Groups changes by concern. Checks staged publication against a reviewed task delta and checks each stack node. Reports commits and uncommitted changes. | Uses `shared/tone.md` for PR drafts. |
| [pr-description](pr-description/SKILL.md) | Drafts PR text from exact heads and separates local, CI, and missing proof. Checks batch workflow fanout before authorized publication waves. | Draft-first. Uses `shared/tone.md`. |
| [babysit](babysit/SKILL.md) | Fixes open PRs until checks pass, reviews threads sequentially, or makes authorized finite corrections while PRs stay closed. | Own worktree for fixes. Verified resolutions and supported declines. Comments are draft-first. Optional `local-config.yml`. |
| [pr-triage](pr-triage/SKILL.md) | Weekly triage of the repo's open PRs: what blocks your own PRs, review drafts for third-party PRs, duplicate checks for bot PRs. | Draft-first. Keeps head SHAs in `local-state.json`. |
| [branch-triage](branch-triage/SKILL.md) | Sorts a remote's branches into merged and open, and deletes merged ones after you confirm the list. | |
| [worktree-gc](worktree-gc/SKILL.md) | Finds worktrees, branches and stashes left by merged or abandoned work. An audit script classifies each one first. | Deletes only what you confirm. |

### Tickets, reports and team communication

| Skill | What it does | Notes |
| --- | --- | --- |
| [jira](jira/SKILL.md) | Drives Jira through [jira-cli](https://github.com/ankitpokhrel/jira-cli): JQL, tickets, sprints, and `jira-link-pr` to link a PR to its ticket. | Run `setup.sh` once. Linux variant in `jira/hermes/`. |
| [ticket](commands/ticket.md) | Runs a ticket, Jira task or bug report from start to finish: analyze, research, branch, plan, implement, validate, self-review. Takes a Jira key or URL. | A command (`/ticket`), not a skill. See [Commands](#commands). |
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
| [learn](learn/SKILL.md) | Saves lessons from a session into `lessons.md` files or into the skill that missed them, and proposes new skills for repeated work. | |
| [update-skill](update-skill/SKILL.md) | Creates or updates a skill in this repo with the repo's conventions (frontmatter, absolute paths, README, symlink). | |
| [skill-checkup](skill-checkup/SKILL.md) | Grades the skills against recent session history and drafts `SKILL.md` edits. | Local HTML report. |
| [awesomeness-incremental-loop](awesomeness-incremental-loop/SKILL.md) | Runs a reference-based improvement loop with a product objective per cycle. It never stops while work is left: it keeps decisions for the human and asks them when the human comes back. It records each choice it makes for reviewers to validate, and plans the PR split. | Never pushes. Guides in `references/` and `senses/`. |
| [grok-build](grok-build/SKILL.md) | Hands coding tasks to the Grok CLI in headless mode, with verification and worktree isolation. | Needs `grok login`. |
| [session-mining](session-mining/SKILL.md) | Reads coding-agent history to find repeated work and review tool use. | Local, read-only. Python standard library. Uses `shared/tone.md` for public drafts. |
| [asd-ste100](asd-ste100/SKILL.md) | Rewrites English in Simplified Technical English. `scripts/ste-lint.py` checks the text. | Installs alone: `npx skills add jeanfbrito/agent-skills -s asd-ste100 -g`. |

### Machine and measurement

| Skill | What it does | Notes |
| --- | --- | --- |
| [disk-cleanup](disk-cleanup/SKILL.md) | Frees disk space on macOS. It measures first and cleans caches that rebuild themselves. It restarts a hung Docker before the prune, and asks before it touches your files. | |
| [photo-measure](photo-measure/SKILL.md) | Measures objects in photos in millimetres. It makes a printable marker card to ask for, finds the reference points, and checks the fit before it gives lengths and radii. | `photo_measure.py`, `mat_calib.py` (cutting-mat camera calibration and triangulation; run through uv). |
| [benchmark-checklist](benchmark-checklist/SKILL.md) | Checks a performance number before you report it or act on it. | |
| [proxmox-lxc-service](proxmox-lxc-service/SKILL.md) | Deploys native LXC services with persistent data, address planning, and recovery checks. Includes read-only inventory and access-policy checks. | Reuses `opnsense` for router changes. Uses `shared/tone.md`. |

### Design and game development

| Skill | What it does | Notes |
| --- | --- | --- |
| [one-page-design](one-page-design/SKILL.md) | Draws one printable diagram of one design idea. `fit-check.sh` fails on a second page or a broken layout rule. | Writes `designs/`. Does not commit. |
| [procedural-animation](procedural-animation/SKILL.md) | Reference corpus for character and procedural animation (IK, foot sliding, springs, motion matching). | Self-contained. |
| [mixamo-download](mixamo-download/SKILL.md) | Searches Mixamo and downloads clips through your logged-in Chrome session. | You approve each download list. |
| [codex-imagegen](codex-imagegen/SKILL.md) | Generates or edits raster assets through Codex and checks the saved image. | Needs Codex authentication and its built-in imagegen skill. Uses `shared/tone.md`. |
| [fit-to-object](fit-to-object/SKILL.md) | Runs the test-print loop for a part that must fit a real object: measure at the part's height, label inputs measured or guessed, back up each print, read the fit photos and refit only the measured misfit. | Uses photo-measure, plus freecad-mcp-modeling and freecad-render-check from the private [freecad-skills](https://github.com/jeanfbrito/freecad-skills) repo. |
| [unreal-editor-loop](unreal-editor-loop/SKILL.md) | Drives an open Unreal editor through the Unreal MCP: console and `py` commands, Live Coding or full build, relaunch, Play, results from the log. `ue.sh` finds the project and engine. | Needs the Unreal MCP plugin on in the project. |
| [unreal-anim-lab](unreal-anim-lab/SKILL.md) | Builds an in-game Anim Lab (frame clock, reference ghost, bone measures, gizmos, sweeps, screenshots) from a reference implementation, and runs the measure-fix-prove loop until every pose check passes. | Uses unreal-editor-loop. Debug-only code (not in Shipping). |
| [unreal-rig-match](unreal-rig-match/SKILL.md) | Makes a character body follow a reference rig of another size: prop move, hand IK, finger reach, elbow side, with lab proof. | Uses unreal-anim-lab. Keep licensed reference assets out of git. |

### Moved

- **yt-transcript** now lives in
  [jeanfbrito/yt2txt](https://github.com/jeanfbrito/yt2txt), in
  [`skill/yt-transcript`](https://github.com/jeanfbrito/yt2txt/tree/main/skill/yt-transcript).
  Its `./install.sh` installs the CLIs and links the skill.
- **freecad-mcp-modeling**, **freecad-render-check** and
  **freecad-photo-reference** now live in
  [jeanfbrito/freecad-skills](https://github.com/jeanfbrito/freecad-skills)
  (private).

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
- [`shared/embargo-guard.sh`](shared/embargo-guard.sh) stops embargoed work
  from leaving the machine. As a git `pre-push` hook, it blocks named refs,
  commits that only an embargoed branch has, and embargoed strings in commit
  messages. With `text <file>`, it checks a PR body or a post. The rules live
  in a private file outside the repos (`~/.config/embargo/denylist`).

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
