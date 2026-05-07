---
name: jira
description: Drive your Atlassian Jira workspace from a terminal session via the `jira` CLI (ankitpokhrel/jira-cli). Use this skill ANY time the user asks about Jira tickets, issues, sprints, JQL, boards, story points, worklogs, or names a project key from your org — even if they don't say the word "Jira". Also use it for vague work-status questions like "what's on my plate", "what am I working on", "what's blocked", "show me my open tickets", "current sprint", "ready for dev queue", because that work usually lives in Jira. Skip this skill only when the user is clearly asking about something else (Confluence pages, GitHub PRs, Slack messages) — for those, use the appropriate other tool. Personal defaults (primary project key, default component, default assignee, workflow status names) live in `local-config.yml` next to this file (gitignored), populated by `setup.sh`.
---

# Atlassian Jira workflow (jira-cli)

This skill captures a working setup against any Atlassian Cloud Jira so you can answer Jira questions and execute Jira workflows directly in the terminal instead of nudging the user to "go check Jira."

User-specific config — Atlassian site, email, primary project, default component, default assignee — lives in `local-config.yml` next to this file. That file is gitignored; run `setup.sh` once to populate it. Read defaults from `local-config.yml` whenever this document references "your primary project" / "your default component" etc.

## Preconditions — verify before running commands

Before the first `jira` invocation in a session, verify the binary exists:

```bash
command -v jira >/dev/null 2>&1 || echo "MISSING"
```

If it prints `MISSING`, do not improvise. Tell the user to run the setup script and stop:

> jira-cli isn't installed. Run `~/.claude/skills/jira/setup.sh` to install it via Homebrew, write the config, store the API token in Keychain, and run `jira init`. Then we can continue.

Also verify the config has an `issue.types` block before any write attempt:

```bash
grep -qE "^[[:space:]]+types:" ~/.config/.jira/.config.yml || echo "CONFIG_INCOMPLETE"
```

If it prints `CONFIG_INCOMPLETE` (or the file only has the four-line stub: installation/auth_type/server/login), `jira issue create` and `jira issue move` will fail. Tell the user:

> The jira-cli config doesn't have project metadata yet. Run `~/.claude/skills/jira/setup.sh` (idempotent — re-running re-runs `jira init`), pick your primary project as default, accept the prompts. That populates `issue.types`, custom fields, board, epic schema. Then we can continue.

Do **not** hand-write the `issue.types` block yourself. Hand-written entries with guessed IDs cause jira-cli to panic at runtime (`interface conversion: interface {} is nil, not bool`).

## Authentication — load the token before each command

`jira-cli` reads the API token from the `JIRA_API_TOKEN` env var. The token lives in macOS Keychain (service `jira-cli`, account = your Atlassian email). The skill-local helper script `~/.claude/skills/jira/jira-env.sh` exports it for you. The skill is self-contained — no external repo paths required.

The right pattern in shell calls is to source it inline so the env var is always fresh and isn't accidentally inherited from somewhere stale:

```bash
source ~/.claude/skills/jira/jira-env.sh && jira me
```

If the user has already added `source jira-env.sh` to their shell rc, the explicit `source` is redundant — but it's cheap and harmless, and guarantees the command works even in a one-off shell.

If `jira me` returns a 401, the most likely cause is a stale or revoked token. Tell the user to mint a fresh one at https://id.atlassian.com/manage-profile/security/api-tokens and rerun the setup script — don't try to "fix" the token yourself.

### `Error: invalid issue types in config`

`jira issue create` requires an `issue.types` block in `~/.config/.jira/.config.yml` listing the issue types known to the target project. If the config is missing this block (e.g. fresh install, or `jira init` was never run), every create call will fail with `Error: invalid issue types in config` regardless of the `--type` value.

Do **not** hand-write fake IDs — jira-cli will panic at runtime (`interface conversion: interface {} is nil, not bool`). Bootstrap correctly:

