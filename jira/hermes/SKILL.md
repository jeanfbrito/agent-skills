---
name: jira
description: Drive your Atlassian Jira workspace from the terminal via `jira` CLI (ankitpokhrel/jira-cli). Use this skill ANY time the user asks about Jira tickets, issues, sprints, JQL, boards, story points, worklogs, or names a project key from your org — even if they don't say the word "Jira". Also for vague work-status questions ("what's on my plate", "current sprint", "ready for dev queue"). Skip only when clearly about Confluence, GitHub, or Slack. Personal defaults live in `local-config.yml` next to this file (gitignored), populated by `setup.sh`.
category: atlassian
---

# Atlassian Jira workflow (jira-cli)

Hermes-adapted version. Original: `~/.claude/skills/jira/` (Claude Code). This copy lives at `~/.hermes-icarus/skills/atlassian/jira/` and is Linux-compatible (no macOS Keychain, no Homebrew).

User-specific config — Atlassian site, email, primary project, default component, default assignee — lives in `local-config.yml` next to this file. Run `setup.sh` once to populate it. Read defaults from `local-config.yml` whenever this document references "your primary project" / "your default component" etc.

## Preconditions — verify before running commands

Before the first `jira` invocation in a session, verify the binary exists:

```bash
command -v jira >/dev/null 2>&1 || echo "MISSING"
```

If it prints `MISSING`, do not improvise. Run the setup script:

> jira-cli isn't installed. Run `~/.hermes-icarus/skills/atlassian/jira/setup.sh` to install it, configure, and generate `local-config.yml`. Then we can continue.

Also verify the config has an `issue.types` block before any write attempt:

```bash
grep -qE "^[[:space:]]+types:" ~/.config/.jira/.config.yml || echo "CONFIG_INCOMPLETE"
```

If it prints `CONFIG_INCOMPLETE`, the jira-cli config doesn't have project metadata yet. Run the setup script again (idempotent).

Do **not** hand-write the `issue.types` block yourself (see "Error: invalid issue types" below).

## Authentication — loading the token

`jira-cli` reads the API token from the `JIRA_API_TOKEN` env var. The Hermes version reads it from `local-config.yml` (not macOS Keychain). The helper script `jira-env.sh` exports it for you.

The right pattern in shell calls:

```bash
source ~/.hermes-icarus/skills/atlassian/jira/jira-env.sh && jira me
```

If `jira me` returns a 401, the token is stale. Tell the user to mint a fresh one at https://id.atlassian.com/manage-profile/security/api-tokens and rerun `setup.sh`.

### `Error: invalid issue types in config`

`jira issue create` requires an `issue.types` block in `~/.config/.jira/.config.yml`. If missing, run `jira init` interactively or fetch real type IDs via REST:

```yaml
issue:
  types:
    - id: "10001"
      name: Bug
      handle: Bug
      subtask: false
```

The `subtask: false` field is mandatory; omitting it triggers a panic.

## Project conventions — what the keys mean

Discover projects on first use:

```bash
jira project list --plain --no-headers --columns key,name | head -20
```

### Your primary project (read from `local-config.yml`)

`defaults.primary_project` — the project you spend most time in.

**Valid issue types** vary per project. Common ones: Bug, Task, Improvement, Story, New Feature, Epic, Sub-task.

**Statuses** vary per project workflow. Classic chain: `To Do` → `In Progress` → `Done`. To enumerate transitions:

```bash
jira issue view <KEY> --raw | jq '.fields.status'
```

## Default sprint context

If your project uses Scrum, re-discover at runtime:

```bash
jira sprint list --project <KEY> --current --plain --no-headers
```

## Read operations — preferred forms

**"What am I working on" / "open tickets":**
```bash
jira issue list -q "assignee = currentUser() AND resolution = Unresolved" --order-by updated --reverse
```

**Current sprint:**
```bash
jira issue list -q "assignee = currentUser() AND sprint in openSprints()"
```

