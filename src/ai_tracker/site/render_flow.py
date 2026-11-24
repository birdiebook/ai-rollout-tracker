"""HTML for the flow page (flode.html, track E2): the chain diagram as inline SVG (no JavaScript needed) and one
card per lead with the reconciliations between them. Text in Swedish, neutral wording, every string escaped."""

from __future__ import annotations

from ai_tracker.site import render as H
from ai_tracker.site.render import esc, num

STATE_GLYPH = {"accelererar": "↑", "stabil": "→", "bromsar in": "↓"}
DIR_GLYPH = {1: "↑", 0: "→", -1: "↓"}

# horizontal diagram (desktop)
HW, HGAP, HY, HH = 104, 19, 74, 80
# vertical diagram (phones)
VW, VNODE, VGAP, VEXTRA = 343, 206, 26, 18


SUPERSCRIPT = str.maketrans("-0123456789", "⁻⁰¹²³⁴⁵⁶⁷⁸⁹")


def num_auto(x) -> str:
    """A level in a readable form: grouped digits up to 10 million, then mantissa × 10^exponent."""
    if x is None:
        return "–"
    a = abs(x)
    if a >= 1e7:
        e = len(str(int(a))) - 1
        return f"{num(x / 10 ** e, 2)} × 10{str(e).translate(SUPERSCRIPT)}"
    nd = 0 if a >= 1000 else 1 if a >= 20 else 2 if a >= 1 else 3
    return num(x, nd)


def state_glyph(state) -> str:
    return STATE_GLYPH.get(state or "", "·")


def dir_glyph(d) -> str:
    return DIR_GLYPH.get(d, "·")


def state_cls(state) -> str:
    return H.STATE_CLASS.get(state or "för få serier", "few")


def recon_label(r: dict) -> str:
    if r.get("hidden"):
        return "visas inte"
    return f"{r['short']} {dir_glyph(r.get('direction'))}"


def _between(recons: list[dict]) -> tuple[list[dict], dict[int, list[dict]]]:
    """(ratios spanning two or more leads, {lead number: ratios within that lead})."""
    span, within = [], {}
    for r in recons:
        s = r.get("span")
        if not s:
            continue
        if s[0] < s[1]:
            span.append(r)
        else:
            within.setdefault(s[0], []).append(r)
    return span, within


def _node_chips(lead: dict) -> str:
    return "  ".join(f"{b['code']} {state_glyph(b.get('state'))}" for b in lead["branches"])


def _state_bars(lead: dict, x: float, y: float, w: float) -> str:
    n = max(1, len(lead["branches"]))
    bw = w / n
    return "".join(f'<rect class="bar st-{state_cls(b.get("state"))}" x="{x + i * bw:.1f}" y="{y:.1f}" '
                   f'width="{bw:.1f}" height="4"/>' for i, b in enumerate(lead["branches"]))


