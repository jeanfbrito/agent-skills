# Isolate a reviewed task delta

The helper records explicit file paths before a task. It keeps the later delta after a reviewer inspects it.
It checks the entire staged publication delta against that record, even on a different base.
It uses Python's standard library and read-only Git commands. It never runs commands from an artifact.
It does not stage, commit, push, apply patches, or write source files.

## Trust limit

A baseline does not establish authorship. Concurrent edits can enter the delta before review.
A reviewer must inspect the full delta. The reviewer must check that it has only the intended concern.
The agent can act as reviewer within the authorized task. Ask the user only about ambiguous ownership or expanded scope.
The seal records reviewer inspection, not mandatory human approval. It cannot infer authorship or prove that the reviewer inspected the delta.
Artifacts contain complete file text. Store them in a private directory outside both repositories.
The helper creates artifacts with exclusive writes and mode `0600`. It does not replace existing files.

## Capture, review, seal

Use a separate artifact set for each concern. Use repository-relative file paths, not directories or pathspecs.
The examples use `/tmp/task-delta` as an existing private directory. Select a new private directory for actual work.

1. Capture the selected source paths before editing them.

   ```bash
   python3 -I ~/Github/agent-skills/commit/task_delta.py capture \
     --repo /absolute/source --out /tmp/task-delta/baseline.json \
     -- path/to/file path/to/second-file
   ```

2. Keep the printed baseline digest outside the artifact before editing source.
3. Make the task changes. Preserve unrelated edits.
4. Create the review artifact with the captured digest. The command prints its SHA-256 digest and the full delta.

   ```bash
   python3 -I ~/Github/agent-skills/commit/task_delta.py review \
     --baseline /tmp/task-delta/baseline.json --baseline-sha256 <captured-digest> \
     --out /tmp/task-delta/review.json
   ```

5. As reviewer, inspect every changed line, path, and mode in that output.
   Inspect file text in the artifacts when terminal output hides whitespace or control characters.
   Do not seal a delta that has unrelated edits, even within one file.
   If ownership is ambiguous or scope expands, ask the user before proceeding.
   Create separate reviewed artifacts for separate concerns without replacing user source.
6. Seal after inspecting the exact delta and checking its printed digest. No additional human approval is required.

   ```bash
   python3 -I ~/Github/agent-skills/commit/task_delta.py seal \
     --review /tmp/task-delta/review.json --reviewed-sha256 <review-digest> \
     --out /tmp/task-delta/seal.json
   ```

A source change after review prevents sealing. A source change after sealing prevents verification.
Changes to the captured source HEAD also prevent both operations.
Artifact digests detect changes after review or seal. They do not authenticate the reviewer.
Do not edit artifacts to bypass a rejection. Repeat the workflow with new artifacts and another reviewer inspection.
If no baseline exists, do not claim that a later capture proves which earlier edits belong to the task.

## Check publication

Transfer only the reviewed concern into a separate publication worktree through an authorized process.
The helper does not transfer or stage changes. Existing commit authorization includes normal staging within its scope.
Do not request separate staging approval. Preserve any explicit user restrictions and the existing publication rules.
Keep the captured source unchanged until verification completes.

After authorized staging, check the publication repository.

```bash
python3 -I ~/Github/agent-skills/commit/task_delta.py verify-staged \
  --seal /tmp/task-delta/seal.json --repo /absolute/publication
```

The check uses publication `HEAD` as the base. It compares all staged paths and complete staged file contents.
It rejects extra paths, missing changes, and unrelated changes in a task file.
It also rejects unrelated baseline edits if they enter the staged delta.
It does not check unstaged publication files or run tests. Check the committed artifact separately after an authorized commit.

On a different base, each text hunk needs one exact match with three context lines where available.
The helper rejects missing, repeated, overlapping, or reordered matches. It does not use fuzzy or three-way application.
A deletion requires the exact captured file. A new file requires an absent path.
Only regular UTF-8 text files and executable-mode changes are supported. Symlinks and binary files are not supported.
Paths must be explicit and unique. Source HEAD must exist. Artifacts must remain available at their recorded absolute paths.

Exit `0` means the check passed. Exit `1` means rejection or an input error. CLI syntax errors return `2`.
A PASS applies only to the checked HEAD, index, source, and artifacts at that time.
The helper repeats source and index reads to detect mutation during checks. It does not lock other writers.
It cannot detect a change that occurs and returns to the same bytes between reads.
Any later mutation requires another check. A PASS grants no permission to commit or push.

## Focused tests

```bash
python3 -I -B -m unittest discover \
  -s ~/Github/agent-skills/commit/tests -p 'test_task_delta.py' -v
```

The tests use synthetic Git objects and indexes. They do not run staging or commit commands.
They cover two concerns in one file, concurrent source changes, artifact changes, ambiguous matches, and a different publication base.
