# The report: one local HTML page to recall the run

The loop already writes captures, sidecar records, events, metric digests and
critic verdicts. The report puts them in one place, so the agent and any human
can see where the work is and what happened before. It is a filing system for
evidence. It is not a deliverable and not a work item.

## Rules

1. **The trail writes it.** Each `state.py note` rebuilds the report with
   `tools/report.py`, from the journal, the trail, `captures.jsonl` and the
   sidecars, `events.jsonl`, the metric digests and the critic rounds. So the
   report is current after every step, and no cycle builds it as a job. Do not
   write or edit the HTML by hand.
2. **Cheap.** The script runs in seconds at the end of each cycle. If it gets
   slow, make it read only the new runs. Do not spend a cycle on its style.
3. **Local and private.** Put it in a gitignored folder, for example
   `.localdev/awesomeness/report/index.html`, with relative links to the
   images. Use inline CSS and no network. It opens as a plain file.
   Publish or share it only when the human asks.
4. **Data for the agent.** The script also writes `report-data.json`, the same
   facts in a short form. The agent reads or searches that file to recall
   history. Examples: "When did the wheels first go below the ground?" and
   "What did row 12 look like five cycles ago?". It does not read the HTML.
5. **Say where it is.** Each cycle's status line ends with the report path,
   so the human never has to search for it.
6. **Grow it with the data.** Start with the gap table and the latest image
   per shot. Add a section only when the loop writes the data for it.

## Sections

| Section | Content |
| --- | --- |
| Header | Project, reference, mode, cycle number, commit, frame-rate and physics targets, time of the last update |
| Now | The open cycle, or the last one, with each of its notes, captures and metrics |
| Trail | Every earlier cycle, newest first: its notes, captures, metrics, status, progress and commit |
| Assumptions and asks | Values the loop chose where the sources are open, and what it needs from the human |
| Gap matrix | Each row with a status colour, its last evidence, and a link to its row section |
| Row sections | A timeline of the cycles on that row. Each cycle shows its contact sheets as thumbnails, the metric trend as a small inline SVG line, the invariant breaks, the check level and result, and the commit. |
| Invariant breaks | Each break: the rule, the object, the worst value, the first frame, and the snapshot |
| Critic rounds | The queued rows, the image pairs, the verdicts and deficits. Show the blind key only after the round. |
| Pending verdicts | Each toggle, what it does, how to turn it on, and its evidence |
| Senses and labs | What exists, how to run it, and its last result |

## Size

- Use small thumbnails (about 320 px wide) that link to the full images.
- Keep the first and the last capture of each shot per row, every critic pair
  and every invariant snapshot. Older in-between captures can go when the
  disk gets full. Their sidecar records stay in `captures.jsonl`.
