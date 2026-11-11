"""Before/after sheet of Anim Lab shots.

python compare_sheet.py <shots dir> <out.png> <before_suffix> <after_suffix> <name> [<name> ...]

Each row is <shots dir>/<name><before_suffix>.png beside <name><after_suffix>.png, at half size, with a
label. Example: python compare_sheet.py Saved/AnimLab/Shots cmp.png _off _on cmp_e065_front cmp_e065_fp
"""
import os
import sys

from PIL import Image, ImageDraw

if len(sys.argv) < 6:
    sys.exit(__doc__)
SHOTS, out, before, after, names = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5:]
if not names:
    sys.exit(__doc__)
rows = []
for name in names:
    pair = []
    for suffix in (before, after):
        image = Image.open(os.path.join(SHOTS, name + suffix + ".png")).convert("RGB")
        pair.append(image.resize((image.width // 2, image.height // 2)))
    rows.append(pair)
w, h = rows[0][0].size
sheet = Image.new("RGB", (w * 2 + 10, (h + 10) * len(rows)), "black")
draw = ImageDraw.Draw(sheet)
for i, (a, b) in enumerate(rows):
    y = i * (h + 10)
    sheet.paste(a, (0, y))
    sheet.paste(b, (w + 10, y))
    draw.text((10, y + 5), f"BEFORE {names[i]}{before}", fill="yellow")
    draw.text((w + 20, y + 5), f"AFTER {names[i]}{after}", fill="yellow")
sheet.save(out)
print(out, sheet.size)
