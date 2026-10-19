#!/usr/bin/env bash
# Fit test for a one-page design sheet.
#
#   fit-check.sh "designs/2026-10-08 - Title.html" [--keep]
#
# Renders the sheet with headless Chrome and reports:
#   1. the number of printed pages (must be 1)
#   2. every element whose content overflows its box at page size
#
# Exit 0 when the sheet prints on one page with no overflow. Exit 1
# otherwise. --keep leaves the PDF next to the HTML file.
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "usage: fit-check.sh <sheet.html> [--keep]" >&2
  exit 2
fi

sheet="$1"
keep="${2:-}"
[ -f "$sheet" ] || { echo "no such file: $sheet" >&2; exit 2; }

chrome=""
for c in \
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  "$(command -v google-chrome || true)" \
  "$(command -v chromium || true)" \
  "$(command -v chromium-browser || true)"; do
  if [ -n "$c" ] && [ -x "$c" ]; then chrome="$c"; break; fi
done
[ -n "$chrome" ] || { echo "no Chrome or Chromium found" >&2; exit 2; }

abs="$(cd "$(dirname "$sheet")" && pwd)/$(basename "$sheet")"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

# 1. Page count. --no-pdf-header-footer keeps the @page margins honest.
pdf="$tmp/sheet.pdf"
"$chrome" --headless=new --disable-gpu --no-pdf-header-footer \
  --print-to-pdf="$pdf" "file://$abs" >/dev/null 2>&1
pages="$(python3 -c "import re,sys;print(len(re.findall(rb'/Type\s*/Page[^s]',open(sys.argv[1],'rb').read())))" "$pdf")"
if [ "$keep" = "--keep" ]; then cp "$pdf" "${abs%.html}.pdf"; fi

# 2. Overflow report. A copy of the sheet gets a style that pins html,
# body and article to the printable page box (page size minus the
# @page margin, at 96 dpi) and a script that marks every element whose
# scroll size exceeds its client size. --dump-dom returns the marked
# DOM. The headless window loses ~90px to browser chrome, so the box
# is pinned in CSS and the window is made larger than the box.
copy="$tmp/copy.html"
box="$(python3 - "$abs" <<'PY'
import re, sys
css = open(sys.argv[1], encoding="utf-8").read()
m = re.search(r'@page\s*\{([^}]*)\}', css)
decl = m.group(1) if m else ""
size = re.search(r'size\s*:\s*([^;]+)', decl)
size = size.group(1).strip().lower() if size else "letter landscape"
margin = re.search(r'margin\s*:\s*([\d.]+)\s*(mm|in|cm|pt|px)', decl)
mv, mu = (float(margin.group(1)), margin.group(2)) if margin else (12.0, "mm")
to_px = {"mm": 96/25.4, "cm": 96/2.54, "in": 96.0, "pt": 96/72, "px": 1.0}[mu]
m_px = mv * to_px
pages = {"letter": (8.5*96, 11*96), "a4": (210*96/25.4, 297*96/25.4),
         "legal": (8.5*96, 14*96), "a3": (297*96/25.4, 420*96/25.4),
         "tabloid": (11*96, 17*96), "ledger": (17*96, 11*96)}
name = next((k for k in pages if k in size), "letter")
w, h = pages[name]
if "landscape" in size:
    w, h = h, w
