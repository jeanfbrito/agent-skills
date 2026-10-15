---
name: good-night
description: 'Closes the work day: collects what got done today (morning plan from good-morning, PRs opened, merged and reviewed, comments, pushes, Jira tickets, local commits and ledger entries, plus this session), drafts a closing note (Done, In progress, Waiting on, Tomorrow first, Notes) that good-morning reads the next morning, then runs an optional short check-in on stress, load, mood, energy, anxiety and sleep with a trend table. Triggered by "/good-night", "good night", "boa noite", "end of day", "wrap up the day", "closing notes", "day notes", "how was my day", "prepare my session". Local only: notes and journal stay in ~/.local/share/good-night.'
---

# Good Night

Close the day in a few minutes. The main output is the **closing note**: what
got done, what is still open, who you wait on, and what comes first tomorrow.
good-morning reads it the next morning, so the next day starts where this one
stopped. A short check-in on how the day felt follows, and the user can skip it.

Scripts live in `~/Github/agent-skills/good-night/`. Call `gn.py` by that
absolute path. Setup and formats are in `README.md` in the same folder.

## Privacy (read first)

- Notes and the journal live in `~/.local/share/good-night/` (or
  `$GOOD_NIGHT_HOME`). When the user sets a vault, the closing note also goes
  into the vault's daily note.
- The closing note is a work note. Share it, for example as a standup post,
  only when the user asks. Show the exact text first, and post nothing without
  approval.
- The check-in answers are personal health data. Never copy them into a repo,
  ticket, chat message, PR, memory file, mastermind entry, vault note or any
  other tool. Never put them in the closing note. The vault gets the closing
  note only.
- Do not interpret or diagnose. Show the user's own numbers and words.

## 1. Collect the day

```bash
~/Github/agent-skills/good-night/gn.py status
```

It shows whether today has a note and a check-in. It shows the morning plan
with the state of each item now. It also lists what the user did today:

- PRs merged, opened and reviewed, issues opened
- comments that the user wrote today
- commits pushed to GitHub, and local commits on any branch in the
  good-morning `projects`
- Jira tickets that the user moved or updated
- `.localdev/workflow/done.md` entries dated today

Add what this session did that the sources do not show: decisions,
investigations, drafts, and work that is not committed. A source error
(`!` line) is a gap. Name it in the note, and do not guess.

## 2. Draft the closing note

Write the note in the user's language, with these five sections in this
order. Each line is one item with its link (PR URL, Jira key, ledger card).

```markdown
# Closing note — 2026-10-15

## Done
- <what got finished, with link>

## In progress
- <item> — <state now, and the next concrete step>

## Waiting on
- <person or event> — <what> — <link>

## Tomorrow first
- <one item, at most three>

## Notes
- <decisions, surprises, things to remember; "none" when empty>
```

- **Done** comes from the facts in step 1. Group many small items, such as
  "reviewed 4 bot PRs".
- **In progress**: each morning-plan item that is not done goes here or in
  "Waiting on", with the reason.
- **Tomorrow first**: propose the item that unblocks the most. The user
  decides.

Show the draft. Apply the user's edits, then save it to the session
scratchpad and run `gn.py note <file>`. Use `--replace` to change a saved note.

The vault is optional. `gn.py config` shows if the user set one. If the user
set a vault, `gn.py note` also writes the note into the vault's daily note, and
its output names that file. If the vault copy fails, the local note is still
saved: report the error. If the user set no vault and `$OBSIDIAN_VAULT_PATH`
exists, offer the setup once (`gn.py config --vault <path>`). Do not ask
again after the user says no.

## 3. Check-in (optional)

Offer it in one line: "Two more minutes for the check-in?" If the user says
no, stop here.

Run `gn.py questions`. Ask every question in ONE message, as a compact
numbered form:

- Show the scale and the anchors on the same line, for example
  `1. Stress 1–5 (1 not at all · 5 very much)`.
- Group the yes/no and checklist questions. Mark open-text questions as
  optional. Ask an extra set in its own language.
- Tell the user that a one-line answer is fine, for example
  `3 4 2 4 · 3 2 3 6.5h no · restless · helped: a walk`.

Parse the reply into an entry in the session scratchpad:

```json
{"answers": {"work_stress": 3, "load": 4, "mood": 3, "noticed": ["restless"]},
 "context": {"plan_done": 2, "plan_total": 3}}
```

`multi` answers are lists of option ids. `bool` answers are `true` or
`false`. Run `gn.py record <entry.json>`. If it reports missing or invalid
answers, ask only for those. Show the recorded values in one line, so that
the user can correct them (`--replace`).

Then run `gn.py trends --days 7` and show the table. Add at most one
observation that the numbers show directly. Give no advice unless the user
asks.

## 4. Care check

After a check-in, read the answers once more. Look for these signs:

- a mood score at the bottom of its scale
- anxiety at the top of its scale
- text about hopelessness, self-harm or not wanting to live

If you find one, say plainly that this looks like a hard day. Suggest
talking to someone they trust, or to a professional if they have one. In
Brazil, CVV answers 24 hours a day at **188** or cvv.org.br. In an
emergency, call **192** (SAMU). Outside Brazil, name the local crisis line.
Do not diagnose, and do not lecture.

## On request

| Request | Command |
| --- | --- |
| "show yesterday's note" | `gn.py note --date <YYYY-MM-DD>` |
| "show my trend" | `gn.py trends --days 14` |
| "prepare my session" | `gn.py session` (or `--since <date>`). Show the output without changes. The user decides what to share. |
| "I had my session" | `gn.py session --mark` |
