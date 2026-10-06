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
