#!/usr/bin/env python3
"""Read a user's marked screenshot of a CAD view in model millimetres.

The screenshot must show the model at a known scale: you give one pixel whose
model position you know (usually the origin) and px/mm, or two pixels with
their model positions, and the tool converts marked points and lines.

  # 1. Grid overlay, to read pixel positions of the marks (writes <out>)
  screenshot_mm.py grid shot.png --out shot_grid.png [--step 100]

  # 2. Convert points / lines. Lines are x1,y1,x2,y2 in screenshot pixels.
  screenshot_mm.py convert --origin 706,491 --px-per-mm 10.25 \
      --line 40,1070,230,790 --line 1375,1025,1165,760 --point 1093,676 \
      [--flip-x] [--flip-y] [--at-y 40]

  # Scale from two known features instead of --px-per-mm:
  screenshot_mm.py convert --origin 706,491 --known 190,1040,1222,1040,100.4 ...
  (two pixels and the model distance between them, in mm)

Screen +y points down. By default model +Y = screen down (a Bottom view of a
part whose +Y is away from the viewer); use --flip-y when model +Y is screen up
(Top view). --flip-x when the view mirrors X (Bottom view): for a symmetric
part it changes only the sign. Angles are reported from the model Y axis
(fore-aft) and from the X axis.
"""
import argparse
import math
import sys


def _pair(s):
    a = [float(v) for v in s.split(",")]
    return a


def cmd_grid(a):
    from PIL import Image, ImageDraw
    im = Image.open(a.image).convert("RGB")
    d = ImageDraw.Draw(im)
    w, h = im.size
    for y in range(0, h, a.step):
        d.line([(0, y), (w, y)], fill=(255, 255, 0))
        d.text((3, y + 2), str(y), fill=(255, 255, 0))
    for x in range(0, w, a.step):
        d.line([(x, 0), (x, h)], fill=(0, 255, 255))
        d.text((x + 2, 3), str(x), fill=(0, 255, 255))
    im.save(a.out)
    print("grid %dx%d step %d -> %s" % (w, h, a.step, a.out))


def cmd_convert(a):
    ox, oy = _pair(a.origin)
    if a.known:
        x1, y1, x2, y2, mm = _pair(a.known)
        ppm = math.hypot(x2 - x1, y2 - y1) / mm
    elif a.px_per_mm:
        ppm = a.px_per_mm
    else:
        sys.exit("give --px-per-mm or --known")
    sx = -1 if a.flip_x else 1
    sy = -1 if a.flip_y else 1

    def mm(px, py):
        return sx * (px - ox) / ppm, sy * (py - oy) / ppm

    print("scale %.3f px/mm (%.4f mm/px)" % (ppm, 1 / ppm))
    for p in a.point or []:
        x, y = mm(*_pair(p))
        print("point %s -> X %.1f  Y %.1f mm" % (p, x, y))
    for ln in a.line or []:
        x1, y1, x2, y2 = _pair(ln)
        X1, Y1 = mm(x1, y1)
        X2, Y2 = mm(x2, y2)
        dx, dy = X2 - X1, Y2 - Y1
        from_y = math.degrees(math.atan2(abs(dx), abs(dy)))
        out = "line %s -> (%.1f, %.1f) to (%.1f, %.1f) mm, length %.1f, %.1f deg from Y, %.1f deg from X" % (
            ln, X1, Y1, X2, Y2, math.hypot(dx, dy), from_y, 90 - from_y)
        if a.at_y is not None and abs(dy) > 1e-9:
            out += ", X at Y=%g: %.1f" % (a.at_y, X1 + (a.at_y - Y1) * dx / dy)
        print(out)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("grid")
    g.add_argument("image")
    g.add_argument("--out", required=True)
    g.add_argument("--step", type=int, default=100)
    c = sub.add_parser("convert")
    c.add_argument("--origin", required=True, help="px,py of a known model point (model 0,0)")
    c.add_argument("--px-per-mm", type=float)
    c.add_argument("--known", help="x1,y1,x2,y2,mm: two pixels and their model distance")
    c.add_argument("--point", action="append")
    c.add_argument("--line", action="append")
    c.add_argument("--flip-x", action="store_true")
    c.add_argument("--flip-y", action="store_true")
    c.add_argument("--at-y", type=float, help="also report each line's X at this model Y")
    a = p.parse_args()
    cmd_grid(a) if a.cmd == "grid" else cmd_convert(a)


if __name__ == "__main__":
    main()
