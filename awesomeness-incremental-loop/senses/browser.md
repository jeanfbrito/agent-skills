# Sense guide: browser app or game (for example Three.js)

- **Control and probe:** expose one object in dev builds, for example
  `window.__agent`, with functions such as `state()`, `step(n)`, `seed(n)`,
  `pause()`, `camera(name)`, `load(scene)`, `metrics()` and `shot(name)`.
  Each function returns small JSON. Call it from the browser automation tool
  or from a Playwright script.
- **Logs:** prefix every agent log with a tag, for example `[agent]`. Read the
  console with a filter on that tag, not the full console.
- **Self-capture:** render one frame, then read the canvas
  (`renderer.domElement.toDataURL()` after a render call, or
  `preserveDrawingBuffer: true` in dev builds). A headless Playwright script
  can save the PNG without opening a visible window. Set the viewport size so
  that all shots have the same size.
- **Time:** drive the update loop from `step(n)` with a fixed delta. Do not
  depend on `requestAnimationFrame` timing for measurements.

## Traps seen in real sessions (2026-10)

- **A browser tab that is not in front pauses `requestAnimationFrame`.** A
  game in a Chrome tab driven by an extension stops updating, so its shots
  freeze (excitebike, 2026-10-04). Use a headless Playwright or
  puppeteer-core script for timed runs.
- **Headless Chrome needs its own profile.** Launching the installed Chrome
  with the default profile clashes with the open browser. Pass a new
  `--user-data-dir` in the scratchpad (grass, 2026-10-09).
- **GPU WebGL in headless Chrome on macOS:** the grass benchmarks launched
  `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome` through
  `puppeteer-core` with `headless: 'new'`, `--use-angle=metal` and
  `--ignore-gpu-blocklist`. Without a GPU flag, Chrome can fall back to a
  software renderer, which makes timings meaningless.
- **Wait for a ready flag, not for a delay.** Set `window.__rendered = true`
  after the first full render, and wait for it with
  `page.waitForFunction('window.__rendered === true')`.
- **Collect `pageerror` and console errors** in the same script. A blank
  canvas with a shader compile error looks like a slow load.
