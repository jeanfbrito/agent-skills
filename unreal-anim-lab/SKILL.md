---
name: unreal-anim-lab
description: Builds (once per project) and uses an Anim Lab in Unreal Engine - an in-game debug harness with a frame clock, a ghost of the reference animation, bone references, distance measures, colored skeleton gizmos, camera presets, JSON sweeps and screenshots with the lab text - then runs the measure, hypothesis, fix, re-measure loop until every pose check passes, with before/after proof. Use for any animation, IK, retarget, hand, finger, foot, elbow, prop-attachment or pose problem, or when a visual change needs proof. Triggered by "anim lab", "make a test scene for the animation", "create gizmos to measure bones", "add an animation player to scrub frames", "the hands look wrong", "the fingers are off the rig", "the elbow is wrong", "foot sliding", "match the bones", "screenshot the frame", "before and after".
---

# Unreal Anim Lab

Paths: `SK=~/Github/agent-skills/unreal-anim-lab` (expand to absolute in every `py` call). Editor driving, builds
and log reading: the `unreal-editor-loop` skill (`UE` = its `ue.sh`). Design and pitfalls:
`$SK/references/design.md`. Port guide: `$SK/references/porting.md`. Reference code: `$SK/reference/Source/`.
User guide template: `$SK/reference/ANIM_LAB.md`.

## A. Does the project have a lab?

Search the project for `AnimLabSubsystem`, `docs/ANIM_LAB.md`, a lab level. If yes, go to C. If no, B.
Do not judge a pose from a normal gameplay screenshot when the question is "is this bone in the right place".

## B. Build the lab (once)

1. Read `references/design.md` (every part has a reason). Tell the user the plan in a few lines and the cost
   (a full build, a new level, ~1,900 lines of debug-only code).
2. Port the reference (`references/porting.md`). Copy the sources and rename the API macro and namespace. Change
   the adapters: pawn, prop, clock driver, reference rig data, solver diagnostics, presets.
3. Add what the game code must expose. The action needs a preview API with a time override. The lab reads the
   solver settings it mirrors and the `GetLast...()` diagnostics of the anim proxy.
4. Full build. Make the level: `py "$SK/scripts/make_anim_lab.py" --level /Game/Dev/AnimLab/Lvl_AnimLab
   --game-mode <class path>`. Copy the guide to `docs/ANIM_LAB.md`; add a short section to `AGENTS.md`.
5. Prove the lab before you trust it. `AnimLab help` lists the verbs. `snap test` shows the panel text in the shot.
   A measure from a bone to itself reads 0.00, and a known socket offset reads its value.

## C. Use it

1. `UE launch /Game/Dev/AnimLab/Lvl_AnimLab`, start Play, `UE wait-log '<lab start line>'`.
2. Batch commands in ONE editor call:
   `py "$SK/scripts/anim_lab_run.py" "clip <c>; time 0.97; cam front; wait 4; shot name; cam fp; wait 4; shot name_fp"`.
   - `wait 4` after `time`, `clip` or `cam`, before `shot`/`snap`. The script waits 2 frames after each shot.
   - `!<console command>` for a raw command. No nested quotes. A second script is a second editor call.
   - `ANIM_LAB_PREFIX` env var if the project's verb is not `AnimLab`.
3. Set the clip before a sweep (`clip tactical; wait 3; sweep ...`). Every max "at 0.000 s" with the same value
   means the sweep ran on a one-frame clip: not a result.
   End: `UE wait-log 'ANIM_LAB_RUN: done'`. A sweep ends later: `UE wait-log '<name>.json' 600`, then
   `UE log 'sweep <name>:' 30` (mean, max, time of max per measure).
4. Read every shot (`Saved/AnimLab/Shots/*.png`) with the Read tool. The MCP Slate screenshot has no lab text.

Checks that work for most pose questions:

| Question | Commands |
| --- | --- |
| Is the effector on its target? | `measure <n> body:<bone> ik` or `mapped:<bone>`. Sweep the clip |
| Do contacts match the reference? | `tip:<bone>` vs `ghost:<tip bone>` / `ghosttip:<bone>` |
| Bend direction (elbow, knee) | `skel body:upperarm_l`, `skel ghost:<rig upper arm>`, `cam front` and `cam top` |
| What does the player see? | `cam fp` (forearm, prop or hand must not cover the view) |
| Raw numbers for reasoning | `get <ref>`, `rel <a> <b>` (record space `space <ref>`) |
| Frames to look at | The action step marks on the timeline. The time of max from the sweep |

## D. Debug until every check passes

Loop, and keep a short list of open checks with their numbers:

1. **Measure first.** Name each check as a measure with a tolerance. Sweep the whole clip. Red = a fact.
2. **Explain before you change code.** `get` the bones involved and compare lengths and positions. Then name the
   kind of error. Wrong rotation: the directions differ. Wrong target: the IK goal is off (`ik` ref). Unreachable:
   proportions, and no rotation can close it. Timing: a frame offset. Artifact: shot timing or a wrong ref.
3. **Change the smallest thing**, compile (`.cpp` → Live Coding, header → full build), rerun the setup scripts.
4. **Re-measure the same checks** with the same commands. Keep the numbers before and after.
5. **Prove with a picture**: switch the change off and on during Play with
   `py "$SK/scripts/pie_set.py" <Class> <struct.field>=<json>` (one editor call), shots `_off`/`_on`, then
   `python $SK/scripts/compare_sheet.py <project>/Saved/AnimLab/Shots <out.png> _off _on <names...>`.
6. **Two failed fixes on one check**: stop and attack the premise. Write the one sentence both fixes assumed and
   test it with a measure. Revert code from a refuted idea.
7. **Stop** when every check is within tolerance over the sweep, or is explained as out of reach with numbers.
   Ask the user before changing proportions or other defaults.

## E. Report

Start with what the user must do (or "nothing"). Then give each check: before and after (mean, max, time of max),
measured or inferred, and the comparison sheet path. Name the checks that stay out, with their cause. Update `docs/ANIM_LAB.md`
and `AGENTS.md` for new verbs, refs or findings. Write a wiki page for a root cause that differs from the first guess.
