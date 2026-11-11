<!-- Template user guide of the reference lab (unreal-anim-lab skill). Copy to docs/ANIM_LAB.md and adapt the names. -->
# Anim Lab

The Anim Lab is a development tool to play, scrub, see and measure animations on the player body. Use it when you
match bones (hands on a gun, fingers, magazine), check a reload frame by frame, or record numbers to compare
before and after a change.

Code: `Source/UnrealTarkov/AnimLab/` (`UAnimLabSubsystem`, `AAnimLabActor`). It is not in Shipping builds.

## Start

1. Open `/Game/Dev/AnimLab/Lvl_AnimLab` (or start the editor with that map as an argument).
   `py "Scripts/make_anim_lab.py"` makes the level again: floor with a 1 m grid, sun, sky light, player start,
   the lab actor, the Shooter game mode. There are no bots.
2. Click **Play**. The lab actor gives the player the first weapon of `PreferredWeapons` that exists (a project weapon with a
   reference arms animation, or the template rifle) and runs `StartupCommands`:
   `hud 0`, `preset hands`, `cam left`.
3. In another level, type `AnimLab enable` in the console during Play. It makes a lab actor with no weapon and no
   start commands.

## Screen

- Top left: the measures, green when the distance is in the tolerance (`tol`, 1 cm), red when it is not.
- In the world: bone axes (`watch`: red X, green Y, blue Z), skeletons with joint dots (`skel`: pink = body,
  cyan = ghost), measure lines (green in the tolerance, red out of it) and labels, yellow points on mapped bones,
  an orange point on the IK goal of the left hand. The colors are at the top of `AnimLabSubsystem.cpp`.
- Bottom: the timeline (clip, animation, time, frame, rate, state) with the reload step marks (out, pouch, in,
  bolt), and the keys.

## Keys (`AAnimLabActor::Keys`)

| Key | Command |
| --- | --- |
| P | play / pause |
| `.` / `,` | one frame forward / back (Shift: 10 frames) |
| `]` / `[` | rate ×2 / ×0.5 |
| Home / End | first / last frame |
| K | next clip (hold, tactical, empty) |
| G / L | gizmos / labels on and off |
| J | snap: JSON record and screenshot |
| Num 0 | first person camera |
| Num 1, 3, 9, 5, 7 | front, right, left, back, top |
| Num 4, 6, 8, 2 | orbit 15° |
| Num + / − | camera nearer / farther |

The keys are a property of the lab actor: change them in the level, or add one in `AAnimLabActor()`.

## Commands

Type `AnimLab <command>` in the console. `AnimLab help` lists them. Output goes to the log, category `LogAnimLab`,
with the prefix `ANIMLAB:`.

| Group | Command | Effect |
| --- | --- | --- |
| Clock | `play`, `pause`, `toggle` | Play the clip in a loop (`loop 0` stops at the end) |
| | `step [n]`, `time <s>`, `frame <n>`, `end` | Go to a time (the clock pauses) |
| | `rate <x>`, `rate up`, `rate down` | Play rate, −8 to 8 |
| | `clip hold\|tactical\|empty\|next` | The hold pose or a reload of the held gun |
| | `clip /Game/Path/Anim` | Any animation, on the ghost only |
| Ghost | `ghost [0\|1]` | The bones of the clip animation, aligned to the held gun |
| | `ghost align <bone> <ref>` | Put a ghost bone on a reference |
| Match | `map <bodybone> <ghostbone>` | Calibrate now: `mapped:<bodybone>` = offset × ghost bone |
| | `map <bodybone> <ghostbone> weapon` | Use the offset of the weapon (`FWeaponHands::HandOffset`) |
| | `unmap <bodybone\|all>` | |
| | `preset hands` | Hold clip, ghost, maps and measures of both hands |
| | `preset fingers` | Adds one measure per finger: the end of the body finger against the end of the animation finger |
| Gizmos | `watch <ref>`, `unwatch <ref\|all>` | Bone axes (red X, green Y, blue Z), `axes <cm>` sets the length |
| | `measure <name> <refA> <refB>`, `unmeasure <name\|all>` | A distance line, on the screen and in the records |
| | `skel <space[:root]>`, `unskel <ref\|all>` | A skeleton, or the bones under a root bone |
| | `gizmo`, `labels`, `tol <cm>` | |
| | `show body\|gun [0\|1]` | Hide a mesh to see the gizmos behind it |
| | `hud [0\|1]` | The game widgets (health, ammo, crosshair) |
| Measure | `get <ref>` | The reference in the record space (`space <ref>`, default `gun`) |
| | `rel <refA> <refB>` | A relative to B: location, rotation, quaternion |
| | `snap [name]` | `Saved/AnimLab/<name>.json` and `Saved/AnimLab/Shots/<name>.png` |
| | `sweep [from to step name]` | One record per time (default: every frame of the clip) |
| | `shot [name] [multiplier]` | A screenshot with the lab text; a multiplier > 1 uses HighResShot (no text) |
| Camera | `cam fp\|front\|left\|right\|back\|top\|below` | Presets around the pivot, relative to the aim yaw |
| | `cam orbit <yaw> <pitch> [dist]`, `cam yaw <deg>`, `cam pitch <deg>` | |
| | `cam dist <cm>`, `cam zoom <factor>`, `fov <deg>` | |
| | `cam pivot <ref\|auto>` | Default (auto): the middle of the two hands |
| Other | `status`, `weapon <class path>`, `enable`, `disable` | |

