---
name: street-view-reference
description: Reopens Street View links and saves stills from local media in the browser. Use for repeatable art references without a Maps API key, or with /street-view-reference.
---

# Street View reference

Use one selected view at a time. A **view bookmark** reopens a place in Google Maps. A **still** comes from a separate file the user owns or can reuse. A bookmark beside a still is a comparison, not evidence that both cameras occupied the same spot.

## Browser workflow

1. Open `~/Github/agent-skills/street-view-reference/reference.html` as a local file in the user's browser. On Windows, use `Start-Process` with its resolved absolute path. No server, extension, key, or sign-in is necessary for the local tool.
2. Enter the exact Maps link the user supplied, or load their `.url` bookmark. Use **Open live view**. If browser controls are available, operate the new tab rather than asking the user to click. Leave unrelated tabs alone.
3. Use the normal Maps controls to change the framing. Select **Share → Copy link**. You can also use the visible Maps address if it shows the current camera. Put that link in the local tool. Use **Save view bookmark**. Reopen it to check the framing. If the camera does not load, report that. Do not substitute another location.
4. Keep a short link unchanged. Do not try to decode it offline. Google documents `pano`, `viewpoint`, `heading`, `pitch`, and `fov` for its `api=1` links. Native browser links can contain other fields. Preserve the entire link rather than rebuilding it from a coordinate and heading. Imagery can change. An old bookmark is not a permanent image.
5. To collect pixels, select an eligible **local file**, not the Maps tab. For a user-selected online photo that permits reuse, use its publisher's normal download in the browser first. Keep the file in a new local folder. Record its source and credit. Never use a Street View screenshot or tile as that input.
6. For a video, pause on a frame, or enter seconds and select **Seek**. For an owned 2:1 equirectangular photo, select **Frame a 360 photo**. Set yaw, pitch, and horizontal field of view. Yaw is relative to the middle of that image, not geographic north.
7. Select **Prepare still**. Save the **PNG** and the **frame record**. The record identifies the source filename, size, source dimensions, and time or camera angles. The optional Maps link stays separate from those measurements. Use distinct output names or directories for different shots. Keep private links, files, and records outside version control.
8. Read the saved PNG. Check the time or angles against the record. Report which views you only opened and which images you actually saved. Never report a bookmark as a captured image.

The helper reads only the chosen files. It has no remote image input, telemetry, map crawler, or desktop capture. It does not call an imagery API.

To repeat a still, select the same file and enter the settings in the record. A video time is the browser's playback position, not an exact frame index. The PNG keeps the full photo framing. For large photos, the helper limits the longest side to 4096 pixels. A 360 export is a 960 × 540 perspective view.

Google permits live links and does not permit separate Street View screenshots or offline image copies. This also applies to study. If the user needs a local image of a material or shape, prefer their original image or a reusable substitute. Do not build a real-site photo survey from panorama links. Keep art observations separate from measured dimensions.

Sources: [Google Maps URLs](https://developers.google.com/maps/documentation/urls/get-started#street-view-action), [Google Geo Guidelines](https://about.google/brand-resource-center/products-and-services/geo-guidelines/#street-view), [browser PNG export](https://developer.mozilla.org/en-US/docs/Web/API/HTMLCanvasElement/toBlob).
