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
`item | reference evidence | status | lab result | full-project result | impact | effort | last checked`.

- `status` values:
  - `missing`, `partial`, `below` (a sense or the critic shows it under the
    reference).
  - `lab-only`: it passes in its lab, not yet in the full project.
  - `queued`: senses pass in the full project. It waits for the critic gate.
  - `matches`, `exceeds`, `blocked`.
- A `quality bar` row reaches `matches` only through the critic gate. A
  `functional only` row reaches it through senses alone.
- Each status needs evidence: a sense digest, a capture path, a critic verdict,
  or a file and line. A status with no evidence is `unknown`. Treat it as
  `partial`.
- Write `impact` and `effort` as S, M or L. Give the reason in a few words.
