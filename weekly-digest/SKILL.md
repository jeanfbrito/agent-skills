---
name: weekly-digest
description: Drafts a short weekly work digest, translated from commit/ticket language into impact language a manager or teammate can read in 30 seconds. Pulls from real sources only — the project ledger (`.localdev/workflow/done.md`), merged PRs, git history, and optionally Jira — never invents metrics. Triggered by "/weekly-digest", "weekly digest", "draft my weekly update", "what did I ship this week", "status update for the team". Draft-first: never posts anywhere without explicit approval. Personal window state (`last_run`, optional extra project paths, target channel) lives in `local-config.yml` next to this file (gitignored), created on first run.
---

# Weekly Digest

Turn a week of shipped work into a short, honest status update — without
inventing metrics, without burying the outcome in jargon, and without
posting anywhere until the user has read the exact final text.

## Purpose

The goal is visibility: a manager or teammate who has never opened this
codebase should be able to read 3–6 bullets in 30 seconds and know what
shipped and why it matters. Noise — a bullet for every commit, jargon that
requires reading the diff to parse, invented numbers — is the failure mode.
When the week's real output doesn't clear that bar, say so; a thin digest
costs more credibility than skipping it.

## Tone (READ FIRST — applies to EVERY bullet)

**Read the full tone rules before drafting**:
`~/Github/agent-skills/shared/tone.md` (REQUIRED — load it with Read; use
the absolute path, skills are symlink-installed and relative paths break).

Call out inline, since this skill lives or dies on it:

- **Real numbers only.** No invented metrics, no estimated hours, no
  speculated user counts. Any count in a bullet ("7 CVEs patched", "3
  workspaces affected") must trace to git history, the ledger, or a ticket.
- **No self-deprecating or defensive framing.** This is not the place to
  hedge or apologize for scope not covered — frame gaps as scope, per the
  tone doc's Rule 1, or drop the item.
- **Lead every bullet with the outcome.** What changed for someone outside
  the codebase, first; the technical anchor (PR link) comes last, in
  parentheses.

## 1. Determine the window

Default window: the last 7 days.

Check `local-config.yml` next to this file (gitignored — see template
below). If it has a `last_run:` date, use that as the window start instead
of the 7-day default, and tell the user which window you're using ("Digest
covers 2026-08-05 through today, since your last run"). If the file doesn't
exist yet, this is the first run — use the 7-day default and create the
file from the template after the user approves a digest (step 8).

## 2. Gather evidence (real sources only)

Run these from the current project root. Prefer batching them through a
context-mode batch execution (or equivalent) so raw log/PR output stays out
of the conversation — only the filtered results should surface.

**Ledger** — entries in `.localdev/workflow/done.md` since the window
start. Headers are `^## YYYY-MM-DD HH:MM — <title>`; filter by date on that
header, not by scanning free text. If an entry carries an `Impact:` line (or
similar durable-effect note), use it verbatim as the seed for the bullet —
it's already been through one translation pass.

**Merged PRs** — the primary source when a PR exists:

```bash
gh pr list --author "@me" --state merged --search "merged:>=<YYYY-MM-DD>" \
  --json number,title,url,mergedAt
```

**Commits (fallback where no PR exists)** — direct-to-branch work, small
fixes, anything merged without a PR:

```bash
git log --since=<date> --author="$(git config user.name)" --oneline --no-merges
```

**Optional extra repos** — if `local-config.yml` lists `projects:` (absolute
paths), repeat the ledger + git gathering in each one and merge results
before translating.

**Optional Jira** — if the `jira` skill is installed, tickets resolved or
moved to Done this week are fair game for one line. Keep it optional and
brief; this skill's primary evidence is code-shipped, not ticket-moved.

## 3. Translate to impact language

This is the core of the skill — the difference between a changelog and a
digest.

Rules:

- **One bullet per meaningful item, 3–6 bullets total.** Merge related
  PRs/commits (a feature + its follow-up fix) into a single bullet.
- **Outcome first, in words a non-engineer gets.** Technical anchor (PR
  link) in parentheses at the end of the bullet, not the start.
- **Drop items with no audience-visible effect** rather than dressing them
  up with vague language. A refactor with no behavior change doesn't get a
  bullet unless it unblocks something visible — fold it into that bullet's
  context or drop it.

| Raw source                         | Translated bullet                                                                                                                                     |
| ---------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| "Fixed webview boot wedge (#3436)" | "Workspaces no longer hang forever on the loading spinner at startup — closes our largest desktop support-escalation category (#3436)"                |
| "Bumped electron 28→30"            | "Desktop app now ships 7 upstream security fixes (electron 30 upgrade, #1234)"                                                                        |
| "Refactored downloads manager"     | Only include if there's a user- or team-visible effect (faster downloads, fixed progress bar); otherwise fold into another bullet or drop it entirely |

## 4. Compose two drafts

Two versions exist; `local-config.yml`'s `lead:` key decides which one you
compose and present first (`team` if unset). Offer the other one after
presenting the lead version — don't compose both unprompted.

**Team/manager version** — 3–6 impact bullets, one optional "next week"
line. No SHAs, no file paths, no jargon.

**Technical version** — same items, but with PR links and a brief technical
note per bullet, suitable for an engineering channel.

## 5. The empty-week rule

If fewer than 2 items survive translation (step 3), say so plainly and
recommend skipping the digest this week — a thin digest reads as filler and
costs credibility more than silence does. Skipping is a valid, expected
outcome, not a failure of the skill.

If the user still wants something posted despite a thin week, that's their
call — draft it, but don't talk them into padding it with non-outcomes.

Only update `last_run` if the user agrees to "count" the week as covered
(see step 8) — a skipped week they want to fold into next week's window
should NOT advance `last_run`.

## 6. Deliver (draft-first, ALWAYS)

Present both drafts in the conversation for the user to review and copy
into their team channel themselves. If a Rocket.Chat or Slack connector is
available in the session, OFFER to post the approved draft directly — but
NEVER post without the user approving the exact final text first, word for
word. No auto-sending, no "posting now unless you object."

Record nothing anywhere else. The digest itself is ephemeral by design —
`.localdev/workflow/done.md` is already the durable record; this skill only
repackages it for an audience that doesn't read the ledger.

## 7. `local-config.yml` template

Not created by this skill's setup — created on first run, after the first
digest is approved. Gitignored (see repo `.gitignore`).

```yaml
last_run: 2026-08-12 # window start for the next digest
lead: team # which version to compose first: team | technical
projects: # optional extra repos to sweep
  - /Users/jean/Github/Rocket.Chat.Electron
channel: "" # optional: team channel name for the offer-to-post step
```

## 8. After approval

Once the user approves a digest (whether or not it gets posted), update
`last_run:` in `local-config.yml` to today's date. If the file doesn't
exist yet, create it from the template above with `last_run` set to today
and `projects`/`channel` left as empty/example placeholders. Do not update
`last_run` on a digest the user rejected or asked to redo.

## Quality checklist

Before presenting the drafts, verify:

- [ ] Window stated to the user (default 7 days, or `last_run`-derived)
- [ ] Every number in every bullet traces to a source (git, ledger, ticket)
- [ ] Tone rules loaded from `shared/tone.md` and applied — no invented
      metrics, no defensive framing, outcome leads every bullet
- [ ] 6 bullets or fewer in the lead version
- [ ] Empty-week rule honored if fewer than 2 items survived translation
- [ ] Nothing posted anywhere without explicit approval of the exact text
- [ ] `last_run` updated only after the user approved a digest (or agreed to
      count a skipped week as covered)
