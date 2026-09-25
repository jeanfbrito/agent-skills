---
name: mixamo-download
description: Searches Mixamo and downloads animation clips (FBX, no skin, 30 fps, no keyframe reduction) through the user's logged-in Mixamo session in Chrome, using the Mixamo web app's own API from the page, then hands the files to the project's import step. Use when a game or animation project needs mocap clips from Mixamo. Triggered by "download from Mixamo", "get the Mixamo animations", "grab crouch/sprint/strafe clips", "download these animations for me", "mixamo".
---

# Mixamo download

Fetch Mixamo clips without the user clicking through the site: search,
pick a coherent set, export on the selected character, download, file into
the project.

## Requirements and safety

- Needs the **Claude in Chrome** tools and the user **already logged in** to
  mixamo.com in that Chrome. Never type credentials; if the page has no
  session (`localStorage.access_token` missing), ask the user to log in and
  wait.
- **Downloading needs explicit approval.** Before any export, show the
  exact clip list (description, count, character, settings, destination)
  and wait for a clear yes. One approval covers that list only.
- Downloads go through Chrome. If Chrome's **"Ask where to save each file
  before downloading"** is on (chrome://settings/downloads), every clip
  opens a Save dialog; ask the user to switch it off for the run (never
  change browser settings yourself). Chrome may also ask once to allow
  "download multiple files"; the user answers that too.
- The export link is a signed URL. The browser tool blocks returning it
  (query-string data), so it cannot be handed to `curl`; do not encode or
  smuggle it out. Trigger the download inside the page instead.
- Load the browser tools in one `ToolSearch` call (tabs_context_mcp,
  tabs_create_mcp, tabs_close_mcp, navigate, computer, javascript_tool),
  start a new tab, and close it when done.

## Helper

`~/Github/agent-skills/mixamo-download/mixamo-api.js` defines
`window.mixamo` in the page. `Read` it and run the whole file with
`javascript_tool` after the page loads (again after any reload). Functions:

| Call | Returns |
|---|---|
| `await mixamo.character()` | `{id, name}` of the selected rig; exports retarget onto it |
| `await mixamo.search("rifle crouch")` | `{total, items:[{i, id, name, description}]}` |
| `await mixamo.startExport(id, charId)` | queues one export; optional 3rd arg overrides preferences |
| `await mixamo.status(charId)` | `{status, job_result}`; `job_result` is the file URL when `completed` |
| `await mixamo.download(url, "name.fbx")` | saves to the browser's download folder |

Default preferences: `format "fbx7"` (FBX binary), `skin "false"`,
`fps "30"`, `reducekf "0"`. Root motion is kept (the product's
`inplace` flag stays false) so clip speed can be measured.

## Workflow

1. **Open Mixamo.** New tab, navigate to `https://www.mixamo.com/#/`, run
   the helper, call `mixamo.character()`. Confirm the character is the rig
   the project uses (e.g. Y Bot). If not, ask the user to select it in the
   UI; a different rig changes proportions and the retargeted clip.
2. **Search.** Return only index + description (names repeat). Try a couple
   of queries if the first is thin ("rifle crouch", "crouched walk rifle").
   Page 2 exists when `total > 96`.
3. **Pick a coherent set.** Prefer one family whose descriptions share a
   pattern (e.g. "Rifle Crouched Walk Forward / Backward / Left / Right /
   Forward Left..." plus "Rifle Crouched Idle"). One family keeps posture,
   speed and style consistent inside a blend space. Skip deaths,
   transitions and duplicates unless asked.
4. **Ask for approval** with the list: description → planned filename,
   character, settings, and where the files will land.
5. **Export sequentially, one clip per call.** `startExport`, poll
   `status` every ~2 s until `completed` with a `job_uuid` different from
   the previous clip's (the monitor keeps returning the last job), then
   `download(job_result, filename)` inside the page. Mixamo rate-limits
   exports: three back-to-back gave `429` (2026-09-24), so wait ~20 s
   between clips and ~60 s after a 429. Stop on `failed`; retry once.
   Downloads keep the server name (the product name, which repeats across
   variants), so set a timestamp marker before each clip and take the
   first `.fbx` newer than it.
6. **Collect.** List `~/Downloads` by modification time and match the new
   files. Filenames: snake_case from the description
   (`rifle_crouched_walk_left.fbx`). Copy into the project's clip folder.
   Leave the originals in Downloads unless the user asks to remove them.
7. **Hand off to the project's import step.** Follow the project's own
   instructions (AGENTS.md or its docs), e.g. a headless engine import,
   then measure each clip before wiring it in.

## Known Mixamo data quirks (observed 2026-09-24)

- Some FBX files hold an empty **`Take 001`** beside the real
  **`mixamo_com`** animation. Load `mixamo_com` explicitly.
- **Turn-in-place** clips can arrive with the hip rotation removed: only the
  stepping feet remain, and the game's body yaw must supply the turn.
- **Start/stop** clips take 1.5-2.7 s to change speed. Too slow for a
  responsive player unless animation drives movement.
- Sprint packs can be athletic (8-way set at 6.96 m/s; crouch set 1.97).
  Check a clip's root speed by driving the engine's runtime body at that
  speed and measuring planted-toe slide (2-5% of speed = consistent).
  Seeking poses outside the running scene can silently return the rest pose.
- 30 fps data makes running foot contacts 1-2 frames long; label contacts
  from toe velocity at the engine's rate, not raw keys.

## If the API has changed

The endpoints are the web app's internal ones and can change without
notice. On an error: ask the user to click Download once in the UI while
you run `read_network_requests` on the tab, compare the export POST body
and monitor call with `mixamo-api.js`, update the helper, and say what
changed. Never fall back to guessing credentials or scraping other sites.

## Report

List what was downloaded (description → file → project path), anything
skipped or failed, and the handoff status. Close the tab you opened.