1. Run `jira init` interactively and let it pick the default project. It populates the `issue.types` block with real IDs and `subtask` flags pulled from the API.
2. Or, if `jira init` is not feasible, fetch real type IDs via REST and write them yourself with the exact shape jira-cli expects:
   ```yaml
   issue:
     types:
       - id: "10001"
         name: Bug
         handle: Bug
         subtask: false
   ```
   The `subtask: false` (or `true` for Sub-task) field is mandatory; omitting it triggers the panic above.

Until the config is valid, all `jira issue create` invocations are blocked. Tell the user, do not improvise.

## Project conventions — what the keys mean

Most orgs have a few core projects you'll see often. Discover them on first use:

```bash
jira project list --plain --no-headers --columns key,name | head -20
```

Save the keys you actually care about into `local-config.yml` (or just remember the conversational mapping). When the user says "the desktop one" / "the customer issue" / "the platform bug" without a key, infer the project from context (working directory, recent conversation, branch name). If you can't tell, ASK — guessing wrong on a write is worse than a one-line clarifying question.

### Your primary project (read from `local-config.yml`)

`defaults.primary_project` in `local-config.yml` is the project you spend most time in. Whenever the user mentions "ticket / issue / bug" without a project key, default to that project.

**Valid issue types** vary per project. Run `jira init` once to populate them in `~/.config/.jira/.config.yml`. Common ones across most projects:

- `Bug` — broken behavior, regression, crash
- `Task` — generic engineering work that doesn't fit Bug/Story
- `Improvement` — chore / refactor / ops / cleanup / runbook / dep bump / credential rotation
- `Story` — new capability tracked as user-facing work
- `New Feature` — user-visible feature (some teams use Story instead)
- `Epic` — multi-issue effort
- `Sub-task` — child of another issue

Some orgs add `Debt`, `sub-bug`, `Spike`, etc. — ask the user which ones their team actually files before defaulting.

For chore/credential/runbook work pick `Improvement`. For investigation tickets that ship code, `Task`. Don't second-guess if the work matches one of these — file it.

**Statuses** vary per project workflow. The classic chain is `To Do` → `In Progress` → `Done`. Many engineering orgs add `Ready for Dev` (after triage) and `Ready for QA` (after PR opens). When transitioning via `jira issue move`, pass the target status name **exactly** as the workflow expects (case- and space-sensitive). To enumerate available transitions for a specific issue:

```bash
jira issue view <KEY> --raw | jq '.fields.status'
# or
jira issue move <KEY>   # interactive — shows available transitions
```

Pin known statuses in `local-config.yml` under `workflow_statuses:` so the skill doesn't have to rediscover them every session.

**Default component:** read from `defaults.default_component` in `local-config.yml`. If set, pass `--component <value>` whenever creating in the primary project. Other projects keep their own defaults — apply this rule only to the primary project unless the user says otherwise.

### Defaults for primary-project tickets

When creating a ticket in the primary project, always pass:

- `-a $(jira me)` — assign on creation if `defaults.default_assignee` is empty (or matches the current user). Standing preference; do not ask.
- `--component <defaults.default_component>` — when set; required so the ticket reaches the right swimlane.

Other projects keep their own defaults — these rules are scoped to the primary project. Confirm with the user before applying assignee/component to a non-primary project.

## Default sprint context

If your primary project uses Scrum, the active sprint changes regularly. Re-discover at runtime:

```bash
jira sprint list --project <KEY> --current --plain --no-headers
```

Don't hard-code sprint IDs in commands you write for the user. Always look them up at runtime if needed. Kanban-only projects won't return sprints — that's expected, not an error.

## Read operations — preferred forms

The user is a software engineer, so favor concise, scriptable forms. Default to `--plain` when piping to other tools, default to TUI/styled output when showing the user something to skim.

**"What am I working on" / "open tickets":**

```bash
jira issue list -q "assignee = currentUser() AND resolution = Unresolved" --order-by updated --reverse
```

**Filter to current sprint:**

```bash
jira issue list -q "assignee = currentUser() AND sprint in openSprints()"
```

**View a single issue:**

```bash
jira issue view <KEY>
```

