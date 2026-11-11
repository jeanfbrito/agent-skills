"""Cutting-mat calibration: the grid of a cutting mat as the size reference.

A mat under the object gives tens of grid points per photo. With 3 or more
photos of the same mat, one camera calibration gives the camera pose of each
photo. Then a pixel maps to the mat plane at any height Z, and a feature seen
in 2 photos from different spots is triangulated in 3D (mat mm, Z up).

Subcommands (run with numpy + opencv-python-headless + pillow):
  lines PHOTO --out o.png [--rt 12] [--hue 40,110]
      Find the mat grid lines (white on a coloured mat). Writes o.json (segments)
      and o.png (overlay, 1/3 size). Read the overlay. Raise --rt for fewer,
      cleaner lines; lower it when lines are missing.
  grid SEGS.json --rough ROUGH.json --out PAIRS.json [--pitch 10]
      Label the lines from 4+ rough points [[[X_mm, Y_mm], [u, v]], ...] that you
      read on a `photo_measure.py grid` crop, intersect them, fit a homography and
      print the leave-one-out error. PAIRS.json works with photo_measure.py too.
  calib PAIRS.json [PAIRS.json ...] --size W,H --out CAMERA.json
      One camera (f + k1, centred principal point) for all views of the same
      phone and zoom. Prints the reprojection error per view, the camera
      centres and the angle between each pair of views.
  plane CAMERA.json --view I --pt u,v [--pt u,v ...] [--z H]
      Pixel -> mat point at height Z (default 0, the mat).
  tri CAMERA.json --view I --pt u,v --view J --pt u,v
      Triangulate one feature seen in 2+ views. Prints X, Y, Z and the ray miss
      distances (the check: a miss over ~1 mm = not the same physical point).
"""
import argparse, json, sys
import numpy as np, cv2
from PIL import Image, ImageOps


def load(photo):
    return np.array(ImageOps.exif_transpose(Image.open(photo)).convert("RGB"))


