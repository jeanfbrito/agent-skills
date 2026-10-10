# Sense guide: Godot

- **Control and probe:** an autoload that runs only with a command-line flag.
  It reads a JSON script of actions (load, set camera, inject input, wait N
  physics frames) and writes JSON results. An MCP or TCP debug server can do
  the same in a running session that the agent started itself.
- **Logic and metrics:** run `--headless` with `--fixed-fps` so that physics
  and animation numbers repeat.
- **Self-capture:** the dummy renderer in `--headless` gives no real image. For
  a visual check, use the real renderer in a no-focus window and read
  `get_viewport().get_texture().get_image()`, or use `--write-movie`. Put the
  frame number in the file name or metadata.

## Traps seen in real sessions (2026-10)

- **A real-window capture script** (cozy-farm `tools/shot.gd`): run
  `SHOTS=<dir> godot --quit-after 900000 --path . -s tools/shot.gd -- <views>`.
  The script loads the main scene, waits, sets each named view, awaits
  `RenderingServer.frame_post_draw`, then saves
  `root.get_texture().get_image()` to `$SHOTS/<view>.png`.
- **Headless sims and the player's save:** a sim that writes `user://` can
  overwrite the real save. Keep sims from saving, or delete the test save
  before and after the run.
- **Find the right binary first:** `defaults read
  /Applications/Godot.app/Contents/Info.plist CFBundleShortVersionString`
  must match `config/features` in `project.godot`.
