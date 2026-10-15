# good-morning

A Claude Code skill that plans your work day. Type `/good-morning` (or "good
morning", "bom dia", "plan my day"). The skill reads all your inboxes,
ranks each item, and gives you one plan:

- one **main focus**, with the reason, the first step and when it is done
- an **unblock batch**: the people who wait for you, time-boxed first
- at most two **secondary** items
- **carry-over** from yesterday, **stale** work, a **not today** list with
  reasons, **ledger** actions, **FYI**, and the **questions** only you can
  answer

The skill is read-only. It marks nothing as read, posts nothing, moves no
ticket and comments on no PR. Reply drafts and Jira moves happen only when
you ask, and each one needs your approval.

## What it reads

| Source | What it collects | Tool |
| --- | --- | --- |
| Jira Cloud | Your unresolved tickets (priority projects such as SUP first). Tickets where **someone else** changed a field or commented in the window (your own edits are left out). New tickets assigned to you. | REST API (`gm_jira.py`) |
| Rocket.Chat | Mentions, DMs and thread replies in the window, each with a check if you already answered. New channel messages, grouped by room. Older unread messages are counted, not listed. | `rocket-cli` (`gm_chat.py`) |
| GitHub | Review requests sent to you by name (team requests are left out). Your open PRs: checks with the failing check names, review state, human threads. Threads where someone else wrote last, with a hint if it is a question. New PRs and issue comments in the watched repos. Release health: red runs on protected branches and release tags, draft releases, open PRs into release branches. | `gh` CLI (`gm_github.py`) |
| Ledgers (optional) | Open cards and active blockers in `.localdev/workflow/` of each project, with the live state of the PRs that each card names. | files + `gh` (`gm_ledger.py`) |
| Calendar (optional) | Today's meetings, to size the day. | Google Calendar connector in Claude |

## Requirements

| Need | Why | How to get it |
| --- | --- | --- |
| [Claude Code](https://docs.claude.com/en/docs/claude-code) | Runs the skill. | — |
| macOS or Linux, Python 3.9+ | The scripts. Standard library only, no `pip install`. | `python3 --version` |
| `gh` (GitHub CLI) 2.x, signed in | PRs, reviews, notifications, CI runs, releases. The token needs the `repo` and `read:org` scopes (`repo` also covers notifications). | `brew install gh` then `gh auth login` |
| [`rocket-cli`](https://github.com/jeanfbrito/rocket-cli) on your `PATH`, with a profile | Chat triage. Node 20+. A read-only profile is enough and is safer. | See "Set up rocket-cli" below. |
| A Jira Cloud API token | Jira queue and changes by others. | See "Set up Jira" below. |
| This repo at `~/Github/agent-skills` | The skill calls its scripts and the shared tone rules by that absolute path. | See "Install". |

## Install

```bash
git clone https://github.com/jeanfbrito/agent-skills.git ~/Github/agent-skills
mkdir -p ~/.claude/skills
ln -s ~/Github/agent-skills/good-morning ~/.claude/skills/good-morning
```

Restart Claude Code (or start a new session). Skills load at session start.

### Set up rocket-cli

```bash
git clone https://github.com/jeanfbrito/rocket-cli.git ~/Github/rocket-cli
cd ~/Github/rocket-cli && npm install && npm run build && npm link
```

In Rocket.Chat, open **My Account → Personal Access Tokens**, create a token,
and copy the token and your user ID. Then add a read-only profile and make it
the default:

```bash
rocket-cli profiles --add work --url https://open.rocket.chat --token <token> --user-id <user-id> --read-only
rocket-cli profiles --default work
rocket-cli attention --json | head    # check: prints JSON, no error
```

The skill reads your chat username from this profile (`/api/v1/me`).

### Set up Jira

Create an API token at <https://id.atlassian.com/manage-profile/security/api-tokens>.
Then use one of these two options:

- **macOS (recommended):** run the setup of the `jira` skill in this repo. It
  stores the token in the Keychain and writes your site and priority
  projects to `jira/local-config.yml`:

  ```bash
  ~/Github/agent-skills/jira/setup.sh
  ```

- **Any OS:** export the credentials in your shell profile:

  ```bash
  export ATLASSIAN_EMAIL="you@example.com"
  export JIRA_API_TOKEN="<token>"
  export JIRA_SITE="https://yourcompany.atlassian.net"   # default: https://rocketchat.atlassian.net
  ```

Tickets from the projects in `priority_projects` (in `jira/local-config.yml`,
for example `SUP`) always go to the top, as customer escalations.

### Check the setup

```bash
~/Github/agent-skills/good-morning/gm.py collect
```

The `SOURCES` line must show `jira ok | chat ok | github ok | ledger ok`. A
failed source shows its exact error. See "Troubleshooting".

## Configure

The skill keeps your settings in `good-morning/local-config.yml`. Git ignores
this file. The first `gm.py save` creates it from the defaults, or you can
write it by hand before the first run:

```yaml
last_run: null              # gm.py save writes it; the next run starts here
repos:                      # new PRs, issue comments and release health
  - RocketChat/Rocket.Chat.Electron
orgs:                       # your open PRs are listed only in these orgs
  - RocketChat
protected_branches:         # a red CI run here is a "Fire" ('*' is a wildcard)
  - dev
  - master
  - release/*
projects:                   # local clones whose .localdev/workflow is read
  - ~/Github/Rocket.Chat.Electron
rocket_profile: null        # rocket-cli profile; null = the default profile
rocket_username: null       # null = ask the server
stale_days: 7               # idle days before a PR or ticket is "stale"
report: terminal            # terminal | local | artifact (see below)
artifact_url: null          # set after the first artifact publish
vault_path: null            # optional vault (see below); null = no vault
vault_daily_folder: Daily   # daily notes folder inside the vault
vault_section: "## 🎯 Today's Focus"   # the plan goes at the end of this heading
```

Set `repos` and `protected_branches` for the repos that you own or release.
Leave `projects` empty if you do not keep `.localdev/workflow` ledgers.

### Report modes

| `report` | Output |
| --- | --- |
| `terminal` (default) | The full plan as Markdown in the Claude Code session. It has a status line, the main focus, the order of the day and the questions. Each section is a table with colored priority dots. |
| `local` | The same, plus an HTML day sheet that opens in your browser. It follows your light or dark theme. |
| `artifact` | The same, plus the day sheet published as a private claude.ai page. The skill updates the same page every day. |

In any mode, you can ask "show the day sheet" to get the HTML page once.

### Vault (optional)

If you keep an Obsidian vault, or any folder of Markdown notes, set
`vault_path`. Then `gm.py save` also writes the accepted plan into that
day's daily note: main focus, unblock checklist, secondary items and "Not
today", with links. Without `vault_path`, nothing changes.

- The plan goes into `<vault_path>/<vault_daily_folder>/<YYYY-MM-DD>.md`, at
  the end of the `vault_section` heading. If the heading is missing, the
  skill adds it. If the daily note is missing, the skill creates a small one.
- The plan sits between `<!-- good-morning:start -->` and
  `<!-- good-morning:end -->`. A new save on the same day replaces that block
  only. The skill does not change the rest of your daily note.
- If the vault write fails, the plan is still saved.
- [good-night](../good-night/README.md) can write its closing note into the
  same daily note, so each day starts with the plan and ends with what
  happened.

## Use it

1. Type `/good-morning`. A run takes about 30 seconds to collect, then the
   agent decides and prints the plan.
2. Answer the questions at the end of the plan, if there are any.
3. Say "accept" (or "accept, but …" with your changes). The skill saves the
   plan and moves the window, so the next run starts from now and counts
   the carry-over days. If you do not accept, the next run covers the same
   window again.
4. Optional follow-ups: "draft the replies", "move the tickets", "start the
   main focus". Each outward action shows the exact text or change first.

### How it decides

Each item goes on one rung. A higher rung always wins. Inside a rung, the
most recently updated item goes first.

| Rung | Examples |
| --- | --- |
| 🔴 Fire | SUP ticket, escalation post, broken release or auto-update, red CI on a protected branch or release tag |
| 🟠 Unblock | Review request, unanswered question in a DM, mention or PR thread, QA request |
| 🟢 Finish | Your green PR that waits for review, PR into a release branch, ticket In Progress or Changes Requested |
| 🟣 Focus | Highest-priority ticket in Ready for Dev or To Do, current fixVersion first |
| ⚪ FYI | Everything that asks nothing |

Then it applies these rules. There is one main focus and at most two
secondary items. The unblock batch comes first. An item that stays open 3
days in a row must be split, handed off or dropped.

## Commands

The skill runs these for you. You can also run them by hand.

| Command | What it does |
| --- | --- |
| `gm.py collect` | Runs the four collectors at the same time, saves the raw JSON in `$TMPDIR/good-morning/<time>/`, prints a digest of about 80 lines. |
| `gm.py render plan.json` | Prints the plan as the Markdown report, and keeps a copy in `today-plan.json`. |
| `gm.py show` | Prints today's last rendered plan again, with no collection. Exits 1 when there is no plan for today. |
| `gm.py render plan.json --format html [--open] [--fragment] [--out FILE]` | Writes the HTML day sheet. |
| `gm.py save plan.json` | Saves the accepted plan to `last-plan.json`, sets `last_run`, and writes the plan into the vault's daily note when you set `vault_path`. |
| `gm_github.py`, `gm_jira.py`, `gm_chat.py`, `gm_ledger.py` | Each collector alone, JSON on stdout. Run one with `--help` for its flags. |

The plan file format is in `references/plan-schema.md`.

## Files

| File | Purpose |
| --- | --- |
| `SKILL.md` | The steps that the agent follows. |
| `gm.py` | Entry point: `collect`, `render`, `save`, and the digest. |
| `gm_common.py` | Config, time window, ages, `gh` helpers. |
| `gm_github.py`, `gm_jira.py`, `gm_chat.py`, `gm_ledger.py` | The collectors. |
| `gm_render.py` | The Markdown report and the HTML day sheet. |
| `references/plan-schema.md` | The plan JSON format. |
| `local-config.yml`, `last-plan.json`, `pending-run.json` | Your state. Git ignores these files. |

## Privacy

- All collection runs on your machine with your own credentials. Raw data
  stays in `$TMPDIR/good-morning/`.
- Nothing leaves your machine except in `artifact` mode, where the day sheet
  goes to a private claude.ai page in your account.
- When you set `vault_path`, the accepted plan also goes into your vault, which
  is a local folder. If you sync the vault, the plan syncs with it.
- Tokens are never written to the skill folder. Jira uses the Keychain or
  your environment, chat uses the rocket-cli profile, and GitHub uses `gh`.

## Troubleshooting

| Symptom | Cause and fix |
| --- | --- |
| `jira FAILED: no Jira token` | Run `~/Github/agent-skills/jira/setup.sh`, or export `ATLASSIAN_EMAIL` and `JIRA_API_TOKEN`. |
| `jira ... HTTP 401` | The API token expired or the email is wrong. Create a new token. |
| `chat FAILED: rocket-cli ...` | `rocket-cli` is not on your `PATH` (run `npm link` in its clone), or the profile has no valid token. Check with `rocket-cli attention --json`. |
| `chat cache refreshing` | rocket-cli served cached data while it syncs. Counts can be a few seconds old. Run again for exact numbers. |
| `github partial: ... HTTP 504` | GitHub search timed out. The script retries 5xx errors twice. Run again. |
| `github truncated: my_prs` | You have more than 100 open PRs in `orgs`. Narrow `orgs`. |
| No release health | `repos` is empty, or no push, tag or scheduled runs exist on `protected_branches`. |
| The window is wrong | Edit `last_run` in `local-config.yml`, or set it to `null` for the last 24 hours (Friday 00:00 on a Monday). |
