# CodeRabbit dismissal patterns

Learned patterns for review-bot findings (CodeRabbit first, any bot in
`bot_authors`) that the babysit loop declined with evidence. A pattern is a
shortcut for the Decline verdict in SKILL.md §5, never a replacement for
checking the claim against the code.

When a babysit ends, append any dismissal pattern seen twice (same reason,
two items in one PR or one item in two PRs). One sighting is not a pattern.

Never auto-dismiss, whatever the confidence: security, privacy, auth, data
loss, migrations, concurrency, or any finding whose suggested fix is small and
clearly reduces risk. Those always get a full check, or go to Escalate.

## Format

```markdown
### <short pattern name>

- Pattern: <phrases or code context that identify the finding>
- Skip when: <conditions that must all be true to decline>
- Don't skip when: <risk boundaries that force a full check>
- Confidence: candidate | recurring | strong
- Source: <PR number and comment id, or a short note>
```

`candidate` after two sightings, `recurring` once several PRs confirm it,
`strong` only when the pattern is narrow, repeatedly verified and low-risk.

## Patterns

<!-- Append new entries below this line. -->
