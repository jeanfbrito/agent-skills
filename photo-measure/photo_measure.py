#!/usr/bin/env python3
"""Measure real objects in photos, in millimetres.

A photo has no scale. Put a size reference in the same plane as the feature,
get 6+ reference points (reference mm -> photo px), fit a homography
(perspective map), then convert any photo pixel ON THAT PLANE to mm.

Needs numpy + OpenCV + Pillow. Run it through uv (no install):
  F() { uv run --quiet --with numpy --with opencv-python-headless --with pillow \
        python ~/Github/agent-skills/photo-measure/photo_measure.py "$@"; }

  F target  --out card.pdf [--paper a4|letter]             # printable marker cards
  F detect  photo.jpg --out /scratch/p [--card-scale 1.0]  # -> p_card0.json, p_markers.png
  F grid    photo.jpg --out crop.png --crop x0,y0,x1,y1 --step 20 --scale 2
  F fit     photo.jpg --pairs pairs.json [--overlay lines.json] --out o.png [--crop ...]
  F measure --pairs pairs.json --pt A=u,v --pt B=u,v [--dist A,B] [--circle A,B,C,...]

pairs.json : [[[x_mm, y_mm], [u_px, v_px], "optional name"], ...]
             Pixels are in the EXIF-rotated photo (what `grid` labels).
             A pixel can be {"intersect": [[u1,v1],[u2,v2],[u3,v3],[u4,v4]]}:
             the point where line 1-2 meets line 3-4 (for a rounded corner,
             read 2 points on each straight edge).
lines.json : {"name": [[x_mm, y_mm], ...], ...}   (one colour per name)

Card frame (target/detect): origin at the card centre, +x right, +y up, mm.
Marker id = 4 * card + i, i = 0 top-left, 1 top-right, 2 bottom-right,
3 bottom-left. Card A = ids 0-3, card B = ids 4-7.
"""
import argparse
import json
import sys

COLOURS = [(255, 60, 60), (0, 255, 120), (255, 200, 0), (0, 220, 255), (255, 0, 255), (255, 255, 255)]

# ---- marker card layout (target and detect share it) -----------------------
DICT = "DICT_4X4_50"
MARKER = 20.0                    # marker side, mm (6 x 6 modules incl. border)
CENTRES = [(-40.0, 22.0), (40.0, 22.0), (40.0, -22.0), (-40.0, -22.0)]
CARD_W, CARD_H = 110.0, 74.0     # cut line, mm
NCARDS = 2
PAPER = {"a4": (210.0, 297.0), "letter": (215.9, 279.4)}
DPI = 300


def marker_corners_mm(i, s=1.0):
    """Corners of marker i in the card frame, in OpenCV order (TL, TR, BR, BL)."""
    cx, cy = CENTRES[i]
    h = MARKER / 2
    return [((cx - h) * s, (cy + h) * s), ((cx + h) * s, (cy + h) * s),
            ((cx + h) * s, (cy - h) * s), ((cx - h) * s, (cy - h) * s)]


# ---- helpers ---------------------------------------------------------------
def _photo(path):
    from PIL import Image, ImageOps
    return ImageOps.exif_transpose(Image.open(path)).convert("RGB")


def _box(s):
    return tuple(int(v) for v in s.split(",")) if s else None


def _font(size):
    from PIL import ImageFont
    try:
        return ImageFont.load_default(size=size)
    except TypeError:            # Pillow < 10.1
        return ImageFont.load_default()


def _px(p):
    """A pair's pixel: [u, v] or {"intersect": [a, b, c, d]} (line a-b x line c-d)."""
    import numpy as np
    if isinstance(p, dict):
        a, b, c, d = (np.float64(q) for q in p["intersect"])
        r, s = b - a, d - c
        den = r[0] * s[1] - r[1] * s[0]
        if abs(den) < 1e-9:
            sys.exit("intersect: the two lines are parallel")
        t = ((c[0] - a[0]) * s[1] - (c[1] - a[1]) * s[0]) / den
        return a + t * r
    return np.float64(p)


