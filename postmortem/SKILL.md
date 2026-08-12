---
name: postmortem
description: Write a post-mortem and extract durable lessons after completing a challenging task. Use when the user says "/postmortem", "document what we learned", "write a post-mortem", "extract lessons", or after any task that involved debugging, failed attempts, or non-obvious solutions. This skill turns hard-won experience into persistent rules that prevent repeating the same mistakes.
---

# Post-Mortem & Knowledge Extraction

After a challenging task — especially one with failed attempts, debugging rabbit holes, or non-obvious solutions — run this skill to crystallize the experience into durable project knowledge and personal engineering rules.

## Framing (READ FIRST — applies to EVERY section of the postmortem)

Postmortems are customer-facing artifacts. They get read by enterprise customers, account managers, auditors, and future-you writing a PR description from this doc. Negative framing damages trust even when technically accurate.

**Rule**: If a feature shipped and worked in the context it was tested in but didn't cover a deployment/usage path that wasn't validated pre-ship, frame it as scope extension — not regression.

| Do NOT write | Write instead |
|---|---|
| "was broken" / "broke in production" | "did not cover path X" |
| "silently non-functional" | "silent under context Y — no observable side-effect assertion" |
| "regression" | "gap exposed by enterprise validation" |
| "failed in every real deployment" | "worked for interactive installs; SCCM/SYSTEM path required additional hardening" |
| "the feature never worked" | "the feature worked in the tested context; coverage was extended to context X" |
| "was silently no-op" | "silent under SYSTEM context; observable-assert gap" |

**Technical root-cause analysis stays unchanged.** The rule is about narrative, not substance. If there was a CustomActionData plumbing bug, describe the plumbing bug exactly as it was — just don't wrap it in "we shipped a broken feature" language.

**Honest but forward-looking**: it is OK (and correct) to say "we did not validate against the SYSTEM-context path before shipping" once, in the Context or Objective section. That's honest scoping, not self-flagellation. Don't repeat that framing in every section.

**Remove customer identity**: never name the customer. "An enterprise customer deploying via SCCM" / "a field report from a managed-desktop environment". Internal ticket IDs (PROD-595) OK; external customer tracker IDs NOT OK.

**Before finishing**, grep the draft for: `broken|regression|silently non-functional|never worked|failed in production|was a bug|shipped broken`. Each hit needs review.

## Workflow

### 1. Reconstruct the timeline

Review the conversation history to identify:

- **What was the goal?** (1 sentence)
- **What approaches were tried?** List each attempt chronologically
- **What failed and WHY?** For each failed attempt, identify the root cause — not the symptom
- **What finally worked and WHY?** What was the key insight that made the difference?
- **What was the time cost of each wrong path?**

Don't rely on memory — scroll back through the conversation and read the actual code changes, error messages, and screenshots that happened.

### 2. Write the post-mortem document

Create `docs/postmortem-<topic>.md` in the project root with this structure:

```markdown
# Post-Mortem: <Topic>

## Objective
What we were trying to achieve (1-2 sentences).

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

Read the current `AGENTS.md` and identify where new rules should go:

- **New CRITICAL rules** (go in the `⚠️ CRITICAL` section): Only for lessons that, if ignored, will waste hours. These are the "read this first" items.
- **New architecture knowledge** (go in relevant sections): File roles, system behavior, invariants discovered during debugging.
- **Updated feature status**: Mark features as done/changed if the task affected them.
- **New debugging guidance**: If the task revealed a new class of bugs, add to the debugging section.

**Rules for writing rules:**
- State the rule as an imperative ("Do X", "Do NOT do Y")
- Include the WHY — what goes wrong if the rule is violated
- Include a concrete example if possible
- Reference the post-mortem doc for the full story

### 4. Create/update memory files

Check the auto-memory directory (`/Users/jean/.claude/projects/<project>/memory/`):

- **New feedback rule**: Create `feedback_<topic>.md` with:
  - The rule (1-2 sentences)
  - What happened when it was violated
  - The correct approach
  - Related files
- **Update MEMORY.md**: Add a link to the new feedback file
- **Check for outdated memories**: If the task invalidated previous assumptions, update or remove stale memory entries

### 5. Update global lessons

Check `~/.claude/lessons.md` for engineering lessons that apply ACROSS projects:

- Algorithm porting mistakes
- Verification failures
- Debugging anti-patterns
- Architectural insights

Only add truly general lessons — project-specific knowledge goes in AGENTS.md and memory files.

### 6. Update TASKS.md

Update the session tracker with:
- What was completed
- What was learned
- What the next priorities are

## Quality checklist

Before finishing, verify:

- [ ] Post-mortem document covers ALL attempts, not just the successful one
- [ ] Each failed attempt has a specific root cause, not just "it didn't work"
- [ ] Rules in AGENTS.md are actionable imperatives, not vague advice
- [ ] Memory files are linked from MEMORY.md
- [ ] Global lessons are truly general (not project-specific)
- [ ] TASKS.md reflects current state
- [ ] No duplicate rules — check existing rules before adding new ones
- [ ] Framing check passed: no "broken / regression / silently non-functional / never worked / failed in production" language (see Framing section). Grep the draft.
- [ ] No customer name, no external tracker ID. Generic "enterprise customer" / "field report" only.

## Anti-patterns to avoid

- **Vague lessons**: "Be more careful" is not a lesson. "Always A/B test against baseline before declaring success" is.
- **Symptom-level explanations**: "The rendering was broken" is a symptom. "CheckBoundingBox is a partial order that produces wrong results in pairwise comparison sorts" is a root cause.
- **Missing the WHY**: Every rule needs a WHY. "Do NOT use pairwise comparison" — why? Because CheckBoundingBox returns true in both directions for edge/surface pairs, causing the sort to leave them in arbitrary order.
- **Skipping failed attempts**: The failures are the most valuable part. Future readers (including future Claude sessions) need to know what NOT to do and why.