print(f"{round(w - 2*m_px)} {round(h - 2*m_px)}")
PY
)"
box_w="${box% *}"
box_h="${box#* }"
python3 - "$abs" "$copy" "$box_w" "$box_h" <<'PY'
import sys
src, dst, w, h = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
html = open(src, encoding="utf-8").read()
pin = f"""
<style>
  html, body {{ width: {w}px !important; height: {h}px !important; overflow: visible !important; }}
  article {{ height: {h}px !important; }}
</style>
"""
html = html.replace("</head>", pin + "</head>", 1) if "</head>" in html else pin + html
probe = r"""
<script>
(function () {
  var hits = [];
  document.querySelectorAll('body *').forEach(function (el) {
    if (el instanceof SVGElement) return;
    var cs = getComputedStyle(el);
    if (cs.display === 'none') return;
    var dy = el.scrollHeight - el.clientHeight;
    var dx = el.scrollWidth - el.clientWidth;
    if (dy > 2 || dx > 2) {
      var tag = el.tagName.toLowerCase();
      if (el.id) tag += '#' + el.id;
      if (el.className && typeof el.className === 'string') tag += '.' + el.className.split(' ').join('.');
      hits.push(tag + ' +' + dy + 'px tall, +' + dx + 'px wide');
    }
  });
  var m = document.createElement('meta');
  m.name = 'fit-overflow';
  m.content = hits.join(' | ') || 'none';
  document.head.appendChild(m);

  /* geometry of the figure: connector rules */
  var geo = [];
  var svg = document.querySelector('figure svg');
  if (svg) {
    var nodes = [];
    svg.querySelectorAll('[data-id]').forEach(function (g) {
      if (g.classList.contains('edge')) return;
      var r = g.querySelector('rect.node') || g.querySelector('rect');
      if (!r) return;
      nodes.push({ id: g.getAttribute('data-id'), x: +r.getAttribute('x'), y: +r.getAttribute('y'),
        w: +r.getAttribute('width'), h: +r.getAttribute('height'), region: r.classList.contains('region-box') });
    });
    function inside(p, n, pad) { return p.x > n.x + pad && p.x < n.x + n.w - pad && p.y > n.y + pad && p.y < n.y + n.h - pad; }
    function rectDist(p, b) {
      var dx = Math.max(b.x - p.x, 0, p.x - (b.x + b.w)), dy = Math.max(b.y - p.y, 0, p.y - (b.y + b.h));
      return Math.sqrt(dx * dx + dy * dy);
    }
    var ports = [];
    var edges = svg.querySelectorAll('.edge');
    edges.forEach(function (e) {
      var id = e.getAttribute('data-id') || '?';
      var rel = (e.getAttribute('data-rel') || '').split(/\s+/);
      e.querySelectorAll('path').forEach(function (p) {
        var d = p.getAttribute('d') || '';
        if (/[CcQqSsTtAa]/.test(d)) geo.push(id + ': curved segment; use straight lines and rounded elbows');
        var pts = [], cur = null, m;
        var re = /([MLHVmlhv])\s*([-\d.,\s]*)/g;
        while ((m = re.exec(d))) {
          var nums = m[2].trim().split(/[\s,]+/).filter(Boolean).map(Number), c = m[1];
          for (var i = 0; i < nums.length;) {
            var nx, ny;
            if (c === 'M' || c === 'L') { nx = nums[i]; ny = nums[i + 1]; i += 2; }
            else if (c === 'm' || c === 'l') { nx = cur.x + nums[i]; ny = cur.y + nums[i + 1]; i += 2; }
            else if (c === 'H') { nx = nums[i]; ny = cur.y; i += 1; }
            else if (c === 'h') { nx = cur.x + nums[i]; ny = cur.y; i += 1; }
            else if (c === 'V') { nx = cur.x; ny = nums[i]; i += 1; }
            else { nx = cur.x; ny = cur.y + nums[i]; i += 1; }
            cur = { x: nx, y: ny }; pts.push(cur);
          }
        }
        for (var k = 1; k < pts.length; k++) {
          var ddx = Math.abs(pts[k].x - pts[k - 1].x), ddy = Math.abs(pts[k].y - pts[k - 1].y);
          if (ddx > 1.5 && ddy > 1.5) { geo.push(id + ': diagonal segment ' + pts[k - 1].x + ',' + pts[k - 1].y + ' to ' + pts[k].x + ',' + pts[k].y); break; }
        }
        if (pts.length) { ports.push({ e: id, p: pts[0] }); ports.push({ e: id, p: pts[pts.length - 1] }); }
        var len = p.getTotalLength ? p.getTotalLength() : 0;
        var hit = {};
        for (var t = 4; t < len - 4; t += 3) {
          var q = p.getPointAtLength(t);
          nodes.forEach(function (n) {
            if (n.region || rel.indexOf(n.id) >= 0 || hit[n.id]) return;
            if (inside(q, n, 1)) { hit[n.id] = 1; geo.push(id + ': passes behind node ' + n.id); }
          });
        }
        e.querySelectorAll('text').forEach(function (tx) {
          var tf = tx.getAttribute('transform') || '';
          if (/rotate/.test(tf)) { geo.push(id + ': rotated label "' + tx.textContent.trim() + '"'); return; }
          var b = tx.getBBox();
          var box = { x: b.x, y: b.y, w: b.width, h: b.height };
          var best = 1e9;
          for (var t2 = 0; t2 <= len; t2 += 2) { var q2 = p.getPointAtLength(t2); var dd = rectDist(q2, box); if (dd < best) best = dd; }
          if (best < 4) geo.push(id + ': label "' + tx.textContent.trim() + '" is ' + best.toFixed(1) + 'px from its stroke; keep 4px or more');
          nodes.forEach(function (n) {
            if (n.region) return;
            var ox = Math.min(box.x + box.w, n.x + n.w) - Math.max(box.x, n.x), oy = Math.min(box.y + box.h, n.y + n.h) - Math.max(box.y, n.y);
            if (ox > 1 && oy > 1) geo.push(id + ': label "' + tx.textContent.trim() + '" overlaps node ' + n.id);
          });
        });
      });
    });
    for (var a = 0; a < ports.length; a++) for (var b2 = a + 1; b2 < ports.length; b2++) {
      if (ports[a].e === ports[b2].e) continue;
      var pd = Math.hypot(ports[a].p.x - ports[b2].p.x, ports[a].p.y - ports[b2].p.y);
      if (pd < 10) geo.push(ports[a].e + ' and ' + ports[b2].e + ': attach points ' + pd.toFixed(1) + 'px apart; fan them 10px or more');
    }
    var t0 = svg.querySelector(':scope > title'), d0 = svg.querySelector(':scope > desc');
    if (!t0 || !d0) geo.push('figure: svg needs a <title> and a <desc> as its first children');
    var g2 = document.createElement('meta');
    g2.name = 'fit-budget';
    g2.content = nodes.filter(function (n) { return !n.region; }).length + ' nodes, ' + edges.length + ' edges';
    document.head.appendChild(g2);
  }
  var g1 = document.createElement('meta');
  g1.name = 'fit-geometry';
  g1.content = geo.join(' | ') || 'none';
  document.head.appendChild(g1);
})();
</script>
"""
if "</body>" in html:
    html = html.replace("</body>", probe + "</body>", 1)
