# Cutting-mat calibration

Use this when a part must fit an object of free shape (a helmet, a bike
frame, a pipe). It gives the object's section at a given height, in mm.
A card gives one plane. A mat under the object gives the mat plane in every
photo and, with 3 or more photos, a camera pose per photo. Measured on the
chin mount (2026-11-08): leave-one-out 0.32-0.54 mm per photo, reprojection
3.5-4 px (about 0.16 mm) on one calibration of 3 photos.

```bash
M() { uv run --quiet --with numpy --with opencv-python-headless --with pillow \
      python ~/Github/agent-skills/photo-measure/mat_calib.py "$@"; }
```

## Photos to ask for

> Put <the object> on a cutting mat with a 1 cm grid, with grid lines visible
> on all sides of it. Use the main camera at 2x, from about 30-50 cm.
> 1. One photo from above, a bit to the left.
> 2. One photo from above, a bit to the right (move the phone about 20 cm,
>    do not only turn it).
> 3. One low photo from the corner, at about 30-45 degrees to the mat.
> 4. One photo from the side, low, along the surface you want measured.

Two photos taken from the same spot cannot triangulate: the rays are almost
parallel. `calib` prints the angle between each pair of views and marks a pair
under 10 degrees. A side photo with only a few grid lines in view cannot be
calibrated. Use it for shape only.

## Steps

1. `M lines photo.jpg --out /scratch/l1.png`. Read the overlay. The default
   mask is for a green mat (`--hue 40,110`). If lines are missing, lower
   `--rt` (6-7 worked on darker photos). If noise shows, raise it.
2. Read 4 rough grid crossings on a `photo_measure.py grid` crop. Give them
   in mat mm (count the cm lines from a corner you chose as the origin):
   `[[[300, 0], [954, 2070]], ...]`.
3. `M grid /scratch/l1.json --rough r1.json --out p1.json`. Accept the photo
   when the leave-one-out maximum is under about 0.5 mm.
4. `M calib p1.json p2.json p3.json --size 4000,3000 --out camera.json` (the
   EXIF-rotated photo size). All photos must come from the same phone camera
   and zoom.
5. Measure:
   - A contact line on the mat (the object's foot): `M plane camera.json
     --view 0 --pt u,v`. Map it from 2 photos. If they agree within about
     0.5 mm, the points are on the mat.
   - An edge above the mat: `M tri camera.json --view 0 --pt u,v --view 2
     --pt u,v`. A ray miss above about 1 mm means the 2 pixels are not the
     same physical point. Use sharp features (a decal corner, a trim end),
     not a smooth edge.
   - An edge at a known height: `M plane ... --z H`.
6. Save `p*.json`, `camera.json` and the curves in the user's project.

## Pitfalls (each one cost a print or more on the chin mount)

- **A silhouette is not a section.** The outline seen from above or below is
  the widest part of the object at any height. The chin bar silhouette was
  6-7 mm wider at the corners than the section at the 25 mm mount height.
  Measure at the height of the part.
- **A guessed curve reads as a measurement later.** If a section is an
  allowance (outline + 1 mm), name it so in the code and the notes. Check
  it first when a test print shows a gap.
- **Fix the frame from a fit you trust.** The mat frame and the model frame
  differ by a shift. Get the shift from a section that already fits on a
  test print. Do not assume it: an assumed frame gave a wrong 1 mm side
  error.
- **A tangent view gives the envelope.** A low photo along a side shows the
  outermost line of the surface there. This bounds the surface on one side
  only.
