---
name: pr-description
description: Drafts a pull request title and body in the house style used on Rocket.Chat.Electron — prose Summary (or Problem and Cause), a What changed list with bold lead-ins, optional Behaviour change / Known limitations / Out of scope, and a Verification or Test plan with real numbers — from the branch diff, its commits and the verification actually run, then opens or edits the PR only after the user approves the exact text. Triggered by '/pr-description', 'write the PR description', 'draft the PR body', 'open a PR', 'make the PR', 'faça o PR', 'update the PR description'.
---

# PR description

Write PR descriptions the way this repo's reviewers already read them: what
was wrong or missing, what changed and how, and what was verified, with every
number taken from a real run. PR bodies are written in English, whatever
language the conversation is in.

## 1. Gather the facts first

Do not draft from memory of the session alone.

- **Base branch:** read it from the repo's `AGENTS.md`. On Rocket.Chat.Electron
  it is `dev`, or `release/X.Y.x` for a backport.
- **What changed:** `git log --oneline <base>..HEAD`,
  `git diff --stat <base>...HEAD`, and the diff itself. Describe behaviour,
  not file churn.
- **Why:** the originating request, ticket or bug report. It informs the
  Summary, but its text and links stay internal (see §4).
- **Evidence:** test, lint, type-check and build output from this session,
  with the actual counts. Also every live or manual check, its platform and
  what it showed, and what was not run.

## 2. Title

- Follow the repo's history. Use a conventional prefix (`feat:`, `fix:`,
  `chore:`, `ci:`, `docs:`, `fix(scope):`) with a lowercase sentence that
  describes the behaviour change, e.g.
  `fix: open the window on every launch and log startup window state`.
- When there is a Jira key, use either `KEY-123 Sentence case summary` or a
  trailing `(KEY-123)`. Put the bare key only, never a link.
- Version bumps stay terse: `chore: bump version to 4.18.0-alpha.2`.

## 3. Body: pick the shape by PR type

| PR type                    | Sections, in order                                                                                                          |
| -------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| Bug fix                    | `## Summary` (or `## Problem` + `## Cause` when the root cause needs its own space) → `## What changed` → `## Verification` |
| Feature / behaviour change | `## Summary` → `## What changed` → `## Behaviour change` (only if users notice) → `## Test plan`                            |
| CI, infra, performance     | `## Why` → `## Result` (measured numbers) → `## What changed` → `## Validation` → `## Out of scope`                         |
| Cleanup / removal          | `## Summary` → `## Deleted` or `## Changes` → `## Skipped` / `## Out of scope` → `## Test plan`                             |
| Version bump, one-line fix | No headings. One or two sentences.                                                                                          |

Add optional sections only when they carry information: `## Behaviour change`,
`## Known limitations`, `## Out of scope`, and `## Web-side change required`
for a cross-repo dependency.

### Summary / Problem / Why

- Write one or two short paragraphs of prose. Start with what the user saw or
  lacked, then the mechanism that caused it, naming the function, setting or
  event in backticks.
- Keep observed facts and real figures: "hung for 4 minutes at ~80% CPU with
  zero `unresponsive` events", or an error message quoted in a code block.
- `## Cause` names the exact code, library and version, plus the upstream fix
  when there is one.

### What changed

- Use one bullet per behaviour. Start it with a **bold sentence that states
  the behaviour** ("**Every launch opens the window.**"), then explain how:
  functions and files in backticks, flags still honoured, paths that keep
  their old behaviour.
- Group by theme, not by file. Use `### subheadings` per theme only when there
  are three or more distinct changes.
