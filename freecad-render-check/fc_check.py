"""Render and check helpers for FreeCAD, run inside FreeCAD (MCP execute_code):

    exec(open(os.path.expanduser("~/Github/agent-skills/freecad-render-check/fc_check.py")).read())

Functions:
    render(path, view="iso", doc=None, show=None, target=None, eye=None, size=(1200, 900))
    check_shape(shape, small_face=1.0, short_edge=0.3)       -> dict, prints one line
    probe(shape, points)                                      -> list of bools (point inside?)
    check_stl(path, overhang_deg=45.0)                        -> dict, prints one line
    check_all(shapes=None, stls=())                           -> True when everything passes
"""

import math
import FreeCAD as App

_VIEWS = {
    "iso": "viewIsometric", "top": "viewTop", "bottom": "viewBottom",
    "front": "viewFront", "rear": "viewRear", "left": "viewLeft", "right": "viewRight",
}


def render(path, view="iso", doc=None, show=None, target=None, eye=None, size=(1200, 900)):
    """Save a PNG of the active (or named) document.

    view   : one of iso/top/bottom/front/rear/left/right (ignored when eye is set)
    show   : list of object names to keep visible (others hidden); None = no change
    target : (x, y, z) point to look at for a close-up; needs eye
    eye    : (x, y, z) camera position for a close-up
    The camera animation is turned off first: with it on, saveImage captures
    the camera halfway through the view change."""
    import FreeCADGui as Gui
    d = App.getDocument(doc) if doc else App.ActiveDocument
    App.setActiveDocument(d.Name)
    gd = Gui.getDocument(d.Name)
    Gui.ActiveDocument = gd
    if show is not None:
        for o in d.Objects:
            if hasattr(o, "ViewObject") and o.ViewObject is not None:
                o.ViewObject.Visibility = o.Name in show
    v = gd.ActiveView
    try:
        v.setAnimationEnabled(False)
    except Exception:
        pass
    getattr(v, _VIEWS[view])()
    Gui.updateGui()
    v.fitAll()
    if eye is not None and target is not None:
        from pivy import coin
        cam = v.getCameraNode()
        cam.position.setValue(coin.SbVec3f(*eye))
        cam.pointAt(coin.SbVec3f(*target), coin.SbVec3f(0, 0, 1))
    Gui.updateGui()
    v.saveImage(path, size[0], size[1], "Current")
    print("render", view if eye is None else "close-up", "->", path)
    return path


def check_shape(shape, small_face=1.0, short_edge=0.3, label="shape"):
    """Solid checks: valid, one solid, no sliver faces or short edges."""
    faces = [f for f in shape.Faces if f.Area < small_face]
    short = [e for e in shape.Edges if e.Length < short_edge]
    # A short arc is usually a small corner rounding (an offset join), not a
    # sliver: list it, do not fail on it.
    arcs = [e for e in short if e.Curve.__class__.__name__ == "Circle"]
    edges = [e for e in short if e.Curve.__class__.__name__ != "Circle"]
    r = dict(label=label, valid=shape.isValid(), solids=len(shape.Solids),
             small_faces=len(faces), short_edges=len(edges), short_arcs=len(arcs),
             small_face_at=[tuple(round(c, 2) for c in f.CenterOfMass) for f in faces[:5]],
             short_edge_at=[tuple(round(c, 2) for c in e.CenterOfMass) for e in edges[:5]],
             bbox=tuple(round(x, 2) for x in (shape.BoundBox.XLength, shape.BoundBox.YLength, shape.BoundBox.ZLength)))
    r["ok"] = r["valid"] and r["solids"] == 1 and not faces and not edges
    print("%s %s valid=%s solids=%d faces<%.1f=%d edges<%.1f=%d (short arcs %d) bbox=%s%s" % (
        "PASS" if r["ok"] else "FAIL", label, r["valid"], r["solids"], small_face, len(faces),
        short_edge, len(edges), len(arcs), r["bbox"],
        "" if r["ok"] else " at " + str(r["small_face_at"] + r["short_edge_at"])))
    return r


def probe(shape, points, label="probe"):
    """Points that must be inside the solid (for example a corner where a
    groove could hide). Sliver checks do not see a V groove; a probe does."""
    res = [shape.isInside(App.Vector(*p), 1e-6, True) for p in points]
    print("%s %s %d/%d inside%s" % ("PASS" if all(res) else "FAIL", label, sum(res), len(res),
          "" if all(res) else " outside: " + str([p for p, ok in zip(points, res) if not ok])))
    return res


def check_stl(path, overhang_deg=45.0):
    """Mesh checks on an exported STL, plus the area of downward facets
    steeper than overhang_deg from vertical that do not touch the bed (Z min)."""
    import Mesh
    m = Mesh.Mesh(path)
    zmin = m.BoundBox.ZMin
    lim = -math.cos(math.radians(overhang_deg)) - 1e-4
    over = 0.0
    for f in m.Facets:
        if f.Normal.z < lim and min(p[2] for p in f.Points) > zmin + 0.05:
            over += f.Area
    r = dict(path=path, solid=m.isSolid(), non_manifold=m.hasNonManifolds(),
             self_intersections=m.hasSelfIntersections(), components=m.countComponents(),
             overhang_mm2=round(over, 1),
             bbox=tuple(round(x, 1) for x in (m.BoundBox.XLength, m.BoundBox.YLength, m.BoundBox.ZLength)))
    r["ok"] = r["solid"] and not r["non_manifold"] and not r["self_intersections"] and r["components"] == 1
    print("%s %s solid=%s nonmanifold=%s selfint=%s parts=%d overhang>%g=%.1fmm2 bbox=%s" % (
        "PASS" if r["ok"] else "FAIL", path.split("/")[-1], r["solid"], r["non_manifold"],
        r["self_intersections"], r["components"], overhang_deg, over, r["bbox"]))
    return r


def check_all(shapes=None, stls=()):
    """shapes: dict label -> shape. stls: STL paths. Returns True when all pass."""
    ok = True
    for label, s in (shapes or {}).items():
        ok &= check_shape(s, label=label)["ok"]
    for p in stls:
        ok &= check_stl(p)["ok"]
    print("ALL PASS" if ok else "SOME CHECKS FAILED")
    return ok
