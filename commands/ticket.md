# Ticket/Task Workflow

You are starting a structured workflow to solve a ticket, Jira task, bug report, or feature request.

## Step 1: Receive the Ticket

Ask the user to paste the ticket/task content. Say:

"Paste the ticket, Jira task, bug report, or feature request below. I'll analyze it and create a plan."

Wait for the user to paste the content. Do NOT proceed until they do.

## Step 2: Analyze the Ticket

Once the ticket is pasted:

1. Summarize the ticket in your own words (2-3 sentences max)
2. Identify the type: bug fix, feature, refactor, etc.
3. List acceptance criteria / definition of done
4. Identify any ambiguities or missing information - ask the user to clarify before proceeding

## Step 3: Research the Codebase

Before planning, deeply research the relevant parts of the codebase:

1. Find all files related to the ticket
2. Understand the current behavior and architecture
3. Identify dependencies and potential side effects
4. Check for existing tests related to the area

## Step 4: Create a Branch

**IMPORTANT**: The `dev` branch is the primary working branch for this project — all feature and fix branches MUST be created from `dev`. Do NOT reuse the current branch, do NOT branch from `master`, and do NOT skip this step even if you are already on a branch. Always start fresh from `dev`.

```
git fetch origin dev
git checkout -b <branch-name> origin/dev
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
