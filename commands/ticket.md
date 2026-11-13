---
description: Structured workflow to solve a ticket, Jira task, bug report, or feature request — analyze, research, branch, plan, implement, validate, self-review.
argument-hint: [ticket key, Jira URL, or pasted ticket content]
---

# Ticket/Task Workflow

You are starting a structured workflow to solve a ticket, Jira task, bug report, or feature request.

## Step 1: Receive the Ticket

The user may have passed the ticket as an argument: $ARGUMENTS

- **Jira key or URL** (e.g. `PROJ-123`, `https://…/browse/PROJ-123`): fetch it yourself — use the jira skill / `jira issue view <KEY>` if available. Only ask the user to paste if the fetch fails.
- **Pasted ticket text**: use it directly.
- **Nothing provided**: say "Paste the ticket, Jira task, bug report, or feature request below. I'll analyze it and create a plan." and wait. Do NOT proceed until they do.

## Step 2: Analyze the Ticket

Once the ticket is pasted:

1. Summarize the ticket in your own words (2-3 sentences max)
2. Identify the type: bug fix, feature, refactor, etc.
3. List acceptance criteria / definition of done
4. Identify any ambiguities or missing information - ask the user to clarify before proceeding

**Evidence first.** If the ticket links a recording, screenshots, or logs, get them before you research code. If a link needs a login you do not have (a Loom page, a private drive), ask the user for the file at once — do not reason from the ticket text alone. For a video: `ffmpeg -i <file> -vf "fps=1/3,scale=1280:-1" f_%02d.jpg`, tile the frames into one sheet with `ffmpeg -i f_%02d.jpg -vf "scale=640:-1,tile=5x5" -frames:v 1 sheet.jpg`, read the sheet, and transcribe the audio with `whisper`. A ticket written from a transcript drops the visual detail that decides the cause (which page, which part of the window).

**Cause outside this repo.** If research shows the root cause is in another system (server config, a third-party deployment, another repo), skip Steps 4-9. Draft a ticket comment with the cause, the evidence, and the fix steps, post it only after the user approves the text, and stop. Do not create a branch. Routing the work to the owner is the managers' job.

## Step 3: Research the Codebase

Before planning, deeply research the relevant parts of the codebase:

1. Find all files related to the ticket
2. Understand the current behavior and architecture
3. Identify dependencies and potential side effects
4. Check for existing tests related to the area

## Step 4: Create a Branch

Start from a fresh branch off the project's integration branch, also when you are already on a branch, so that the work does not inherit unrelated commits.

Resolve the integration branch in this order:
1. What the project's AGENTS.md, CLAUDE.md or CONTRIBUTING.md says (some projects branch off `dev`, never `master`)
2. `origin/dev` if it exists
3. The repo default branch (`git symbolic-ref --short refs/remotes/origin/HEAD`)

```
git fetch origin <base>
git checkout -b <branch-name> origin/<base>
```

Branch naming convention: `<type>/<short-description>` (e.g., `fix/screen-picker-crash`, `feat/outlook-calendar-sync`)

Confirm the branch name with the user before creating it.

## Step 5: Present the Plan

Present a detailed, numbered plan with:

- **Summary**: What we're solving
- **Files to modify**: List each file and what changes are needed
- **Files to create**: Any new files needed (minimize these)
- **Implementation order**: Step-by-step sequence
- **Testing strategy**: How we'll verify the changes work
- **Risk areas**: What could break and how we'll mitigate it

Format it clearly and ask: "Does this plan look good? Should I adjust anything before starting?"

**Do NOT start implementation until the user explicitly approves the plan.**

## Step 6: Implement

Once the plan is approved:

1. Implement changes following the plan, one step at a time
2. After each significant change, briefly state what was done
3. Follow all project conventions (check AGENTS.md if available)
4. Keep changes minimal and focused - don't refactor unrelated code

## Step 7: Validate

After implementation is complete, run ALL validations:

1. **Lint**: Run the project's lint command - fix any issues
2. **Type check**: Run type checking if applicable - fix any type errors
3. **Tests**: Run the project's test suite - fix any failing tests
4. **Build**: Verify the project builds cleanly
5. **For UI changes**: Use available tools to visually verify the UI renders correctly

If any validation fails, fix the issues and re-run until everything passes.

## Step 8: Self-Review

Before presenting to the user, do a thorough self-review:

1. Run `git diff` and review every changed line
2. Check for:
   - Security vulnerabilities (XSS, injection, etc.)
   - Missing error handling at system boundaries
   - Unintended side effects
   - Code that doesn't match the plan
   - Leftover debug code or console.logs
   - Cross-platform compatibility issues
3. Fix any issues found

## Step 9: Present Results

Present a summary to the user:

- What was changed and why
- Files modified/created
- All validations passed
- Any decisions made during implementation
- Anything the user should manually test

Then say: "All changes are ready. Want me to commit?"

**Do NOT commit until the user explicitly says to commit.**
