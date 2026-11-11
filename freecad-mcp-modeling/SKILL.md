---
name: freecad-mcp-modeling
description: Builds and changes parametric FreeCAD parts through the FreeCAD MCP (execute_code, execute_code_async, execute_code_headless) - keeps the build script in the repo, picks the right execution tool for heavy OpenCascade work, measures shapes without the usual traps (loose B-spline bounding boxes, document Placement offsets), builds loft sections that do not make slivers, and maps OpenCascade errors to their known fixes. Use when you script geometry in FreeCAD from Claude Code, when a FreeCAD MCP call fails or times out, or when a loft, offset, fillet, chamfer or boolean gives an error or an invalid solid. Triggered by "build it in FreeCAD", "change the model", "regenerate the part", "BRep_API: command not done", "the loft fails", "FreeCAD stopped responding", "connection refused 9875", "the bounding box is wrong".
---

# FreeCAD MCP modeling

The FreeCAD MCP runs Python inside a live FreeCAD. This skill holds the
working pattern and the failures already paid for. After each geometry
change, run `freecad-render-check` (solid, slivers, STL).

## 1. Session

- FreeCAD must be open with the MCP addon's RPC server on `127.0.0.1:9875`.
  Check: `nc -z 127.0.0.1 9875`. Turn on the addon's auto-start so that a
  FreeCAD start is enough.
- "Connection refused" after a call = FreeCAD crashed or hung. Start it
  again (`open -a FreeCAD`). Wait for the port with a Monitor until-loop
  (the harness blocks a foreground `sleep`). Then load the script again,
  because the namespace is gone.
- To open an FCStd file that crashed FreeCAD before, or to run any risky
  OpenCascade job, use `execute_code_headless`. A crash then kills only
  the helper process.

## 2. Choose the tool

| Job | Tool |
| --- | --- |
| Normal build, document edits, renders | `execute_code` (GUI thread, 90 s budget) |
| Slow geometry on shapes you already have (fuse, cut, loft, many `distToShape` calls) | `execute_code_async`. Write to the document only inside `commit(fn)`. Poll with `get_async_status` |
| Code that can crash OpenCascade, or a file to open from disk | `execute_code_headless` (separate `freecadcmd`) |

"GUI dispatch gave up after 90 s" means the last call is still running on the
GUI thread. Wait for it. Do not send more calls on top of it.

## 3. Script in the repo

- The build script lives in the repo next to the FCStd it writes. Run it by
  `exec(open(path).read())`. Never keep the model only in the session.
- To load the helpers without the build, split on a marker comment that
  occurs once (`# ---- sections from measured gaps`). Do not split on
  `"if __name__"`: that text can also occur in a string or a comment.
- `build(write=...)`: write FCStd and STL files only from measured inputs.
  Back up the last printed version before you overwrite it (see
  `fit-to-object`).
- scipy and numpy are available in FreeCAD's Python (scipy 1.16.3 on 1.1).
  Run fits against the real model functions there. The system python has
  neither: outside FreeCAD use `uv run --with numpy --with scipy ...`.

## 4. Measure shapes correctly

- `Shape.BoundBox` of B-spline faces is loose. It looked 301 x 328 mm on a
  100 mm part. Use `shape.optimalBoundingBox()`, vertex coordinates,
  slices, or the mesh bounding box.
- A document object can have a `Placement`. Before you measure in model
  coordinates: `s = obj.Shape.copy(); s.Placement = App.Placement()`.
- A boolean can leave a small separate solid. Keep the largest solid
  (`max(s.Solids, key=lambda x: x.Volume)`) and report what you dropped.
- Inside/outside: `shape.isInside(App.Vector(...), 1e-6, True)`. Distance:
  `shape.distToShape(Part.Vertex(p))[0]`. Wall thickness: section the solid
  with planes and measure in 2D. `nearestFacetOnRay` on meshes returned
  wrong hits.

## 5. Sections and lofts

- Build each loft section analytically with a fixed edge count and edge
  order (for example: line, arc, spline, arc, line, closing edge). The loft
  pairs edges by index. Offsetting a polyline and rounding it with
  `makeOffset2D` split splines into about 67 edges. That gave slivers, edges
  near 0 mm and 65 s builds (analytic wire: 3.7 s).
- Every edge must stay longer than about 1-4 mm for all parameter values.
  An edge near 0 mm gives `BRep_API: command not done`. Put the minimum
  length in the fit bounds.
- Loft through 4 wires (z = -1, 0, H, H+1) and cut back to 0..H, so the end
  faces are clean planar cuts.
- Join two different profiles with a ruled loft, not a vertical union. A
  union of two extrusions leaves a step.

## 6. OpenCascade failure recipes

| Symptom | Cause | Fix |
| --- | --- | --- |
| `BRep_API: command not done` on a loft or offset | An edge near 0 mm long | Bound the segment lengths. Check `min(e.Length for e in wire.Edges)` |
| `makeOffset2D`: "input shape is not an edge, wire or face" | A fuse gave a Shell | Make a face first (`Part.Face(wire)` or the outer wire of the fused face) |
| `makeOffset2D` returns no wires | Offset larger than the local radius | Cap the radius search. Wrap it in try/except |
| Fillet or chamfer fails, or gives `isValid() == False` | Small faces near the edge, or end faces across many edges | Cut the shape with prisms instead. After 2 failed tries, leave it off and use the slicer (elephant-foot compensation) |
| A feature skin 0.01 mm thick | A cut that stops just short of a face | Start the cut 0.05 mm past the face |
| Slivers (faces < 1 mm2, edges < 0.3 mm) where two parts meet | Two edges that almost coincide | Move one edge to the other's position (a shared helper for both). Check again |
| V groove at a rounded corner (checks pass) | A sharp feature fused onto a rounded corner | Square the corner first. Probe with `isInside` |
| Self-intersections in the STL on small tips | Mesh deflection too fine | `MeshPart.meshFromShape(Shape=s, LinearDeflection=0.05, AngularDeflection=0.3)` |
| A render shows the wrong view | Camera animation | `freecad-render-check` `render()` |

## 7. GUI details

- `Gui.activateDocument` does not exist. Set `Gui.ActiveDocument` and
  activate the document's MDI window.
- Image planes and renders need the GUI (`App.GuiUp`). Skip them in a
  headless build.