Note: jira-cli's ADF renderer is incomplete — some Atlassian Document Format nodes (panels, status lozenges, custom emoji) render imperfectly. If the user wants the raw description for inspection, use `--raw` to dump JSON instead.

**JQL search with custom output for parsing:**

```bash
jira issue list -q "project = <KEY> AND status = 'Ready for Dev'" \
  --plain --no-headers --columns key,summary | head
```

**Boards / sprints (Scrum projects only):**

```bash
jira board list --project <KEY>
jira sprint list --project <KEY> --current
jira sprint list --project <KEY> --state future,active
```

## Write operations — confirm first, then act

Mutations are cheap to perform but expensive to undo (especially in projects with many watchers). Before any of these, **echo the exact command back to the user and ask "shall I run this?"** unless the user explicitly said "go ahead and X" with the specifics.

**Comment on an issue:**

```bash
jira issue comment add <KEY> "Shipped the dep bumps in PR #1234"
```

**Create an issue:**

```bash
jira issue create --project <KEY> --type Task \
  --summary "Brief actionable summary" \
  --body "Detailed description (markdown ok)" \
  --no-input
```

`--no-input` skips the interactive editor — required when invoking from a non-TTY context like a tool call. Without it, jira-cli will hang waiting for an editor.

**Transition status:**

```bash
jira issue move <KEY> "In Progress"
# or
jira issue move <KEY> "Ready for QA"
```

The target status name must exactly match a valid transition from the current status. If you get an error like "transition not available", run `jira issue view <KEY> --raw | jq '.fields.status'` and ask the user which transition they want; don't guess.

**Assign:**

```bash
jira issue assign <KEY> $(jira me)
jira issue assign <KEY> someone@example.com
jira issue assign <KEY> default        # default assignee
jira issue assign <KEY> x              # unassign
```

**Worklog:**

```bash
jira issue worklog add <KEY> "2h 30m" --comment "Reviewing CVE patches"
```

**Edit fields (description, summary, labels, custom fields):**

```bash
jira issue edit <KEY> --summary "New summary" --label needs-review
jira issue edit <KEY> --custom story-points=3
```

## Workflow: synthesize session work into a ticket update

When the user says any variant of *"update <KEY> with what we did"*, *"log today's work to the ticket"*, *"leave a status note on this issue"*, *"summarize what we shipped on the JIRA"*, or hands you a ticket key after a working session — this is the highest-value workflow this skill exists for. Don't just paste back the user's last message as a comment; the user already knew what they did. The job is to **synthesize the session's actual work into a comment future-you would want to read.**

### What "session context" means

You're (typically) running inside Claude Code with full visibility into the user's working state. Pull from:

- **`git log -n 10 --oneline`** — what commits landed during the session
- **`git diff --stat HEAD~N`** or staged/unstaged diffs — files touched and rough size
- **`gh pr view`** if a PR is open in the working directory's repo — link, title, status
- **The conversation itself** — decisions discussed, alternatives ruled out, things you debugged together
- **Files you edited** — concrete config keys flipped, function signatures changed, deps bumped

A comment written from this synthesis is dramatically more useful than one paraphrased from the user's prompt alone.

### Pattern

1. **Pull session context** before drafting. If you've been working in a repo, run `git log` and `git diff --stat` (no need to ask permission for read-only git). If a PR exists, grab its URL.
2. **Draft a comment** that's concise, factual, past-tense, and mentions concrete artifacts (PR link, commit SHA, file paths, version numbers). Aim for 1–3 short paragraphs. No greetings, no sign-offs, no thanks.
3. **Echo the proposed comment AND the exact command** back to the user, formatted as a block quote followed by the bash. This is the contract — they see the wording before it lands on a ticket their team watches.
4. **Wait for explicit confirmation.** "shall I post?" — and stop. Don't run the write until they say yes/go/post/ship/do it. Editing the wording on request is fine and expected.
5. **Offer adjacent updates as a follow-up** in the same response: *"also want me to (a) log a worklog of Xh, (b) move it to Ready for QA, (c) link the PR via Smart Commits?"* — but as a question, not an assumed next step.

### Comment style guide

