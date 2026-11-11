---
name: freecad-photo-reference
description: Adds reference photos to a FreeCAD model as Image::ImagePlane objects with a scale and anchor calibration (top, bottom with mirroring, front), reads a user's marked screenshot of the model in millimetres by calibrating it from model features, and exports model outlines and candidate shapes as overlays for photos of a test print. Use when a part must fit a real object known only from photos (helmet, bike frame, bracket), or when the user draws arrows or lines on a CAD screenshot. To measure sizes in photos, use photo-measure. Triggered by "add the photos as reference", "put my photos in the model", "overlay the photo", "it should follow this line", "look at my screenshot", "make it match the photo".
---

# FreeCAD photo reference

Two tools:

- `photo_ref.py` runs inside FreeCAD and places photos as image planes.
- `screenshot_mm.py` runs in a normal shell and turns marks on a screenshot
  into model millimetres and angles.

## Place photos in the model

```python
import os
exec(open(os.path.expanduser("~/Github/agent-skills/freecad-photo-reference/photo_ref.py")).read())
add_photo(doc, "/abs/down.jpg", "bottom", mm_per_px=18/206,
          anchor_px=(1241, 988), anchor_mm=(0, 18.2), offset=-0.5, name="PhotoDown")
add_photo(doc, "/abs/front.jpg", "front", mm_per_px=117/680,
          anchor_px=(720, 1560), anchor_mm=(0, 0), offset=60, name="PhotoFront")
```

1. Look at each photo first (`Read`). Name the camera direction and the
   feature you will anchor on.
2. Choose the `view`:
   - `top`: the camera looked down from above.
   - `bottom`: the camera looked up from below. The helper turns the plane
     180° about X. This mirrors the photo, so the Top view shows it the
     right way round.
   - `front`: the camera looked from the -Y side. The plane stands in XZ.
3. Calibrate: set `mm_per_px` from one length that you know (mm divided by
   pixels in the original image). Set `anchor_px` to a pixel you can find
   again, and `anchor_mm` to its model position.
4. Put the calibration in a `PHOTOS` list in the project script that builds
   the model, so a rebuild adds the planes again. The planes need the GUI:
   skip them when `App.GuiUp` is false.
5. Render the Top and Front views with `freecad-render-check` and check
   which way the photo faces.

**Say that the scale is a guess** until a size reference calibrates it.
Perspective also makes far features smaller, so one scale fits only one
depth in the photo. Ask for photos with the marker card of the
`photo-measure` skill (its step 1), on the plane that you care about.

## Read a marked screenshot

The user often draws arrows on a screenshot of the model over the photo.
The model in that screenshot gives the scale, so read the marks in mm. Do
not ask for a new measurement.

```bash
S=~/Github/agent-skills/freecad-photo-reference/screenshot_mm.py
$S grid shot.png --out /scratch/shot_grid.png           # then Read it
$S convert --origin 706,491 --known 190,1040,1222,1040,100.4 \
   --line 40,1070,230,790 --line 1375,1025,1165,760 --at-y 40
```

1. Draw the grid and `Read` it to get the pixel positions of the marks.
2. Find two calibration features in the screenshot: the origin dot (model
   0,0) and one known model length, for example the overall width from the
   bbox.
3. Convert the marks. Each line gives its ends in mm, its angle from the
   fore-aft axis (Y), and with `--at-y` its X at a given depth.
4. Check the sign convention. Screen +y points down. Use `--flip-y` for a
   Top view and `--flip-x` for a mirrored view.
5. Map the result to the model parameters, rebuild, and render the same
   view over the photo. Compare it with the user's marks before you report.

## Read photos of a test print on the object

Measure with the `photo-measure` skill
(`~/Github/agent-skills/photo-measure/SKILL.md`). The print is the size
reference. This skill adds the FreeCAD parts:

1. Get the reference points from the vertices of the end face (the snippet
   is in photo-measure, step 3).
2. Export the current outline as `lines.json` for `fit --overlay`:
   `{"now": [[p.x, p.y] for p in wire.discretize(Distance=0.5)]}`.
3. Export candidate shapes the same way, for example 3 corner radii with
   the contact points fixed. Pick the candidate that follows the object on
   2 photos.
4. When the photos cannot settle the value, build thin test slices
   (gauges) of the candidates and ask the user to try them.

## Rules

- A part that you extrude straight up must clear the **widest** section of
  the object inside its height. In a photo from below, that is the outer
  silhouette, not the nearest rim.
- Report each value as measured on the photo, or as a guess, in the same
  sentence.
- Keep the photos in the user's project folder, and reference them by
  absolute path.
