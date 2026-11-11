"""Reference photos as Image::ImagePlane objects, run inside FreeCAD (GUI):

    exec(open(os.path.expanduser("~/Github/agent-skills/freecad-photo-reference/photo_ref.py")).read())
    add_photo(doc, "/abs/photo.jpg", view="bottom", mm_per_px=0.087,
              anchor_px=(1241, 988), anchor_mm=(0, 18.2), offset=-0.5)

view (which FreeCAD view shows the photo the right way round):
    "top"    : photo taken from above, lies in XY, image up = +Y
    "bottom" : photo taken from below, lies in XY, mirrored (180 deg about X),
               image up = -Y; it then matches the Top view of the part
    "front"  : photo taken from the front (-Y side), stands in XZ, image up = +Z
anchor_px : pixel (from the top-left of the ORIGINAL image) placed at anchor_mm
anchor_mm : (x, y) for top/bottom, (x, z) for front
offset    : z of the plane for top/bottom, y of the plane for front
"""

import os
import FreeCAD as App

V = App.Vector


def image_size(path):
    """(width, height) in pixels, through Qt (bundled with FreeCAD)."""
    try:
        from PySide import QtGui
    except ImportError:
        from PySide2 import QtGui
    img = QtGui.QImage(path)
    if img.isNull():
        raise IOError("cannot read image: " + path)
    return img.width(), img.height()


def photo_placement(view, size_px, mm_per_px, anchor_px, anchor_mm, offset):
    w, h = size_px
    s = mm_per_px
    du, dv = (anchor_px[0] - w / 2) * s, (h / 2 - anchor_px[1]) * s   # anchor from image centre
    a, b = anchor_mm
    if view == "top":
        return App.Placement(V(a - du, b - dv, offset), App.Rotation())
    if view == "bottom":
        return App.Placement(V(a - du, b + dv, offset), App.Rotation(V(1, 0, 0), 180))
    if view == "front":
        return App.Placement(V(a - du, offset, b - dv), App.Rotation(V(1, 0, 0), 90))
    raise ValueError("view must be top, bottom or front")


def add_photo(doc, path, view, mm_per_px, anchor_px, anchor_mm=(0.0, 0.0), offset=0.0,
              name=None, transparency=40):
    """Add one photo plane. Returns the object, or None without the GUI."""
    if not App.GuiUp:
        print("photo skipped (no GUI):", path)
        return None
    size = image_size(path)
    o = doc.addObject("Image::ImagePlane", name or "Photo")
    o.ImageFile = path
    o.XSize = size[0] * mm_per_px
    o.YSize = size[1] * mm_per_px
    o.Placement = photo_placement(view, size, mm_per_px, anchor_px, anchor_mm, offset)
    try:
        o.ViewObject.Transparency = transparency
    except Exception:
        pass
    print("photo %s: %s view, %.1f x %.1f mm" % (o.Name, view, o.XSize, o.YSize))
    return o


def model_to_photo_px(view, size_px, mm_per_px, anchor_px, anchor_mm, point):
    """Inverse map: a model point (x, y) or (x, z) -> pixel in the original photo.
    Use it to check where a model feature falls on the photo."""
    w, h = size_px
    s = mm_per_px
    a, b = anchor_mm
    x, y = point
    px = anchor_px[0] + (x - a) / s
    if view == "top":
        py = anchor_px[1] - (y - b) / s
    elif view == "bottom":
        py = anchor_px[1] + (y - b) / s
    else:
        py = anchor_px[1] - (y - b) / s
    return px, py
