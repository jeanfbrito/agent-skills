---
name: photo-measure
description: Measures real objects in photos in millimetres. It makes a printable marker card and asks the user for photos with a size reference in the plane of the feature (the card, a test print of known geometry, a bank card, an A4 sheet). It finds the reference points (marker corners automatically, or points read on grid crops), fits a homography with a leave-one-out check, and converts photo pixels to positions, lengths and circle radii in mm with their error. Use before you estimate any size from a photo with no scale, when a part must fit an object known only from photos, or when the user sends photos of a test print on the object. Triggered by "measure this from the photo", "how big is this", "I have no calipers", "get the size from the pictures", "what size reference do you need", "here is the print on the helmet", "the photos show the adjustments needed", "it does not fit here".
---

# Photo measure

A photo has no scale. Put a size reference in the same plane as the feature.
Then `photo_measure.py` maps photo pixels to millimetres on that plane with a
homography (a perspective map). Lengths, positions and radii on that plane
then come out in mm.

```bash
F() { uv run --quiet --with numpy --with opencv-python-headless --with pillow \
      python ~/Github/agent-skills/photo-measure/photo_measure.py "$@"; }
```

## 1. Ask for a size reference first

Ask before you estimate a size from a photo that has no reference. Without a
reference, a photo gives shapes and ratios only. Tell the user that.

Make the marker sheet in the user's project:
`F target --out <project>/measure_card.pdf` (`--paper letter` for US Letter).
Then send this request. Change the parts in angle brackets.

> To measure from photos, I need a size reference in each photo, on the same
> surface as <the feature>.
> 1. Print `<project>/measure_card.pdf` at 100 % ("Actual size", not "Fit to page").
> 2. Measure the long bar with a ruler. If the bar is not 100 mm, tell me its length.
> 3. Cut out one card. Tape it flat on <the surface>, next to <the feature>.
> 4. Take the photo straight at the card, from about 50 cm, with 2x zoom.
>    Keep the 4 black squares and <the feature> in the frame.
> 5. Take a second photo from a different angle.
>
> No printer: put a bank card or a sheet of A4 paper flat on the same surface.

If a test print of known geometry already sits on the object, the print is
the reference. Then do not ask for the card.

## 2. Choose the reference

| Reference | Points | Notes |
| --- | --- | --- |
| Marker card (`target`) | 16, found by `detect` | Best. Card A and card B can be in one photo. |
| Test print of known geometry | Corners of one flat face, from the CAD model | Best for a fit check: it sits at the feature. |
| Bank card, ISO ID-1 | 4 corners, 85.60 x 53.98 mm | Rounded corners (R3.18): use `intersect`. |
| A4 or Letter sheet | 4 corners, 210 x 297 or 215.9 x 279.4 mm | It must lie flat. |
| Ruler | Points on one line | No homography. It gives a scale only for a length along the ruler, at the same depth. |

Do not use a coin or a "typical" object size. Use one only when the user
gives its exact size.

## 3. Get the reference points

- **Marker card**: `F detect photo.jpg --out /scratch/p` writes
  `p_card0.json` (card A) and `p_card1.json` (card B). Read `p_markers.png`
  and make sure that each square shows its id. When the bar measured 98.5 mm,
  add `--card-scale 0.985`.
- **Other references**: draw grids and Read them:
  `F grid photo.jpg --out /scratch/g.png --crop x0,y0,x1,y1 --step 20 --scale 2`.
  Write `pairs.json` by hand: `[[[x_mm, y_mm], [u_px, v_px], "name"], ...]`.
  The pixels are in the EXIF-rotated photo, as the grid labels show them.

Rules for the points:

1. Put all points on one plane: the plane that you measure on.
2. Use 6 or more points, spread around the feature. The map is good inside
   the points and poor outside them. Do not measure outside their area.
3. Use sharp corners. Do not read a point on a rounded edge. For a rounded
   corner, read 2 points on each straight edge and write
   `{"intersect": [[u1,v1],[u2,v2],[u3,v3],[u4,v4]]}` as the pixel.