def svg_horizontal(doc: dict) -> str:
    leads = doc["leads"]
    span, within = _between(doc["reconciliations"])
    W = len(leads) * HW + (len(leads) - 1) * HGAP
    H_ = HY + HH + 18 + 18 * max([len(v) for v in within.values()] or [0]) + 6
    cx = lambda i: i * (HW + HGAP) + HW / 2  # noqa: E731
    out = [f'<svg class="flowmap flowmap-h" viewBox="0 0 {W} {H_}" role="img" '
           f'aria-labelledby="flowmap-h-title"><title id="flowmap-h-title">Kedjan L1 till L9 med grenarnas tillstånd '
           f'och avstämningarna mellan leden</title>',
           '<defs><marker id="ah" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" '
           'orient="auto-start-reverse"><path d="M0 0 L8 4 L0 8 z" class="arrowhead"/></marker></defs>']
    for r in sorted(span, key=lambda r: -(r["span"][1] - r["span"][0])):
        a, b = r["span"][0] - 1, r["span"][1] - 1
        h = 24 + 26 * (b - a - 1)
        x0, x1 = cx(a), cx(b)
        out.append(f'<path class="arc{" hidden" if r.get("hidden") else ""}" d="M{x0:.1f} {HY} Q{(x0 + x1) / 2:.1f} '
                   f'{HY - 2 * h} {x1:.1f} {HY}"/>')
        lx, ly = (x0 + x1) / 2, HY - h - 6
        out.append(f'<text class="arc-label" x="{lx:.1f}" y="{ly:.1f}" text-anchor="middle">{esc(recon_label(r))}</text>')
    for i, lead in enumerate(leads):
        x = i * (HW + HGAP)
        if i < len(leads) - 1:
            out.append(f'<line class="flowline" x1="{x + HW + 2}" y1="{HY + HH / 2}" x2="{x + HW + HGAP - 3}" '
                       f'y2="{HY + HH / 2}" marker-end="url(#ah)"/>')
        lines = lead["short"]
        tspans = "".join(f'<text class="node-name" x="{x + 8}" y="{HY + 36 + 14 * j}">{esc(t)}</text>'
                         for j, t in enumerate(lines))
        out.append(f'<a href="#{lead["code"].lower()}"><rect class="node" x="{x}" y="{HY}" width="{HW}" height="{HH}" '
                   f'rx="8"/>{_state_bars(lead, x + 8, HY + 6, HW - 16)}'
                   f'<text class="node-code" x="{x + 8}" y="{HY + 22}">{lead["code"]}</text>{tspans}'
                   f'<text class="node-chips" x="{x + 8}" y="{HY + HH - 9}">{esc(_node_chips(lead))}</text></a>')
        for j, r in enumerate(within.get(i + 1, [])):
            out.append(f'<text class="arc-label" x="{x + HW / 2}" y="{HY + HH + 18 + 18 * j}" text-anchor="middle">'
                       f'{esc(recon_label(r))}</text>')
    out.append("</svg>")
    return "".join(out)


