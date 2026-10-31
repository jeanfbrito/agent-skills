# Check each stack node

Use the project's stack validator or its equivalent of `split-pr-stack`.
Do not replace it with checks from a private combined tree.

1. Identify each concern's repository, branch, base, exact commit SHA, and declared prerequisites.
2. Read the destination repository's instructions and CI configuration.
3. Check each node's own tree with its declared prerequisites.
   Record the exact CI commands, working directory, flags, environment, results, and log paths.
4. Record local changes that are absent from the commit.
   Do not attribute their checks to the committed tree.
5. Check the integrated tree separately when the project requires it.
   An integrated PASS does not establish a node PASS.
6. Run the shared evidence check against each node's schema-valid evidence manifest.
   Keep batch metadata in a separate index that links these manifests.
   Use `~/Github/agentic-workflow-framework/skills/agentic-workflow/references/evidence.md` for the schema and its limits.

```bash
python3 ~/Github/agentic-workflow-framework/skills/agentic-workflow/scripts/evidence.py check <manifest.json> --json
```

Exit 0 means `PASS`. Exit 1 means `FAIL`. Exit 2 means `UNVERIFIED`.
A missing checker, missing log, or blocked dependency installation is `UNVERIFIED`, not PASS.
A dependency installation failure does not establish a code failure.
The checker tests evidence records. It does not establish evidence quality or grant permission.

Report each node's validator result and the evidence-check result.
A partial lint command is different from the CI command. Label it separately.
Reuse a PASS only for the same source and relevant conditions.
Recheck affected nodes after propagation or extraction changes their source or dependency context.
Do not report stack verification complete while a required result is `FAIL` or `UNVERIFIED`.
Authorized commits can still preserve incomplete work. Report their limits explicitly.
