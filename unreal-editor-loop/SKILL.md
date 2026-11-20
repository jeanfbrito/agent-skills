---
name: unreal-editor-loop
description: Drives an open Unreal Engine editor from Claude Code for any project - types console and py commands through the Unreal MCP Slate inspector, picks Live Coding or a full build, closes, rebuilds and relaunches the editor, waits for the MCP server, starts Play, and reads every result from the editor log. Use for any C++, Python editor script, asset or level change that must be built, run and seen working. Triggered by "build and test it in the editor", "rebuild", "recompile", "live coding", "restart the editor", "run this script in the editor", "start play", "check it in game", "unreal mcp".
---

# Unreal editor loop

Helper: `~/Github/agent-skills/unreal-editor-loop/ue.sh` (call it `UE`). It finds the `.uproject` from the
current folder upward, the engine from `EngineAssociation` (registry builds, Launcher installs, macOS
`Install.ini`), the target `<Project>Editor`, and `Saved/Logs/<Project>.log`. Overrides: `UE_PROJECT`,
`UE_ENGINE`, `UE_MCP_PORT`. Start with `UE info`. Fix a wrong engine with `UE_ENGINE` before anything else.

## 0. Setup check (once per project)

1. Turn on the MCP plugins in the `.uproject` (UE 5.8: `ModelContextProtocol` and `AllToolsets`, off by default).
   Make the server start with the editor:
   `Config/DefaultEditorPerProjectUserSettings.ini` →
   `[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]` `bAutoStartServer=True`.
2. Claude Code needs the server: `claude mcp add --transport http --scope user unreal-mcp http://127.0.0.1:8000/mcp`.
3. `unreal-mcp` "Failed to connect" means the editor is closed or still loading, not broken. One editor per port.
4. Write the project facts (map, build command, scripts) in the project's `AGENTS.md` or `CLAUDE.md`.

## 1. Type a command in the editor

The MCP has no console tool. Type into the **Cmd** box of the editor status bar:

1. `mcp__unreal-mcp__call_tool`, toolset `SlateInspectorToolset.SlateInspectorToolset`, tool `Type`,
   `{"ref": "tb2", "text": "<command>", "submit": true}`.
2. `false` after an editor start: call `Observe` and then `Snapshot` (both `{"ref": "", "maxDepth": 60}`), find the
   `textbox` right after the `Cmd` combobox in the snapshot (usually `tb2`), and `Type` again.
3. If PIE captures input, release it with `Shift+F1` immediately before the Cmd sequence.
   Select the editor window. Then `Type` one space into Cmd without submit, `PressKey` Ctrl+A, `PressKey` BackSpace,
   and `Type` the command, in one sequence. The first `Type` sets the focus. A `Click` can land in the viewport.
4. `py "<path>.py" args`: always an **absolute path**. A relative path resolves against the process folder
   (`Engine/Binaries/Win64` after `UE launch`) and fails with "Could not load Python file".
5. No nested quotes inside one command. Send a second `Type`.
6. A true `Type` result is not execution evidence. Require a unique start message before waiting for completion.
   If it is absent, inspect focus and logs before retrying. Execution can be uncertain. Never retry automatically.
   Stop on editor exit, Python errors, assertions, ensures, or either `Fatal error!` or `Fatal error:`.
   Run a check in the background when it can take more than a minute.
7. The sandbox of `execute_tool_script` only has `json`, `math`, `re`, `time`, `copy`, `datetime`: real work goes in
   a `.py` file run with `py`.

### Guarded command runner

Use `UE command '<command>' '<unique start marker>' '<unique completion marker>' [timeout]` for finite scripts.
It selects the editor, releases PIE capture, clears Cmd and submits exactly once.
It focuses Cmd with a `Type` of one space, not a `Click`. A click can land in the viewport. Then Ctrl+A and
BackSpace select and delete actors (once, the Landscape). A `Cmd: DELETE` or `Cmd: ACTOR DELETE` log line fails the
run at once: type `TRANSACTION UNDO` directly into Cmd, and do not save. When Play state is uncertain, use a direct
`Type`.
The helper watches only new log lines and ignores command echoes.
It reports `submitted`, `started`, `completed`, `failed` or `not-submitted`. Missing acknowledgment fails after eight seconds.
`not-submitted` means execution is unknown, not permission to repeat an action.
The operation timeout starts at acknowledgment. Completion without a start marker fails.
Write the start marker on the script's first line, before imports or asset work. A script that runs more than 8 s
before the marker reports `not-submitted` although it runs. Then read the log for the completion marker. Do not submit
again.

The helper is `~/Github/agent-skills/unreal-editor-loop/run_command.py`. It uses the existing local MCP endpoint without changing configuration.
It requires one editor process. Supply distinct markers per run. It never saves assets or changes CPU settings.
Use direct `Type` for `QUIT_EDITOR`, never the runner or a ProgrammaticToolset script.
It changes Git Bash paths (`/c/...`, `~/...`) in the command to Windows paths.
It refuses a second command while one runs on the same editor (lock file per port).
A script can block the game thread longer than the 15 s MCP timeout. Then the `Type` answer comes late:
the runner reports `submitted` and watches the log.
Run a long command with `run_in_background`, never with `nohup` or `&`: a detached runner dies without a report.
For `Automation RunTests <filter>` (UE 5.8), use the markers `Ready to start automation` and `Automation Test Queue Empty`.
The `Found N automation tests` line comes about 6 s later, so it can miss the 8 s start limit.

