---
name: fit-to-object
description: Runs the test-print loop for a 3D-printed part that must fit a real object of free shape (helmet, handlebar, bike frame, dashboard) - measures the object at the part's own height, keeps every shape input labelled measured or guessed, models the contact faces as lofted sections with a tape or clearance gap, backs up each print, reads the user's photos and reports of the print on the object, refits only the measured misfit, and records each round. Use when a user prints a part, puts it on the object and reports or photographs the fit. Triggered by "here is the print on the helmet", "it does not touch here", "there is a gap", "the tape does not stick", "it fits better now", "make it follow the shape", "what is the newest to print", "print N".
---

# Fit to object

A part that fits a free-shape object takes several prints. Each print is a
measurement. Three things break the loop. You carry a guess as a
measurement. You read a photo past its accuracy. You overwrite an old print.

Related skills (the `freecad-*` skills live in the `freecad-skills` repo):
- `photo-measure`: sizes from photos, the cutting-mat method for sections.
- `freecad-mcp-modeling`: script structure and OpenCascade failure recipes.
- `freecad-render-check`: solid and STL checks before every hand-over.

## 1. Measure the object where the part sits

- Measure the section **at the part's height**: one at its bottom edge, one
  at its top edge. A silhouette from above or below is the widest line at
  any height. On the chin mount it was 6-7 mm too wide (prints 1-3).
- Best source: the object on a cutting mat, 3-4 photos
  (`~/Github/agent-skills/photo-measure/references/mat-calibration.md`).
- With a test print on the object: feelers at named points (drill bits,
  hex keys, paper sheets) give the gap in mm. A photo from closer than
  about 15 cm cannot show a 1-2 mm gap.
- Copy an interface from a part that fits, when the user has one. Measure the section of that part's STL (trimesh `section`). Do not
  use generic dimensions. Generic GoPro buckle sizes were 0.1-0.6 mm loose.
  The user's Airoh STL had no play.

## 2. Keep an input inventory

Before each fit round, write the list of shape inputs and the source of each:

| Input | Source | Value |
| --- | --- | --- |
| bottom section | measured: mat photos, rms 0.12 mm | 54.7 / 35 deg / R36.8 |
| top section | **guess**: outline + 1 mm | ... |

Put the source next to the value in the script (a comment or a `source=`
field). When a print shows a misfit, check the guessed inputs first. On the
chin mount, a guessed top section stayed in 3 prints and caused a 5-7 mm gap.
The build must refuse to write an STL from unmeasured data unless the user
asks for a print from estimates (`MEASURED = None` gives a check-only build).

## 3. Model the contact faces

- One section function that always gives the same number of edges in the
  same order (front line, corner arcs, side curves). Join the bottom and top
  sections with a ruled loft. The loft pairs edges by index.
- The contact face is an exact offset of the section by the gap: tape
  thickness minus squeeze (1.0 mm foam tape: 0.8 mm). No preload on a taped
  part: a squeeze loads the tape in peel.
- To make a part conform, make it thin along its full length. Bending
  stiffness grows with t cubed. A 6 to 3 mm wing: about 85 N per mm of tip
  bend. A 1.6 mm wing (2 lines of a 0.6 nozzle) from 6 mm past the root:
  about 5 N. A straight taper to a thin tip: 53 N, so it does not help.
- Pick the print orientation for the face that must stay whole. If an
  interface is symmetric, the part can print upside down.

## 4. Version every print

1. Before you overwrite, copy the outputs of the print the user has:
   `part_printN.FCStd`, `print/part_printN.stl`, `print/*_printN.stl`.
2. Keep the file to print at one fixed name (`print/part.stl`). The answer
   to "what is the newest to print" is that file, its time stamp and what
   changed since the last print.
3. Add one log entry per print to the project `CLAUDE.md`. Write what
   changed, the inputs and their sources, the backups, the user's report and
   the open risk.
4. For a value photos cannot fix (a corner radius), print thin gauges
   (4 mm slices) at 3 values around the estimate. A gauge prints in minutes.

## 5. Read the user's report

- Photos of a print with no text mean "fix what these show". Find the
  misfit, measure it, change the model and report. Ask only what the
  photos cannot show.
- The user's correction is right. On the chin mount, "the tips touch" (my
  reading of a photo) was wrong.
- Foam tape on a translucent print is a contact map: light grey = foam with
  air behind it (no contact). Dark = contact, or a wall too thick to see
  through.
- A line the user draws can follow a seam or an edge off the plane of the
  gap. Find the physical edge it follows before you measure a gap against
  it. Cross-check the gap with a second source in one common frame.
- Calibrate a photo of the print on rigid features only (feet, pockets,
  rail ends), not on flexible tips. See `photo-measure`.
- For a small shape detail (a chamfer, a lip end), offer 2-4 sketched
  options early (AskUserQuestion with ASCII previews). Take the endpoints
  of a user's sketch as exact and report the angle they give.

## 6. Refit only the measured misfit

1. Put the new data in the model frame. Get the shift from a section that
   already fits on a print. Do not assume it.
2. Target = the inner envelope of the old section and the new measurement:
   move the section only where the measurement is inside it. Keep the parts
   that fit.
3. Fit the parameters of the **real section function** (run it inside
   FreeCAD, where scipy is available). A numpy copy of the curve drifts from the
   model's spline.
4. Weight interference (target outside the section) about 3 times more than
   a gap. Leave out regions with no material. Bound each segment to a
   minimum length (4 mm). An edge near 0 mm makes the loft fail.
5. Report the fit: rms, maximum inside, maximum outside. Note when the
   parameters are not unique (several sets fit equally well).

## 7. Check and hand over

- Run `freecad-render-check` on the whole part and the STL.
- Compare the contact area (faces on the shell plus the gap) with the last
  print, by the same method.
- Report the file to print, and what changed and why (measured / inferred /
  guess). Then give the checks, the open risk, and the one measurement that
  settles it on the next print.