def cmd_lines(a):
    img = load(a.photo)
    hsv = cv2.cvtColor(img, cv2.COLOR_RGB2HSV)
    h, s, v = (hsv[..., i].astype(np.float32) for i in range(3))
    white = v - 1.5 * s                                   # lines: less saturated, brighter
    ridge = white - cv2.GaussianBlur(white, (0, 0), 15)
    h0, h1 = (float(x) for x in a.hue.split(","))
    mat = (h > h0) & (h < h1) & (s > 5) & (s < 120) & (v > 120)
    mat = cv2.erode(mat.astype(np.uint8), np.ones((5, 5)), 1)
    mat = cv2.dilate(mat, np.ones((31, 31)), 1)
    m = ((ridge > a.rt) & (mat > 0)).astype(np.uint8) * 255
    segs = cv2.HoughLinesP(m, 1, np.pi / 720, threshold=300, minLineLength=500, maxLineGap=40)
    segs = np.zeros((0, 4)) if segs is None else np.asarray(segs).reshape(-1, 4).astype(float)
    json.dump({"segs": segs.tolist(), "size": [img.shape[1], img.shape[0]]},
              open(a.out.rsplit(".", 1)[0] + ".json", "w"))
    vis = img.copy()
    for x1, y1, x2, y2 in segs.astype(int):
        cv2.line(vis, (x1, y1), (x2, y2), (255, 0, 0), 3)
    Image.fromarray(vis).resize((vis.shape[1] // 3, vis.shape[0] // 3)).save(a.out)
    print(f"{len(segs)} segments -> {a.out}")


def to_mm(H, pts):
    return cv2.perspectiveTransform(np.asarray(pts, float).reshape(-1, 1, 2), H).reshape(-1, 2)


def cmd_grid(a):
    segs = np.array(json.load(open(a.segs))["segs"])
    rough = json.load(open(a.rough))
    H, _ = cv2.findHomography(np.float64([r[1] for r in rough]), np.float64([r[0] for r in rough]))
    p = a.pitch

    def label(H, tol):
        fam = {"X": {}, "Y": {}}
        for sg in segs:
            e0, e1 = to_mm(H, [sg[:2], sg[2:]])
            for k, i in (("X", 0), ("Y", 1)):
                o = 1 - i
                if abs(e1[o] - e0[o]) < 3 * abs(e1[i] - e0[i]):     # must run along the other axis
                    continue
                n0, n1 = np.round(e0[i] / p), np.round(e1[i] / p)
                if n0 == n1 and abs(e0[i] - p * n0) < tol and abs(e1[i] - p * n0) < tol:
                    fam[k].setdefault(int(n0), []).append(sg)
        return fam

    def fit_line(ss):
        samp = np.array([sg[:2] * (1 - t) + sg[2:] * t for sg in ss
                         for t in np.linspace(0, 1, max(2, int(np.hypot(*(sg[2:] - sg[:2])) / 50)))])
        vx, vy, x0, y0 = cv2.fitLine(samp.astype(np.float32), cv2.DIST_HUBER, 0, 0.01, 0.01).ravel()
        return np.array([x0, y0]), np.array([vx, vy]), samp

    for it in range(3):
        fam = label(H, 3.0 if it == 0 else 1.5)
        L = {k: {n: fit_line(ss) for n, ss in d.items()} for k, d in fam.items()}
        pairs = []
        for nx, (px, dx, sx) in L["X"].items():
            for ny, (py, dy, sy) in L["Y"].items():
                t = np.linalg.solve(np.array([dx, -dy]).T, py - px)
                q = px + t[0] * dx
                # keep intersections near detected pixels of both lines (visible mat only)
                if np.min(np.hypot(*(sx - q).T)) < 120 and np.min(np.hypot(*(sy - q).T)) < 120:
                    pairs.append([[p * nx, p * ny], [float(q[0]), float(q[1])], f"X{nx}Y{ny}"])
        if len(pairs) < 6:
            sys.exit(f"only {len(pairs)} grid points: check the rough points and the lines overlay")
        M = np.float64([q[0] for q in pairs]); P = np.float64([q[1] for q in pairs])
        H, _ = cv2.findHomography(P, M)
        res = np.hypot(*(to_mm(H, P) - M).T)
        print(f"iter {it}: {len(L['X'])} X lines, {len(L['Y'])} Y lines, {len(pairs)} points, "
              f"rms {np.sqrt(np.mean(res ** 2)):.2f} max {res.max():.2f} mm")
    loo = []
    for i in range(len(P)):
        m = np.ones(len(P), bool); m[i] = False
        Hi, _ = cv2.findHomography(P[m], M[m])
        loo.append(np.hypot(*(to_mm(Hi, P[i:i + 1])[0] - M[i])))
    loo = np.array(loo)
    print(f"leave-one-out mean {loo.mean():.2f} max {loo.max():.2f} mm (worst {pairs[int(loo.argmax())][2]})")
    json.dump(pairs, open(a.out, "w"))


def cmd_calib(a):
    W, Hh = (int(x) for x in a.size.split(","))
    obj, img = [], []
    for f in a.pairs:
        pr = json.load(open(f))
        obj.append(np.float32([[q[0][0], q[0][1], 0] for q in pr]))
        img.append(np.float32([q[1] for q in pr]))
    K0 = np.array([[1.3 * W, 0, W / 2], [0, 1.3 * W, Hh / 2], [0, 0, 1.0]])
    flags = (cv2.CALIB_USE_INTRINSIC_GUESS | cv2.CALIB_FIX_PRINCIPAL_POINT | cv2.CALIB_FIX_ASPECT_RATIO
             | cv2.CALIB_ZERO_TANGENT_DIST | cv2.CALIB_FIX_K2 | cv2.CALIB_FIX_K3)
    rms, K, D, rv, tv = cv2.calibrateCamera(obj, img, (W, Hh), K0, np.zeros(5), flags=flags)
    print(f"f {K[0, 0]:.0f} px, k1 {D.ravel()[0]:.3f}, rms {rms:.2f} px")
    C = []
    for f, o, i, r, t in zip(a.pairs, obj, img, rv, tv):
        pr, _ = cv2.projectPoints(o, r, t, K, D)
        e = np.sqrt(np.mean(np.sum((pr.reshape(-1, 2) - i) ** 2, 1)))
        R = cv2.Rodrigues(r)[0]; C.append(-R.T @ t.ravel())
        print(f"  {f}: reproj rms {e:.2f} px, camera at {np.round(C[-1], 0)} mm")
    for i in range(len(C)):
        for j in range(i + 1, len(C)):
            mid = np.vstack(obj).mean(0)   # angle seen from the middle of the mat points
            u, v = C[i] - mid, C[j] - mid
            ang = np.degrees(np.arccos(np.dot(u, v) / np.linalg.norm(u) / np.linalg.norm(v)))
            note = "  <- too close to triangulate" if ang < 10 else ""
            print(f"  views {i}-{j}: {ang:.0f} deg apart{note}")
    json.dump(dict(K=K.tolist(), D=D.ravel().tolist(), rv=[r.ravel().tolist() for r in rv],
                   tv=[t.ravel().tolist() for t in tv], views=a.pairs, size=[W, Hh]), open(a.out, "w"))


def pose(c, i):
    R = cv2.Rodrigues(np.array(c["rv"][i]))[0]; t = np.array(c["tv"][i])
    return np.array(c["K"]), np.array(c["D"]), R, t


def ray(c, i, uv):
    K, D, R, t = pose(c, i)
    und = cv2.undistortPoints(np.float64([uv]).reshape(-1, 1, 2), K, D).ravel()
    d = R.T @ np.array([und[0], und[1], 1.0])
    return -R.T @ t, d / np.linalg.norm(d)


def pt(s):
    return [float(x) for x in s.split(",")]


def cmd_plane(a):
    c = json.load(open(a.camera))
    for s in a.pt:
        o, d = ray(c, a.view, pt(s))
        X = o + (a.z - o[2]) / d[2] * d
        print(f"{s} -> X {X[0]:.2f} Y {X[1]:.2f} (Z {a.z})")


def cmd_tri(a):
    c = json.load(open(a.camera))
    if len(a.view) != len(a.pt) or len(a.view) < 2:
        sys.exit("give one --view per --pt, 2 or more")
    A = np.zeros((3, 3)); b = np.zeros(3); rays = []
    for i, s in zip(a.view, a.pt):
        o, d = ray(c, i, pt(s)); rays.append((o, d))
        Pm = np.eye(3) - np.outer(d, d); A += Pm; b += Pm @ o
    X = np.linalg.solve(A, b)
    miss = [np.linalg.norm((np.eye(3) - np.outer(d, d)) @ (X - o)) for o, d in rays]
    print(f"X {X[0]:.2f} Y {X[1]:.2f} Z {X[2]:.2f} mm, ray miss {', '.join(f'{m:.2f}' for m in miss)} mm")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    s = sp.add_parser("lines"); s.add_argument("photo"); s.add_argument("--out", required=True)
    s.add_argument("--rt", type=float, default=12); s.add_argument("--hue", default="40,110")
    s = sp.add_parser("grid"); s.add_argument("segs"); s.add_argument("--rough", required=True)
    s.add_argument("--out", required=True); s.add_argument("--pitch", type=float, default=10.0)
    s = sp.add_parser("calib"); s.add_argument("pairs", nargs="+"); s.add_argument("--size", required=True)
    s.add_argument("--out", required=True)
    s = sp.add_parser("plane"); s.add_argument("camera"); s.add_argument("--view", type=int, required=True)
    s.add_argument("--pt", action="append", required=True); s.add_argument("--z", type=float, default=0.0)
    s = sp.add_parser("tri"); s.add_argument("camera"); s.add_argument("--view", type=int, action="append")
    s.add_argument("--pt", action="append")
    a = ap.parse_args()
    dict(lines=cmd_lines, grid=cmd_grid, calib=cmd_calib, plane=cmd_plane, tri=cmd_tri)[a.cmd](a)


if __name__ == "__main__":
    main()
