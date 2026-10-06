# Senses: control, measure and see the project

The agent can only improve what it can perceive. A "sense" is a harness that
lets the agent drive, read, measure or look at the project. It works with no
human in the loop. If an item has no sense that can judge it, the first work
on that item is to build the sense.

All guides are in `~/Github/agent-skills/awesomeness-incremental-loop/senses/`. Read this index first. Then read only the guides that
the current item needs.

## Rules for every sense

1. **No user input.** A sense never takes the user's mouse, keyboard or focus.
   Use headless runs, no-focus windows and isolated scripted input. Project
   rules about automation (in `AGENTS.md`) win over this file.
2. **Quiet output.** Write raw data to a file. Return only a digest (`digest.md`). Open the raw file only to answer one specific question.
3. **Repeatable.** Fix the seed, the time step, the camera and the start state.
   The same call gives the same result.
4. **Cheap.** One call takes seconds, not minutes. It does not slow the
   machine or the app.
5. **Proven.** Before you trust a sense, make it fail on a known bad state. A
   check that cannot fail is not a sense.
6. **Out of the product.** Put the harness behind a debug flag, a dev build or
   a command-line flag. Ship builds do not expose it.
7. **Registered.** Add each sense to the "Senses" table in the journal: name,
   how to call it, what it returns, and its cost.

## The sense ladder

Build only what the current items need, in this order:

| Level | Sense | Answers | Guide |
| --- | --- | --- | --- |
| 1 | Control | "Put the app in state X." (load a level, spawn, set the camera, play an animation, step N frames, pause) | platform guide |
| 2 | State probe and invariants | "What is the value of Y now?" and "Is anything breaking a common-sense rule?" | platform guide, `invariants.md` |
| 3 | Debug gizmos | "Where is it, and does it line up?" | `gizmos.md` |
| 4 | Tagged logs | "What happened, and in which order?" | platform guide, `digest.md` |
| 5 | Metrics | "How good is it, as a number, over time?" | `metrics.md`, `digest.md` |
| 6 | Self-capture | "What does it look like at named view V, and what happened at that frame?" | platform guide, `capture-metadata.md` |
| 7 | Convergence | "How near to the reference is it, and where is the difference?" | `visual-convergence.md` |

## Guides

| Guide | Use it for |
| --- | --- |
| `browser.md` | Browser apps and games: `window.__agent`, tagged console logs, canvas capture, fixed time step |
| `godot.md` | Godot: flag-gated autoload, headless metrics, real-renderer capture |
| `desktop.md` | Electron and native apps: dev IPC, main-process inspector, one-window capture |
| `invariants.md` | Common-sense rules checked every frame (nothing below the ground, no penetration, no NaN, no text overflow), with event snapshots on a break |
| `capture-metadata.md` | A sidecar record and an event log for every capture: build, shot, event, state, check results |
| `3d-views.md` | 3D checks: many fixed angles in one contact sheet, and hiding everything that is not measured |
| `gizmos.md` | Debug gizmos with a UI toggle panel and API toggles |
| `digest.md` | Scripts that turn raw output into a short answer |
| `metrics.md` | Metrics for motion, physics, feel and performance |
| `visual-convergence.md` | Shot lists, measurement views, critic mode, fresh frames, blind pairs |

## When a sense is the next item

- A gap row that says `unknown` because nothing can measure it: build the sense.
- A critic who cannot see the difference that the human reports: improve the
  view (critic mode, crop, frame rate, slow motion).
- A metric that stays green while the human or the critic says "wrong": the
  metric measures the wrong thing. Fix the metric before the feature.

## Add a guide when a blocker teaches something

The loop adds to this folder. Do it when one of these happens:

- An item went `blocked` because the agent could not control, measure or see
  something. Later, the agent found a fix.
- A sense gave a wrong answer, and the cause is now known. Examples: a stale
  frame, a metric that passed through a cheat, a capture that took focus.
- A new platform or tool needed a new way to drive or capture it.

Then do these steps:

1. If a guide for that topic exists, add a section to it. If not, copy
   `TEMPLATE.md` to a new file with a short topic name, for example
   `audio.md` or `unity.md`.
2. Fill in every part of the template. Write the sign and the fix as facts that
   another agent can check. Do not name the project, its people or its private
   paths. Write the general rule.
3. Add the guide to the "Guides" table above.
4. If the blocker was a trap more than a technique, also add it to
   `~/Github/agent-skills/awesomeness-incremental-loop/references/lessons.md`.
5. Run the STE lint on the new text:
   `~/.claude/skills/asd-ste100/scripts/ste-lint.py <file>`.
