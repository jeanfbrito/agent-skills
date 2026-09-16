---
name: grok-build
description: Delegate coding tasks to xAI's Grok CLI (Grok Build, binary `grok`) running headless. Use when the user says "use grok", "ask grok", "grok build", "grok this", "delegate to grok", wants a second implementation or opinion from Grok, or wants a task run by Grok in parallel/isolation (worktree). Not for questions about xAI's API — this drives the local CLI agent.
---

# Grok Build — headless coding delegation

Drive the local `grok` CLI (Grok Build, xAI's coding agent) non-interactively to implement, review, or diagnose code. Verified against `grok 0.2.118` (2026-08-06, including a live headless run + session resume); the CLI updates often — re-check `grok --help` if any flag errors.

## Preflight (every session, once)

```bash
which grok && grok --version
grok models     # auth check — prints "You are logged in with grok.com." + model list when authenticated
```

- Not authenticated → tell the user to run `! grok login` themselves (interactive browser flow) or `! grok login --device-auth` (device-code flow for headless/remote), or export `XAI_API_KEY`. Do NOT attempt `grok login` from a non-interactive shell.
- Default model: `grok-4.5` (currently the only model on this account). Override with `-m <model>`.
- `grok doctor` diagnoses terminal/env problems; `grok inspect` shows the config Grok discovers for a directory (rules files, MCP, plugins).

## Core invocation — one-shot headless

```bash
grok -p "<task prompt>" --cwd <project-dir> --output-format json --always-approve
```

- `-p/--single` = single-turn headless: runs the agent with full tool access, prints result to stdout, exits. This is the ONLY mode to use from Claude Code — never launch bare `grok` (interactive TUI, will hang the shell).
- `--output-format json` → parse with `jq -r '.text'`. Result object fields (verified): `text`, `thought`, `num_turns`, `sessionId` (reusable with `-r`), `stopReason`, `requestId`, `total_cost_usd`, `usage`, `modelUsage`.
- `--always-approve` auto-approves Grok's tool executions (file edits, commands). Required for unattended edit tasks; omit for read-only analysis prompts so Grok can't mutate anything it wasn't asked to. Finer control: `--permission-mode <default|acceptEdits|auto|dontAsk|bypassPermissions|plan>`, `--allow <RULE>` / `--deny <RULE>`.
- `--prompt-file <path>` when the prompt is long — write it to the scratchpad first, avoids shell-quoting pain. `--verbatim` sends the prompt exactly as given.
- `--max-turns <N>` to bound runaway tasks (good default: 30).

## Run it backgrounded — always

Grok tasks take minutes. NEVER run in foreground Bash (the smoke-test-sized prompts above are the only exception):

- Preferred: `Bash` with `run_in_background: true`, stdout redirected to a scratchpad file:
  ```bash
  grok --prompt-file /path/to/prompt.md --cwd "$PWD" --output-format json --always-approve \
    > /path/to/scratchpad/grok-result.json 2> /path/to/scratchpad/grok-stderr.log
  ```
- Or dispatch a `watcher` agent to run it and return a digest (per AGENTIC.md rule 4b).
- **A subagent driving the CLI must run it in the FOREGROUND** (`run_in_background: false`, generous Bash `timeout`). Backgrounding only works for the main session, which can receive the completion notification. A subagent that backgrounds the run ends its turn immediately and reports something like "the job is running, I'll verify when it completes" — but the notification is delivered to the *parent*, so the subagent is never resumed and its verification never happens. Observed three times in one session. If the foreground call times out, resume in the foreground with `-r <sessionId>` rather than switching to background.
- Liveness check on a long run: use `--output-format streaming-json` (NDJSON of session updates; `streaming-messages-json` for Anthropic wire format, `--include-partial-messages` for deltas) and `tail` the log — a growing file means it's working.
- On completion, read only the parsed `.text` (and the git diff) — not the raw log.

## Task patterns

### Implement a scoped change
```bash
grok -p "Fix <bug>: <symptoms>. Constraints: <contracts>. Run <scoped tests> to verify." \
  --cwd <repo> --always-approve --output-format json --max-turns 40
```
Then verify yourself: `git diff --stat`, run the project's scoped tests. Grok's claim of success is not verification.

### Second opinion / review (read-only)
```bash
grok -p "Review the uncommitted diff for bugs and risky changes. Do not modify anything." \
  --cwd <repo> --output-format json --deny "Edit" --deny "Write"
```
Omit `--always-approve`; add `--deny` rules so it stays read-only. `--no-memory` makes it a clean-room opinion (Grok has cross-session memory that could bias re-reviews).

### Risky/parallel work → worktree isolation
```bash
grok -w grok-attempt -p "<task>" --always-approve --output-format json
```
`-w/--worktree [name]` runs in a fresh git worktree off HEAD (`--worktree-ref <ref>` to base elsewhere). Inspect with `grok worktree` / plain git; merge only what survives review.

### Multi-step scripted session
```bash
SID=$(grok -p "Step 1: analyze X. Report findings, change nothing." --cwd <repo> --output-format json | jq -r '.sessionId')
grok -p "Step 2: now implement what you proposed." -r "$SID" --always-approve --output-format json
```
Continuation is via `-r/--resume <sessionId|title>` (or `-c` for the most recent session in the cwd). **`-s/--session-id` no longer resumes** — since ~0.2.11x it only names a NEW session and must be an unused UUID; passing a prior id errors. `--fork-session` branches a resumed session instead of extending it; `--restore-code` checks out the original session's commit when resuming.

### Hard problems
- `--reasoning-effort <effort>` (alias `--effort`) — crank for strategy-grade tasks.
- `--best-of-n` and `--check` were REMOVED from the CLI (gone by 0.2.118) — don't use them; run parallel worktree attempts (`-w a1`, `-w a2`) yourself if you want best-of-N.

### Structured output
```bash
grok -p "<extraction task>" --json-schema '{"type":"object","properties":{...}}'
```
Constrains the model to schema-valid JSON (implies `--output-format json`).

## Prompt-writing rules for Grok

- Grok reads project rules files (`AGENTS.md`, `CLAUDE.md`, `AGENT.md`) from the cwd and appends them to its system prompt — do not paste CLAUDE.md content into the prompt; it's already there. Confirm what it sees with `grok inspect`.
- Write the brief like a builder-agent brief: task, constraints/contracts, files in scope, verification command, definition of done.
- `--rules "<extra>"` appends ad-hoc rules to its system prompt without editing files; `--system-prompt-override` replaces it entirely (rarely wanted).
- `--disable-web-search` when the task must stay offline; `--no-subagents` to keep it single-agent and cheaper; `--no-plan` to skip plan mode on small tasks.

## Invariants must be mechanical, not prompt text

`--rules`, `--system-prompt-override` and brief text are *requests*. Anything you would be unhappy to discover afterwards needs an enforcement mechanism the agent cannot talk its way past.

Worked example: a project whose orchestrator owns the task ledger told Grok, in `--rules` and again in the brief, never to write `.localdev/workflow/*.md`. It did anyway, twice, in separate runs — each time writing an accurate entry, which is precisely why prose failed to stop it: the action looked helpful. The fix that worked was three lines in the wrapper:

```bash
LEDGER=(todo.md done.md blockers.md findings.md)   # resolve to real paths first
trap 'chmod u+w "${LEDGER[@]}" 2>/dev/null' EXIT INT TERM
chmod a-w "${LEDGER[@]}"
"${CMD[@]}" > result.json 2> stderr.log
chmod u+w "${LEDGER[@]}"
```

Generalise it:

- **Files that must not change** → make them read-only for the duration of the run and restore on any exit (`trap ... EXIT INT TERM`, so a kill or a timeout still restores them).
- **Calls that must not appear** → a grep-based check in the repo's own test suite, whitelisting by *enclosing function name* rather than line number so it survives edits, failing non-zero on any hit. Keep it in the suite the DoD already runs.
- **Paths that must not be touched** → `--deny` rules plus worktree isolation (`-w`), not a sentence in the brief.
- **Numbers that must not move** → record them before the run and diff after; "behaviour-neutral" is a claim to verify, not to accept.

Corollary for briefs: state the invariant anyway (it helps Grok cooperate), but never let it be the *only* thing standing between the run and an outcome you cannot undo.

## After Grok finishes

1. Parse result: `jq -r '.text' grok-result.json` (`.thought` holds its reasoning summary; `.total_cost_usd` for cost reporting).
2. Inspect actual changes: `git status` + `git diff` (or worktree diff).
3. Run the project's own verification (scoped tests, typecheck) yourself — treat Grok as a builder whose work gets reviewed, same bar as any subagent.
4. Synthesize for the user: what Grok changed, whether it verified, your own verdict. Never paste raw Grok output.
5. Useful forensics: `grok sessions list`, `grok sessions search <kw>`, `grok export <session>` (Markdown transcript).

## Gotchas

- Bare `grok` or missing `-p` → interactive TUI, hangs a non-TTY shell. Always `-p` (or `--prompt-file`).
- `-s <old-session-id>` errors ("must not already exist") — resume is `-r`, not `-s`. See multi-step pattern.
- `--always-approve` gives Grok unrestricted tool execution in that cwd — for untrusted/experimental tasks prefer worktree isolation (`-w`) and/or `--sandbox <profile>` / `--permission-mode acceptEdits`, and scope `--deny` rules or `--disallowed-tools`.
- Auth errors surface on stderr; keep stderr captured to a separate log file.
- Exit code isn't a task-success signal — verify via diff + tests, not `$?` alone.
- Grok now keeps cross-session memory; use `--no-memory` when you need an unbiased fresh run.
- `grok agent stdio|serve` exists for SDK/IDE integrations — not needed for this workflow.
