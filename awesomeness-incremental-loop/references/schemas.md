# Data schemas

All loop data uses these formats, so that every project can use the shared
report script (`~/Github/agent-skills/awesomeness-incremental-loop/tools/report.py`).
You can add fields. Do not rename or remove the fields below.

## Folder layout

Keep the data root in a gitignored folder. Default: `.localdev/awesomeness/`.

```text
.localdev/awesomeness/
  runs/<run-id>/            one folder per sense run
    captures.jsonl          one line per image
    events.jsonl            one line per event
    metrics.json            the digest numbers of this run
    *.png, *.json           images and their sidecar records
  critic/<round-id>.json    one file per critic round
  report/index.html         made by tools/report.py
  report/report-data.json   made by tools/report.py
```

`<run-id>`: `YYYYMMDD-HHMMSS-<short-slug>`, for example
`20261006-141502-wheel-contact`.

## `captures.jsonl` (one JSON object per line)

| Field | Type | Meaning |
| --- | --- | --- |
| `id` | string | Unique in the run, for example `"0123"` |
| `file` | string | Image path, relative to the run folder |
| `frame` | integer | Frame number in the run |
| `t` | number | Seconds since the run started |
| `shot` | string | Shot name from the shot list |
| `row` | string | Gap-matrix item that this capture is for, or `""` |
| `event` | string | Event ID in `events.jsonl` that caused the capture, or `""` |
| `commit` | string | Short git commit. Add `"+dirty"` when the tree has changes. |
| `toggles` | object | Toggle name to value |
| `view` | object | `camera`, `size`, `isolation`, `gizmos`, `mode` (`"normal"`, `"critic"` or `"measure"`) |
| `state` | object | The values that the item is about |
| `checks` | object | Invariant name to `{"ok": bool, "value": number, "limit": number}` |

The sidecar `<image>.json` holds the same object as its line.

## `events.jsonl`

| Field | Type | Meaning |
| --- | --- | --- |
| `id` | string | Unique in the run |
| `frame` | integer | Frame number |
| `t` | number | Seconds since the run started |
| `kind` | string | `"step"`, `"input"`, `"invariant"`, `"error"` or `"note"` |
| `name` | string | For example `"land after jump"` or `"wheel_fl below ground"` |
| `object` | string | The object concerned, or `""` |
| `value`, `limit` | number | For `"invariant"` events |
| `capture` | string | Capture ID that shows this event, or `""` |

## `metrics.json`

```json
{
  "run": "20261006-141502-wheel-contact",
  "row": "wheel contact",
  "commit": "a1b2c3d",
  "level": 0,
  "pass": false,
  "prediction": "max penetration under 1 cm",
  "metrics": {
    "penetration_cm": {"p50": 0.2, "p95": 3.1, "max": 4.0, "limit": 1.0, "ok": false}
  },
  "invariant_breaks": {"wheel below ground": {"count": 12, "first_frame": 88, "worst": 4.0}}
}
```

`level` is the check level from `references/checks.md` (0 or 1).

## `critic/<round-id>.json`

```json
{
  "round": "critic-007",
  "cycle": 42,
  "rows": ["wheel contact", "suspension travel"],
  "pairs": [
    {"row": "wheel contact", "left": "runs/.../a.png", "right": "refs/.../b.png",
     "ours": "left", "verdict": "right", "margin": "clear",
     "deficits": ["tyre does not deform at contact"]}
  ]
}
```

`ours` is the blind key. Write it to the file only after the critic answers.

## `report-data.json`

`tools/report.py` writes it. It holds the gap rows from the journal, and for
each row its captures, metrics, events and critic verdicts in time order. The
agent searches this file to recall history. It does not read the HTML.
