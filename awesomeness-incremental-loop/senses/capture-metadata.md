# Sense guide: capture metadata (every image says what happened)

## When to use it

Every capture: self-checks, lab shots, invariant snapshots and critic pairs.

## The blocker

- **Sign:** the agent has a folder of images. It cannot say which frame shows
  the landing, which build made it, or the state of the scene. It must
  capture again, or guess.
- **Cause:** the image holds pixels only. The facts that explain the pixels
  stayed in the running app.

## The sense

Write one metadata record for each image, at the moment of the capture.

- **Where:** a sidecar file with the same name (`shot-0123.png` and
  `shot-0123.json`), and one line per image in the run's `captures.jsonl`.
  If the format allows, also put the record ID in the image metadata (for
  example a PNG text chunk). Do not draw the metadata into the image: the
  critic must see a clean image.
- **What to record:**

| Group | Fields |
| --- | --- |
| Identity | run ID, frame number, time since start, wall-clock time, file name |
| Build | git commit, dirty flag, toggle states, project settings that change the look |
| Shot | shot name, camera transform and projection, view size, isolation set, gizmo set, critic mode or measurement view |
| Event | what triggered the capture: a scripted step (`"land after jump"`), an input (`"fire pressed"`), or an invariant break (`"wheel_fl below ground"`), plus the event ID in the event log |
| State | the values that the item is about: positions, velocities, contacts, active animation states, the current values of the metrics |
| Checks | invariant results for this frame: which passed, which failed, by how much |

- **Event log:** the run also writes `events.jsonl`, one line per event with
  frame number and time. A capture points to its event. Then the agent can
  read the story of a run in order and open only the images that matter.

## Proof that it works

Take any image from a run. With only its sidecar, the agent must be able to
answer: which build, which shot, which frame, what event, and which checks
failed. If one of these answers needs a new run, add the missing field.

## Cost and limits

A record is a few hundred bytes. Keep large data (full skeleton poses, point
clouds) in a separate file and put only its path in the record. Do not pass
the full records to the critic. It gets the clean images and the blind key
only.