def _load_pairs(path):
    import numpy as np
    pairs = json.load(open(path))
    if len(pairs) < 4:
        sys.exit("need 4 or more pairs (6+ recommended)")
    M = np.float32([p[0] for p in pairs])
    P = np.float32([_px(p[1]) for p in pairs])
    names = [p[2] if len(p) > 2 else "#%d" % k for k, p in enumerate(pairs)]
    return M, P, names


def _homography(M, P):
    import cv2
    H, _ = cv2.findHomography(M, P, 0)
    if H is None:
        sys.exit("homography fit failed: are the reference points on one line?")
    return H


def _map(H, pts):
    import numpy as np
    import cv2
    return cv2.perspectiveTransform(np.float32(pts).reshape(1, -1, 2), H)[0]


def _ppm(H, xy):
    """Photo pixels per mm on the reference plane at model point xy."""
    import numpy as np
    x, y = xy
    q0, qx, qy = _map(H, [(x, y), (x + 1, y), (x, y + 1)])
    return float((np.hypot(*(qx - q0)) + np.hypot(*(qy - q0))) / 2)


# ---- commands --------------------------------------------------------------
def cmd_target(a):
    """Printable sheet: NCARDS marker cards and a 100 mm check bar."""
    import cv2
    from PIL import Image, ImageDraw
    W, Hm = PAPER[a.paper]
    k = DPI / 25.4
    im = Image.new("L", (round(W * k), round(Hm * k)), 255)
    d = ImageDraw.Draw(im)
    dic = cv2.aruco.getPredefinedDictionary(getattr(cv2.aruco, DICT))
    f_big, f_small = _font(round(3.2 * k)), _font(round(2.4 * k))

    def P(x, y):                 # page mm -> px
        return (round(x * k), round(y * k))

    def bar(x0, y, length, label):
        d.line([P(x0, y), P(x0 + length, y)], fill=0, width=3)
        for t in range(int(length) + 1):
            h = 3.0 if t % 10 == 0 else (2.0 if t % 5 == 0 else 1.2)
            if length > 60 or t % 10 == 0:
                d.line([P(x0 + t, y), P(x0 + t, y - h)], fill=0, width=2)
        d.text(P(x0, y + 1.2), label, fill=0, font=f_small)

    cx = W / 2
    for c in range(NCARDS):
        ccx, ccy = cx, 52.0 + c * (CARD_H + 12.0)       # card centre, page mm
        x0, y0 = ccx - CARD_W / 2, ccy - CARD_H / 2
        # dashed cut line
        for xa in range(int(CARD_W // 4)):
            d.line([P(x0 + 4 * xa, y0), P(x0 + 4 * xa + 2, y0)], fill=128, width=2)
            d.line([P(x0 + 4 * xa, y0 + CARD_H), P(x0 + 4 * xa + 2, y0 + CARD_H)], fill=128, width=2)
        for ya in range(int(CARD_H // 4)):
            d.line([P(x0, y0 + 4 * ya), P(x0, y0 + 4 * ya + 2)], fill=128, width=2)
            d.line([P(x0 + CARD_W, y0 + 4 * ya), P(x0 + CARD_W, y0 + 4 * ya + 2)], fill=128, width=2)
        for i in range(4):
            bits = cv2.aruco.generateImageMarker(dic, 4 * c + i, 6)   # 1 px per module
            mx, my = CENTRES[i]
            ox, oy = ccx + mx - MARKER / 2, ccy - my - MARKER / 2  # page y points down
            m = MARKER / 6
            for r in range(6):
                for q in range(6):
                    if bits[r, q] < 128:
                        d.rectangle([P(ox + q * m, oy + r * m),
                                     (round((ox + (q + 1) * m) * k) - 1, round((oy + (r + 1) * m) * k) - 1)], fill=0)
        # middle column (|x| <= 25 mm) stays clear of the markers' quiet zone
        d.text(P(ccx - 24, ccy - 30), "photo-measure card %s" % "AB"[c], fill=0, font=f_big)
        d.text(P(ccx - 24, ccy - 25), "ids %d-%d   110 x 74 mm" % (4 * c, 4 * c + 3), fill=0, font=f_small)
        d.text(P(ccx - 24, ccy - 8), "Keep it flat.", fill=0, font=f_small)
        d.text(P(ccx - 24, ccy - 4), "Do not cover a square.", fill=0, font=f_small)
        bar(ccx - 25, ccy + 14, 50, "50 mm")
    y = 52.0 + NCARDS * (CARD_H + 12.0) + 4
    bar(cx - 50, y, 100, "100 mm: measure this bar with a ruler before you cut.")
    lines = ["1. Print at 100 % (Actual size). Do not use Fit to page.",
             "2. The bar above must be 100 mm. If not, tell the agent the length.",
             "3. Cut out a card on the dashed line.",
             "4. Tape it flat on the surface to measure, next to the feature.",
             "5. Photo straight at the card, from about 50 cm, with 2x zoom.",
             "   Keep the 4 squares and the feature in the frame."]
    for n, t in enumerate(lines):
        d.text(P(cx - 50, y + 8 + 5.0 * n), t, fill=0, font=f_small)
    if a.out.lower().endswith(".pdf"):
        im.save(a.out, "PDF", resolution=DPI)
    else:
        im.save(a.out, dpi=(DPI, DPI))
    print("target %s %.1f x %.1f mm, %d dpi -> %s" % (a.paper, W, Hm, DPI, a.out))
    print("print at 100 %; the long bar must measure 100 mm")


def cmd_detect(a):
    """Find the marker cards in a photo; write one pairs file per card."""
    import numpy as np
    import cv2
    from PIL import Image
    rgb = np.array(_photo(a.photo))
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    dic = cv2.aruco.getPredefinedDictionary(getattr(cv2.aruco, DICT))
    prm = cv2.aruco.DetectorParameters()
    det = cv2.aruco.ArucoDetector(dic, prm)
    # detect on a copy with the long side <= 2000 px, refine the corners at full size
    s = min(1.0, 2000.0 / max(gray.shape))
    small = cv2.resize(gray, None, fx=s, fy=s, interpolation=cv2.INTER_AREA) if s < 1 else gray
    corners, ids, _ = det.detectMarkers(small)
    if ids is None:
        sys.exit("no markers found: check focus and glare, and keep all 4 squares in the frame")
    crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 50, 0.01)
    win = max(3, int(round(3 / s)))
    cards = {}
    for c, i in zip(corners, ids.flatten()):
        card, j = divmod(int(i), 4)
        if card >= NCARDS:
            continue
        pts = (c[0] / s).astype(np.float32).reshape(-1, 1, 2)
        cv2.cornerSubPix(gray, pts, (win, win), (-1, -1), crit)
        for n, (m, (u, v)) in enumerate(zip(marker_corners_mm(j, a.card_scale), pts.reshape(-1, 2))):
            cards.setdefault(card, []).append([[round(m[0], 3), round(m[1], 3)],
                                               [round(float(u), 2), round(float(v), 2)],
                                               "id%d.%d" % (i, n)])
    if not cards:
        sys.exit("markers found, but none from a photo-measure card (ids 0-%d)" % (4 * NCARDS - 1))
    for card, pairs in sorted(cards.items()):
        path = "%s_card%d.json" % (a.out, card)
        json.dump(pairs, open(path, "w"), indent=0)
        n = len(pairs) // 4
        note = "" if n == 4 else "  (only %d of 4 markers: measure inside their area only)" % n
        print("card %s: %d markers, %d pairs -> %s%s" % ("AB"[card], n, len(pairs), path, note))
    vis = rgb.copy()
    cv2.aruco.drawDetectedMarkers(vis, [c / s for c in corners], ids)
    out = Image.fromarray(vis)
    out.thumbnail((1600, 1600))
    out.save(a.out + "_markers.png")
    print("check the ids on", a.out + "_markers.png")


def cmd_grid(a):
    from PIL import Image, ImageDraw
    im = _photo(a.photo)
    x0, y0, x1, y1 = _box(a.crop) or (0, 0, im.width, im.height)
    im = im.crop((x0, y0, x1, y1))
    im = im.resize((int(im.width * a.scale), int(im.height * a.scale)), Image.LANCZOS)
    d = ImageDraw.Draw(im)
    for x in range((x0 // a.step + 1) * a.step, x1, a.step):
        X = (x - x0) * a.scale
        d.line([(X, 0), (X, im.height)], fill=(0, 255, 255))
        d.text((X + 2, 2), str(x), fill=(0, 255, 255))
    for y in range((y0 // a.step + 1) * a.step, y1, a.step):
        Y = (y - y0) * a.scale
        d.line([(0, Y), (im.width, Y)], fill=(255, 255, 0))
        d.text((2, Y + 2), str(y), fill=(255, 255, 0))
    im.save(a.out)
    print("grid", im.size, "->", a.out)


def cmd_fit(a):
    import numpy as np
    from PIL import Image, ImageDraw
    M, P, names = _load_pairs(a.pairs)
    H = _homography(M, P)
    fit = _map(H, M)
    loo = [None] * len(M)
    if len(M) >= 5:              # leave-one-out: predict each point from the others
        for i in range(len(M)):
            keep = [j for j in range(len(M)) if j != i]
            loo[i] = float(np.hypot(*(_map(_homography(M[keep], P[keep]), M[i:i + 1])[0] - P[i])))
    errs = []
    for k, (m, p, q) in enumerate(zip(M, P, fit)):
        e = float(np.hypot(*(p - q)))
        errs.append(e)
        ppm = _ppm(H, m)
        l = "" if loo[k] is None else "  leave-one-out %.1f px = %.2f mm" % (loo[k], loo[k] / ppm)
        print("%-8s model (%7.2f, %7.2f) photo (%6.0f, %6.0f) error %.1f px = %.2f mm%s"
              % (names[k], m[0], m[1], p[0], p[1], e, e / ppm, l))
    ppm = _ppm(H, M.mean(axis=0))
    print("scale near the centre %.1f px/mm; max error %.1f px = %.2f mm" % (ppm, max(errs), max(errs) / ppm))
    if loo[0] is not None:
        worst = int(np.argmax(loo))
        print("max leave-one-out error %.2f mm at %s (accept under about 1 mm)"
              % (loo[worst] / _ppm(H, M[worst]), names[worst]))
    else:
        print("only %d pairs: no leave-one-out check; add pairs (6+)" % len(M))
    np.save(a.out.rsplit(".", 1)[0] + "_H.npy", H)
    im = _photo(a.photo)
    d = ImageDraw.Draw(im)
    for p in P:
        d.ellipse([p[0] - 6, p[1] - 6, p[0] + 6, p[1] + 6], outline=(255, 0, 255), width=2)
    if a.overlay:
        for i, (name, pts) in enumerate(json.load(open(a.overlay)).items()):
            col = COLOURS[i % len(COLOURS)]
            for sx in ((1, -1) if a.mirror_x else (1,)):
                q = _map(H, [(x * sx, y) for x, y in pts])
                d.line([tuple(v) for v in q], fill=col, width=a.width)
            print("line %s: colour %s" % (name, col))
    box = _box(a.crop)
    if box:
        im = im.crop(box)
    if a.scale != 1:
        im = im.resize((int(im.width * a.scale), int(im.height * a.scale)), Image.LANCZOS)
    im.save(a.out)
    print("overlay ->", a.out)


def cmd_measure(a):
    import numpy as np
    M, P, _ = _load_pairs(a.pairs)
    H = _homography(M, P)
    Hi = np.linalg.inv(H)
    pts = {}
    for spec in a.pt:
        name, uv = spec.split("=", 1)
        u, v = (float(t) for t in uv.split(","))
        xy = _map(Hi, [(u, v)])[0]
        pts[name] = (np.float64(xy), np.float64((u, v)))
        ppm = _ppm(H, xy)
        print("point %-4s photo (%6.0f, %6.0f) -> (%8.2f, %8.2f) mm   1 px = %.3f mm"
              % (name, u, v, xy[0], xy[1], 1 / ppm))
    for spec in a.dist or []:
        p, q = spec.split(",")
        print("dist %s-%s: %.2f mm" % (p, q, float(np.hypot(*(pts[p][0] - pts[q][0])))))
    rng = np.random.default_rng(0)
    for spec in a.circle or []:
        ns = spec.split(",")
        if len(ns) < 3:
            sys.exit("circle needs 3 or more points")

        def kasa(xy):
            A = np.c_[2 * xy, np.ones(len(xy))]
            cx, cy, c = np.linalg.lstsq(A, (xy ** 2).sum(1), rcond=None)[0]
            return cx, cy, np.sqrt(c + cx * cx + cy * cy)

        xy = np.array([pts[n][0] for n in ns])
        cx, cy, r = kasa(xy)
        res = np.abs(np.hypot(xy[:, 0] - cx, xy[:, 1] - cy) - r).max()
        # reading noise: move each photo point by a.noise px (1 sigma), refit
        uv = np.array([pts[n][1] for n in ns])
        rs = [kasa(_map(Hi, uv + rng.normal(0, a.noise, uv.shape)).astype(np.float64))[2] for _ in range(300)]
        print("circle %s: centre (%.2f, %.2f) mm, R %.2f mm, max residual %.2f mm, "
              "R spread +-%.2f mm for %.1f px reading noise"
              % (spec, cx, cy, r, res, float(np.std(rs)), a.noise))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("target")
    t.add_argument("--out", required=True)
    t.add_argument("--paper", choices=sorted(PAPER), default="a4")
    de = sub.add_parser("detect")
    de.add_argument("photo")
    de.add_argument("--out", required=True, help="prefix for <out>_card<k>.json and <out>_markers.png")
    de.add_argument("--card-scale", type=float, default=1.0,
                    help="measured length of the 100 mm bar / 100 (printer scale)")
    g = sub.add_parser("grid")
    g.add_argument("photo")
    g.add_argument("--out", required=True)
    g.add_argument("--crop")
    g.add_argument("--step", type=int, default=50)
    g.add_argument("--scale", type=float, default=1.0)
    f = sub.add_parser("fit")
    f.add_argument("photo")
    f.add_argument("--pairs", required=True)
    f.add_argument("--overlay")
    f.add_argument("--out", required=True)
    f.add_argument("--crop")
    f.add_argument("--scale", type=float, default=1.0)
    f.add_argument("--width", type=int, default=4)
    f.add_argument("--mirror-x", action="store_true")
    m = sub.add_parser("measure")
    m.add_argument("--pairs", required=True)
    m.add_argument("--pt", action="append", required=True, help="NAME=u,v (photo px)")
    m.add_argument("--dist", action="append", help="NAME,NAME")
    m.add_argument("--circle", action="append", help="NAME,NAME,NAME[,...] (3+ points on an arc)")
    m.add_argument("--noise", type=float, default=1.5, help="reading noise in px for the R spread")
    a = p.parse_args()
    {"target": cmd_target, "detect": cmd_detect, "grid": cmd_grid,
     "fit": cmd_fit, "measure": cmd_measure}[a.cmd](a)


if __name__ == "__main__":
    main()
