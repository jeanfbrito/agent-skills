# Anim Lab design: what the harness must do, and why

An Anim Lab is a debug harness inside the game world. It makes every animation question measurable: where is this
bone, where should it be, how far apart, at which frame. Build it once per project. Each part below exists because
a real bug was invisible or mis-measured without it.

## Parts

| Part | Does | Why it is needed |
| --- | --- | --- |
| World subsystem (`UTickableWorldSubsystem`, not in Shipping) | Owns all state; off until turned on | No cost in normal play; works in any level |
| One console command `AnimLab <verb> ...` | Every feature is a verb; output to one log category with a prefix | An agent drives it through the editor Cmd box and reads the log; a person uses the same verbs |
| Lab actor | Placed in the lab level: turns the lab on, gives the pawn its prop, runs start commands, maps keys to verbs | One click on Play gives a ready state; keys for a person |
| Lab level script | Floor with a 1 m grid, wall, sun, sky, player start, lab actor, game mode; no AI; reruns | Fast in the background; sizes readable |
| Clock | play, pause, step ±n frames, time, frame, rate, loop, clip select | The pose of ONE frame must hold still to be measured. Drive the game code through a preview API (e.g. `PreviewReload(bEmpty, Time)`), not by faking input |
| Ghost | Bones of a reference animation sampled at the clock time, aligned on a reference (`ghost align <bone> <ref>`) | Shows the target pose on top of the real one |
| References `space[:bone]` | body, prop, ghost, mapped, tip, ghosttip, ik, cam, world, @actor | One syntax for every measure, gizmo and record |
| Maps | `mapped:<bodybone>` = offset × ghost bone (calibrate now, or use the game's offset) | Compares bodies of different proportions |
| Measures | Named distance between two refs; line + label, green within tolerance, red outside; listed in a panel | The number, not the impression |
| Gizmos | Bone axes (`watch`), skeleton subtrees with joint dots in strong colors (body pink, ghost cyan), IK goal, labels | White bones on a white mannequin are invisible |
| Diagnostics from the anim code | The anim instance stores its last IK goals and other results; the lab reads them (`ik` ref) | Shows what the solver aimed at, not only where the bone ended |
| Camera | Presets around a pivot (front, left, right, back, top, below, fp), orbit, zoom, pivot on a ref | Hands are small; first person hides errors; front shows elbows |
| Records | `snap` one frame and `sweep from to step` to JSON (measures + both refs of each), log mean/max/time of max | Proof over the whole clip, before/after numbers |
| Shots | `shot name` with the UI (`FScreenshotRequest`, `bShowUI = true`) | The canvas text and gizmos are in the picture |
| Timeline | Clip, time, frame, rate, state, step marks of the action | Find the frame that matters |
| Run script | `anim_lab_run.py "cmd; wait 4; shot x; ..."` with frame waits | One editor call per batch; correct shot timing |

## Pitfalls that cost hours (build them in)

- **A screenshot is taken at the end of the next frame.** A command in the same frame changes the picture. The run
  script waits 2 frames after `shot`/`snap`. A false 26–45 cm hand error came from this.
- **Only a screenshot with the UI has the debug canvas** (`UDebugDrawService` "Game"). The MCP Slate screenshot and
  `HighResShot` do not.
- **The body pose follows the clock one frame later.** Wait ≥ 2 frames after a time change; sweeps wait 3 per sample.
- **A new world has no animated pose in its first frame.** Anything that reads the pose (physical animation) must
  wait for it, or it reads an empty array.
- **Test worlds** must end with `EndPlay` (`FTestWorldWrapper`), or plugins keep dangling pointers.
- **Background editor ≈ 3 FPS.** Sweeps are slow; do not misread it as a hang.
- **FName is case-insensitive**: `index_03_r` == `Index_03_R`. Body and ghost refs need separate spaces.
- **An outside camera must lock the mouse look**, or the aim moves while you inspect.
- **Sample animations without a mesh** (`SamplePose` in component space) for the ghost and for game code that reads
  a reference rig: one shared sampler, so the lab and the game agree.
- **Live Coding keeps old globals**: rename a changed color or constant.

## Data the game code should expose for the lab

- A preview API on the thing that owns the action (time override, which clip, clip length, step times).
- Read-only getters of the settings the lab mirrors (e.g. finger tip length) so lab and solver use one value.
- `GetLast<Something>()` diagnostics from the anim proxy: IK goals, errors, the pose it computed.