| Do | Don't |
|---|---|
| Past tense, declarative ("Bumped electron 28→30, patched 7 CVEs.") | Future/aspirational ("Will work on CVEs.") |
| Concrete artifacts (PR #1234, file paths, commit SHAs, versions) | Vague ("did some work on the deps") |
| Lead with the outcome, then context if needed | Bury the outcome in setup |
| Skip greetings/signoffs — Jira knows who you are | "Hi team," / "Thanks!" / "— Name" |
| Mention follow-ups explicitly if any | Leave them implied |

### Worked example

**User:** *(after a session)* update PROJ-1755 with what we shipped today

**You (good):**

```bash
git log -n 5 --oneline && git diff --stat origin/main...HEAD
# (pulls SHAs and file scope)
gh pr view --json url,title,state -q .url 2>/dev/null
# (grabs PR URL if open)
```

Then:

> Here's what I'd post on PROJ-1755, synthesized from this session:
>
> > Bumped framework 28.3.3 → 30.4.1 and patched 7 high-severity CVEs (axios, ws, formidable, semver, cookie, ip, tar — see `package.json` lockfile). Updated build matrix; macOS arm64 smoke test green. PR: https://github.com/example/repo/pull/1234
>
> ```bash
> source ~/.claude/skills/jira/jira-env.sh && \
>   jira issue comment add PROJ-1755 "Bumped framework 28.3.3 → 30.4.1 and patched 7 high-severity CVEs (axios, ws, formidable, semver, cookie, ip, tar — see package.json lockfile). Updated build matrix; macOS arm64 smoke test green. PR: https://github.com/example/repo/pull/1234"
> ```
>
> Shall I post it? Also: want me to (a) log a worklog with the time, or (b) move the ticket to "Ready for QA" since the PR is up?

**You (bad — just paraphrasing the prompt):**

> ```bash
> jira issue comment add PROJ-1755 "Shipped the dep update work today"
> ```

The bad version wastes the context Claude Code has. The good version captures what actually changed and gives the team something to grep for in three months.

### When the user IS the source of truth

If the user explicitly dictates the comment ("post 'PR coming today' on PROJ-1755"), don't editorialize — use their wording verbatim. Synthesis is for when they ask you to capture *what we did*, not when they're handing you a literal message to send.

## Workflow: open a new ticket for in-flight work

The mirror image of "synthesize → update": the user is mid-work on something that doesn't have a ticket yet, and asks you to create one. Triggers: *"open a ticket for this"*, *"create a jira task for what I'm working on"*, *"there's no ticket yet — can you make one"*, *"file a bug for what we just hit"*. This is a write — same safety posture as comments.

### Decisions you have to make first

1. **Project.** Infer from working directory, conversation, and `defaults.primary_project` in `local-config.yml`. Customer-reported issue → support project. Partner integration repo → integration project. If unclear, ASK — don't guess at a project that has many watchers.

2. **Issue type.** Map the work to one of the project's valid types:
   | Work pattern | Type |
   |---|---|
   | We're fixing broken behavior, regression, crash | `Bug` |
   | We're doing chore / refactor / dep-bump / cleanup / runbook / credential rotation | `Improvement` |
   | Generic engineering work that doesn't fit Bug or Story | `Task` |
   | We're adding a user-visible capability or feature | `Story` (or `New Feature` if the team prefers) |
   | We're researching/spiking/POC | `Task` (with `[spike]` prefix in summary) |
   | We're tracking a multi-issue effort | `Epic` (rare — usually you want a child issue linked to an existing Epic) |
   | We're filing a child of an existing issue | `Sub-task` |

   If genuinely unsure about which type fits, ASK. Default-guessing wrong clutters the wrong reports.

3. **Component.** If `defaults.default_component` is set in `local-config.yml` AND you're filing in the primary project, pass `--component <value>`. To list a project's components:
   ```bash
   curl -sS -u "$ATLASSIAN_EMAIL:$JIRA_API_TOKEN" \
     "https://$ATLASSIAN_SITE/rest/api/3/project/<KEY>/components" | jq '.[].name'
   ```
   Other projects often don't use components — don't force one in.

4. **Parent / epic link.** Many projects organize Stories/Improvements/Bugs under an Epic. If you've been working in a feature branch named like `feat/PROJ-1234-foo`, that issue key is probably the parent epic — use `--parent PROJ-1234`. If you can't tell, omit the flag and the user can add it after.

### Drafting the summary and description

**Summary** — one line, imperative, ≤ 80 chars, no period. Lead with the verb. Include enough specifics that someone scanning a backlog gets it without opening the ticket.

| Good summary | Bad summary |
|---|---|
| "Audio echoes after Bluetooth headset reconnects mid-call" | "Audio bug" |
| "Bump framework 28 → 30 and patch 7 transitive CVEs" | "Update dependencies" |
| "Crash on macOS arm64 when opening Settings while in DND" | "Settings crash" |

**Description** — three short sections, no headers needed unless the description gets long:

1. **Context / what's happening** — the problem in 1-2 sentences, with reproduction steps if it's a bug
2. **Approach** — what you're doing about it (link the PR or branch if one exists)
3. **Status** — where this stands right now (investigating, PR open, blocked on X)

Pull from session context: branch name, PR URL, recent commits, files touched, decisions made together. Same synthesis discipline as the comment workflow.

### The command

```bash
jira issue create --project <KEY> \
  --type Bug \
  --component <component-if-applicable> \
  --summary "Audio echoes after Bluetooth headset reconnects mid-call" \
  --body "On macOS 14+, after disconnecting and reconnecting an AirPods Pro mid-voice-call, the local mic input loops back into the speaker stream causing a 200–400ms echo.

Repro: start a voice call, disconnect AirPods, wait 5s, reconnect.
Affected: macOS 14.4+, framework 28.x.

Approach: investigating whether it's the WebRTC audio pipeline reinitializing or a Chromium-side regression. Branch: bugfix/audio-echo-bt-reconnect.

Status: investigating, no PR yet." \
  --no-input
```

`--no-input` is mandatory for non-TTY invocation. `--label`, `--priority`, `--assignee`, `--parent` are optional — only set when the user specifies (or per `local-config.yml` defaults).

### Pattern in practice

1. Pull session context (`git status`, `git log`, branch name, optionally `gh pr view`).
2. Decide project + type. If ambiguous, **ask before drafting** — a single clarifying question is cheaper than a wrong-shaped ticket.
3. Draft summary + description.
4. Echo the proposed `jira issue create` command back to the user **including** the rendered summary + description as a block quote so they can read what's about to land.
5. Wait for confirmation. Stop.
6. After creation, jira-cli prints the new key. Capture it and offer follow-ups: *"Created PROJ-2117. Want me to (a) assign it to you, (b) link the PR via Smart Commits, (c) add it to the active sprint?"*

### Common slips to avoid

- **Don't assign on create unless the user said so** (or `defaults.default_assignee` is set). Many teams have triage workflows that route unassigned bugs differently. Let the user opt in.
- **Don't set priority unless asked.** Priority is usually a triage/PM call, not the engineer's.
- **Don't include `[BUG]` / `[TASK]` prefixes in the summary.** Jira already shows the type as an icon — the prefix is noise.
- **Don't paste raw stack traces into the summary.** Stack traces go in description with triple-backtick fencing; summary should be human-readable.
- **Match the project's prevailing tone.** A scan of recent tickets via `jira issue list -q "project = <KEY>" --order-by created --reverse --plain --no-headers --columns key,summary | head -20` will show whether the project uses sentence-case, title-case, or terse imperative.

## Cross-project workflows (escalations, linking, references)

A common pattern: a customer-reported issue lives in a support project; the engineering fix lives in a separate ticket linked back to it. The support ticket is the customer-facing record; the engineering ticket carries the technical detail.

### When the user mentions a ticket by URL or key

If the user says *"I'm working on SUPP-1025"* or pastes a Jira URL, **load the ticket context first** before doing anything else. The user may assume you already know what's in it; you don't.

```bash
source ~/.claude/skills/jira/jira-env.sh && jira issue view SUPP-1025
```

If the description renders poorly because of ADF nodes jira-cli doesn't handle (panels, info banners, embedded media), fall back to REST:

```bash
curl -sS -u "$ATLASSIAN_EMAIL:$JIRA_API_TOKEN" \
  "https://$ATLASSIAN_SITE/rest/api/3/issue/SUPP-1025?fields=summary,status,description,issuelinks" | jq .
```

Also scan the **summary text for bare ticket references** like *"PROJ-595 is Done, worked for a while, but now it doesn't work anymore."* — those are informal links the team relies on but Jira doesn't treat as formal `issuelinks`. When you see them, mention the related tickets to the user and offer to view them too.

### Comment voice depends on audience

| Project audience | Voice |
|---|---|
| Customer-facing (support tickets often visible to the customer who filed) | Plain English, no internal jargon, no PR/SHA gunk, customer-progress-oriented ("Confirmed the regression on Windows 11. Working on a fix; expect it in the next release.") |
| Internal engineering | Technical, precise, artifact-heavy (PR, commit, file paths, version numbers) |
| Mixed (PM, eng, occasionally exec) | Outcome-oriented; technical detail in collapsibles or links |

When the user asks you to *"comment on SUPP-1025 with what I'm doing"*, draft for the customer audience even though they framed it as their own work — strip jargon, lead with outcome. When they ask you to comment on the engineering-side fix ticket, use the technical voice.

### Spawning an engineering follow-up linked to a support ticket

The shape:

1. Read the support ticket (above).
2. Create the engineering ticket (use the create workflow above), referencing the support key in the description.
3. Link them formally so the relationship shows up on both tickets.

```bash
# After creating PROJ-2117:
jira issue link SUPP-1025 PROJ-2117 "is caused by"
# or, depending on which direction the team prefers:
jira issue link PROJ-2117 SUPP-1025 "blocks"
```

Available link types vary by Jira config. Common ones: `relates to`, `blocks`, `is blocked by`, `is caused by`, `clones`, `duplicates`. If `jira issue link` errors with "invalid link type", run:

```bash
curl -sS -u "$ATLASSIAN_EMAIL:$JIRA_API_TOKEN" \
  "https://$ATLASSIAN_SITE/rest/api/3/issueLinkType" | jq '.issueLinkTypes[] | .name'
```

to enumerate what's actually configured, and ask the user which direction makes sense.

## Output discipline

| Goal | Flags |
|---|---|
| Show the user a readable list | (defaults — TUI table) |
| Pipe to `head`, `awk`, etc. | `--plain --no-headers` |
| Pick specific columns | `--plain --no-headers --columns key,summary,status,assignee` |
| Get raw JSON for further processing | `--raw` |
| CSV for spreadsheet export | `--csv` |
| Fixed pagination | `--paginate 1:N` (page:size) |

## JQL cookbook

Pass any of these to `jira issue list -q '...'`:

```jql
# My open work, freshest first
# (use --order-by updated --reverse on the command line, not ORDER BY in JQL)
assignee = currentUser() AND resolution = Unresolved

# What I'm doing in the active sprint
assignee = currentUser() AND sprint in openSprints()

# Things I reported that are still open
reporter = currentUser() AND resolution = Unresolved

# Stale stuff — open >30 days, not updated in 14
resolution = Unresolved AND created < -30d AND updated < -14d AND assignee = currentUser()

# Bugs ready to pick up in your primary project
project = <KEY> AND status = "Ready for Dev" AND assignee is EMPTY AND issuetype = Bug

# Customer-driven escalations in a support project
project = <SUPP> AND assignee = currentUser() AND resolution = Unresolved

# Touched by me this week (any project)
assignee was currentUser() AFTER -7d
```

JQL gotchas: use `currentUser()` not your account ID (more portable), use double-quoted strings for status names with spaces (`"Ready for Dev"`), and `was` for historical assignee changes.

**`ORDER BY` in jira-cli:** the JQL `ORDER BY` clause is rejected when passed via `-q` (`Error in the JQL Query: Expecting ',' but got 'ORDER'`). Use the dedicated flags instead:

```bash
jira issue list -q "project = <KEY>" --order-by created --reverse
```

Drop `ORDER BY ...` from the JQL string entirely; pass it as `--order-by <field> [--reverse]` next to the query.

## Pitfalls

- **`jira sprint list` caps at 25 sprints.** Usually fine (you want `--current` or `--state active,future`). For historical sprint analytics, fall back to `/rest/agile/1.0/board/<id>/sprint?startAt=N` directly via curl.
- **Pagination on `issue list`.** `--paginate <page>:<limit>` — `<limit>` is capped at 100 (passing larger errors with `Format <from>:<limit>, where <from> is optional and <limit> must be between 1 and 100`). For "all" loop pages: `--paginate 1:100`, `--paginate 2:100`, etc.
- **Custom fields.** Story points, epic link, etc. are `customfield_*`. They're not in the default columns; you have to add them via `--columns` or use `--raw` and parse JSON.
- **Display names with spaces.** When using `-a` for assignee, prefer the email or `$(jira me)`, not the display name — display name matching is fuzzy and can match the wrong person.
- **`Error: invalid issue types in config`.** Means the config has no `issue.types` block (fresh install or stub). Run `jira init` interactively to populate it. Do not hand-write entries — bad IDs panic the binary.
- **Issue-type names are case-sensitive.** Pass them as `Bug`, `Task`, `Improvement`, `Story`, `New Feature`, `Epic`, `Sub-task` — not lowercase, not pluralised. If `jira issue create` returns `Error: invalid issue type 'X'`, check spelling against the populated config (`grep -A 30 "^issue:" ~/.config/.jira/.config.yml`).
- **`ORDER BY` inside `-q` is rejected** (`Expecting ',' but got 'ORDER'`). Use `--order-by <field> [--reverse]` flags. See JQL cookbook above.
- **REST `/rest/api/3/project/<KEY>` may return 404** (`No project could be found with key '<KEY>'`) when called with the API token. Browse permissions for some projects are not granted to API tokens, only to the logged-in UI session. Don't rely on REST for project metadata or `createmeta` lookups against those projects — fetch type names indirectly via `jira issue list` against existing issues, and let `jira init` populate the config.
- **`git push` after `git checkout -b`** still requires `-u origin <branch>` for the first push of a new branch (no auto-tracking by default). If you see `fatal: The current branch ... has no upstream branch`, retry with `git push -u origin <branch>`.

## When to escape to direct REST

The `jira` CLI covers ~90% of needs. Reach for `curl` against `https://$ATLASSIAN_SITE/rest/api/3/...` when:

- You need fields jira-cli doesn't surface (custom field schemas, workflow definitions, screen configs)
- You need historical sprint data beyond the 25-cap
- You're inspecting raw ADF to debug a rendering issue
- You're doing a bulk operation jira-cli doesn't support

Auth pattern: `curl -u "$ATLASSIAN_EMAIL:$JIRA_API_TOKEN"` — the same email/token combo, basic auth. Both env vars are populated by `~/.claude/skills/jira/jira-env.sh` (token from Keychain, email from `local-config.yml`).

**Permission caveat:** the API token has narrower project access than the logged-in UI. Endpoints like `/rest/api/3/project/<KEY>`, `/rest/api/3/issue/createmeta/<KEY>/issuetypes`, and individual issue fetches against some projects (`/rest/api/3/issue/<KEY>-XXXX`) can return `404 No project could be found` or `errorMessages: ["You are not authorized..."]` even when `jira me` works and `jira issue list -q "project = <KEY>"` returns rows. The CLI uses a different code path that the token is allowed on; raw REST often is not. If REST 404s, fall back to: (a) the CLI for that operation, (b) extracting the data from a CLI-listed sample issue, or (c) asking the user to fetch the resource from the browser.

## What this skill does NOT cover

- Confluence (use REST or a separate skill)
- Bitbucket / GitHub / GitLab (use their respective CLIs)
- Compass
- Atlassian admin operations (user management, billing)
- Setting up jira-cli from scratch — `setup.sh` handles that