4. Read at 2x zoom with a 20 px grid. Expect about 2 px of reading error.

### Points from a CAD part (test print)

The CAD model gives exact positions on the face that the camera sees. For an
extrusion, that face is the end face. In FreeCAD:

```python
f = min(part.Shape.Faces, key=lambda f: f.CenterOfMass.z)   # end face at the bed
for v in f.Vertexes: print(round(v.X, 2), round(v.Y, 2))
```

Choose tips, notch corners and rail corners that you can see in the photo.
On a symmetric part, use points on the two sides.

Use only **rigid** features: feet, pockets, rail ends. A thin flexible part
(a wing tip, a knee) bends onto the object and is not where the CAD model
puts it. With such points the leave-one-out error was 8-10 mm. Without
them, it was 1-2.5 mm.

## 4. Fit and check

```bash
F fit photo.jpg --pairs pairs.json --overlay lines.json --out /scratch/o.png --scale 0.5
```

- The **leave-one-out** error is the check. The tool predicts each point
  from the other points. Accept the fit when the maximum is less than about
  1 mm. The fit error alone looks better than the truth, and with 4 points it
  is always 0.
- One point with a large error: read it again. All points with large errors:
  the points are not on one plane, or the lens bends the photo. Then ask for
  a photo from the main camera, not the wide camera.
- Draw known geometry over the photo (`lines.json` in mm, `--mirror-x` for a
  half profile). It must lie on the photo.

## 5. Measure

Read the feature points with `grid`. Then:

```bash
F measure --pairs pairs.json --pt A=u,v --pt B=u,v --dist A,B \
  --pt C1=u,v --pt C2=u,v --pt C3=u,v --pt C4=u,v --circle C1,C2,C3,C4
```

- `--dist` gives a length. `--circle` gives the centre, R, and the R spread
  for 1.5 px of reading noise (`--noise`).
- A photo fixes a corner radius badly. On a corner that turns 56°, a radius
  change of 8 mm moves the middle of the arc by only 1.1 mm. Put the circle
  points across the full arc. If the R spread is larger than the choice that
  you must make, print thin test gauges around the value.

## 5b. Object on a cutting mat (3D, several photos)

When the object stands on a cutting mat, the mat grid is the reference. It
gives tens of points per photo. One camera calibration for all photos gives
each camera's pose. Then pixels map to the mat at any height, and `tri` gives
the 3D point of a feature that 2 photos show. Use it to measure a section of the object at
a given height. Procedure, photo requests and pitfalls:
`~/Github/agent-skills/photo-measure/references/mat-calibration.md`
(tool: `~/Github/agent-skills/photo-measure/mat_calib.py`).

## 6. Depth error

The map gives true values only on the reference plane. A point that is a distance d
in front of or behind the plane moves by about r·d/D. Here r is its distance
from the photo centre (measured on the plane), and D is the camera distance.
For r = 50 mm, d = 10 mm and D = 300 mm, the error is 1.7 mm. At
D = 600 mm (2x zoom), the error drops to 0.8 mm.

- Put the reference on the plane of the feature.
- A surface that you see through a gap is behind the plane. Do not measure it
  as a point on the plane.
- A line the user draws on a photo can follow an edge that is not on the
  plane (a seam that rises up the object). Before you measure a gap against
  it, find which physical edge it follows. Check the gap against a second
  source (another photo, a mat measurement) in one common frame.
- Measure on 2 photos from different angles. If the 2 values do not agree,
  the point is not on the plane.
- A photo from closer than about 15 cm has depth errors larger than most fit
  gaps. Do not judge contact or gaps from it. Ask for the gap at each named
  point, measured with feelers (drill bits, hex keys, sheets of paper). Or
  ask for a new photo from about 50 cm.

## Report

- Give each value with its source: measured on the photo, the leave-one-out
  error, and the plane. Say when a point is off the plane, and give the depth
  error.
- Save the photos and `pairs.json` in the user's project. The next round then
  uses the same calibration.
