/* one-page-design screen layer.
 * Inlined into a sheet by the skill. Runs only on screen. It never
 * changes the print: everything it adds carries class "screen-only",
 * which the sheet's print CSS hides, except pencil marks, which print.
 *
 * Markup it reads:
 *   data-id="x"        a node, edge or callout the layer can address
 *   data-rel="a b"     ids this element is related to (edges list both ends)
 *   data-for="x"       a callout that describes node x
 *   data-src="path:12" where the label was read; "user" or "unknown" allowed
 *
 * Keys: wheel or pinch zooms, drag pans, 0 resets, P pencil, E erase
 * last stroke, S saves the marks as a sidecar SVG.
 */
(function () {
  if (matchMedia('print').matches) return;
  var stage = document.querySelector('.stage');
  var fig = document.querySelector('figure svg');
  if (!stage || !fig) return;
  var SO = 'screen-only';

  /* ---------- 1. trace relationships ---------- */
  var nodes = Array.prototype.slice.call(document.querySelectorAll('[data-id]'));
  var byId = {};
  nodes.forEach(function (n) { byId[n.getAttribute('data-id')] = n; });
  function rels(el) {
    var set = {};
    set[el.getAttribute('data-id')] = 1;
    (el.getAttribute('data-rel') || '').split(/\s+/).forEach(function (r) { if (r) set[r] = 1; });
    var f = el.getAttribute('data-for');
    if (f) set[f] = 1;
    nodes.forEach(function (n) {
      var r = (n.getAttribute('data-rel') || '').split(/\s+/);
      if (r.indexOf(el.getAttribute('data-id')) >= 0) set[n.getAttribute('data-id')] = 1;
      if (n.getAttribute('data-for') === el.getAttribute('data-id')) set[n.getAttribute('data-id')] = 1;
    });
    return set;
  }
  var tracing = null;
  function trace(el) {
    tracing = el;
    var keep = el ? rels(el) : null;
    nodes.forEach(function (n) {
      var id = n.getAttribute('data-id');
      n.classList.toggle('dim', !!keep && !keep[id]);
      n.classList.toggle('lit', !!keep && !!keep[id] && n !== el);
      n.classList.toggle('focus', n === el);
    });
    drawLeaders(el);
  }
  nodes.forEach(function (n) {
    if (!n.hasAttribute('tabindex')) n.setAttribute('tabindex', '0');
    n.addEventListener('mouseenter', function () { trace(n); });
    n.addEventListener('focus', function () { trace(n); });
    n.addEventListener('mouseleave', function () { trace(null); });
    n.addEventListener('blur', function () { trace(null); });
  });

  /* leader line from a callout to the node it describes */
  var leaders = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  leaders.setAttribute('class', SO + ' leaders');
  leaders.style.cssText = 'position:fixed;inset:0;width:100%;height:100%;pointer-events:none;z-index:5';
  document.body.appendChild(leaders);
  function center(el) {
    var b = el.getBoundingClientRect();
    return { x: b.left + b.width / 2, y: b.top + b.height / 2, l: b.left, r: b.right, t: b.top, b: b.bottom };
  }
  function drawLeaders(el) {
    while (leaders.firstChild) leaders.removeChild(leaders.firstChild);
    if (!el) return;
    var pairs = [];
    var f = el.getAttribute('data-for');
    if (f && byId[f]) pairs.push([el, byId[f]]);
    nodes.forEach(function (n) {
      if (n.getAttribute('data-for') === el.getAttribute('data-id')) pairs.push([n, el]);
    });
    pairs.forEach(function (p) {
      var a = center(p[0]), b = center(p[1]);
      var ax = a.x < b.x ? a.r : a.l;
      var line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
      line.setAttribute('x1', ax); line.setAttribute('y1', a.y);
      line.setAttribute('x2', b.x); line.setAttribute('y2', b.y);
      line.setAttribute('stroke', '#b5542a'); line.setAttribute('stroke-width', '1.2');
      line.setAttribute('stroke-dasharray', '3 3');
      leaders.appendChild(line);
    });
  }

  /* ---------- 2. provenance ---------- */
  var tip = document.createElement('div');
  tip.className = SO + ' src-tip';
  tip.style.cssText = 'position:fixed;display:none;font:9pt ui-monospace,Menlo,monospace;background:#1a1a1a;color:#fff;padding:2px 6px;border-radius:2px;pointer-events:none;z-index:6;max-width:60vw;white-space:nowrap;overflow:hidden;text-overflow:ellipsis';
  document.body.appendChild(tip);
  Array.prototype.forEach.call(document.querySelectorAll('[data-src]'), function (el) {
    el.addEventListener('mouseenter', function () {
      tip.textContent = el.getAttribute('data-src');
      tip.style.display = 'block';
    });
    el.addEventListener('mousemove', function (e) {
      tip.style.left = (e.clientX + 12) + 'px';
      tip.style.top = (e.clientY + 14) + 'px';
    });
    el.addEventListener('mouseleave', function () { tip.style.display = 'none'; });
    el.addEventListener('click', function (e) {
      if (pencil) return;
      var s = el.getAttribute('data-src');
      if (navigator.clipboard) navigator.clipboard.writeText(s).then(function () {
        tip.textContent = 'copied: ' + s;
      });
      e.stopPropagation();
    });
  });

  /* ---------- 3. zoom as walking closer ---------- */
  var vb0 = (fig.getAttribute('viewBox') || '0 0 800 500').split(/[\s,]+/).map(Number);
  var vb = vb0.slice();
  function setVB() { fig.setAttribute('viewBox', vb.join(' ')); drawLeaders(tracing); }
  function toSvg(e) {
    var r = fig.getBoundingClientRect();
    var sx = vb[2] / r.width, sy = vb[3] / r.height, s = Math.max(sx, sy);
    var ox = (r.width - vb[2] / s) / 2, oy = (r.height - vb[3] / s) / 2;
    return { x: vb[0] + (e.clientX - r.left - ox) * s, y: vb[1] + (e.clientY - r.top - oy) * s, s: s };
  }
  fig.addEventListener('wheel', function (e) {
    e.preventDefault();
    var p = toSvg(e);
    var k = Math.exp(e.deltaY * 0.0015);
    var nw = Math.min(vb0[2] * 1.5, Math.max(vb0[2] / 12, vb[2] * k));
    k = nw / vb[2];
    vb = [p.x - (p.x - vb[0]) * k, p.y - (p.y - vb[1]) * k, vb[2] * k, vb[3] * k];
    setVB();
  }, { passive: false });
  var drag = null;
  fig.addEventListener('pointerdown', function (e) {
    if (pencil) return;
    drag = { x: e.clientX, y: e.clientY, vb: vb.slice() };
    fig.setPointerCapture(e.pointerId);
  });
  fig.addEventListener('pointermove', function (e) {
    if (!drag) return;
    var r = fig.getBoundingClientRect();
    var s = Math.max(vb[2] / r.width, vb[3] / r.height);
    vb[0] = drag.vb[0] - (e.clientX - drag.x) * s;
    vb[1] = drag.vb[1] - (e.clientY - drag.y) * s;
    setVB();
  });
  fig.addEventListener('pointerup', function () { drag = null; });
  fig.addEventListener('dblclick', function () { vb = vb0.slice(); setVB(); });
  fig.style.cursor = 'grab';

  /* ---------- 4. the pencil ---------- */
  var pencil = false;
  var marks = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  marks.setAttribute('class', 'marks');
  marks.style.cssText = 'position:absolute;inset:0;width:100%;height:100%;pointer-events:none;z-index:4;overflow:visible';
  if (getComputedStyle(stage).position === 'static') stage.style.position = 'relative';
  stage.appendChild(marks);
  var key = 'opd-marks:' + location.pathname;
  function sizeMarks() {
    var r = stage.getBoundingClientRect();
    marks.setAttribute('viewBox', '0 0 ' + r.width + ' ' + r.height);
    marks.setAttribute('preserveAspectRatio', 'none');
  }
  sizeMarks();
  addEventListener('resize', sizeMarks);
  function stroke() {
    var p = document.createElementNS('http://www.w3.org/2000/svg', 'polyline');
    p.setAttribute('fill', 'none'); p.setAttribute('stroke', '#b5542a');
    p.setAttribute('stroke-width', '1.6'); p.setAttribute('stroke-linecap', 'round');
    p.setAttribute('stroke-linejoin', 'round'); p.setAttribute('opacity', '0.9');
    marks.appendChild(p);
    return p;
  }
  try {
    var saved = localStorage.getItem(key);
    if (saved) JSON.parse(saved).forEach(function (pts) { stroke().setAttribute('points', pts); });
  } catch (e) {}
  function persist() {
    try {
      localStorage.setItem(key, JSON.stringify(Array.prototype.map.call(marks.children, function (p) { return p.getAttribute('points'); })));
    } catch (e) {}
  }
  var cur = null;
  function pt(e) { var r = stage.getBoundingClientRect(); return (e.clientX - r.left).toFixed(1) + ',' + (e.clientY - r.top).toFixed(1); }
  stage.addEventListener('pointerdown', function (e) {
    if (!pencil) return;
    cur = stroke(); cur.setAttribute('points', pt(e));
    stage.setPointerCapture(e.pointerId);
    e.preventDefault();
  });
  stage.addEventListener('pointermove', function (e) {
    if (!cur) return;
    cur.setAttribute('points', cur.getAttribute('points') + ' ' + pt(e));
  });
  stage.addEventListener('pointerup', function () { if (cur) { cur = null; persist(); } });
  function setPencil(on) {
    pencil = on;
    stage.classList.toggle('pencil', on);
    stage.style.cursor = on ? 'crosshair' : '';
    marks.style.pointerEvents = 'none';
    legend.querySelector('b').textContent = on ? 'pencil on' : '';
  }
  function saveMarks() {
    var r = stage.getBoundingClientRect();
    var out = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ' + r.width + ' ' + r.height + '">' +
      '<!-- marks for ' + document.title + ', ' + new Date().toISOString().slice(0, 10) + ' -->' +
      marks.innerHTML + '</svg>';
    var a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([out], { type: 'image/svg+xml' }));
    a.download = document.title + '.marks.svg';
    a.click();
  }

  /* ---------- legend and keys ---------- */
  var legend = document.createElement('div');
  legend.className = SO + ' legend';
  legend.style.cssText = 'position:fixed;right:10px;bottom:8px;font:8.5pt system-ui,sans-serif;color:#666;background:rgba(255,255,255,.85);padding:3px 8px;border-radius:3px;z-index:6';
  legend.innerHTML = 'hover traces · wheel zooms, drag pans, double-click resets · P pencil · E erase last · S save marks <b style="color:#b5542a"></b>';
  document.body.appendChild(legend);
  addEventListener('keydown', function (e) {
    if (e.target && /input|textarea/i.test(e.target.tagName)) return;
    var k = e.key.toLowerCase();
    if (k === 'p') setPencil(!pencil);
    else if (k === 'e' && marks.lastChild) { marks.removeChild(marks.lastChild); persist(); }
    else if (k === 's') { e.preventDefault(); saveMarks(); }
    else if (k === '0') { vb = vb0.slice(); setVB(); }
    else if (k === 'escape') { setPencil(false); trace(null); }
  });

  var css = document.createElement('style');
  css.textContent =
    '@media screen{' +
    '[data-id]{transition:opacity .15s}' +
    '[data-id].dim{opacity:.18}' +
    '[data-id].lit{outline:none}' +
    'svg [data-id].lit *{stroke-width:2}' +
    'svg [data-id].focus *{stroke:#b5542a}' +
    'aside [data-id].lit, aside [data-id].focus{background:#fff3ea;box-shadow:0 0 0 3px #fff3ea}' +
    '[data-id]:focus{outline:none}' +
    '[data-src]{cursor:help}' +
    '.stage.pencil [data-id]{pointer-events:none}' +
    '}' +
    '@media print{.' + SO + '{display:none !important}}';
  document.head.appendChild(css);
})();
