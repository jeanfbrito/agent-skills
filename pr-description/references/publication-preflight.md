# Publication preflight

## Artifact and evidence

1. Read the destination repository's instructions, package scripts, and CI workflow files.
2. Record a batch index entry for each proposed PR.
   Include repository, head branch, exact commit SHA, base branch and SHA, prerequisites, and uncommitted remainder.
   Link one schema-valid evidence manifest per node. Keep batch metadata in a separate index, outside the closed evidence schema.
   Use `~/Github/agentic-workflow-framework/skills/agentic-workflow/references/evidence.md` for that schema and its limits.
3. Check the actual remote head with `git ls-remote <remote> refs/heads/<branch>`.
   Use the head repository for forks. Compare it with the proposed commit.
   If publication includes an authorized first push, record the absent ref and intended SHA.
   A mismatch requires reconciliation before publication, not a claim that local evidence covers the remote.
4. Use the project's stack validator or equivalent of `split-pr-stack` for each node.
   Check its own tree with its declared dependencies.
   A combined-tree PASS is not evidence for the extracted node.
5. Record actual CI commands, including working directories, flags, environment, setup, and matrix variants.
   Do not substitute partial lint, default flags, or a smaller test input.
6. Separate each PR's evidence into local checks, CI runs, and missing proof.
   Tie each result to its exact source, command, environment, and log or run URL.
   Mark blocked checks `UNVERIFIED`. An installation failure is not a lint verdict.
7. Run the shared checker against each node's evidence manifest.

```bash
python3 ~/Github/agentic-workflow-framework/skills/agentic-workflow/scripts/evidence.py check <manifest.json> --json
```

Exit 0 means `PASS`. Exit 1 means `FAIL`. Exit 2 means `UNVERIFIED`.
A missing checker is `UNVERIFIED`. Never claim that it passed.
Do not publish a batch until its required local and node checks pass.
CI that can run only after publication remains missing proof until its actual run completes.
If a required check is blocked, report it before publication and obtain explicit authorization for that exception.
The checker neither grants permission nor judges evidence quality.
Do not put private manifest paths or workflow-tool details in a public PR body.

## Workflow fanout and waves

Before an authorized batch, list the workflows that each push and PR action can trigger.
Read event filters, branch filters, path filters, reusable workflows, matrices, and concurrency rules.
Do not assume that stacked PRs skip CI. A workflow can accept every base branch.

Estimate workflow runs and matrix jobs per action and for the full batch.
State the assumptions and unknowns. This is a configuration-based estimate, not a measured run count.
Do not invent runtime or cost figures.

For large fanout, propose waves with one representative prerequisite node first.
Show the proposed wave membership, dependencies, triggers, and expected fanout before publication.
Publish only within explicit batch or wave authorization and approved exact PR text.
Do not silently expand an authorized wave into the full stack.

Check the first wave's remote refs and actual triggered workflows before the next wave.
If a defect affects shared prerequisites, stop propagation and correct the affected nodes first.
Do not disable checks, cancel runs, or reopen closed PRs to reduce the queue without separate authorization.
After each authorized wave, report published heads, run URLs, failures, and remaining missing proof.
