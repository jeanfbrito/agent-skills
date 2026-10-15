---
name: good-morning
description: 'Builds the daily work plan from every inbox: Jira tickets (my queue and what others changed), unread Rocket.Chat chats on open.rocket.chat, GitHub review requests, my open PRs, threads waiting on me, release and CI health, and the project ledgers. Ranks it all on a fixed priority ladder, decides one main focus, the unblock batch and what waits, and reports it here as an organized Markdown plan, with an optional HTML day sheet. Triggered by "/good-morning", "good morning", "bom dia", "plan my day", "what should I work on today", "start of day triage", "morning briefing". Read-only: drafts replies only on request and sends nothing without approval. Window, repos and report mode live in a gitignored `local-config.yml`, and the accepted plan in `last-plan.json`, both created on first run.'
---

# Good Morning

Collect every inbox once, then **decide** the day. The scripts collect and
propose. The agent judges and decides. The output is a plan with one
main focus, not a list of everything that happened.

Scripts live in `~/Github/agent-skills/good-morning/`. Call them by that
absolute path. Config is `local-config.yml` in the same folder. The first
`gm.py save` creates it, so a first run works with the defaults. The
requirements, setup and troubleshooting are in `README.md` in the same
folder. When a source fails, give the user the matching setup or
troubleshooting step from that file.

## 1. Collect

Run one command. It runs Jira, chat, GitHub and ledger collectors at the
same time, in about 30 seconds:

```bash
~/Github/agent-skills/good-morning/gm.py collect
```

It prints a digest of about 80 lines and a run directory with the raw JSON
(`github.json`, `jira.json`, `chat.json`, `ledger.json`). Read the digest.
Open the raw JSON only to answer a question that the digest leaves open.

The digest gives:

- `WINDOW` and `SOURCES`: the window and the state of each source. Each
  failure keeps its exact error, and each truncated list is named.
- `CARRY-OVER`: each item of the last accepted plan, with its current state
  and its day count.
- Candidate lists, `FIRE`, `UNBLOCK`, `FINISH` and `FOCUS`, newest first.
  The scripts sort mechanically, so you make the final call.
- `STALE`, `LEDGER` and `FYI`.

Fill only the gaps that need judgment, with targeted reads:

- **Unblock items marked `[ack?]`**: the last comment came from someone
  else, but it has no question or request. Read the comment in
  `github.json` and decide: a real ask (Unblock) or a thank-you (FYI).
- **Jira changes by others**: a status change or a reassignment that
  someone else made can change your plan. Read every field of a SUP or
  priority-project ticket, because the description often lives in a custom
  field.
- **Chat items**: `answered` means you wrote after the message, and
  `others_after_my_last` counts the replies since your last message. Read the
  context with MCP `get_message_context` when a reply could hold a new ask.
- **Ledger hints** (`all named PRs closed`): check the card's DoD against
  the code before you propose to close the card. A card can name an old PR
  as context.
- **Calendar** (optional): if a Google Calendar connector is authenticated,
  read today's events and count the free focus hours. Otherwise set the
  Calendar source to `none`.

Completion criterion: each candidate that asks something has a label,
"asks me something" or "FYI", and each source has data or its exact error.

## 2. Rank on the ladder

Put each item on exactly one rung. A higher rung always wins. Inside a rung,
the most recently updated item goes first.

1. **Fire**: a customer escalation, such as a SUP ticket or an escalation
   post in a support room. Also a broken release, a broken auto-update, or
   CI red on a protected branch or a release tag.
2. **Unblock**: a person waits for me. Examples: a direct review request,
   an open question in a DM, a mention or a PR thread, a QA request.
3. **Finish**: work in flight that is close to done. Examples: my green PR
   that waits for review, a PR into a release branch, a ticket in In
   Progress or Changes Requested. Finishing comes before starting.
4. **Focus**: the highest-priority ticket in Ready for Dev or To Do, with
   the current fixVersion first.
5. **FYI**: everything that asks nothing. Classify a mention by its content,
   not by its room.

