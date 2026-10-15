# PLAN.json format

The agent writes this file at step 4. `gm.py render` draws it as the day sheet,
and `gm.py save` stores it for carry-over. Every field except `date`, `window`
and `main` is optional; an empty list hides its panel.

`id` is the carry-over key. Use the Jira key (`DMV2-30`), the full PR or issue
URL, or `chat:<message id>`. Keep the same `id` for the same item every day.

`age` is the age string from the digest (`14h`, `3d`). `source` is one of
`jira`, `chat`, `github`, `ledger`, `release`. `rung` is one of `fire`,
`unblock`, `finish`, `focus`, `fyi`.

```json
{
  "date": "2026-10-15",
  "window": {"start": "2026-10-14T11:53:40Z", "end": "2026-10-15T11:53:40Z",
             "hours": 24, "label": "first run: last 24h"},
  "sources": [
    {"name": "Jira", "state": "ok"},
    {"name": "Chat", "state": "ok", "note": "cache refreshing"},
    {"name": "GitHub", "state": "partial", "note": "my PRs truncated at 100"},
    {"name": "Calendar", "state": "none", "note": "not connected"}
  ],
  "main": {
    "id": "DMV2-30", "title": "Ship the DMV2-30 and DMV2-32 fixes as 4.18.4",
    "url": "https://…", "rung": "finish", "source": "jira",
    "why": "Two Highest customer bugs; both fixes are green and wait only for review.",
    "first_step": "Ask for review on #3581 and #3582.",
    "done_when": "4.18.4 draft built with both fixes.",
    "links": [{"label": "#3582", "url": "https://…"}, {"label": "#3581", "url": "https://…"}]
  },
  "unblock_minutes": 45,
  "unblock": [
    {"id": "https://github.com/…/pull/3566", "who": "jhaabhijeet864", "source": "github",
     "what": "Asks for the exact cert publisher name.", "url": "https://…", "age": "17h"}
  ],
  "secondary": [
    {"id": "https://github.com/…/pull/3580", "title": "Merge 4.18.3 into master", "rung": "finish",
     "source": "github", "why": "…", "first_step": "…", "url": "https://…", "age": "19h"}
  ],
  "carry_over": [
    {"id": "DMV2-30", "title": "…", "url": "https://…", "days": 2, "decision": "keep, main focus"}
  ],
  "stale": {"summary": "21 PRs and 4 tickets idle 7d+", "decision": "Park all; run /pr-triage Friday.",
            "items": [{"id": "…", "title": "#3058 Outlook debug logs", "url": "https://…",
                       "age": "62d", "red": true}]},
  "not_today": [{"id": "DMV2-31", "title": "…", "url": "https://…", "reason": "Blocked on reporter."}],
  "ledger": [{"title": "Card: #3493 bridge collision", "action": "Close: fixed on dev."}],
  "fyi": [{"source": "chat", "text": "11 new messages in 6 rooms; 86 older unread left out."},
          {"source": "release", "text": "4.18.3 is the latest release (19h ago).", "url": "https://…"}],
  "questions": ["Is the DMV2-22 QA request yours?"]
}
```