else:
    html += probe
open(dst, "w", encoding="utf-8").write(html)
PY

size="$((box_w + 200)),$((box_h + 200))"

dom="$tmp/dom.html"
"$chrome" --headless=new --disable-gpu --window-size="$size" \
  --dump-dom "file://$copy" > "$dom" 2>/dev/null
meta() { python3 -c "import re,sys,html;m=re.search(r'name=\"'+sys.argv[2]+r'\" content=\"([^\"]*)\"',open(sys.argv[1],encoding='utf-8').read());print(html.unescape(m.group(1)) if m else 'probe did not run')" "$dom" "$1"; }
overflow="$(meta fit-overflow)"
geometry="$(meta fit-geometry)"
budget="$(meta fit-budget)"

# 3. The screen layer must not change the print. Render a copy with every
# <script> removed and compare page count and extracted text.
noscript="$tmp/noscript.html"
python3 -c "import re,sys;h=open(sys.argv[1],encoding='utf-8').read();open(sys.argv[2],'w',encoding='utf-8').write(re.sub(r'<script\b.*?</script>','',h,flags=re.S|re.I))" "$abs" "$noscript"
"$chrome" --headless=new --disable-gpu --no-pdf-header-footer \
  --print-to-pdf="$tmp/noscript.pdf" "file://$noscript" >/dev/null 2>&1
pages_ns="$(python3 -c "import re,sys;print(len(re.findall(rb'/Type\s*/Page[^s]',open(sys.argv[1],'rb').read())))" "$tmp/noscript.pdf")"
if command -v pdftotext >/dev/null; then
  t1="$(pdftotext -layout "$pdf" - 2>/dev/null | tr -s ' \n' ' ')"
  t2="$(pdftotext -layout "$tmp/noscript.pdf" - 2>/dev/null | tr -s ' \n' ' ')"
  if [ "$pages" = "$pages_ns" ] && [ "$t1" = "$t2" ]; then print_same="yes"; else print_same="no"; fi
else
  if [ "$pages" = "$pages_ns" ]; then print_same="yes (pages only, pdftotext missing)"; else print_same="no"; fi
fi

# 4. Provenance. Every <text> in the figure and every <p>/<li> in an aside
# needs data-src on itself or an ancestor.
nosrc="$(python3 - "$abs" <<'PY'
import re, sys
from html.parser import HTMLParser
html = open(sys.argv[1], encoding="utf-8").read()
class P(HTMLParser):
    def __init__(self):
        super().__init__(); self.stack=[]; self.miss=[]; self.infig=0; self.inaside=0
    def handle_starttag(self, tag, attrs):
        a=dict(attrs); has=('data-src' in a) or any(s for s in self.stack)
        self.stack.append('data-src' in a)
        if tag=='figure': self.infig+=1
        if tag=='aside': self.inaside+=1
        if (tag=='text' and self.infig) or (tag in('p','li') and self.inaside):
            if not has: self.miss.append(tag+'@'+str(self.getpos()[0]))
    def handle_endtag(self, tag):
        if self.stack: self.stack.pop()
        if tag=='figure': self.infig-=1
        if tag=='aside': self.inaside-=1
p=P(); p.feed(html)
print(len(p.miss), ' '.join(p.miss[:12]))
PY
)"
nosrc_n="${nosrc%% *}"

echo "pages: $pages"
echo "overflow: $overflow"
echo "print same without script: $print_same"
echo "labels without data-src: $nosrc"
echo "geometry: $geometry"
echo "budget: $budget (guide: 12 nodes, 18 edges; split above that)"

status=0
[ "$pages" = "1" ] || status=1
[ "$overflow" = "none" ] || status=1
case "$print_same" in yes*) ;; *) status=1 ;; esac
[ "$nosrc_n" = "0" ] || status=1
[ "$geometry" = "none" ] || status=1
if [ $status -eq 0 ]; then
  echo "FIT"
else
  echo "DOES NOT FIT: change the frame or cut facts. Do not shrink the type."
fi
exit $status
