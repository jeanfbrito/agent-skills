# Labs: isolate one subject, then integrate it

A full project has many moving parts. When all of them run together, the
feedback on one subject is slow and full of noise. So work on one subject at a
time in a small, controlled place (a "lab"). Make it match the reference there.
Then bring it into the full project with the same checks.

This file uses the senses from
`~/Github/agent-skills/awesomeness-incremental-loop/senses/README.md`.

## The four steps

| Step | What | Done when |
| --- | --- | --- |
| 1. Spike | A throwaway script that answers one question ("Does this idea work at all?") | The journal has the answer and its evidence |
| 2. Lab | The subject alone, with fixed inputs, the reference and measures in view | The lab senses pass: metrics, gizmos and the agent's own look at the capture. No critic. |
| 3. Integrate | The same subject inside the full project, with the same shots and metrics | The full-project senses are within tolerance of the lab numbers |
| 4. Full critic | A blind compare of the full project against the reference, at the critic gate (`references/checks.md`) | The critic picks ours or calls a tie |

Skip a step only when it adds nothing. For example, a one-line fix needs no
spike. A subject that already sits alone needs no lab.

## Spikes

- A spike answers one question with real inputs. Example questions:
  - "Can this IK solve reach the target inside the joint limits?"
  - "Does this API return the data we need?"
  - "Is this parser fast enough on the largest real file?"
- Put it in the scratch folder or a gitignored `spikes/` folder. It does not
  touch the project code.
- Record the question, the answer and the evidence in the journal. Then
  remove the spike, or promote its code into a lab.

## Lab rules

1. **One subject per lab.** Put only the subject and what it needs to run in
   the lab. Keep stand-ins for every part that touches the subject in the full
   project (for example a prop in the hands). Without them the lab pose is
   not the real pose.
2. **Real code.** The lab imports the project's real component, script, asset
   or scene. It does not use a copy. Then the integration cannot drift.
3. **Fixed inputs.** Fix the seed, the time step, the cameras, the lights and
   the data. Use named presets (poses, frames, fixtures), so every run can go
   back to them.
4. **Reference in view.** Show the reference at the same camera and scale. Use
   an overlay, a ghost or a side-by-side panel.
5. **Measures in view and in data.** Show debug gizmos with a toggle panel
   (see `senses/gizmos.md`): grids, rulers, target and
   actual markers, and number readouts.
   Write the same numbers to a file for the digest script.
6. **Same senses.** The lab uses the same control API, digest scripts and shot
   list format as the full project. The checks can then move with the subject.
7. **Dev only.** Keep labs in a dev folder (for example `labs/` or
   `dev/labs/`), out of ship builds. Add each lab to the "Labs" table in the
   journal.

## Lab types

| Subject | Lab setup | Measures |
| --- | --- | --- |
| 3D model | The mesh on a turntable. Front, side and top orthographic cameras. Fixed light rig. A grid and a known-size scale object (for example a 1.8 m figure). | Bounding box in metres, pivot position, socket positions, polygon count |
| Alignment of parts | The two parts and their attach points. Cameras along the attach axes. | Position offset (mm) and angle error (degrees) between the sockets. Line-of-sight error where it applies (for example a weapon sight to the eye) |
| Skeleton pose | The rig frozen at named poses. The reference image or a ghost pose from the same camera. | Joint angles against the limits, bone lengths, contact heights, hand and foot target error |
| Animation clip | One clip on a fixed root or a treadmill. Scrub to a frame. Onion skin. | Foot slide, root velocity curve, contact timing, pops between frames |
| Physics | One body or one joint chain. Scripted impulses. A recorded path. | Path error against the expected path, settle time, energy drift, penetration |
| Material or lighting | One object or a material ball under a light rig that matches the reference. | Colour and luminance difference in the matched region |
| UI component | The component alone with fixture data, at fixed viewport sizes. | Layout box sizes, overlap, contrast, a visual difference against the reference |
| App logic | A small script or a test page that calls the real module with real inputs. | Right output, time, errors |

## Integrate

1. Run the same shot list and metrics in the full project, with all other
   systems on.
2. Compare each number with the lab number. Write both in the gap matrix.
3. Within tolerance: set the row to `queued` for the critic gate, or to
   `matches` for a `functional only` row.
4. Out of tolerance: the difference comes from an interaction with another
   part. Turn the other systems on one at a time (toggles help) until the
   number breaks. The part that breaks it becomes a new item.
5. Keep the lab after integration. It is the fastest place to check a later
   regression in that subject.

## Status in the gap matrix

A row that passes in its lab but not yet in the full project has the status
`lab-only`. Only the full-project result can set `matches` or `exceeds`.
