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
