# CI triage in normal mode

Give every failing check its own decision row.
A failure caused by this PR is Act.
For a flaky or pre-existing failure, rerun once with `gh run rerun <run-id> --failed`.
A second failure is Escalate.

For failures outside the diff or `merge.stale_base` (BEHIND), suspect a stale base first.
Check with `git merge-base --is-ancestor origin/<base> HEAD`.
A moved base is Escalate, not a retry.

Compare an `in_progress` check with the same job on recent base-branch runs.
Use `gh run list --branch <base>`.
Treat it as hung past approximately twice that duration, with sibling OS jobs green on the same SHA.
For a hung check, run `gh run cancel`.
Poll `--json status` until `completed`.
Then run `gh run rerun --failed`.
Use one background Bash call. Never sleep in the main loop.

This procedure does not grant workflow permissions to review-only or closed-correction mode.
