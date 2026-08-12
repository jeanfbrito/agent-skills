---
name: postmortem
description: Write a post-mortem and extract durable lessons after completing a challenging task, then publish it for visibility (internal write-up, team-channel summary, optional blog draft). Use when the user says "/postmortem", "document what we learned", "write a post-mortem", "extract lessons", or after any task that involved debugging, failed attempts, or non-obvious solutions. Turns hard-won experience into persistent rules and visible artifacts.
---

# Post-Mortem & Knowledge Extraction

After a challenging task — especially one with failed attempts, debugging
rabbit holes, or non-obvious solutions — run this skill to crystallize the
experience into durable project knowledge, and to publish it where people
actually see it.

## Framing (READ FIRST — applies to EVERY section)

Post-mortems are outward-facing artifacts: enterprise customers, account
managers, auditors, and future-you writing a PR description all read them.
Negative framing damages trust even when technically accurate.

**Read the full tone rules before drafting**:
`~/Github/agent-skills/shared/tone.md` (REQUIRED — load it with Read).

Minimum summary if that file is unavailable: frame untested paths as scope
extension, not regression ("did not cover path X", never "shipped broken");
keep technical root-cause analysis exact and unsoftened; never name the
customer; real numbers only; grep the draft for
`broken|regression|silently non-functional|never worked|failed in production|was a bug|shipped broken`
and review every hit.

## Workflow

### 1. Reconstruct the timeline

Don't rely on memory — gather the actual evidence:

- The conversation history: real code changes, error messages, screenshots.
- The project ledger if present: `.localdev/workflow/done.md` entries,
  handoffs in `.localdev/workflow/handoffs/`, `findings.md`.
- Git history of the arc: `git log` on the branch, PR discussion via `gh`.
- Any forensic artifacts the task produced (watchdog reports, log captures).

Then identify:

- **What was the goal?** (1 sentence)
- **What approaches were tried?** List each attempt chronologically.
- **What failed and WHY?** Root cause per attempt — not the symptom.
- **What finally worked and WHY?** The key insight that made the difference.
- **What was the cost of each wrong path?** (only real, observable costs)

### 2. Write the post-mortem document

Create `docs/postmortem-<topic>.md` in the project root:

```markdown
# Post-Mortem: <Topic>

## Objective

What we were trying to achieve (1-2 sentences).

## Impact

Who noticed and what changed for them — users, support, other teams.
Observable effects only (ticket categories closed, behavior fixed,
platform paths now covered). Skip if genuinely internal-only.

## Timeline

### Attempt N: <Name> (failed/succeeded)

**What was done:** Concrete description of the approach.
**What went wrong:** Specific technical explanation of the failure.
**Root cause:** The underlying reason, not just the symptom.

### Attempt N+1: ...

(repeat for each attempt)

## Lessons Learned

### 1. <Lesson title>

Explain the lesson with enough context that a future reader can understand
it without reading the full timeline. Include the specific mistake and the
correct approach.

(repeat for each lesson)

## What this does NOT fix

Clarify any misconceptions about what the solution achieves. If the original
problem description was partially wrong, say so here.
```

### 3. Extract rules for AGENTS.md

Read the project's `AGENTS.md` (or `CLAUDE.md` if that's the canonical file)
and place new knowledge where it belongs:

- **Hard-won warnings** — lessons that, if ignored, waste hours. Put them in
  the project's critical/first-read section if it has one, otherwise the most
  relevant existing section.
- **Architecture knowledge** — file roles, system behavior, invariants
  discovered during debugging.
- **Debugging guidance** — if the task revealed a new class of bugs.

**Rules for writing rules:**

- State the rule as an imperative ("Do X", "Do NOT do Y").
- Include the WHY — what goes wrong if the rule is violated.
- Include a concrete example if possible.
- Reference the post-mortem doc for the full story.

### 4. Create/update auto-memory

In the session's auto-memory directory (`~/.claude/projects/<project>/memory/`),
write one file per durable fact, using the current format — YAML frontmatter
with `name` (kebab-case slug), `description` (one line), and
`metadata.type` (`feedback` for corrections/guidance, `project` for ongoing
context, `reference` for pointers). For feedback entries include **Why:** and
**How to apply:** lines. Then add a one-line pointer in `MEMORY.md`.

Also check for outdated memories: if the task invalidated previous
assumptions, update or delete the stale entries.

### 5. Capture cross-project lessons

For lessons that apply ACROSS projects (porting mistakes, verification
failures, debugging anti-patterns, architectural insights):

- If the mastermind MCP is available, capture with `mm_write` (war-story or
  lesson type).
- Otherwise, use the `/learn` skill to write project + global `lessons.md`.

Only truly general lessons go here — project-specific knowledge stays in
AGENTS.md and auto-memory.

### 6. Close the ledger

If the project uses the agentic workflow ledger, append the completion entry
to `.localdev/workflow/done.md` (canonical `## YYYY-MM-DD HH:MM — <title>`
format) with a link to the post-mortem doc, and absorb + delete any handoff
for the task.

### 7. Publish for visibility (draft-first, ALWAYS)

A post-mortem that dies in `docs/` is invisible. Turn it into artifacts
people see — but NEVER send or publish anything without the user approving
the exact draft first:

- **Internal write-up**: offer to create a Confluence page from the
  post-mortem (Atlassian MCP, `createConfluencePage`). Ask which space, or
  reuse the space from a previous run. Link it from the done.md entry.
- **Team-channel summary**: draft a 5–10 line post for the team channel —
  what happened, impact, one key lesson, link to the full doc. Run it through
  the tone rules; hand the draft to the user to send.
- **Public blog** (optional): if the story generalizes beyond the company,
  offer a handoff to the `blog-post` skill, which strips private/proprietary
  content and drafts for the personal blog.

If the user declines all three, that's fine — record the decision and stop.

## Quality checklist

Before finishing, verify:

- [ ] Post-mortem covers ALL attempts, not just the successful one
- [ ] Each failed attempt has a specific root cause, not just "it didn't work"
- [ ] Impact section states observable effects only (or was consciously skipped)
- [ ] Rules in AGENTS.md are actionable imperatives, not vague advice
- [ ] Memory files use the frontmatter format and are linked from MEMORY.md
- [ ] Cross-project lessons captured (mastermind or /learn) — general ones only
- [ ] done.md entry appended (if the project uses the ledger)
- [ ] Tone check passed per `shared/tone.md`: grep ran, every hit reviewed,
      no customer names, no external tracker IDs, no invented numbers
- [ ] Distribution drafts offered; nothing was sent without explicit approval

## Anti-patterns to avoid

- **Vague lessons**: "Be more careful" is not a lesson. "Always A/B test
  against baseline before declaring success" is.
- **Symptom-level explanations**: "The rendering was broken" is a symptom.
  "CheckBoundingBox is a partial order that produces wrong results in
  pairwise comparison sorts" is a root cause.
- **Missing the WHY**: Every rule needs a WHY. "Do NOT use pairwise
  comparison" — why? Because CheckBoundingBox returns true in both directions
  for edge/surface pairs, causing the sort to leave them in arbitrary order.
- **Skipping failed attempts**: The failures are the most valuable part.
  Future readers (including future Claude sessions) need to know what NOT to
  do and why.
- **Publishing internals externally**: the blog handoff strips proprietary
  detail; never paste the internal doc into a public artifact as-is.
- **Auto-sending**: distribution is draft → user approves → user (or approved
  tool call) sends. No exceptions.