**View a single issue:**
```bash
jira issue view <KEY>
```

**JQL search:**
```bash
jira issue list -q "project = <KEY> AND status = 'Ready for Dev'" --plain --no-headers --columns key,summary
```

## Write operations — confirm first, then act

**Always echo the exact command back to the user and ask "shall I run this?"** unless the user explicitly said "go ahead" with specifics.

**Comment:**
```bash
jira issue comment add <KEY> "Your comment here"
```

**Create issue:**
```bash
jira issue create --project <KEY> --type Task --summary "Brief summary" --body "Description" --no-input
```

`--no-input` is mandatory (non-TTY context).

**Transition:**
```bash
jira issue move <KEY> "In Progress"
```

**Assign:**
```bash
jira issue assign <KEY> $(jira me)
```

**Worklog:**
```bash
jira issue worklog add <KEY> "2h 30m" --comment "Reviewing CVE patches"
```

**Edit:**
```bash
jira issue edit <KEY> --summary "New summary" --label needs-review
```

## Workflow: synthesize session work into a ticket update

When the user says *"update <KEY> with what we did"*, *"log today's work"*, *"summarize what we shipped"*, or hands you a ticket key after a working session — synthesize the session into a comment.

### What "session context" means

Pull from the working environment:
- **`git log -n 10 --oneline`** — commits during the session
- **`git diff --stat HEAD~N`** — files touched
- **`gh pr view`** if a PR is open in the CWD
- **The conversation itself** — decisions discussed
- **Files edited** — config keys flipped, function signatures changed

### Pattern

1. Pull session context (read-only git ops, no need to ask)
2. Draft a concise, factual, past-tense comment with concrete artifacts (PR link, SHA, file paths, versions). 1-3 paragraphs, no greetings/signoffs
3. Echo the proposed comment AND the command back to the user
4. Wait for explicit confirmation before posting

### Output discipline

| Goal | Flags |
|---|---|
| Readable list | (default — TUI table) |
| Pipe/parse | `--plain --no-headers` |
| Specific columns | `--plain --no-headers --columns key,summary,status` |
| Raw JSON | `--raw` |
| CSV export | `--csv` |
| Fixed pagination | `--paginate 1:N` |

## JQL cookbook

```jql
# My open work
assignee = currentUser() AND resolution = Unresolved

# Active sprint
assignee = currentUser() AND sprint in openSprints()

# Reported by me, still open
reporter = currentUser() AND resolution = Unresolved

# Stale — open >30d, not updated in 14d
resolution = Unresolved AND created < -30d AND updated < -14d AND assignee = currentUser()

# Ready for Dev in primary project
project = <KEY> AND status = "Ready for Dev" AND assignee is EMPTY AND issuetype = Bug

# Touched by me this week
assignee was currentUser() AFTER -7d
```

**`ORDER BY` in jira-cli:** rejected inside `-q`. Use `--order-by <field> [--reverse]` flags:
```bash
jira issue list -q "project = <KEY>" --order-by created --reverse
```

## Cross-project workflows (escalations, linking)

### When the user mentions a ticket by URL or key

Load it first before doing anything else:
```bash
source ~/.hermes-icarus/skills/atlassian/jira/jira-env.sh && jira issue view SUPP-1025
```

Fall back to REST for ADF nodes jira-cli doesn't render:
```bash
curl -sS -u "$ATLASSIAN_EMAIL:$JIRA_API_TOKEN" \
  "https://$ATLASSIAN_SITE/rest/api/3/issue/SUPP-1025?fields=summary,status,description,issuelinks" | jq .
```

### Comment voice by audience

| Audience | Voice |
|---|---|
| Customer-facing (support tickets) | Plain English, no internal jargon, customer-progress-oriented |
| Internal engineering | Technical, precise, artifact-heavy (PR, commit, file paths) |
| Mixed (PM, eng, exec) | Outcome-oriented; detail in links |

### Linking tickets

