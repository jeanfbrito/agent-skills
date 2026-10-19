# Reviewer brief for third-party PRs

Send this to a `reviewer` subagent, with at most 3 PRs per agent. Group PRs
that touch the same area into one agent, so it can see their collisions.
Fill in the placeholders. Add one line per PR with the specific thing to check
(an earlier decision named in the title, a sibling PR that touches the same
file, a code path that another open PR deletes).

```text
Review these open third-party pull requests on <owner/repo>: <#N (author, "title")>, ...

Rules:
- Read-only. Do not edit files, do not check out branches, do not post comments, reviews or labels to GitHub.
- Work from <clone path>. Get each diff with `gh pr diff <N>` and the body/discussion with `gh pr view <N> --comments`. Read inline review threads with `gh api repos/<owner/repo>/pulls/<N>/comments`.
- The PR heads are already fetched as refs `refs/pr-triage/<N>`, and the base as `refs/pr-triage/base/<base>`. Read surrounding code with `git show refs/pr-triage/base/<base>:<path>` or `git show refs/pr-triage/<N>:<path>`.
- Read <clone path>/AGENTS.md (or CLAUDE.md / CONTRIBUTING.md) for repo conventions.
- For each PR, find out if a linked issue exists and if a maintainer already replied. Check git history (`git log refs/pr-triage/base/<base> --oneline -- <file>`) for an earlier decision on the same behavior.
<per-PR specific checks>

Return for EACH PR, in this exact shape, max ~20 lines per PR:
#N — title (author)
What it does: 2-3 sentences, plain language.
Why: the problem it claims to fix; linked issue if any.
Correctness: concrete bugs or risks, each with file:line from the PR head. Say "none found" if none.
Fit: collisions with other open PRs or the base branch, earlier maintainer decisions, repo conventions, platform coverage, tests present/missing.
Open review threads: what bots or humans asked and whether the author answered.
Verdict: one of MERGE-READY / NEEDS-CHANGES / NEEDS-DECISION (product call for the maintainer) / CLOSE, plus one sentence why.
Suggested reply to the author: 2-4 sentences, polite, concrete, English.
Label each claim as read-in-source, inferred, or guess.
```
