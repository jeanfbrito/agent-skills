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
3. Play has the focus and Enter does not submit: `Click` the box, `PressKey` Ctrl+A, `PressKey` BackSpace, `Type`.
4. `py "<path>.py" args`: always an **absolute path**. A relative path resolves against the process folder
   (`Engine/Binaries/Win64` after `UE launch`) and fails with "Could not load Python file".
5. No nested quotes inside one command. Send a second `Type`.
6. `Type` returns at once. Read the effect from the log: every script logs a unique prefix (`unreal.log("MYTAG: ...")`),
   then `UE wait-log 'MYTAG|LogPython: Error' [s]` (new lines only) or `UE log 'MYTAG' 20`.
   Run `wait-log` in the background when it can take more than a minute.
7. The sandbox of `execute_tool_script` only has `json`, `math`, `re`, `time`, `copy`, `datetime`: real work goes in
   a `.py` file run with `py`.

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
- Background editor ≈ 3 FPS ("Use Less CPU when in Background"). Frame waits are slow, not broken.
- The user may be using the editor too. Batch commands in one script instead of many `Type` calls.

## 4. Rules

- Commit before a large asset change: assets are binary. Close an asset before you restore it with git.
- Git LFS lockable assets become read-only after checkout: `git config lfs.setlockablereadonly false`.
- Report what you compiled, how (Live Coding or full build), and the log line that proves it ran.
