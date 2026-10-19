#!/usr/bin/env bash
# Create a dated sheet from the skeleton, with the screen layer inlined.
#
#   new-sheet.sh "<title>" [<frame>] [<designs dir>]
#
# Writes <designs dir>/YYYY-MM-DD - <title>.html (default dir: designs/
# in the current directory) and prints its path. Refuses to overwrite.
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
title="${1:?title}"
frame="${2:-unknown}"
dir="${3:-designs}"
date="$(date +%F)"
mkdir -p "$dir"
out="$dir/$date - $title.html"
[ -e "$out" ] && { echo "exists: $out" >&2; exit 1; }
python3 - "$here/skeleton.html" "$here/screen-layer.js" "$out" "$title" "$date" "$frame" <<'PY'
import sys, html
skel, js, out, title, date, frame = sys.argv[1:7]
h = open(skel, encoding="utf-8").read()
h = h.replace("TITLE", html.escape(title)).replace("DATE", date).replace("FRAME", html.escape(frame))
h = h.replace("<!--SCREEN-LAYER-->", "<script>\n" + open(js, encoding="utf-8").read() + "</script>")
open(out, "w", encoding="utf-8").write(h)
print(out)
PY
