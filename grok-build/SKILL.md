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
