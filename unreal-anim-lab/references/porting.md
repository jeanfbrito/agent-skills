# Port the reference lab to a project

Reference sources: `~/Github/agent-skills/unreal-anim-lab/reference/Source/` (from a UE 5.8 first-person shooter
with a full body, a held gun and a reference arms rig). About 1,900 lines. Most of it is generic: clock, ghost,
references, maps, measures, gizmos, camera, records, shots, timeline, keys. The adapters below name project types.

## Steps

1. Copy `AnimLab*.h/.cpp` to `Source/<Module>/AnimLab/` and `AnimPoseSampling.h/.cpp` next to the anim code.
   Replace `UNREALTARKOV_API` with `<MODULE>_API` and the namespace `UnrealTarkov::AnimSampling` with your own.
2. `<Module>.Build.cs`: add `"Json"` (private), plus `"AnimationCore"` if your anim code uses its IK. Add the
   folder to `PublicIncludePaths` if the project uses include paths per folder.
3. Keep `ShouldCreateSubsystem` returning false under `UE_BUILD_SHIPPING` (as the reference does): the lab never
   runs in a shipped game.
4. Change the adapters (search for these names):

| Reference name | What it is | Replace with |
| --- | --- | --- |
| `AShooterCharacter`, `AddWeaponClass` (AnimLabActor) | The pawn and how it gets a prop | Your pawn and its equip call; or remove the give step |
| `AShooterWeapon`, `GetWeapon()` | The prop the body interacts with | Your prop actor, or remove the `gun` space |
| `GetThirdPersonMesh()` | Mesh of the prop that has the bones/sockets | Your prop mesh |
| `PreviewReload / StopReloadPreview / IsReloadPreview / GetReloadClipLength` | Clock driver of the action | A preview API on your action (add it: time override + clip choice) |
| `EAnimLabClip::{Hold,Tactical,Empty}` | The clips of the action | Your clips; keep `Custom` (any animation on the ghost) |
| `FWeaponHands` (HoldAnimation, GunBone, HandBone, HandOffset, Fingers) | Reference rig data | Your reference rig data, or `clip <path>` + `ghost align` by hand |
| `FWeaponReload` step times (timeline marks) | Action step marks | Your step times, or none |
| `UShooterBodyAnimInstance::GetLastOtherHandTarget`, `AimSettings.FingerTipLength` | Solver diagnostics | Your anim instance getters (add them) |
| `PresetHands`, `PresetFingers` | One-command setups for the common check | Presets for your common checks |
| `PreferredWeapons`, `StartupCommands` (AnimLabActor) | Start state | Your prop list and start commands |

5. Build (full build: new classes). Make the level with
   `py "<abs>/make_anim_lab.py" --level /Game/Dev/AnimLab/Lvl_AnimLab --game-mode <class path>`.
6. Copy `reference/ANIM_LAB.md` to `docs/ANIM_LAB.md`, change the names, and point the project `AGENTS.md` to it.

## When the subject is not a held prop

The core works for any skeletal body: drop the `gun` space, align the ghost on a body bone
(`ghost align pelvis body:pelvis`), drive the clock through your anim instance (a time override on the montage or
sequence player), and keep measures and sweeps. Examples: foot contacts on stairs (ghost = mocap, measure
`body:foot_l` vs `@Step_03`), a door handle grab (prop = door), a climb (prop = ledge actor).

## Check the port

- `AnimLab help` lists the verbs; `AnimLab status` names the subject and clip.
- `snap test` writes JSON and a shot with the panel text visible.
- A measure between a bone and itself reads 0.00; a known offset (e.g. a 10 cm socket) reads its value.
