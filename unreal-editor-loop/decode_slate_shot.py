"""decode_slate_shot.py <tool-result.txt> <out.png> [x0 y0 x1 y1]

The SlateInspectorToolset Screenshot result is too big for the context: the harness saves it to a .txt file. This finds
the base64 PNG in that JSON, saves it, and crops it when a box is given. It prints the full image size.
Needs pillow (on Windows: `py`, not the Git Bash `python`).
"""
import base64
import io
import json
import sys

from PIL import Image


def find(o):
    if isinstance(o, dict):
        if isinstance(o.get("data"), str) and len(o["data"]) > 1000:
            return o["data"]
        o = list(o.values())
    if isinstance(o, list):
        for v in o:
            r = find(v)
            if r:
                return r
    if isinstance(o, str) and o.startswith("{"):
        try:
            return find(json.loads(o))
        except ValueError:
            return None
    return None


data = find(json.load(open(sys.argv[1], encoding="utf-8")))
if not data:
    sys.exit("no image in " + sys.argv[1])
im = Image.open(io.BytesIO(base64.b64decode(data))).convert("RGB")
box = tuple(int(v) for v in sys.argv[3:7]) if len(sys.argv) >= 7 else None
(im.crop(box) if box else im).save(sys.argv[2])
print(im.size)
