---
name: unreal-pve
description: Grows, tunes and exports trees and plants with the Unreal Engine 5.8 Procedural Vegetation Editor (PVE) plugin from Python and the editor UI, then places them as instanced Nanite skeletal meshes with wind. Use when a level needs a tree species the PVE samples do not have (a clear trunk, a flat crown, a palm-like shape), when a PVE tree must be tuned by its grower parameters, or when a PVE asset must be exported to a project folder. Triggered by "/unreal-pve", "procedural vegetation", "grow a tree with PVE", "make this tree look like", "export the PVE tree".
---

# Unreal PVE trees

PVE (UE 5.8, experimental) grows a plant from a graph of nodes. The main node is a grower (`PVGrowerSettings`)
whose `FPVGrowerParams` decide the shape. The export makes a Nanite skeletal mesh with a wind skeleton.
This skill changes the grower from Python, judges the shape by screenshots, and exports through the editor UI.
Drive the editor with the `unreal-editor-loop` skill (`UE command`, Slate `Type`/`Click`/`Screenshot`).

## Setup (once per project)

1. Turn on the `ProceduralVegetationEditor` plugin in the `.uproject`.
2. Put `r.Nanite.Foliage=True` in `[SystemSettings]` of `Config/DefaultEngine.ini`, then restart the editor.
   Without it the leaves do not draw (only bark and branches).
3. The samples are in `/ProceduralVegetationEditor/SampleAssets/StarterContent/` (deciduous tree, conifer, shrub,
   plant). The named species (beech, maple) are growth data in JSON only, with no ready mesh.

## 1. Grow a species from a sample

1. Write a spec JSON (example: `~/Github/agent-skills/unreal-pve/example_emergent.json`, a tall tree with a clear trunk
   and a wide crown). `grower: ""` lists the grower nodes of the sample and stops. The deciduous sample's main grower
   is `PVGrowerSettings_6`.
2. `UE command 'py "~/Github/agent-skills/unreal-pve/pve_grow.py" "<abs spec>"' 'PVE_GROW: start' 'PVE_GROW: done'`
   (absolute paths). It copies the sample once, sets the fields, checks each one came back, saves, opens the PVE
   editor. Each run starts from the sample's grower, so an earlier change cannot leak.
3. In the PVE editor: Slate `Snapshot`, find the button `Force Regen`, `Click` it.
4. Slate `Screenshot` with ref `""`. The result goes to a file: decode it with
   `py ~/Github/agent-skills/unreal-editor-loop/decode_slate_shot.py <result.txt> <out.png> [x0 y0 x1 y1]`
   and read the PNG. The viewport shows `Branches`, `Points` and `Foliage Instances`: track the branch count.

## 2. Tune by the documented parameters

Read the tooltips in the plugin's `PVGrowerParams.h` before you guess. Change one or two fields per round, then
regenerate and look. What the fields do (tooltips, and seen in screenshots):

| Field | Effect |
| --- | --- |
| `TrunkGrowth.AxillaryPriorityGradient` | X = height on the trunk / `PlantTargetLength`, Y = chance a side bud opens. Y 0 low = clear trunk |
| `TrunkGrowth.PlantTargetLength` | The trunk target. The gradient X uses it as 1.0. A target the trunk never reaches = a bare pole |
| `TrunkGrowth.Corymb` | Lower branches grow longer: a flat top |
| `TrunkGrowth.BranchScale` | < 1 tapers, > 1 spreads the crown |
| `BranchPhyllotaxy.AxilAngle` | Larger = wider crown |
| `Bifurcation` | Forks the main trunk (it split at the ground). Keep it off. Use `BranchBifurcation` |
| `LightSenescence.SenescenceThreshold` | Shaded branches die. 0.3–0.5 is "realistic". 0.5 left a pole |
| `GravityParams.GravitationalForce` | Default 9.8. A lower value keeps long branches up |
| GrowthCycles | Set by a `CreateConstant` node in the sample graph, not by the grower field: use `cycles` in the spec |

A thin crown is usually starved side buds, not short branches. Seen: a gradient of 0.5 above the clear trunk,
`Auxin.RadicalAuxin` 0.3 and `ApicalParentGrowth` 1.5 each cut the branches to ~50 (sample: 346). Longer
`BranchTargetLength` changed almost nothing. A gradient step from 0 to 1, with the sample values for the rest,
gave 70 branches and a full crown.

## 3. Export to the project

PVE has no export function for Python (`FPVExporter` is not reflected). Use the editor UI:

1. In the PVE editor Details, under Export Settings, set `Content Browser Folder` and `Mesh Name`. Do this first:
   the sample's default folder is the plugin content, and the replace policy overwrites the sample mesh.
2. For each text box: `PressKey` Ctrl+A, `PressKey` BackSpace, `Type` the value with `submit`. Then read it back
   (a snapshot label, or a cropped screenshot). A focus `Type` of one space stays in the value.
3. `Click` the toolbar `Export` button. It opens the modal window "Modify Export Settings" and the `Click` call
   blocks (the MCP and the log stop). Handle it with
   `powershell -NoProfile -ExecutionPolicy Bypass -File ~/Github/agent-skills/unreal-editor-loop/editor_window.ps1`:
   - `-Action list` shows the window. `-Action shot -Title "Modify Export Settings" -Out <png>` captures only it.
   - Read the folder and name, then `-Action click -Title "Modify Export Settings" -X <x> -Y <y>` on its `Export`
     button (window pixels from the shot). A posted click does nothing: Slate reads the real cursor.
4. The log must show `PVEditor: Mesh exported successfully "<name>" <path>`. Save the folder
   (`EditorAssetLibrary.save_directory`): the new mesh is not saved yet.

## 4. Place the trees

- The export is a skeletal mesh: place many with an `InstancedSkinnedMeshComponent` and the plugin's
  `DynamicWindData` asset (search `/ProceduralVegetationEditor/SampleAssets` by class). A C++ editor helper that
  takes a transform list and the wind data worked. Adding the instances from Python alone was not tested.
- `get_instance_transform` on an instanced skinned component needs a `PrimitiveInstanceId`, not an int. Keep your own
  transform list instead of reading instances back.
- The plants have no collision. Give each tree a separate trunk collider (an instanced cylinder, hidden in game).
- Scale from the mesh bounds: `mesh.get_bounds().box_extent.z * 2` is the height in cm.

## Rules

- Judge every shape from a screenshot you read, with the branch count. Do not report a shape you did not see.
- Never write into `/ProceduralVegetationEditor/...`: copy the sample to a project folder first (step 1 does).
- Do not use `AutomationLibrary.take_high_res_screenshot` for the level: it compiles all shaders and crashed the
  editor on a Substrate foliage material. Use the Slate screenshot.
- Report the asset paths, the branch count, the export log line, and the values you estimated (scales, crown sizes).
