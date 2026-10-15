# good-night

A Claude Code skill that closes your work day. Type `/good-night` (or
"good night", "boa noite", "wrap up the day", "closing notes"). The skill:

1. collects what you did today:
   - the state of this morning's plan (from
     [good-morning](../good-morning/README.md))
   - PRs merged, opened and reviewed, your comments, and pushes
   - Jira tickets you moved or updated
   - local commits, ledger entries, and what the Claude session did
2. drafts a **closing note** for you to edit: Done, In progress, Waiting on,
   Tomorrow first, Notes
3. saves the note on your machine. The next morning, good-morning shows its
   "Tomorrow first", "In progress" and "Waiting on" items, so the day starts
   where the last one stopped
4. offers an optional two-minute check-in on how the day felt, and shows the
   last 7 days as a table

For the check-in, the value is the series. One day says little, but four
weeks show whether the load, the interruptions or the stress go up, and what
helps.

## The closing note

```markdown
# Closing note — 2026-10-15

## Done
- Merged #3580: fix the tray icon on Linux

## In progress
- CORE-2793 — repro works on Windows; next: write the spec

## Waiting on
- Reporter — logs for DMV2-31

## Tomorrow first
- CORE-2793 spec

## Notes
- none
```

A note needs all five sections. `gn.py note` refuses a note without them.
The skill shares a note (for example as a standup post) only when you ask,
and it shows you the text first.

### Send the note to your vault (optional)

If you keep an Obsidian vault, or any folder of Markdown notes, the skill
can also write each closing note into that day's daily note. Without a
vault, the skill keeps the notes only in `~/.local/share/good-night/notes/`.

```bash
~/Github/agent-skills/good-night/gn.py config --vault ~/path/to/vault \
  --daily-folder Daily --section "## 🌙 Evening Review"
```

- The note goes into `<vault>/<daily-folder>/<YYYY-MM-DD>.md`, at the end of
  the `--section` heading. If the heading is missing, the skill adds it at
  the end of the note. If the daily note is missing, the skill creates a
  small one.
- The note sits between `<!-- good-night:start -->` and
  `<!-- good-night:end -->`. A new save of the same day replaces that block
  only. The skill does not change the rest of your daily note.
- If the vault write fails, the local note is still saved.
- Only the closing note goes to the vault, never the check-in answers.
- `gn.py config` shows the setting, and `gn.py config --no-vault` removes it.
- good-morning can write the morning plan into the same daily note. Set
  `vault_path` in its `local-config.yml` (see the
  [good-morning README](../good-morning/README.md#vault-optional)).

## The check-in: workday questions

| Question | Scale | Basis |
| --- | --- | --- |
| How stressed did work make you feel today? | 1–5 | Single-item stress measure of the Occupational Stress Questionnaire ([Elo, Leppänen & Jahkola 2003](https://www.sjweh.fi/article/752)) |
| How heavy was the workload today? | 1–5 | Plain workload question |
| How fragmented was the day (meetings, pings, context switches)? | 1–5 | Plain workload question |
| How easy is it to switch off from work tonight? | 1–5 | Psychological detachment, from the Recovery Experience Questionnaire ([Sonnentag & Fritz 2007](https://www.sowi.uni-mannheim.de/en/sonnentag/research/measures-and-tools)) |

## The check-in: wellbeing questions

| Question | Scale |
| --- | --- |
| Mood today | 1–5 (very low · neutral · very high) |
| Energy today | 1–5 |
| Anxiety today | 1–5 |
| Hours of sleep last night | number |
| Did you wake up rested? | yes / no |
| Today I noticed: racing thoughts, restless, irritable, sad, low motivation, wanted to stay in bed | checklist, optional |
| What helped today, even a little? | text, optional |
| Anything you want to bring up later? | text, optional |

These items have no clinical cutoffs. Read them as your own trend, not as a
score.

## Your own questions (optional)

You can add your own question set. Put it in
`~/.local/share/good-night/questions.json`. It never goes into this repo.
The skill asks your questions after the shipped sets, in your words and your
language.

```json
{
  "id": "mine",
  "title": "My questions",
  "questions": [
    {"id": "focus", "short": "Focus", "type": "scale", "min": 1, "max": 5,
     "label": "How well could you focus?", "anchors": {"1": "not at all", "5": "fully"}},
    {"id": "exercise_min", "short": "Exercise", "type": "number", "label": "Minutes of exercise"},
    {"id": "outside", "type": "bool", "label": "Went outside?"},
    {"id": "drains", "type": "multi", "optional": true, "label": "What drained me",
     "options": [{"id": "meetings", "label": "Meetings"}, {"id": "support", "label": "Support"}]},
    {"id": "note", "type": "text", "optional": true, "label": "Anything else"}
  ]
}
```

| Field | Meaning |
| --- | --- |
| `type` | `scale` (needs `min`, `max`), `number`, `bool`, `multi` (needs `options`), `text` |
| `short` | Column name in the trend tables |
| `optional` | The check-in can skip it |
| `anchors` | Labels shown next to the scale |
| `hide_in_trends` | Keep a number out of the trend table |

## Requirements

| Need | Why |
| --- | --- |
| Claude Code, Python 3.9+ | Standard library only. |
| This repo at `~/Github/agent-skills` | The skill calls its script by that path. |
| [good-morning](../good-morning/README.md) set up (optional) | The plan review, merged PRs and moved Jira tickets. Without it, the check-in still works and only the review is empty. |

## Install

```bash
git clone https://github.com/jeanfbrito/agent-skills.git ~/Github/agent-skills   # if you do not have it
ln -s ~/Github/agent-skills/good-night ~/.claude/skills/good-night
```

Restart Claude Code. Skills load at session start.

## Use it

| Say | What happens |
| --- | --- |
| `/good-night` | Collect the day, draft and save the closing note, then the optional check-in and 7-day trend. |
| "show yesterday's note" | `gn.py note --date <YYYY-MM-DD>` |
| "show my trend" | `gn.py trends --days 14` |
| "prepare my session" | A summary since your last session, for example with a therapist or your lead. It has the daily numbers, the checklist counts and every open answer. You decide what to share. |
| "I had my session" | Marks today as the last session date. |

## Commands

| Command | What it does |
| --- | --- |
| `gn.py status` | Today's state, the morning plan review, and what you did today on GitHub, Jira and the local projects. |
| `gn.py note [file] [--date D] [--replace]` | Saves the closing note. Without a file, it prints the note. |
| `gn.py questions` | The question sets as JSON. |
| `gn.py record entry.json [--replace]` | Checks an entry against the questions and saves it. |
| `gn.py trends [--days N]` | A table of recent days, averages, and the change against the period before. |
| `gn.py config [--vault PATH] [--daily-folder F] [--section H] [--no-vault]` | Shows or sets the optional vault. |
| `gn.py session [--since DATE] [--mark]` | The summary since the last session or a date. |

## Privacy

- Notes live in `~/.local/share/good-night/notes/`, and check-in answers in
  `journal.jsonl` in the same folder (both mode 600), or in
  `$GOOD_NIGHT_HOME`. Nothing in this repo holds personal
  data.
- The skill never copies your check-in answers into a repo, ticket, chat,
  PR, memory or the closing note. It shares a summary only when you ask and then share it yourself.
- The answers pass through your Claude session while you check in, like
  anything else you type.
- good-morning reads only the closing note. It never reads the check-in
  answers.
- This is a self-tracking tool, not a clinical one. It does not diagnose. If
  a day is very hard, talk to someone you trust, a professional or a crisis
  line. In Brazil, CVV answers 24 hours a day at 188 (cvv.org.br).
