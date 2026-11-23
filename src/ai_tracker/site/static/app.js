/* ai-rollout-tracker public site: draws the charts (inline SVG) from the JSON next to the page.
   No external hosts. Every number shown in a chart is also in the page text or in the table under the chart. */
(function () {
  'use strict';
  var NS = 'http://www.w3.org/2000/svg';
  var DATA = null;

  function svgEl(tag, attrs, parent) {
    var e = document.createElementNS(NS, tag);
    for (var k in attrs) e.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(e);
    return e;
  }
  function htmlEl(tag, cls, parent, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    if (parent) parent.appendChild(e);
    return e;
  }
  // period string -> decimal year (M: 2026-09, Q: 2026Q3, A: 2026)
  function px(p) {
    var m;
    if ((m = /^(\d{4})-(\d{2})$/.exec(p))) return +m[1] + (+m[2] - 0.5) / 12;
    if ((m = /^(\d{4})Q([1-4])$/.exec(p))) return +m[1] + (+m[2] * 3 - 1.5) / 12;
    if ((m = /^(\d{4})$/.exec(p))) return +m[1] + 0.5;
    return NaN;
  }
  function fmt(v, nd) {
    if (v == null || !isFinite(v)) return '–';
    return v.toLocaleString('sv-SE', { minimumFractionDigits: nd, maximumFractionDigits: nd });
  }
  function decimals(lo, hi) {
    var r = Math.max(Math.abs(lo), Math.abs(hi));
    return r >= 1000 ? 0 : r >= 20 ? 1 : 2;
  }
  function ticks(lo, hi, n) {
    var span = hi - lo || 1, step = Math.pow(10, Math.floor(Math.log10(span / n)));
    var err = span / n / step;
    step *= err >= 7.5 ? 10 : err >= 3.5 ? 5 : err >= 1.5 ? 2 : 1;
    var out = [];
    for (var v = Math.ceil(lo / step) * step; v <= hi + step * 1e-9; v += step) out.push(Math.abs(v) < step * 1e-9 ? 0 : v);
    return out;
  }

  /* spec: {series: [{label, periods, values, color, dash, kind: 'line'|'dot'}], refs: [y], band: [lo, hi],
            zero: bool, ymin, ymax, height, spark, nd} */
  function draw(fig, spec) {
    var old = fig.querySelector('.plot');
    if (old) old.remove();
    var holder = htmlEl('div', 'plot', null);
    fig.appendChild(holder);
    var W = Math.max(fig.clientWidth || 320, 120), H = spec.height || (spec.spark ? 44 : 190);
    var m = spec.spark ? { l: 2, r: 2, t: 4, b: 4 } : { l: 46, r: 10, t: 8, b: 22 };
    var xs = [], ys = [];
    spec.series.forEach(function (s) {
      s.x = s.periods.map(px);
      s.x.forEach(function (x, i) { if (s.values[i] != null && isFinite(x)) { xs.push(x); ys.push(s.values[i]); } });
      (s.ranges || []).forEach(function (r) {  // interval whiskers: [{lo: [...], hi: [...], width}]
        s.x.forEach(function (x, i) { if (r.lo[i] != null && r.hi[i] != null && isFinite(x)) ys.push(r.lo[i], r.hi[i]); });
      });
    });
    if (!xs.length) { holder.textContent = 'Inga värden att visa.'; return; }
    (spec.refs || []).forEach(function (r) { ys.push(r); });
    if (spec.band) { ys.push(spec.band[0], spec.band[1]); }
    if (spec.zero) ys.push(0);
    (spec.domain || []).forEach(function (p) { var x = px(p); if (isFinite(x)) xs.push(x); });
    var x0 = Math.min.apply(null, xs), x1 = Math.max.apply(null, xs);
    if (x0 === x1) { x0 -= 0.5; x1 += 0.5; }
    var y0 = spec.ymin != null ? spec.ymin : Math.min.apply(null, ys);
    var y1 = spec.ymax != null ? spec.ymax : Math.max.apply(null, ys);
    if (spec.ymin == null || spec.ymax == null) { var pad = (y1 - y0 || Math.abs(y1) || 1) * 0.06; if (spec.ymin == null) y0 -= pad; if (spec.ymax == null) y1 += pad; }
    var nd = spec.nd != null ? spec.nd : decimals(y0, y1);
    var X = function (x) { return m.l + (x - x0) / (x1 - x0) * (W - m.l - m.r); };
    var Y = function (y) { return H - m.b - (y - y0) / (y1 - y0) * (H - m.t - m.b); };
    var svg = svgEl('svg', { viewBox: '0 0 ' + W + ' ' + H, width: W, height: H, role: 'img' }, holder);
    var cap = fig.querySelector('figcaption');
    svg.setAttribute('aria-label', cap ? cap.textContent : (spec.label || 'Diagram'));
    if (!spec.spark) {
      var tk = ticks(y0, y1, 4), st = tk.length > 1 ? tk[1] - tk[0] : 1;
      var td = st >= 1 ? 0 : Math.ceil(-Math.log10(st) - 1e-9);
      tk.forEach(function (t) {
        svgEl('line', { x1: m.l, x2: W - m.r, y1: Y(t), y2: Y(t), 'class': 'grid' }, svg);
        var lab = svgEl('text', { x: m.l - 6, y: Y(t) + 4, 'text-anchor': 'end' }, svg);
        lab.textContent = fmt(t, td);
      });
      var span = x1 - x0, step = span > 40 ? 10 : span > 16 ? 4 : span > 8 ? 2 : 1;
      for (var yr = Math.ceil(x0 / step) * step; yr <= x1; yr += step) {
        var t = svgEl('text', { x: X(yr), y: H - 6, 'text-anchor': 'middle' }, svg);
        t.textContent = String(yr);
        svgEl('line', { x1: X(yr), x2: X(yr), y1: H - m.b, y2: H - m.b + 4, 'class': 'grid' }, svg);
      }
    }
    if (spec.band) {
      svgEl('rect', { x: m.l, width: W - m.l - m.r, y: Y(spec.band[1]), height: Math.max(0, Y(spec.band[0]) - Y(spec.band[1])),
        fill: 'var(--band)' }, svg);
    }
    if (spec.zero && y0 < 0 && y1 > 0) svgEl('line', { x1: m.l, x2: W - m.r, y1: Y(0), y2: Y(0), 'class': 'zero' }, svg);
    (spec.refs || []).forEach(function (r) { svgEl('line', { x1: m.l, x2: W - m.r, y1: Y(r), y2: Y(r), 'class': 'ref' }, svg); });
    spec.series.forEach(function (s) {
      if (s.kind === 'dot') {
        (s.ranges || []).forEach(function (r) {
          s.x.forEach(function (x, i) {
            if (r.lo[i] == null || r.hi[i] == null || !isFinite(x)) return;
            svgEl('line', { x1: X(x), x2: X(x), y1: Y(r.lo[i]), y2: Y(r.hi[i]), stroke: s.color, 'stroke-width': r.width || 2,
              'stroke-opacity': 0.55, 'stroke-linecap': 'round' }, svg);
          });
        });
        s.x.forEach(function (x, i) {
          if (s.values[i] == null || !isFinite(x)) return;
          svgEl('circle', { cx: X(x), cy: Y(s.values[i]), r: 4.5, fill: s.color, stroke: 'var(--surface-1)', 'stroke-width': 2 }, svg);
        });
        return;
      }
      var d = '', pen = false;
      s.x.forEach(function (x, i) {
        var v = s.values[i];
        if (v == null || !isFinite(x)) { pen = false; return; }
        d += (pen ? 'L' : 'M') + X(x).toFixed(1) + ' ' + Y(v).toFixed(1);
        pen = true;
      });
      var attrs = { d: d, fill: 'none', stroke: s.color, 'stroke-width': 2, 'stroke-linejoin': 'round', 'stroke-linecap': 'round' };
      if (s.dash) attrs['stroke-dasharray'] = '5 4';
      if (d) svgEl('path', attrs, svg);
      // isolated points (no neighbour) would be invisible as a path
      s.x.forEach(function (x, i) {
        var v = s.values[i];
        if (v == null || !isFinite(x)) return;
        var prev = i > 0 && s.values[i - 1] != null, next = i < s.values.length - 1 && s.values[i + 1] != null;
        if (!prev && !next) svgEl('circle', { cx: X(x), cy: Y(v), r: 3, fill: s.color }, svg);
      });
    });
    if (spec.spark) return;
    // legend (>= 2 series, or a band)
    var keyed = spec.series.filter(function (s) { return s.values.some(function (v) { return v != null; }); });
    if (keyed.length > 1 || spec.band) {
      var lg = htmlEl('div', 'legend', holder);
      keyed.forEach(function (s) {
        var it = htmlEl('span', s.kind === 'dot' ? 'dot' : (s.dash ? 'dash' : ''), lg, s.label);
        it.style.setProperty('--key', s.color);
      });
      if (spec.band) htmlEl('span', 'band', lg, spec.bandLabel || 'dödband');
    }
    // hover: crosshair snaps to the nearest period, one tooltip for every series
    var all = {};
    spec.series.forEach(function (s) { s.periods.forEach(function (p, i) { if (s.values[i] != null && isFinite(s.x[i])) all[p] = s.x[i]; }); });
    var periods = Object.keys(all).sort(function (a, b) { return all[a] - all[b]; });
    var cross = svgEl('line', { y1: m.t, y2: H - m.b, 'class': 'cross', visibility: 'hidden' }, svg);
    var hit = svgEl('rect', { x: m.l, y: 0, width: W - m.l - m.r, height: H, fill: 'transparent', tabindex: 0 }, svg);
    var tip = htmlEl('div', 'tip', holder);
    tip.style.display = 'none';
    var cur = -1;
    function show(i) {
      if (i < 0 || i >= periods.length) return;
      cur = i;
      var p = periods[i], cx = X(all[p]);
      cross.setAttribute('x1', cx); cross.setAttribute('x2', cx); cross.setAttribute('visibility', 'visible');
      tip.textContent = '';
      htmlEl('div', 'muted', tip, p);
      spec.series.forEach(function (s) {
        var j = s.periods.indexOf(p);
        if (j < 0 || s.values[j] == null) return;
        var row = htmlEl('div', 'row', tip);
        row.style.setProperty('--key', s.color);
        htmlEl('strong', '', row, fmt(s.values[j], nd));
        row.appendChild(document.createTextNode(' ' + s.label));
        (s.ranges || []).forEach(function (r) {
          if (r.lo[j] != null && r.hi[j] != null) row.appendChild(document.createTextNode(
            ', ' + r.label + ' ' + fmt(r.lo[j], nd) + '–' + fmt(r.hi[j], nd)));
        });
      });
      tip.style.display = 'block';
      var tw = tip.offsetWidth, left = cx + 10;
      if (left + tw > W) left = Math.max(0, cx - tw - 10);
      tip.style.left = left + 'px';
      tip.style.top = '4px';
    }
    function hide() { cross.setAttribute('visibility', 'hidden'); tip.style.display = 'none'; }
    hit.addEventListener('pointermove', function (ev) {
      var r = svg.getBoundingClientRect(), x = (ev.clientX - r.left) * (W / r.width);
      var best = 0, bd = Infinity;
      periods.forEach(function (p, i) { var d = Math.abs(X(all[p]) - x); if (d < bd) { bd = d; best = i; } });
      show(best);
    });
    hit.addEventListener('pointerleave', hide);
    hit.addEventListener('focus', function () { show(periods.length - 1); });
    hit.addEventListener('blur', hide);
    hit.addEventListener('keydown', function (ev) {
      if (ev.key === 'ArrowLeft') { show(Math.max(0, cur - 1)); ev.preventDefault(); }
      if (ev.key === 'ArrowRight') { show(Math.min(periods.length - 1, cur + 1)); ev.preventDefault(); }
    });
    // table view (last 24 periods)
    if (!fig.querySelector('details')) {
      var det = htmlEl('details', '', fig);
      htmlEl('summary', '', det, 'Visa som tabell');
      var tb = htmlEl('table', 'narrow', det), hr = htmlEl('tr', '', htmlEl('thead', '', tb));
      htmlEl('th', '', hr, 'Period');
      keyed.forEach(function (s) { htmlEl('th', '', hr, s.label); });
      var body = htmlEl('tbody', '', tb);
      periods.slice(-24).reverse().forEach(function (p) {
        var tr = htmlEl('tr', '', body);
        htmlEl('td', '', tr, p);
        keyed.forEach(function (s) { var j = s.periods.indexOf(p); htmlEl('td', 'num', tr, j < 0 ? '' : fmt(s.values[j], nd)); });
      });
    }
  }

  // ------------------------------------------------------------------ chart builders per page

  function indexSeries(history) {
    var periods = history.map(function (h) { return h.month; });
    var pick = function (kind) { return history.map(function (h) { return h.kind === kind ? h.index : null; }); };
    return [
      { label: 'rekonstruerad', periods: periods, values: pick('rekonstruerad'), color: 'var(--series-1)', dash: true },
      { label: 'skarp', periods: periods, values: pick('skarp'), color: 'var(--series-1)' }
    ];
  }
  function findSeries(key) {
    var all = (DATA.counted || []).concat(DATA.not_counted || []);
    for (var i = 0; i < all.length; i++) if (all[i].key === key) return all[i];
    return null;
  }
  var BUILD = {
    spark: function (fig) {
      var code = fig.getAttribute('data-code');
      var b = (DATA.branches || []).filter(function (t) { return t.code === code; })[0];
      if (!b || !b.history.some(function (h) { return h.index != null; })) { fig.remove(); return null; }
      return { spark: true, series: indexSeries(b.history), ymin: 0, ymax: 1, refs: [0.33, 0.67],
        domain: b.history.map(function (h) { return h.month; }) };
    },
    index: function () {
      var h = DATA.history || [];
      return { series: indexSeries(h), ymin: 0, ymax: 1, refs: [0.33, 0.67], nd: 2,
        domain: h.map(function (x) { return x.month; }) };
    },
    pace: function (fig) {
      var s = findSeries(fig.getAttribute('data-key'));
      if (!s || !s.path) return null;
      var time = s.method === 'doubling' || s.method === 'halving';
      return { series: [{ label: 'takt', periods: s.path.periods, values: s.path.pace, color: 'var(--series-1)' }], zero: !time };
    },
    change: function (fig) {
      var s = findSeries(fig.getAttribute('data-key'));
      if (!s || !s.path) return null;
      var spec = { series: [{ label: 'förändring i takt', periods: s.path.periods, values: s.path.change, color: 'var(--series-1)' }], zero: true };
      if (s.deadband != null) { spec.band = [-s.deadband, s.deadband]; spec.bandLabel = 'dödband ±0,25 SD (nu)'; }
      return spec;
    },
    nowcast: function (fig) {
      var id = fig.getAttribute('data-id');
      var n = (DATA.nowcasts || []).filter(function (x) { return x.id === id; })[0];
      if (!n || !n.history) return null;
      var fc = n.forecasts || [];
      var iv = function (k, j) { return fc.map(function (f) { return f.intervals && f.intervals[k] ? f.intervals[k][j] : null; }); };
      var ranges = fc.some(function (f) { return f.intervals; })  // only when the site has intervals (grind G-C)
        ? [{ label: '95 %', lo: iv('95', 0), hi: iv('95', 1), width: 1.5 }, { label: '50 %', lo: iv('50', 0), hi: iv('50', 1), width: 5 }]
        : [];
      return { series: [
        { label: 'utfall', periods: n.history.periods, values: n.history.values, color: 'var(--series-1)' },
        { label: 'skarp prognos', kind: 'dot', periods: fc.map(function (f) { return f.period; }),
          values: fc.map(function (f) { return f.value; }), color: 'var(--series-2)', ranges: ranges }
      ], height: 220 };
    }
  };

  function renderAll() {
    if (!DATA) return;
    document.querySelectorAll('figure[data-chart]').forEach(function (fig) {
      var make = BUILD[fig.getAttribute('data-chart')];
      if (!make) return;
      var spec = make(fig);
      if (spec) draw(fig, spec);
    });
  }

  function start() {
    var src = document.body.getAttribute('data-src');
    if (!src || !document.querySelector('figure[data-chart]')) return;
    fetch(src).then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); }).then(function (d) {
      DATA = d;
      renderAll();
      var t = null;
      var lastW = window.innerWidth;
      window.addEventListener('resize', function () {
        if (window.innerWidth === lastW) return;
        lastW = window.innerWidth;
        clearTimeout(t);
        t = setTimeout(renderAll, 150);
      });
    }).catch(function () {
      document.querySelectorAll('figure[data-chart]').forEach(function (fig) {
        if (!fig.classList.contains('spark')) htmlEl('p', 'muted small', fig, 'Diagrammet kunde inte laddas.');
      });
    });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start); else start();
})();
