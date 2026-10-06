# Sources and the gap matrix

## Sources

Search in this order. Use all that exist. Do not ask for sources you can find.

| Source | Typical paths |
| --- | --- |
| Human priorities | priority/plan/roadmap docs, `.localdev/workflow/` cards, open handoffs, `TODO.md`, the user's latest feedback |
| Known problems | `docs/KNOWN_ISSUES.md`, blockers, failing tests or checks |
| References (tag each one `quality bar` or `functional only`) | `docs/reference*`, `docs/references/`, `.localdev/reference/`, reference images or videos, specs, catalogs, "like X" lines in the README or `AGENTS.md` |
| Product focus | "current focus" sections in `AGENTS.md`, `CLAUDE.md` or the README |

If no reference exists, ask one question: "What is the reference?" Then stop
until you get an answer. This is the only start condition that can block.

## Gap matrix

One row per thing the reference has, or does, or looks like. Columns:
`item | reference evidence | done when | status | lab result | full-project result | impact | effort | last checked`.

### Coverage

Build the rows from the reference, area by area: each mode, screen, mechanic,
behavior and look that the reference has. Then add the human items and the
known problems. A matrix that holds only the open tickets is too narrow. When
it runs out of open rows, the loop has nothing left but beyond mode, while the
reference still has areas that nobody compared. When an area is out of scope on
purpose, write one row for it with status `held` and the reason.

### Done when

Each open row has one measurable target taken from its reference evidence.
Example 1: "the thrown rider's limbs move only by physics joints, and the
crash capture ties the reference clip in a blind side by side". Example 2:
"a click on empty glass reaches the desktop in the click sim, 0 misses".
Write it before the first cycle on the row. Each cycle reports the move of
that metric. A row should close within 3 cycles. When it does not, `state.py`
gives the signal `STALL` and the next cycle is a step back (SKILL.md).

- `status` values:
  - `missing`, `partial`, `below` (a sense or the critic shows it under the
    reference).
  - `lab-only`: it passes in its lab, not yet in the full project.
  - `queued`: senses pass in the full project. It waits for the critic gate.
  - `matches`, `exceeds`.
  - `blocked`: no path remains. The Blocked table gives the root constraint.
  - `held`: the human froze it or put it out of scope. Do not work on it.
- `state.py` groups the statuses: open (`missing`, `partial`, `below`,
  `unknown`, `lab-only`), queued, closed (`matches`, `exceeds`) and parked
  (`blocked`, `held`).
- A `quality bar` row reaches `matches` only through the critic gate. A
  `functional only` row reaches it through senses alone.
- Each status needs evidence: a sense digest, a capture path, a critic verdict,
  or a file and line. A status with no evidence is `unknown`. Treat it as
  `partial`.
- Write `impact` and `effort` as S, M or L. Give the reason in a few words.