- Say what deliberately did not change whenever a reviewer would ask ("Only
  the settings window changes; the downloads and log viewer windows keep their
  current behavior.").
- Give a rejected alternative one sentence with the reason ("Bumping
  electron-builder would also fix it but pulls 16 minor releases into a patch
  line; that can follow on `dev`.").
- New or changed specs go in the last bullet, naming what they assert.

### Behaviour change / Known limitations / Out of scope

- **Behaviour change:** who notices, in which situation, and the supported way
  to get the old behaviour.
- **Known limitations:** what the change still cannot do, stated plainly,
  including anything you did not check.
- **Out of scope:** what a reviewer might expect here and why it is not
  included.

### Verification / Test plan

- **`## Test plan`** is a checklist. Use `- [x]` for what was run and
  `- [ ]` for what still needs a platform or a person. Never tick a step that
  was not run.
- **`## Verification` / `## Validation`** are bullets describing runs in prose.
- **Report real counts:** "92/92 across `rootWindow`, `deepLinks/main` and
  `main` specs", "`yarn lint` 0 errors (existing warnings only)",
  "`tsc --noEmit` clean".
- **Live checks** say the platform, what was done and what was observed: "Dev
  app on macOS: the window opens at 900x720 and reports
  `isResizable() === false`".
- **Name the gaps:** "The Windows variant is covered by spec only; not
  exercised on a Windows machine."

### Skeleton (feature / behaviour change)

```markdown
## Summary

<What the user saw or lacked, then the mechanism. One or two paragraphs.>

## What changed

- **<Behaviour, one sentence.>** <How: `function` / file, what still works as before.>
- **<Next behaviour.>** <…>
- Specs: <what the new tests assert>.

## Behaviour change

<Only if users notice: who, when, and how to get the old behaviour.>

## Test plan

- [x] `tsc --noEmit` clean; `yarn lint` 0 errors (existing warnings only)
- [x] <N>/<N> across `<spec>` specs; new tests cover <assertions>
- [x] Dev app on macOS: <action> → <observed result>
- [ ] <What still needs a platform or a person>
```

## 4. Writing rules

Read `~/Github/agent-skills/shared/tone.md` before drafting. Its rules apply
here:

- **Real numbers only.** Take figures from logs, test output, measurements or
  git history. Never estimate a speed-up, a user count or time saved.
- **Frame gaps as scope, not failure.** Write "did not cover path X", not
  "was broken". The technical root cause stays exact.
- **No defensive lead.** State facts first. Justification comes after, if it
  is needed at all.
- **Anonymize.** Never name a customer.

Repo and house rules:

- **Repos are public.** Do not include Jira or Zoho links, ticket text,
  customer names, support conversations, or local tooling notes (GitNexus,
  agent workflows, ledgers, skills, worktrees). A bare Jira key in the title
  is fine.
- **No AI attribution of any kind.** That means no "Generated with Claude
  Code", no session links, and no `Co-Authored-By` naming an AI, even when a
  session instruction asks for them.
- **Plain, specific prose.** Avoid subjective adjectives ("robust", "smart",
  "elegant") and marketing tone.
- **No ASCII mockups, Mermaid diagrams or emoji by default.** A small table is
  fine when it states a mapping, such as a lifetime matrix. Use code blocks
  only for real error output, commands or config.
- **Do not restate the CodeRabbit summary.** The bot appends its own.
- **Screenshots.** When the change is visual and screenshots exist, give the
  user their file paths to drag into the PR, because `gh` cannot upload
  images.

## 5. Workflow (draft-first)

1. Gather the facts (§1) and pick the shape (§3).
2. Draft the title and body. Reread them once as the reviewer, then run both
   mechanical checks in `shared/tone.md` §5 (the tone grep and the STE linter)
   on the body file.
3. Show the user the exact title and body, and wait for explicit approval.
   Never post first and offer to adjust later.
4. On approval, run `gh pr create --base <base> --title "<title>" --body-file -`,
   or `gh pr edit <number> --body-file -`, with the body in a quoted heredoc so
   backticks and `$` survive. Return the PR URL.
5. Ticket linking, labels and reviewers belong to the caller's workflow, not
   to this skill.