Run helper tests with `python -X utf8 -I -B -m unittest discover -s ~/Github/agent-skills/unreal-editor-loop/tests -v`.
Mocks test state transitions, not keyboard routing. Check the actual PIE capture path after changing submission logic.

## 2. Compile

| Change | Do |
| --- | --- |
| `.cpp` only | Type `LiveCoding.Compile` (works during Play), then `UE live-result` |
| Header, `UCLASS`/`USTRUCT`/`UPROPERTY`/`UFUNCTION`, new file, `Build.cs`, plugin | Full build |

- Live Coding keeps the old value of a changed global or `static const`: rename it, or do a full build.
- An external build fails while Live Coding is active in the open editor.

Full build:
1. Type `QUIT_EDITOR`. The MCP call hangs, then fails when the editor closes: expected.
2. `UE running` must exit 1. If the editor asks to save, ask the user. Never kill it with unsaved work.
3. `UE build` (10 min timeout). Read `Result: Succeeded`. Fix errors and build again.
4. `UE launch [/Game/Map]`, then `UE wait-mcp` in the background, then step 1.2 (Observe, Snapshot).
5. Rerun the editor scripts that write changed properties. A new `UPROPERTY` keeps its C++ default on existing
   Blueprints until a script or a person sets it.

## 3. Play and see it

- Start Play: `py "~/Github/agent-skills/unreal-editor-loop/pie_start.py"` (expand `~` to an absolute path), then
  `UE wait-log 'Play in editor total start time'`. Stop Play with `pie_stop.py` (same folder). Stop Play before a
  script changes a Blueprint: a running Play keeps the old values.
- A script that changes a Blueprint CDO must call `unreal.BlueprintEditorLibrary.compile_blueprint(bp)`, or Play
  keeps the old value. Save assets on purpose and say which ones.
- Prove a visual change with a picture: a viewport screenshot that you read. For animation and poses, build or use
  the lab of the `unreal-anim-lab` skill.
- Background editor ≈ 3 FPS ("Use Less CPU when in Background", log: "max tick rate 3"). Turn it off with
  `ConfigSettingsToolset.SetSectionProperties` (container `Editor`, category `General`, section
  `EditorPerformanceSettings`, `{"bThrottleCPUWhenNotForeground": false}`). It works at once (measured 3 to 59 FPS).
  The console `set` command and Python do not change it.
- The user may be using the editor too. Batch commands in one script instead of many `Type` calls.

### GUI checks

1. List each changed control and its observable result before implementation.
2. Select the editor window. Release Play mouse capture before UI inspection. Obtain current widget refs before clicking.
3. Click each changed control through the real mouse path. Assert its effect on game state.
   A successful Slate `Click` response proves event dispatch, not the intended effect. A screenshot alone does not prove behavior.
4. Test unavailable states. Show a reason instead of leaving a control enabled without an effect.
5. Check input leakage and UI cleanup after disable and Play restart. Panel clicks must not fire or turn the pawn.
6. Keep passing checks when a different control or probe fails. Repeat only the affected checks.

Before promoting a mouse helper, test it with a known scaled-geometry fixture.
Convert snapshot positions and sizes to one coordinate space before comparing them.
The installed Slate inspector reports desktop positions but local widget sizes. Do not add these values without conversion.
Keep a one-task probe local until a second task needs it.

## 4. Rules

- Commit before a large asset change: assets are binary. Close an asset before you restore it with git.
- Git LFS lockable assets become read-only after checkout: `git config lfs.setlockablereadonly false`.
- A tag or property set on a level instance of a component that a Blueprint construction script adds does not stay:
  the script makes the component again. Python cannot tell those components apart (`creation_method` is not exposed).
  Put per-mesh data on the mesh asset (for example a physical material on its body setup) or on the Blueprint template.
- Python cannot read some protected struct fields (for example `PhysicalSurfaceName.Name`). Read the value from
  `Config/Default*.ini`.
- A mesh loaded in an automation test world can have no collision. Call `GetBodySetup()->CreatePhysicsMeshes()` and
  `RecreatePhysicsState()`, and assert that the expected hit happened: without the assert the test passes on a miss.
- A failed engine call in a script can open a modal dialog that freezes the editor (the log stays on one frame
  number). Find it by the visible window titles of the editor process (Win32 `EnumWindows`), then ask the user to
  close it. Never take a desktop screenshot: it captures the user's other windows.
- To empty a data table, remove its rows by name. `fill_data_table_from_json_string(t, "[]")` fails and opens a dialog.
- `rename_asset` from a script cancels on the "source code may reference" prompt. Duplicate to the new path, save,
  then delete the old asset when it has no referencers.
- After a script saves assets, call `AssetRegistry.scan_paths_synchronous(paths, True)` before you read referencers:
  without it, removed references still show.
- Python sees only `UFUNCTION` and `UPROPERTY` members. Do not use `hasattr` as a fallback in a probe: a missing
  getter then looks like a game failure. Check the getter is a `UFUNCTION`, or read the data another way.
- Report what you compiled, how (Live Coding or full build), and the log line that proves it ran.