def svg_vertical(doc: dict) -> str:
    leads = doc["leads"]
    span, within = _between(doc["reconciliations"])
    heights = [52 + VEXTRA * len(within.get(i + 1, [])) for i in range(len(leads))]
    ys, y = [], 0
    for h in heights:
        ys.append(y)
        y += h + VGAP
    H_ = y - VGAP + 2
    mid = lambda i: ys[i] + 26  # noqa: E731
    out = [f'<svg class="flowmap flowmap-v" viewBox="0 0 {VW} {H_}" role="img" aria-labelledby="flowmap-v-title">'
           f'<title id="flowmap-v-title">Kedjan L1 till L9 med grenarnas tillstånd och avstämningarna mellan leden'
           f'</title><defs><marker id="av" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" '
           'orient="auto-start-reverse"><path d="M0 0 L8 4 L0 8 z" class="arrowhead"/></marker></defs>']
    ordered = sorted(span, key=lambda r: (r["span"][1] - r["span"][0], r["span"][0]))
    pills = []
    for k, r in enumerate(ordered):
        a, b = r["span"][0] - 1, r["span"][1] - 1
        xb = VNODE + 8 + 9 * (r["span"][1] - r["span"][0] - 1) + 4 * (k % 2)
        out.append(f'<path class="arc{" hidden" if r.get("hidden") else ""}" d="M{VNODE + 1} {mid(a)} H{xb} '
                   f'V{mid(b)} H{VNODE + 1}"/>')
        # the label: in the gap just above lead b when the span is one lead, else beside the lead in the middle
        py = (ys[b] - VGAP / 2) if b - a == 1 else mid(a + (b - a) // 2) - 12
        pills.append((xb, py, r))
    for xb, py, r in pills:
        w = VW - xb - 6
        out.append(f'<rect class="pill" x="{xb + 4}" y="{py - 10:.1f}" width="{w}" height="20" rx="10"/>'
                   f'<text class="arc-label" x="{xb + 12}" y="{py + 4:.1f}">{esc(recon_label(r))}</text>')
    for i, lead in enumerate(leads):
        y0, h = ys[i], heights[i]
        if i < len(leads) - 1:
            out.append(f'<line class="flowline" x1="{VNODE / 2}" y1="{y0 + h + 2}" x2="{VNODE / 2}" '
                       f'y2="{ys[i + 1] - 3}" marker-end="url(#av)"/>')
        name = lead["name"] if len(lead["name"]) <= 24 else " ".join(lead["short"])
        extra = "".join(f'<text class="node-chips" x="10" y="{y0 + 64 + VEXTRA * j}">↳ {esc(recon_label(r))}</text>'
                        for j, r in enumerate(within.get(i + 1, [])))
        out.append(f'<a href="#{lead["code"].lower()}"><rect class="node" x="0" y="{y0}" width="{VNODE}" height="{h}" '
                   f'rx="8"/>{_state_bars(lead, 8, y0 + 5, VNODE - 16)}'
                   f'<text class="node-name" x="10" y="{y0 + 26}"><tspan class="node-code">{lead["code"]}</tspan> '
                   f'{esc(name)}</text><text class="node-chips" x="10" y="{y0 + 44}">{esc(_node_chips(lead))}</text>'
                   f'{extra}</a>')
    out.append("</svg>")
    return "".join(out)


# ------------------------------------------------------------------ cards


def branch_line(b: dict) -> str:
    if not b.get("has_core"):
        return (f'<li><a href="gren-{b["code"].lower()}.html">{b["code"]} {esc(b.get("name"))}</a>: '
                f'<span class="muted">inga registrerade kärnserier</span></li>')
    hidden = (f' <span class="muted small">(varav {b["n_withheld_counted"]} som inte visas)</span>'
              if b.get("n_withheld_counted") else "")
    return (f'<li><a href="gren-{b["code"].lower()}.html">{b["code"]} {esc(b.get("name"))}</a> '
            f'{H.state_badge(b.get("state"))} <span class="index-sm">{num(b.get("index"))}</span> '
            f'<span class="small">{H.counts(b)}</span>{hidden}</li>')


def series_block(s: dict) -> str:
    unit = s.get("pace_unit") or ""
    d = s.get("direction")
    dir_html = f'{dir_glyph(d)} {esc(H.DIRECTION[d][1].split(" (")[0])}' if d in H.DIRECTION else "–"
    counted = "" if s.get("counted") else (
        f'<p class="small reason">{"Räknas inte" if s.get("in_core") else "Ingen kärnserie, räknas inte i indexet"}'
        f'{": " + esc(s.get("reason")) if s.get("reason") else ""}</p>')
    where = f' · {esc(s["branch"])}' if s.get("branch") else ""
    spark = (f'<figure class="spark flowspark" data-chart="flowspark" data-key="{esc(s["key"])}" '
             f'aria-label="Takt, senaste tio åren"><figcaption class="small muted">Takt, senaste tio åren</figcaption>'
             f'</figure>' if s.get("path") else "")
    return f"""<div class="fseries">
<h4>{esc(s.get('label'))}</h4>
<p class="key"><code>{esc(s['key'])}</code>{where} · {esc(s.get('unit'))} · senaste {esc(s.get('latest_period') or '–')}, känd {esc(s.get('known_from') or '–')}</p>
<dl class="stats">{H.stat("Nivå", num_auto(s.get("level")))}{H.stat("Takt", num(s.get("pace"), 1, signed=s.get("method") not in ("doubling", "halving")), esc(unit))}{H.stat("Förändring i takt", num(s.get("change_in_pace"), 1, signed=True))}{H.stat("Riktning", dir_html)}</dl>
{spark}{counted}
<p class="source">Källa: {esc(s.get('source'))}. Licens: {esc(s.get('license'))}.</p>
</div>"""


def nowcast_block(n: dict, build: dict) -> str:
    dec = n.get("decimals", 0)
    unit = esc(n.get("unit") or "")
    parts = [f'<h4><a href="prognoser.html#{esc(n["id"])}">{esc(n["label"])}</a>: {esc(n["title"])}</h4>']
    lt = n.get("latest")
    if lt:
        iv = lt.get("interval_80")
        ivs = f", 80 %-intervall {num(iv[0], dec)} – {num(iv[1], dec)}" if iv and iv[0] is not None else ""
        parts.append(f'<p>Skarp prognos för <strong>{esc(lt["period"])}</strong> (gjord {esc(lt.get("origin"))}, '
                     f'huvudmodell {esc(lt.get("champion"))}): <strong>{num(lt.get("value"), dec)}</strong> {unit}{ivs}.</p>')
    else:
        nxt = (f" Nästa: {esc(n['next_period'])}, görs {esc(n['next_origin'])}." if n.get("next_origin") else "")
        parts.append(f"<p>Ingen skarp prognos än.{nxt}</p>")
    bt = n.get("backtest") or {}
    mae = bt.get("mae") or {}
    bits = []
    if mae.get("mae") is not None:
        end = lambda p: str(p).split("/")[-1]  # noqa: E731 - N5 periods are collection windows "start/end"
        rng = f", {esc(end(mae.get('first')))}–{esc(end(mae.get('last')))}" if mae.get("first") else ""
        bits.append(f"MAE {num(mae['mae'])} ({esc(n.get('error_unit') or '100 × log')}, n = {mae.get('n')}{rng})")
    if bt.get("coverage_80") is not None:
        band = bt.get("band_80") or [None, None]
        bits.append(f"täckning för 80 %-intervallet {num(bt['coverage_80'])} (binomialt band {num(band[0])}–"
                    f"{num(band[1])}, n = {bt.get('n')}), CRPS {num(bt.get('crps'))}")
    if bits:
        parts.append(f'<p class="small">Backtest, huvudmodell {esc(bt.get("model"))}: {"; ".join(bits)}. '
                     f'<a href="{esc(build["repo"])}/blob/main/{esc(n.get("results_doc"))}">Resultat</a>.</p>')
    elif bt.get("error"):
        parts.append('<p class="small muted">Backtesten kunde inte beräknas vid bygget.</p>')
    return f'<div class="fnowcast">{"".join(parts)}</div>'


def recon_card(r: dict) -> str:
    if r.get("hidden"):
        return (f'<div class="frecon"><p class="small muted">En avstämning ({esc(r.get("lead"))}) visas inte av '
                f'licensskäl, se listan längst ned.</p></div>')
    d = r.get("direction")
    reason = "" if r.get("valid") else (f'<p class="small reason">Inget giltigt mått: {esc(r.get("reason"))}</p>'
                                        if r.get("reason") else "")
    spark = (f'<figure class="spark flowspark" data-chart="flowspark" data-key="{esc(r["key"])}" '
             f'aria-label="Takt i kvoten"><figcaption class="small muted">Takt i kvoten, senaste tio åren</figcaption>'
             f'</figure>' if r.get("path") else "")
    return f"""<div class="frecon">
<p class="frecon-head"><span class="span-tag">{esc(r.get('lead'))}</span> <strong>{esc(r['short'])}</strong> <span class="dir">{dir_glyph(d)}</span></p>
<p class="small">{esc(r.get('label'))}. {esc(r.get('question'))}</p>
<dl class="stats">{H.stat("Senaste period", esc(r.get("latest_period") or "–"))}{H.stat("Nivå", num_auto(r.get("level")))}{H.stat("Takt (log ×100)", num(r.get("pace"), 1, signed=True))}{H.stat("Förändring i takt", num(r.get("change_in_pace"), 1, signed=True))}</dl>
{spark}{reason}
<p class="key"><code>{esc(r['key'])}</code></p>
</div>"""


def lead_card(lead: dict, within: list[dict], build: dict) -> str:
    states = "".join(branch_line(b) for b in lead["branches"])
    series = "".join(series_block(s) for s in lead["series"])
    hidden = (f'<p class="small muted">{lead["n_withheld"]} nyckelserie{"r" if lead["n_withheld"] != 1 else ""} '
              f'visas inte av licensskäl (se listan längst ned).</p>' if lead.get("n_withheld") else "")
    if not series and not hidden:
        series = '<p class="muted">Inga nyckelserier med värden.</p>'
    nc = "".join(nowcast_block(n, build) for n in lead["nowcasts"])
    nc = f'<div class="lead-part"><h3>Nowcast</h3>{nc}</div>' if nc else ""
    inner = ""
    if within:
        inner = (f'<div class="lead-part"><h3>Avstämningar inom ledet</h3><div class="frecons">'
                 f'{"".join(recon_card(r) for r in within)}</div></div>')
    cls = state_cls(lead["branches"][0].get("state")) if lead["branches"] else "few"
    return f"""<article class="fl-lead st-{cls}" id="{lead['code'].lower()}">
<header class="lead-head"><span class="lead-code">{lead['code']}</span><div><h2>{esc(lead['name'])}</h2><p class="muted small">{esc(lead['content'])}</p></div></header>
<ul class="lead-states">{states}</ul>
<div class="lead-part"><h3>Nyckelserier</h3><div class="fseries-grid">{series}</div>{hidden}</div>
{nc}{inner}
</article>"""


def connector(recons: list[dict], a: str, b: str) -> str:
    if not recons:
        return f'<div class="link" aria-hidden="true"><span class="link-arrow"></span></div>'
    return (f'<div class="link"><span class="link-arrow" aria-hidden="true"></span><div class="link-body">'
            f'<p class="small muted">Avstämningar mellan leden, fram till {esc(b)}</p><div class="frecons">'
            f'{"".join(recon_card(r) for r in recons)}</div></div></div>')


def withheld_list(doc: dict) -> str:
    if not doc["withheld"]:
        return ""
    items = "".join(f'<li><strong>{esc(w["label"])}</strong> <code>{esc(w["key"])}</code>. Källa: {esc(w["source"])}. '
                    f'Visas inte: {esc(w["why"])}.</li>' for w in doc["withheld"])
    return (f'<section id="withheld" class="withheld"><h2>Serier som inte visas av licensskäl</h2><p>De här serierna '
            f'hör till leden ovan men publiceras inte här. Grenarnas index och tillstånd omfattar dem enligt registret '
            f'när de är kärnserier.</p><ul>{items}</ul></section>')


def flow_page(doc: dict, build: dict) -> str:
    rec = doc["record"]
    span, within = _between(doc["reconciliations"])
    blocks = []
    leads = doc["leads"]
    for i, lead in enumerate(leads):
        blocks.append(lead_card(lead, within.get(i + 1, []), build))
        if i < len(leads) - 1:
            nxt = i + 2  # lead number of the next lead
            here = [r for r in span if r["span"][1] == nxt]
            blocks.append(connector(here, lead["code"], leads[i + 1]["code"]))
    note = ("" if doc.get("reconciliations_available") else
            '<p class="small muted">Avstämningarna finns inte i den här ögonblicksbilden (skriven före A5).</p>')
    body = f"""<section class="intro">
<h1>Flödet</h1>
<p class="lead">AI-ekonomin som en kedja i nio led: från förmåga och användning, via intäkter, kontrakt och investeringar, till chips, el, effekter och forskning. Varje led visar grenarnas tillstånd, några nyckelserier med takt och förändring i takt, och nowcasten där det finns en. Mellan leden står avstämningarna, kvoter som gör kedjan granskningsbar.</p>
{H.record_banner(rec)}
</section>
<section class="flowmap-wrap" aria-label="Kedjan i översikt">
{svg_horizontal(doc)}
{svg_vertical(doc)}
<p class="small muted flowmap-note">Staplarna överst i varje led är grenarnas tillstånd (↑ accelererar, → stabil, ↓ bromsar in, · för få serier). Bågarna är avstämningarna, med riktningen i kvotens takt. Tryck på ett led för detaljerna.</p>
</section>
<div class="flow">
{''.join(blocks)}
</div>
{note}
<section class="howto">
<h2>Så läses flödet</h2>
<p><strong>Takt</strong> är årsförändringen enligt måttregistret (för de flesta serier log ×100, för andelar procentenheter). <strong>Förändring i takt</strong> är takten nu minus takten ett halvår (två kvartal) tidigare. <strong>Riktning</strong> ↑ eller ↓ betyder att förändringen är större än dödbandet på 0,25 standardavvikelser av seriens egen historik. Ett led som accelererar och ett som bromsar in redovisas på samma sätt.</p>
<p>Nyckelserierna är ett fast urval per led som visar vad ledet innehåller. De ändrar inte grenarnas index. Avstämningarna räknas inte i något index. Alla värden är kända vid {esc(rec['date'])} (<code>as_of</code> beräkningsdagen).</p>
</section>
{withheld_list(doc)}"""
    return H.page(f"Flödet – {H.SITE_TITLE}", "flode", body, "data/flode.json", build)
