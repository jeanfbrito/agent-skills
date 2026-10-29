# Design record

The loop makes many choices that nobody asked for: a pace, a cap, a key
store, a file format, a default. Each one is a proposal until the people who
own that area agree with it. The design record keeps every such choice in one
file, `docs/awesomeness-loop-design-record.md`, so that reviewers can validate
the decisions before they read the code.

The decisions file (`references/decisions.md`) is different. It holds only
the questions that the loop cannot answer alone, and the orchestrator asks
them. The design record holds the answers: the loop's own choices, and the
human's answers after they are applied. Nobody is asked about a record while
the loop runs. The reviewers read it at the handover.

## Why it exists

A POC that works is the best start for a design discussion, because people
can try the real thing. But the discussion needs the decisions as a short list,
each with its options and evidence. In one run, the decisions were only in a
long design doc and in two PRs of 16533 and 23198 changed lines. A reviewer
asked to go back to the decisions before anyone reads the PRs. The work was
right, and the handover made it look like a skipped step.

## When a cycle writes a record

Write or update a record in step 8 (Decide), in the same commit as the
change, when the change does one of these:

- It picks one of two or more options that a reviewer could choose
  differently. Examples: an algorithm, a limit, a pace, a format, a storage
  place, a fallback.
- It changes a contract surface. Examples: an API, a bridge or IPC channel,
  a stored format or schema, a setting and its default, a key or a
  permission.
- It applies a human answer from the decisions file. Then `Decided by` names
  the human and the D entry.

A refactor that keeps every contract the same needs no record. Acknowledge
it instead (see "The check").

## Entry format

```markdown
### R<n> · <short title> · proposed

- Question: <one sentence that ends with "?">
- Options:
  1. **<chosen option>**: for <...>; against <...>
  2. <other option>: for <...>; against <...>
- Choice: <what the loop built>
- Why: <the reason, in one or two sentences>
- Evidence: <measure, test, live run, doc>
- Kind: fixed | configurable (setting `<name>`, default <value>)
- Applies to: <platforms or clients, and where they differ>
- Validate with: <security | core | product | infra | design | team>
- Surface: <paths of the contract it decides>
- Commits: <sha>, <sha>
- Decided by: loop cycle <n> | human <date>, D<n>
- Validation:
```

- Give at least two options. Mark the chosen one in bold. A choice with
  one option is not a decision.
- `Evidence` says what measured or proved the choice. Write `guess` when
  nothing did. The reviewers then know which choices need a measure.
- `Commits` lists the commits that built the choice. The commit that
  writes the record together with the change counts with no sha, because a
  commit cannot hold its own sha. List the later commits.
- `Kind` tells reviewers how much is at stake. A `configurable` choice
  needs only an agreed default, because an admin can change it later.
- `Validate with` names the group that must agree. Use the project's own
  group names. More than one group is allowed.
- The status in the heading is `proposed`, `validated`, `changed` or
  `reverted`. Only a person outside the loop moves it past `proposed`.
- `Validation` records who agreed or what changed, and the date. Examples:
  `validated by security, 2026-11-03` or `changed: cap 100k, product,
  2026-11-03`. A `changed` record also gets a gap row or a decisions entry
  for the work it causes.
- Number the records in order, and never reuse a number. When a later cycle
  changes a choice, update the record, add the new commits, and keep the old
  choice as a rejected option.
- Write the record so that a reviewer can judge it with no other file open.

## Contract surfaces

`state.py` finds contract changes by words in the changed paths. The
default words are in `CONTRACT_WORDS` in `tools/state.py`. Examples:
`api`, `ipc`, `preload`, `bridge`, `protocol`, `schema`, `migration`,
`settings`, `config`, `types`, `crypto`, `key`, `keychain`, `auth`,
`permission`, `security`, `store`, `cache`, `limit`, `lifecycle`.
`package.json` counts, because a dependency is a decision. Tests, docs,
Markdown, build config (`*.config.*`) and editor folders never count. A
journal pattern can add one of them back.

Two rules keep screens and app state out:

- For a UI component (`.tsx`, `.jsx`, `.vue`, `.svelte`), only the file name
  counts. A screen in a `settings/` or `security/` folder shows a choice. It
  does not make one.
- `store`, `stores` and `cache` count only in a file name. A `store/` folder
  often holds app state, such as Redux reducers. `keyStore.ts` and
  `cache.ts` still count.

Each project adds its own surfaces in the journal's "Contract surfaces"
table. A pattern is a glob. A pattern that starts with `!` removes paths.

```markdown
| Pattern | What it decides | Validate with |
| --- | --- | --- |
| `src/search/lifecycle.ts` | when the index is wiped | security |
| `!src/ui/**/settings/*.tsx` | display only | - |
```

Fill the table at Start, step 4, with the senses. Add a row when a review
finds a decision in a file that the table missed.

## The check

`state.py brief` raises these DO FIRST chores:

- `UNRECORDED-DECISION`: a trail commit changes a contract surface, and no
  record lists it in `Commits`, and the same commit does not change the
  record file. Write the record, or add the commit to an
  existing record. When the commit decides nothing new, acknowledge it:
  `S note ack --decision <sha>[,<sha>] "no new decision: <why>"`.
- `RECORD-INCOMPLETE`: a record lacks `Question`, `Options`, `Choice`, `Why`,
  `Evidence`, `Kind` or `Validate with`. The chore also shows for a `Kind`
  that is not `fixed` or `configurable`, and for a status past `proposed`
  with no `Validation`.
- `PR-SPLIT`: see `references/shipping.md`, "Split plan".

`UNRECORDED-DECISION` lists the commits oldest first. Record at least the
listed ones in the cycle that sees the chore. The brief lists the next ones
in the next cycle, and the chore is `OVERDUE` only when the same oldest
commit stays unrecorded.

`RECORD-INCOMPLETE` also refuses a record that still holds the template:

- A value such as `<...>`, `TBD` or `-`.
- Fewer than two options, or no option in bold.
- A question with no `?`.
- A `configurable` kind with no default.
- A number used twice.

Only `### R<n> · <title> · <status>` headings are records. Other headings in
the file are notes.

An ack starts with `no new decision:`, gives the reason in 15 or more
characters, and covers at most 5 commits. The live report lists every ack
next to the records, so the reviewers can check the reasons.

`S note commit --commit <sha>` prints `RECORD-NOW` when the commit changes a
contract surface with no record. The agent that made the choice knows the
options it weighed, so it writes the record in the same cycle.

The brief also prints one line: `DESIGN RECORD: <n> decision(s) (<n>
proposed, ...; <n> configurable). Proposed, by validator: security 4, ...`.
The live report shows the records grouped by validator.

When the loop also commits to other repos, list them in the journal's Setup:
`- Other repos: \`../other-repo\``. The check then reads their commits too.

## At the handover

The feature report starts with the records (`references/final-reports.md`,
"Decisions to validate"). The PR description of a large feature PR lists them
too (the `pr-description` skill). In both, a `proposed` record is a
proposal: never write "decided" before the reviewers validate it.