## References

A reference is `<space>[:<bone or socket>]`:

| Space | Meaning |
| --- | --- |
| `body` | The player body mesh (`body:hand_l`) |
| `gun` | The third person mesh of the held gun (`gun:Muzzle`, `gun:Weapon_Body`) |
| `ghost` | A bone of the ghost (`ghost:Wrist_L`) |
| `mapped` | A body bone where its map puts it (`mapped:hand_l`) |
| `tip` | The end of a body finger after its last bone, as the body aim computes it (`tip:index_03_r`) |
| `ghosttip` | The same estimate on a ghost bone, for a finger with no end bone (`ghosttip:Thumb_03_L`) |
| `ik` | The IK goal of the left hand in the last pose |
| `cam` | The camera that renders |
| `world` | The world origin |
| `@<actor>` | An actor by label or name, its skeletal mesh or root (`@AnimLab_Wall`) |

## Records

`snap` and `sweep` write JSON to `Saved/AnimLab/`. A sweep writes one file and logs the mean and the largest value
of each measure. Each sample:

```json
{ "t": 0.48, "frame": 14,
  "measures": { "R hand vs mapped": 1.49 },
  "refs": { "body:hand_l": { "loc": [x, y, z], "rot": [pitch, yaw, roll], "quat": [x, y, z, w] } } }
```

The locations and rotations are in the record space (`space`, default `gun`). The records contain the watches and
both references of each measure.

## Run a sequence

`Scripts/anim_lab_run.py` runs a list of commands with waits, in one call:

```
py "Scripts/anim_lab_run.py" "clip tactical; cam front; time 0.97; wait 4; shot tac_097; cam left; wait 4; shot tac_097_left"
```

- `wait <frames>` waits (default 3). Wait 2 or more after a time change, before a shot.
- The engine writes a screenshot at the end of the next frame. The script waits 2 frames after `shot` and `snap`, so
  the next command does not change the picture.
- `!<console command>` runs a console command with no `AnimLab` prefix.
- It logs `ANIM_LAB_RUN: done` at the end. A sweep runs on: read its result from the log or the JSON file.

## Things to know

- The body evaluates its pose one frame after the clock changes. A paused clock shows the true pose. A sweep waits
  3 frames per sample.
- A screenshot shows the end of the next frame, not the frame of the command. Do not change the clock or the camera
  in the same frame as `shot` (`anim_lab_run.py` waits for you).
- The editor runs at about 3 FPS when its window is in the background ("Use Less CPU when in Background" in the
  editor preferences). A sweep is slow then.
- The `shot` screenshot includes the UI, so it shows the lab text. The capture of the Slate inspector (MCP) does not
  show the debug canvas.
- An outside camera locks the mouse look, so the aim does not move. `cam fp` gives the look back.
- The hand preset needs a gun with a hands animation (`FWeaponHands`). For another rig, use `clip <anim>`,
  `ghost align`, `map` and `measure`.
