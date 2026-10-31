# Feature PR template

Replace every placeholder with observed evidence. Do not copy checked boxes for checks that did not run.
Keep private evidence manifests and workflow tools out of the public body.

```markdown
## Summary

<What the user saw or lacked, then the cause.>

## What changed

- **<Behaviour, one sentence.>** <How it changes and what stays the same.>
- Specs: <what the tests assert>.

## Behaviour change

<Who notices, when, and how to restore the previous behaviour. Omit this section if not applicable.>

## Test plan

### Local evidence

- [x] `<exact command>` at `<SHA>` on `<environment>`: <observed count and result>.

### CI evidence

- [x] `<workflow/job>` at `<SHA>`: <observed result and run URL>.

### Missing proof

- [ ] UNVERIFIED: <required scenario, platform, or CI run and the reason it is unavailable>.

## Related

<Public issues, source PRs, and companion PRs. Omit this section only when no related work exists.>
```