```bash
jira issue link SUPP-1025 PROJ-2117 "is caused by"
jira issue link PROJ-2117 SUPP-1025 "blocks"
```

Enumerate available link types:
```bash
curl -sS -u "$ATLASSIAN_EMAIL:$JIRA_API_TOKEN" \
  "https://$ATLASSIAN_SITE/rest/api/3/issueLinkType" | jq '.issueLinkTypes[] | .name'
```

## Cross-project workflows: creating a ticket for in-flight work

When the user says *"open a ticket for this"*, *"create a jira task"*, *"file a bug"*:

### Decisions first

1. **Project.** Infer from CWD, conversation, `defaults.primary_project`. Customer issue → support project. If unclear, ASK.
2. **Issue type.** Map the work:
   | Work pattern | Type |
   |---|---|
   | Broken behavior, regression, crash | `Bug` |
   | Chore / refactor / dep-bump / cleanup / credential rotation | `Improvement` |
   | Generic engineering work | `Task` |
   | User-visible feature | `Story` (or `New Feature`) |
   | Research/spike/POC | `Task` (prefix `[spike]` in summary) |
   | Multi-issue effort | `Epic` (or child of existing Epic) |
   | Child of another issue | `Sub-task` |
3. **Component.** If `defaults.default_component` is set AND primary project, pass `--component <value>`.
4. **Parent / epic link.** Infer from branch name like `feat/PROJ-1234-foo`.

### Drafting

**Summary** — ≤80 chars, imperative, no period, verb-leading.

| Good | Bad |
|---|---|
| "Audio echoes after Bluetooth headset reconnects mid-call" | "Audio bug" |
| "Bump framework 28→30 and patch 7 transitive CVEs" | "Update dependencies" |

**Description** — context/what's happening, approach, status.

Pull from session context: branch name, PR URL, recent commits, files touched.

### The command

```bash
jira issue create --project <KEY> \
  --type Bug \
  --summary "Brief actionable summary" \
  --body "Description here" \
  --no-input
```

`--no-input` is mandatory.

### Pattern

1. Pull session context (read-only git/gh ops)
2. Decide project + type. If ambiguous, ASK
3. Draft summary + description
4. Echo the command including rendered text
5. Wait for confirmation. Stop.
6. After creation, offer follow-ups: assign, link PR, add to sprint

### Common slips

- **Don't assign on create** unless `defaults.default_assignee` is set
- **Don't set priority** — that's triage/PM
- **No `[BUG]`/`[TASK]` prefixes** — Jira shows the type icon
- **No raw stack traces in summary** — put them in description with ``` fencing

## When to escape to direct REST

Use `curl` against `https://$ATLASSIAN_SITE/rest/api/3/...` when:
- You need fields jira-cli doesn't surface (custom field schemas, workflow definitions)
- Historical sprint data (beyond 25-sprint cap)
- Raw ADF to debug rendering
- Bulk operations jira-cli doesn't support

Auth: `curl -u "$ATLASSIAN_EMAIL:$JIRA_API_TOKEN"` — both from `local-config.yml`.

**Permission caveat:** API tokens have narrower access than the UI. REST may return 404 for some projects. Fall back to CLI or ask the user.

## Pitfalls

- **`jira sprint list` caps at 25 sprints** — use REST for historical data
- **Pagination limit 100** — `--paginate <page>:<limit>`, limit max 100
- **Custom fields** are `customfield_*` — not in default columns
- **Display names with spaces** — use email or `$(jira me)`, not display name
- **`Error: invalid issue types in config`** — run `jira init` interactively
- **Issue-type names are case-sensitive** — Bug, Task, Improvement, etc.
- **`ORDER BY` inside `-q` is rejected** — use `--order-by` flag
- **REST `/rest/api/3/project/<KEY>` may return 404** — token permissions limited
- **Hermes-specific: no macOS Keychain** — token stored in `local-config.yml`. Setup script handles this.
- **Hermes-specific: no Homebrew** — jira-cli installed via direct binary download (Linux). Setup script handles this.
