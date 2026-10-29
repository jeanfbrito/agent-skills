# The two final reports

The live HTML report (`references/report.md`) is a filing system for the loop's
own evidence. Other people need two different documents. Write them when the
human asks for a report, or when the human stops the loop after a milestone.
Write each one with the orchestrator, from the trail, the journal, the
design record, the decisions file, git and the tickets. Do not write them from memory.

| Report | Reader | Question it answers | Life |
| --- | --- | --- | --- |
| Feature report | Product, Security, reviewers, the team lead | What did we build, why this way, what is still open? | As long as the feature exists |
| Process retrospective | The people who run the loop | How did the loop work, what went wrong, what to change? | Until the next loop run |

Keep them separate. A feature report that reads as a loop retrospective is
hard to follow: a reviewer had to read cycle numbers and labels such as
"C5c", "D1–D6" and "step back" to find the feature. Link the retrospective
from the feature report's appendix. Do not merge them.

## Rules for both

- Lead each section with one bold sentence that states its point.
- Use plain names. A loop label (row ids, decision ids, cycle numbers) goes
  only in the appendix glossary.
- Every number comes from a record: the trail, a spec run, a capture, git or a
  ticket. Mark each claim as measured or not run. Do not estimate.
- Keep sentences under 25 words. Use tables for decisions, requirements and
  status.
- First run a fact-sheet pass: one agent reads the PR bodies, the design docs,
  the journal, the decisions file and the source, and writes every fact with
  its source (file:line, PR line, ticket). Write the report from that sheet.
  The sheet also lists where the design docs, the PR bodies and the code
  disagree. Fix those or name them in the report.
- Publish as a document the human can share (a Docs artifact or the team's
  doc tool). It stays private until the human shares it.
- A design record entry with status `proposed` is a proposal. Write
  "proposed" or "the POC uses", never "decided", until the reviewers validate
  it. The work is a proposal that runs, not a closed design.

## Template 1: the feature report

Title: the feature's name ("E2EE Local Search on Desktop"). Byline: date and
author.

0. **Decisions to validate.** This section comes first, because reviewers
   validate the decisions before they read the code. Build it from the design
   record (`references/design-record.md`). Run `state.py brief` first: an
   `UNRECORDED-DECISION` or `RECORD-INCOMPLETE` chore means the list is not
   complete yet.
   - One bold sentence: how many decisions wait, and for which groups.
   - One table per `Validate with` group: decision, the POC's choice, the
     main alternative, fixed or configurable, status. Put the fixed choices
     first, because they cost the most to change later.
   - For a configurable choice, ask only for the default. Name the setting.
   - Link each row to its section in "Technical decisions".
   - End with the ask: who should join each group, and by when.
1. **The feature for users.** One bold sentence on what users can now do.
   - The problem today: what the user sees or lacks without it.
   - What the user can do: a short list of abilities.
   - The flow: numbered steps from the user's side, including the fallback
     where the feature is absent.
   - What the user can rely on: a table of guarantee and how it holds, with
     the live evidence. Then one paragraph on what it does not protect.
   - Current limits: platforms, cost, not built, not checked live.
2. **How it works.** One diagram of the components and the data flow, each box
   with the few lines that say what it does. Highlight the one box that holds
   the critical asset. One paragraph under it.
3. **Technical decisions.** One section per design record entry, in the
   order of section 0. The status comes from the record: proposed, validated,
   changed or reverted. Each section has:
   - the question
   - an options table: option, for, against, with the chosen one in bold
   - the choice, who made it and when (loop cycle or human answer), and the
     evidence
   - fixed or configurable, with the setting and its default
   - "Open:" with what is still undecided and its ticket.
   Include lifecycle, limits and scale numbers as their own sections when the
   feature has them.
4. **Findings outside the feature.** Problems found while building that exist
   without the feature (for example, security or storage findings). A table of
   problem, evidence, verdict, action. Then the PRs that fix them and the gap
   that remains. Keep this out of section 3.
5. **Implementation spec: components and contracts.** The public contract
   (API, bridge or protocol) as a table of method, input, output. Then one
   table of components per repo: component, job.
6. **Requirements and proofs.** A table of `#`, "The system shall…", proof,
   status. A proof is a test that failed first on the naive or old code, or a
   live run. Say "spec only" or "live missing" where that is the truth. Then
   the suite totals per PR.
7. **PR plan and open work.** The split plan from the journal
   (`references/shipping.md`, "Split plan"): a table of PR, repo, what it
   carries, size, depends on, in merge order. A PR past the size limit says
   why it stays whole. What to fix in the PR bodies. Then a numbered table of
   open work with tickets, then the next phase, then later items.

**Appendix: how it was built.** At most one screen: the method (loop, fail
first, live after mock), the environments, the security reviews, the human
rules that decided trade-offs, and a link to the process retrospective. Then a
glossary of the loop labels used in tickets, and the list of places where older
design docs no longer match the code.

### The handover message

The human usually announces the work in a chat post or an email. Draft it in
this order, in at most 10 lines:

1. What works now, and where to try it (demo, build, branch).
2. The decisions to validate, by group, with the count, and a link to
   section 0.
3. The ask: who should join each group.
4. The PR plan: what to review first, and that the PRs wait for the
   decisions.

Say that the POC exists to make the discussion concrete. Do not apologize for
the order of the work.

## Template 2: the process retrospective

Title: "<Topic> Loop Retrospective". Byline: product, date. Then one paragraph
on the scope, and one line on the sources (trail note count, gap matrix, git,
tickets) with "every number comes from those records".

1. **Outcome.** One paragraph on the result, then a list grouped by cycle
   ranges: what each range delivered.
2. **By the numbers.** A table: cycles and time span, cycle duration (median,
   p90, longest, from trail timestamps), rows moved to `matches`, the share of
   cycles the reviews judged useful, files and spec files per PR candidate,
   tickets and revisit items.
   - How cycles were spent: a table of kind, cycles, share.
   - The gap matrix at the end: counts per status.
   - Other measures: reverts, blocked rows, human decisions, live-run notes.
3. **How the loop works.** A short explanation for a reader who never saw it:
   orchestrator, one subagent per cycle, journal, trail, signals.
4. **Timeline.** Phases by cycle range, with the milestone of each.
5. **What worked.** Three to five themes, each with the cycles and numbers
   that prove it (for example, "live checks found what mocks could not").
6. **What went wrong.** A table of cycle, problem, cause, fix. Then the
   problems with no single cycle (journal size, ticket drift, environment
   noise).
7. **The human's part.** The decisions recorded, and the one-line human rules
   that changed the course. One sentence on where the waits came from.
8. **Recommendations for the next loop.** One bold lead per item, each a rule
   that a skill, a check or a hook can carry. Apply the accepted ones to this
   skill (`update-skill`), not only to the report.
9. **Where things are.** A table of item, status, next step.
