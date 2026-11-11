---
name: freecad-render-check
description: Renders FreeCAD views and close-ups through the FreeCAD MCP with the camera animation off, and checks the model before you report it - solid validity, sliver faces and short edges, corner probes for hidden grooves, and STL mesh checks (closed solid, non-manifold, self-intersections, parts, overhang area). Use after every geometry change in a FreeCAD MCP session, before showing a render or handing over an STL. Triggered by "render the part", "show me the detail", "check the model", "is the STL printable", "check for slivers", "take a screenshot of the view".
---

# FreeCAD render and check

One helper for the two jobs that repeat after every CAD edit: look at the
part, and prove that the part is clean. Load the helper once per FreeCAD session:

```python
import os
exec(open(os.path.expanduser("~/Github/agent-skills/freecad-render-check/fc_check.py")).read())
```

Run it through the FreeCAD MCP `execute_code` tool. FreeCAD must be open with
the MCP RPC server running. `render()` needs the GUI. The checks also run
headless.

## Render

```python
render("/abs/out.png", "front", show=["Part", "PhotoFront"])   # named view
render("/abs/detail.png", target=(19.6, 0.5, 25), eye=(26, -8, 35))   # close-up
```

- Views: `iso`, `top`, `bottom`, `front`, `rear`, `left`, `right`.
- `show` hides every other object. Leave it out to keep the current visibility.
- The helper turns off the camera animation and calls `updateGui()` before
  the capture. With the animation on, `saveImage` captures the camera
  halfway through the view change, and the image shows the wrong view.
- Save the image to the scratchpad. Then `Read` the PNG and look at it before
  you describe it. The MCP's own screenshot is the GUI view, not your file.
- For a small detail, crop and enlarge the PNG with PIL. That is faster than
  a second camera setup.

## Check

```python
check_all({"mount": doc.getObject("Mount").Shape},
          ["/abs/print/mount.stl", "/abs/print/coupon.stl"])
probe(receiver, [(0, 19.45, 7.05), (0, -19.45, 7.05)], "rail corner")
```

Each line starts with `PASS` or `FAIL` and gives the location of a failure.

| Check | Fails when |
| --- | --- |
| `check_shape` | `isValid()` is false, the solid count is not 1, a face is under 1 mm², or a straight edge is under 0.3 mm |
| `probe` | a point that must be solid is outside the shape |
| `check_stl` | the mesh is not a closed solid, has non-manifold edges or self-intersections, or has more than 1 part |

`check_stl` also reports the area of downward facets steeper than 45° that
do not touch the bed. Read it as a print risk, not a failure.

## Rules

1. Check the **whole part** after each change, not only the sub-part you
   edited. A fused part can get slivers that its parts do not have.
2. The helper lists a short **arc** but does not fail on it. A short arc
   is usually a small corner rounding from an offset join. Look at it once and decide.
3. A **V groove** has no small face and no short edge, so `check_shape`
   passes it. When you fuse a sharp feature onto a rounded corner, probe the
   corner. A good probe point is 0.15 mm in from the sharp corner, on both
   sides and at both ends.
4. Test a new check on a known bad shape first. A check that cannot fail
   proves nothing.
5. STL export: a linear deflection under 0.05 mm can add self-intersections
   on small rounded tips. Use 0.05 / 0.3 and run `check_stl` again.
6. Report the numbers the helper printed (measured). Do not report a
   render as proof of the mesh, or the mesh check as proof of the look.
   Each one proves one thing.
