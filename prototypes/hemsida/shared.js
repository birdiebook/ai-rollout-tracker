// Shared helpers for the prototypes: no libraries, no external hosts (the site rule in docs/drift.md).
export const NS = "http://www.w3.org/2000/svg";

export async function load(name) {
  const r = await fetch(`data/${name}`);
  if (!r.ok) throw new Error(`data/${name}: ${r.status} (kör build_data.py först)`);
  return r.json();
}

export function svg(tag, attrs = {}, parent) {
  const e = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) if (v !== undefined && v !== null) e.setAttribute(k, v);
  if (parent) parent.appendChild(e);
  return e;
}

export function h(tag, attrs = {}, ...kids) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") e.className = v; else if (k === "html") e.innerHTML = v; else if (v !== undefined) e.setAttribute(k, v);
  }
  for (const k of kids) if (k !== null && k !== undefined) e.append(k);
  return e;
}

export const lin = (d0, d1, r0, r1) => {
  const f = (x) => r0 + ((x - d0) / (d1 - d0 || 1)) * (r1 - r0);
  f.invert = (y) => d0 + ((y - r0) / (r1 - r0 || 1)) * (d1 - d0);
  return f;
};

// Swedish formats
const nf = (d) => new Intl.NumberFormat("sv-SE", { maximumFractionDigits: d, minimumFractionDigits: d });
export const fmt = (x, d = 0) => (x === null || x === undefined || Number.isNaN(x) ? "–" : nf(d).format(x));
export const signed = (x, d = 1) => (x === null || x === undefined ? "–" : (x > 0 ? "+" : x < 0 ? "−" : "±") + nf(d).format(Math.abs(x)));
const MONTHS = ["jan", "feb", "mar", "apr", "maj", "jun", "jul", "aug", "sep", "okt", "nov", "dec"];
const MONTHS_LONG = ["januari", "februari", "mars", "april", "maj", "juni", "juli", "augusti", "september", "oktober", "november", "december"];
export const monthLabel = (ym, long = false) => {
  const [y, m] = ym.split("-").map(Number);
  return `${(long ? MONTHS_LONG : MONTHS)[m - 1]} ${y}`;
};
export const dateLabel = (iso) => {
  const [y, m, d] = iso.split("-").map(Number);
  return `${d} ${MONTHS[m - 1]} ${y}`;
};

// Period helpers ("YYYY-MM" <-> month ordinal)
export const mo = (ym) => { const [y, m] = ym.split("-").map(Number); return y * 12 + (m - 1); };
export const ym = (o) => `${Math.floor(o / 12)}-${String((o % 12) + 1).padStart(2, "0")}`;

// State vocabulary (docs/mattregister.md section 2). Colour + glyph + word, never colour alone.
export const STATE = {
  "accelererar": { cls: "acc", glyph: "▲", word: "accelererar" },
  "stabil": { cls: "stb", glyph: "●", word: "stabil" },
  "bromsar in": { cls: "brk", glyph: "▼", word: "bromsar in" },
  "för få serier": { cls: "none", glyph: "○", word: "för få serier" },
};
export const stateOf = (s) => STATE[s] || STATE["för få serier"];

// Diverging colour for a diffusion index in [0, 1]: orange (0) - grey midpoint (0.5) - blue (1)
function hex2rgb(hx) { const v = hx.trim().replace("#", ""); return [0, 2, 4].map((i) => parseInt(v.slice(i, i + 2), 16)); }
function cssVar(name) { return getComputedStyle(document.documentElement).getPropertyValue(name).trim(); }
export function divColor(x) {
  if (x === null || x === undefined) return "transparent";
  const mid = hex2rgb(cssVar("--mid")), acc = hex2rgb(cssVar("--acc")), brk = hex2rgb(cssVar("--brk"));
  const t = Math.max(-1, Math.min(1, (x - 0.5) * 2));
  const pole = t >= 0 ? acc : brk, a = Math.abs(t) ** 0.85;
  const c = mid.map((m, i) => Math.round(m + (pole[i] - m) * a));
  return `rgb(${c.join(",")})`;
}

// One tooltip for the page
let tipEl;
export function tip(html, ev) {
  tipEl = tipEl || document.getElementById("tip") || document.body.appendChild(h("div", { id: "tip", role: "status" }));
  if (!html) { tipEl.style.opacity = 0; return; }
  tipEl.innerHTML = html;
  const pad = 14, w = tipEl.offsetWidth, hh = tipEl.offsetHeight;
  let x = ev.clientX + pad, y = ev.clientY + pad;
  if (x + w > innerWidth - 8) x = ev.clientX - w - pad;
  if (y + hh > innerHeight - 8) y = ev.clientY - hh - pad;
  tipEl.style.left = `${Math.max(8, x)}px`; tipEl.style.top = `${Math.max(8, y)}px`; tipEl.style.opacity = 1;
}

// URL hash state: shareable deep links (#as_of=2023-06-30&serie=...)
export function readHash() { return Object.fromEntries(new URLSearchParams(location.hash.slice(1))); }
export function writeHash(obj) {
  const p = new URLSearchParams(readHash());
  for (const [k, v] of Object.entries(obj)) (v === null ? p.delete(k) : p.set(k, v));
  history.replaceState(null, "", `#${p.toString()}`);
}

export function themeButton() {
  const b = document.querySelector(".theme-btn");
  if (!b) return;
  const apply = (t) => { if (t) document.documentElement.dataset.theme = t; else delete document.documentElement.dataset.theme; };
  let t = null;
  try { t = localStorage.getItem("theme"); } catch (_) { /* private mode */ }
  apply(t);
  b.addEventListener("click", () => {
    const dark = matchMedia("(prefers-color-scheme: dark)").matches;
    const cur = document.documentElement.dataset.theme || (dark ? "dark" : "light");
    const next = cur === "dark" ? "light" : "dark";
    apply(next);
    try { localStorage.setItem("theme", next); } catch (_) { /* ignore */ }
    window.dispatchEvent(new Event("themechange"));
  });
}

export function onResize(fn) {
  let w = innerWidth, raf;
  addEventListener("resize", () => { if (innerWidth === w) return; w = innerWidth; cancelAnimationFrame(raf); raf = requestAnimationFrame(fn); });
  addEventListener("themechange", fn);
}
