# Sense guide: desktop app (Electron, native)

- **Control and probe:** a dev-only command-line flag, IPC channel or local
  socket that accepts the same small actions and returns JSON. Electron can
  also expose `window.__agent` in the renderer.
- **Electron without a renderer debugger:** start the app with `--inspect` and
  use `Runtime.evaluate` in the main process. With
  `process.mainModule.require('electron')` it can click menus, run
  `webContents.executeJavaScript()` and call `capturePage()`.
- **Self-capture:** Electron `webContents.capturePage()` captures one window
  with no screen grab. On macOS it returns old frames for an occluded window,
  so make sure the window paints first, and read the DOM for state.
  On macOS, `screencapture -x -o -l <window-id>` captures one window
  without focus. On Linux, run the app on Xvfb and capture the
  virtual screen. On Windows, use a window-capture API (`PrintWindow`), not a
  full-desktop grab.
- Capture the app window only. A full-desktop screenshot adds noise and can
  show the user's private data.