## 3. Decide the day

Apply these rules, in this order:

- **One main focus.** Pick the top of Fire. If Fire is empty, pick from
  Finish, or else from Focus. Give the reason in one sentence.
- **WIP limit.** One main focus and at most two secondary items. Everything
  else goes to "Not today", with a one-line reason.
- **Unblock batch first.** Time-box the Unblock items before the main focus
  (default 60 minutes). An item that needs more than 30 minutes becomes a
  secondary item or waits.
- **Carry-over.** An item that stays open 3 days in a row must change:
  split it, ask for help, or drop it. Name the choice.
- **Stale work.** Give the stale list one decision (for example "park all,
  run /pr-triage on Friday"), and name any stale item that blocks a person.
- **Ask only real calls.** Ask the user only for choices that no data
  settles. Make every other call and show the reason.

Completion criterion: each item that asks something is in the plan, in "Not
today" with a reason, or shown to be answered.

## 4. Report the plan

1. Write the plan as JSON in the session scratchpad, in the format of
   `~/Github/agent-skills/good-morning/references/plan-schema.md`. Use the
   `id` rules there, so that carry-over can match items tomorrow.
2. Print the terminal report and send it as your reply, word for word. It is
   the default output on every run:

   ```bash
   ~/Github/agent-skills/good-morning/gm.py render <plan.json>
   ```

   It prints Markdown: a status line, the main focus, the order of the day
   and the questions. Tables follow for the unblock batch, secondary work,
   carry-over and "not today". Priority dots mark each item: 🔴 Fire,
   🟠 Unblock, 🟢 Finish, 🟣 Focus, ⚪ FYI. To change the layout, change
   `render_markdown` in `gm_render.py`. Do not reformat the report by hand.
3. The HTML day sheet is optional. Make it only when `report` in the config
   is `local` or `artifact`, or when the user asks for it ("show the day
   sheet", "open the HTML"):
   - `local`: `gm.py render <plan.json> --format html --open` writes the
     sheet and opens it in the browser. Add its path below the report.
   - `artifact`: `gm.py render <plan.json> --format html --fragment --out
     <scratchpad>/day-sheet.html`, then publish that file with the Artifact
     tool. If `artifact_url` is set, read it and pass it as `url`, so that
     the same private page updates every day. On the first publish, use
     icon `calendar` and write the new URL into `artifact_url`. Add the
     link below the report.

## 5. Follow-ups (only on request)

Offer these in one line after the report. Do them only when the user asks:

- **Reply drafts** for the Unblock batch. Read
  `~/Github/agent-skills/shared/tone.md` first and apply its rules: real
  facts only, no defensive lead, frame gaps as scope, anonymize customers in
  public places. Send chat replies through the `rocket-send` skill, which
  asks for confirmation before each post.
- **Jira moves**: show the exact transition per ticket and wait for
  approval.
- **Start the main focus**: hand off to the `ticket` skill or the project's
  normal flow.

## 6. Save (after the user accepts the plan)

When the user accepts the plan, with or without edits, apply the edits to
the plan JSON and run:

```bash
~/Github/agent-skills/good-morning/gm.py save <plan.json>
```

It writes `last-plan.json` (items with day counts) and sets `last_run` to
the time when collection started. If the user set `vault_path` in
`local-config.yml`, it also writes the plan into the vault's daily note and
prints that path. If the vault write fails, the plan is still saved: report
the error. If the user does not accept the plan, do
not save. The next run then uses the same window again.

## Rules

- Read-only. Mark nothing as read, post nothing, move no ticket, and comment
  on no PR. Every outward action goes through step 5 with explicit approval.
- Report only facts from the sources. Each count and each age comes from a
  timestamp in the data.
- State the coverage: the window, the failed sources, and the truncated
  lists. Never write "nothing pending" for a source that failed.
- When a collector fails, fix the cause if you can (an expired token, an
  unknown flag). Otherwise report the exact error and continue with the
  other sources.
