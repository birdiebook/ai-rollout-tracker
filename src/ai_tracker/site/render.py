"""HTML for the site, rendered from the documents of ai_tracker.site.data. Text in Swedish.

Numbers and lists are rendered here (they read without JavaScript); assets/app.js only draws the charts from the
JSON next to the pages. Every string from the data is escaped.
"""

from __future__ import annotations

import html
import math

from ai_tracker import catalog

SITE_TITLE = "AI-utrullningen"
STATE_ICON = {"accelererar": "↑", "stabil": "→", "bromsar in": "↓", "för få serier": "·"}
STATE_CLASS = {"accelererar": "accel", "stabil": "stable", "bromsar in": "brake", "för få serier": "few"}
DIRECTION = {1: ("↑", "accelererar (+1)"), 0: ("→", "neutral (0)"), -1: ("↓", "bromsar in (−1)")}
METHOD_TEXT = {"log": "årsförändring i log ×100", "share": "förändring i procentenheter över ett år",
               "logit": "förändring i logit över ett år (frontvärde)", "doubling": "fördubblingstid (24 månader)",
               "halving": "halveringstid (24 månader)"}
NOT_INVESTMENT_ADVICE = ("Sidan beskriver utvecklingen och är inte investeringsrådgivning. Ingenting här är en "
                         "rekommendation att köpa, sälja eller behålla något värdepapper.")


def esc(x) -> str:
    return html.escape("" if x is None else str(x), quote=True)


def num(x, nd: int = 2, signed: bool = False) -> str:
    """Swedish number: decimal comma, thin-space thousands, real minus sign. None -> '–'."""
    if x is None or (isinstance(x, float) and not math.isfinite(x)):
        return "–"
    s = f"{x:+,.{nd}f}" if signed else f"{x:,.{nd}f}"
    return s.replace(",", " ").replace(".", ",").replace("-", "−")


def state_badge(state: str | None) -> str:
    state = state or "för få serier"
    cls = STATE_CLASS.get(state, "few")
    return (f'<span class="badge st-{cls}"><span class="badge-icon" aria-hidden="true">{STATE_ICON.get(state, "·")}'
            f'</span>{esc(state)}</span>')


def kind_note(kind: str | None) -> str:
    return ' <span class="kind">(rekonstruerad)</span>' if kind == "rekonstruerad" else ""


def counts(v: dict) -> str:
    n = v.get("n_series") or 0
    word = "serie" if n == 1 else "serier"
    if not n:
        return "0 räknade serier"
    return (f'{n} räknade {word} <span class="muted">(↑{v.get("n_up", 0)} · →{v.get("n_neutral", 0)} · '
            f'↓{v.get("n_down", 0)})</span>')


def change_text(v: dict) -> str:
    prev = v.get("previous")
    if not prev:
        return '<span class="muted">Ingen föregående månad att jämföra med.</span>'
    parts = []
    if v.get("delta_index") is not None:
        parts.append(f"Index {num(v['delta_index'], 2, signed=True)}")
    elif prev.get("index") is None and v.get("index") is not None:
        parts.append("Index nytt")
    if v.get("state_changed"):
        parts.append(f"tillstånd: {esc(prev.get('state'))} → {esc(v.get('state'))}")
    else:
        parts.append("oförändrat tillstånd")
    text = ", ".join(parts)
    return f"{text[:1].upper()}{text[1:]} sedan {esc(prev['month'])}{kind_note(prev.get('kind'))}."


# ------------------------------------------------------------------ shell


def nav(active: str) -> str:
    items = [("index.html", "Översikt", "oversikt"), ("prognoser.html", "Prognoser", "prognoser"),
             ("metod.html", "Metod och källor", "metod")]
    links = "".join(f'<a href="{href}"{" aria-current=\"page\"" if key == active else ""}>{label}</a>'
                    for href, label, key in items)
    return f'<nav class="top" aria-label="Huvudmeny"><a class="brand" href="index.html">{SITE_TITLE}</a>{links}</nav>'


def branch_nav(active: str | None) -> str:
    links = "".join(f'<a href="gren-{c.lower()}.html"{" aria-current=\"page\"" if c == active else ""} '
                    f'title="{esc(n)}">{c}</a>' for c, n in catalog.BRANCHES.items())
    return f'<nav class="branches" aria-label="Grenar">{links}</nav>'


def record_banner(rec: dict) -> str:
    if rec["kind"] == "skarp":
        return (f'<p class="banner live"><strong>Skarp ögonblicksbild</strong> {esc(rec["month"])}, beräknad '
                f'{esc(rec["date"])} och committad som <code>{esc(rec["file"])}</code>. Månader före den första skarpa '
                f'ögonblicksbilden är {esc(rec["recon_label"])}.</p>')
    return (f'<p class="banner recon"><strong>{esc(rec["label"]).capitalize()}.</strong> Det skarpa registret börjar '
            f'med den första ögonblicksbilden, som skrivs {esc(rec["first_live_date"])}. Fram till dess visas tillståndet '
            f'beräknat i efterhand vid varje månadsslut med samma kod och bara data som var känd då, men med dagens '
            f'versioner av serier som saknar sparade versioner. Revideringar kan därför läcka in.</p>')


def page(title: str, active: str, body: str, data_src: str | None, build: dict) -> str:
    data_attr = f' data-src="{esc(data_src)}"' if data_src else ""
    rec = build["record"]
    footer = (f'<footer><p>{NOT_INVESTMENT_ADVICE}</p><p>Byggd {esc(build["built_utc"])} från '
              f'<a href="{esc(build["repo"])}">{esc(build["repo"].removeprefix("https://"))}</a> '
              f'(git {esc(build["git_sha"])}). Läge {esc(rec["month"])}: {esc(rec["label"])}. '
              f'Data hämtad senast {esc(build.get("table_max_fetched_at"))}.</p></footer>')
    return f"""<!doctype html>
<html lang="sv">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark">
<title>{esc(title)}</title>
<meta name="description" content="Neutral, kvantitativ spårning av AI-utrullningen i nio grenar: takt och förändring i takt, förregistrerade mått.">
<link rel="stylesheet" href="assets/style.css">
<script src="assets/app.js" defer></script>
</head>
<body{data_attr}>
<header>{nav(active)}</header>
<main>
{body}
</main>
{footer}
</body>
</html>
"""


# ------------------------------------------------------------------ overview


def tile(t: dict) -> str:
    code = t["code"]
    note = ""
    if not t.get("has_core"):
        note = '<p class="muted small">Inga registrerade kärnserier.</p>'
    elif t.get("n_withheld"):
        note = (f'<p class="muted small">{t["n_withheld"]} serie{"r" if t["n_withheld"] != 1 else ""} visas inte av '
                f'licensskäl (bara grenens summering).</p>')
    return f"""<article class="tile st-{STATE_CLASS.get(t.get('state'), 'few')}">
<a class="tile-link" href="gren-{code.lower()}.html">
<h2><span class="code">{code}</span> {esc(t['name'])}</h2>
<p class="question">{esc(t.get('question'))}</p>
<div class="tile-state">{state_badge(t.get('state'))}<span class="index" title="Diffusionsindex">{num(t.get('index'))}</span></div>
<p class="small">{counts(t)}</p>
<p class="small change">{change_text(t)}</p>
<figure class="spark" data-chart="spark" data-code="{code}" aria-label="Diffusionsindex per månad, {code}"></figure>
{note}
</a>
</article>"""


def overview_page(doc: dict, build: dict) -> str:
    rec = doc["record"]
    tiles = doc["branches"]
    changed = [t for t in tiles if t.get("state_changed")]
    prev_month = next((t["previous"]["month"] for t in tiles if t.get("previous")), None)
    if prev_month is None:
        summary = "<p>Ingen föregående månad att jämföra med.</p>"
    elif changed:
        items = "".join(f'<li><a href="gren-{t["code"].lower()}.html">{t["code"]} {esc(t["name"])}</a>: '
                        f'{esc(t["previous"]["state"])} → {state_badge(t["state"])} '
                        f'<span class="muted">(index {num(t["previous"].get("index"))} → {num(t.get("index"))})</span></li>'
                        for t in changed)
        summary = f"<p>Tillståndet ändrades i {len(changed)} av 9 grenar sedan {esc(prev_month)}:</p><ul>{items}</ul>"
    else:
        summary = f"<p>Inget tillstånd ändrades sedan {esc(prev_month)}.</p>"
    moved = sorted((t for t in tiles if t.get("delta_index")), key=lambda t: -abs(t["delta_index"]))
    if moved:
        summary += ("<p class='small muted'>Största indexförändringar: " +
                    ", ".join(f"{t['code']} {num(t['delta_index'], 2, signed=True)}" for t in moved[:3]) + ".</p>")
    body = f"""<section class="intro">
<h1>Vad ändrade takt den här månaden?</h1>
<p class="lead">Läget vid {esc(rec['date'])} i nio grenar av AI-utrullningen. Varje gren beskrivs med takt och förändring i takt, mätt med förregistrerade mått. En förstärkning är lika mycket en signal som en försvagning.</p>
{record_banner(rec)}
<div class="summary">{summary}</div>
</section>
<section class="tiles" aria-label="Grenar">
{''.join(tile(t) for t in tiles)}
</section>
<section class="howto">
<h2>Så läses rutorna</h2>
<p><strong>Diffusionsindex</strong> är andelen av grenens kärnserier som accelererar: (antal ↑ + 0,5 × antal →) / antal räknade serier. En serie accelererar när förändringen i takt är större än 0,25 standardavvikelser av sin egen historik. 0,5 betyder balans.</p>
<p><strong>Tillstånd:</strong> accelererar om index ≥ 0,67, bromsar in om index ≤ 0,33, annars stabil. Med färre än tre räknade serier visas index men inget tillstånd. Reglerna låstes i <a href="{esc(build['repo'])}/blob/main/docs/mattregister.md">måttregistret</a> innan data analyserades.</p>
</section>"""
    return page(f"{SITE_TITLE} – översikt", "oversikt", body, "data/oversikt.json", build)


# ------------------------------------------------------------------ branch


def stat(label: str, value: str, extra: str = "") -> str:
    return f'<div class="stat"><dt>{label}</dt><dd>{value}{f" <span class=muted>{extra}</span>" if extra else ""}</dd></div>'


def pct(x) -> str:
    return "" if x is None else f"percentil {num(x, 0)}"


def source_caption(s: dict) -> str:
    return f'<p class="source">Källa: {esc(s.get("source"))}. Licens: {esc(s.get("license"))}.</p>'


def series_card(s: dict, counted: bool) -> str:
    key = s.get("key")
    if key is None:
        return (f'<article class="series"><h3>{esc(s.get("entry"))}</h3>'
                f'<p class="reason">Räknas inte: {esc(s.get("reason"))}</p></article>')
    d = s.get("direction")
    dir_html = "–"
    if d in DIRECTION:
        dir_html = f'<span aria-hidden="true">{DIRECTION[d][0]}</span> {DIRECTION[d][1]}'
    unit = s.get("pace_unit") or ""
    stats = "".join([
        stat("Senaste period", esc(s.get("latest_period"))),
        stat("Känd från", esc(s.get("known_from"))),
        stat(f"Takt ({esc(unit)})", num(s.get("pace")), pct(s.get("pace_percentile"))),
        stat("Förändring i takt", num(s.get("change_in_pace"), 2, signed=True), pct(s.get("change_percentile"))),
        stat("Riktning", dir_html, f"dödband ±{num(s.get('deadband'))}" if s.get("deadband") is not None else ""),
        stat("Överraskning", num(s.get("surprise"), 2, signed=True), esc(s.get("surprise_basis"))),
    ])
    notes = []
    if s.get("resolved"):
        notes.append(esc(s["resolved"]))
    if s.get("flag"):
        notes.append(f"Flagga: {esc(s['flag'])}")
    if s.get("sources") and "backfill" in s["sources"]:
        notes.append("Innehåller rader som är daterade med publiceringsfördröjning (backfill), inte sparade versioner.")
    if s.get("derived_from"):
        notes.append("Härledd: " + " / ".join(f"<code>{esc(k)}</code>" for k in s["derived_from"]))
    reason = "" if counted else f'<p class="reason"><strong>Räknas inte:</strong> {esc(s.get("reason"))}</p>'
    charts = ""
    if s.get("path"):
        charts = f"""<div class="charts">
<figure class="chart" data-chart="pace" data-key="{esc(key)}"><figcaption>Takt: {esc(METHOD_TEXT.get(s.get('method'), unit))}, senaste tio åren</figcaption></figure>
<figure class="chart" data-chart="change" data-key="{esc(key)}"><figcaption>Förändring i takt, med dödbandet ±0,25 SD, senaste tio åren</figcaption></figure>
</div>"""
    q = f'<p class="question">{esc(s.get("question"))}</p>' if s.get("question") else ""
    note_html = "".join(f'<p class="small muted">{n}</p>' for n in notes)
    return f"""<article class="series" id="s-{esc(key)}">
<h3>{esc(s.get('label'))}</h3>
<p class="key"><code>{esc(key)}</code> · {esc(s.get('unit'))}</p>
{q}{reason}
<dl class="stats">{stats}</dl>
{note_html}
{charts}
{source_caption(s)}
</article>"""


def withheld_section(v: dict) -> str:
    if not v["withheld"]:
        return ""
    items = "".join(
        f'<li><strong>{esc(w["label"])}</strong> <code>{esc(w["key"])}</code>. Källa: {esc(w["source"])}. '
        f'Visas inte: {esc(w["why"])}. '
        f'{"Räknas i grenens index." if w["counted"] else "Räknas inte i grenens index."}</li>' for w in v["withheld"])
    return f"""<section id="withheld" class="withheld">
<h2>Serier som inte visas av licensskäl</h2>
<p>De här serierna ingår i grenens kärnserier men publiceras inte här. Indexet, tillståndet och antalen ovan omfattar dem enligt registret. Värden, takter och riktning per serie visas inte.</p>
<ul>{items}</ul>
</section>"""


def branch_page(v: dict, build: dict) -> str:
    rec = v["record"]
    code = v["code"]
    if not v.get("has_core"):
        state_html = "<p>Grenen har inga registrerade kärnserier än.</p>"
    else:
        state_html = f"""<div class="branch-state">{state_badge(v.get('state'))}
<span class="index" title="Diffusionsindex">{num(v.get('index'))}</span>
<span>{counts(v)}</span></div>
<p class="change">{change_text(v)}</p>"""
    sel = ""
    if v.get("selected_benchmarks") is not None:
        names = ", ".join(f"<code>{esc(b)}</code>" for b in v["selected_benchmarks"]) or "inga"
        sel = f'<p class="small muted">Valda benchmarks på beräkningsdagen (registrerad urvalsregel): {names}.</p>'
    counted = "".join(series_card(s, True) for s in v["counted"]) or "<p>Inga serier räknas den här månaden.</p>"
    not_counted = ""
    if v["not_counted"]:
        not_counted = (f'<section><h2>Serier som inte räknas</h2><p>Kärnserier som saknar ett giltigt mått på '
                       f'beräkningsdagen, med skälet. De beskriver men påverkar inte indexet.</p>'
                       f'{"".join(series_card(s, False) for s in v["not_counted"])}</section>')
    hist = ""
    if any(h.get("index") is not None for h in v["history"]):
        hist = """<figure class="chart wide" data-chart="index"><figcaption>Diffusionsindex per månadsslut. Streckat: rekonstruerat. Heldraget: skarpa ögonblicksbilder. Linjerna vid 0,33 och 0,67 är tillståndsgränserna.</figcaption></figure>"""
    body = f"""{branch_nav(code)}
<section class="intro">
<p class="crumb"><a href="index.html">Översikt</a> › {code}</p>
<h1><span class="code">{code}</span> {esc(v['name'])}</h1>
<p class="lead">{esc(v.get('question'))}</p>
{record_banner(rec)}
{state_html}
{sel}
{hist}
</section>
<section><h2>Serier som räknas</h2>
<p>Takt och förändring i takt så som de var kända vid {esc(rec['date'])} (en version, <code>as_of</code> beräkningsdagen). Riktningen avgörs av den senaste perioden.</p>
{counted}</section>
{not_counted}
{withheld_section(v)}"""
    return page(f"{code} {v['name']} – {SITE_TITLE}", "gren", body, f"data/gren/{code}.json", build)


# ------------------------------------------------------------------ nowcasts


def nowcast_section(n: dict, build: dict) -> str:
    variants = "".join(f'<li><strong>{esc(x["id"])}</strong>{" (huvudmodell)" if x["id"] == n["champion"] else " (skugga)"}: '
                       f'{esc(x["text"])}</li>' for x in n["variants"])
    nxt = (f"Nästa skarpa prognos: {esc(n['next_period'])}, görs {esc(n['next_origin'])}."
           if n.get("next_origin") else "")
    var_ids = [x["id"] for x in n["variants"]]
    with_iv = any(f.get("intervals") for f in n["forecasts"])  # only with intervals.ENABLED (grind G-C)

    def iv_cell(f):
        lo, hi = ((f.get("intervals") or {}).get("80") or [None, None])
        return f'<td class="num">{num(lo, 0)} – {num(hi, 0)}</td>' if lo is not None else "<td></td>"

    if n["forecasts"]:
        head = "".join(f"<th>{esc(v)}</th>" for v in var_ids) + ("<th>80 % intervall</th>" if with_iv else "")
        rows = "".join(
            f'<tr><td>{esc(f["period"])}</td><td>{esc(f.get("origin"))}</td><td>{esc(f.get("champion"))}</td>'
            f'<td class="num">{num(f.get("value"), 0)}</td>'
            + "".join(f'<td class="num">{num((f.get("variants") or {}).get(v), 0)}</td>' for v in var_ids)
            + (iv_cell(f) if with_iv else "")
            + f'<td><a href="{esc(build["repo"])}/blob/main/{esc(f["file"])}">fil</a></td></tr>' for f in n["forecasts"])
        fc = (f'<div class="table-wrap"><table><thead><tr><th>Period</th><th>Origin</th><th>Huvudmodell</th>'
              f'<th>Prognos</th>{head}<th>Git</th></tr></thead><tbody>{rows}</tbody></table></div>')
    else:
        fc = "<p>Inga skarpa prognoser än.</p>"
    sc = ""
    if n["scorecard"]:
        rows = "".join(
            f'<tr><td>{esc(r.get("period"))}</td><td>{esc(r.get("champion"))}</td><td class="num">{num(r.get("forecast"), 0)}</td>'
            f'<td class="num">{num(r.get("outcome"), 0)}</td><td>{esc(r.get("known_from"))}</td>'
            f'<td class="num">{num(r.get("err_champion"), 2, signed=True)}</td>'
            + "".join(f'<td class="num">{num(r.get(f"err_{v}"), 2, signed=True)}</td>' for v in var_ids)
            + f'<td>{esc(r.get("status"))}</td></tr>' for r in n["scorecard"])
        head = "".join(f"<th>Fel {esc(v)}</th>" for v in var_ids)
        sc = (f'<h3>Scorecard</h3><div class="table-wrap"><table><thead><tr><th>Period</th><th>Huvudmodell</th>'
              f'<th>Prognos</th><th>Utfall</th><th>Känt från</th><th>Fel huvudmodell</th>{head}<th>Status</th></tr>'
              f'</thead><tbody>{rows}</tbody></table></div>')
        summ = [s for s in n["summary"] if s["n"]]
        if summ:
            sc += ('<div class="table-wrap"><table class="narrow"><thead><tr><th>Variant</th><th>n</th><th>MAE</th>'
                   '<th>Bias</th></tr></thead><tbody>' +
                   "".join(f'<tr><td>{"huvudmodell" if s["variant"] == "champion" else esc(s["variant"])}</td>'
                           f'<td class="num">{s["n"]}</td><td class="num">{num(s["mae"])}</td>'
                           f'<td class="num">{num(s["bias"], 2, signed=True)}</td></tr>' for s in summ) +
                   "</tbody></table></div><p class='small muted'>Få utfall: skillnader mellan varianter kan vara slump.</p>")
        cov = [c for c in n.get("coverage") or [] if c["n"]]
        if cov:
            keys = n["interval_levels"]
            sc += ('<div class="table-wrap"><table class="narrow"><thead><tr><th>Variant</th><th>n</th>'
                   + "".join(f"<th>Täckning {esc(k)} %</th>" for k in keys) + '<th>CRPS</th></tr></thead><tbody>'
                   + "".join(f'<tr><td>{"huvudmodell" if c["variant"] == "champion" else esc(c["variant"])}</td>'
                             f'<td class="num">{c["n"]}</td>'
                             + "".join(f'<td class="num">{num(c.get(f"coverage_{k}"))} '
                                       f'[{num((c.get(f"band_{k}") or [None, None])[0])}–'
                                       f'{num((c.get(f"band_{k}") or [None, None])[1])}]</td>' for k in keys)
                             + f'<td class="num">{num(c["crps"])}</td></tr>' for c in cov)
                   + "</tbody></table></div><p class='small muted'>Täckning = andel utfall inom intervallet, med ett binomialt "
                     "90 %-band inom hakparentes. Den blir meningsfull först efter många utfall, och dålig kalibrering "
                     "byter inte huvudmodell.</p>")
    elif n.get("scorecard_error"):
        sc = f'<p class="reason">Scorecarden kunde inte beräknas: {esc(n["scorecard_error"])}</p>'
    chart = ""
    if n.get("history"):
        chart = (f'<figure class="chart wide" data-chart="nowcast" data-id="{esc(n["id"])}"><figcaption>'
                 f'{esc(n["target_label"])} ({esc(n["unit"])}), senaste kända version. Punkter: skarpa prognoser '
                 f'(huvudmodellen){", med 50 %- och 95 %-intervall" if with_iv else ""}.</figcaption></figure>'
                 f'<p class="source">Källa: {esc(n["source"])}. Licens: {esc(n["license"])}.</p>')
    return f"""<section class="nowcast" id="{esc(n['id'])}">
<h2>{esc(n['label'])}: {esc(n['title'])}</h2>
<p>Mål: <code>{esc(n['target'])}</code>, {esc(n['target_label'])}, första publicerade värdet. Frekvens: {esc(n['frequency'])}. Prognosdag: {esc(n['origin_rule'])}. {nxt}</p>
<p>Huvudmodell nu: <strong>{esc(n['champion'])}</strong>. Skuggor: {esc(', '.join(n['shadows']))}.</p>
<ul class="variants">{variants}</ul>
{chart}
<h3>Skarpa prognoser</h3>
{fc}
{sc}
<p class="small">Backtest och regeln för befordran: <a href="{esc(build['repo'])}/blob/main/{esc(n['results_doc'])}">{esc(n['results_doc'])}</a>.</p>
</section>"""


def nowcast_page(doc: dict, build: dict) -> str:
    body = f"""<section class="intro">
<h1>Prognoser</h1>
<p class="lead">Två nowcasts med scorecard. Varje skarp prognos görs på en registrerad prognosdag med bara data som var känd den dagen, committas till git och skrivs aldrig om. Tidsstämpeln i git är beviset. Utfallet är målseriens första publicerade värde, och felet är 100 × (log prognos − log utfall).</p>
<p>Huvudmodellen är den som stod i filen när prognosen gjordes. Övriga varianter visas som skuggor och jämförs på samma utfall. Alla prognoser i <a href="{esc(build['repo'])}/tree/main/forecasts">forecasts/</a>.</p>
</section>
{''.join(nowcast_section(n, build) for n in doc['nowcasts'])}"""
    return page(f"Prognoser – {SITE_TITLE}", "prognoser", body, "data/prognoser.json", build)


# ------------------------------------------------------------------ method


def method_page(doc: dict, build: dict) -> str:
    repo = esc(build["repo"])
    rows = "".join(
        f'<tr><td>{esc(s["source"])}</td><td>{esc(", ".join(s["branches"]))}</td><td>{esc(s["license"])}</td>'
        f'<td class="num">{s["n_published"]} av {s["n_series"]}</td>'
        f'<td><details><summary>villkor</summary><p class="small">{esc(s["license_text"])}</p></details></td></tr>'
        for s in doc["sources"])
    withheld = "".join(f'<tr><td>{esc(w["branch"])}</td><td><code>{esc(w["key"])}</code></td><td>{esc(w["label"])}</td>'
                       f'<td>{esc(w["why"])}</td></tr>' for w in doc["withheld"])
    body = f"""<section class="intro prose">
<h1>Metod och källor</h1>
<p class="lead">Projektet följer AI-utrullningen i världen kvantitativt, neutralt och öppet, och visar när utvecklingen ändrar takt, i båda riktningarna.</p>
<h2>Neutral spårning</h2>
<p>Varje gren (G1–G9) beskrivs med nivå, takt, förändring i takt och överraskning. Det finns inga larmnivåer och inget val av riktning: en gren som accelererar och en som bromsar in redovisas på samma sätt. Projektet tar inte ställning för någon tes om AI.</p>
<h2>Förregistrering</h2>
<p>Vilka serier som följs, hur takten beräknas och hur tillståndet klassas låstes i <a href="{repo}/blob/main/docs/mattregister.md">måttregistret</a> innan data analyserades. Ändringar läggs till med datum och motivering, och ingenting skrivs om. Det skyddar mot att man i efterhand väljer de serier som passar.</p>
<h2>Ingen läcka</h2>
<p>Varje värde har ett <code>known_from</code>: inlämningsdatum för SEC-dokument, publiceringsdatum för övrigt. Alla mått beräknas med bara data som var känd på beräkningsdagen, och statistik över historiken med expanderande fönster. Serier utan sparade versioner dateras med publiceringsfördröjning och märks <em>backfill</em>.</p>
<h2>Oföränderliga filer i git</h2>
<p>En ögonblicksbild per månad skrivs vid månadsslut till <a href="{repo}/tree/main/snapshots">snapshots/</a>, och de skarpa prognoserna till <a href="{repo}/tree/main/forecasts">forecasts/</a>. Båda skrivs en gång och aldrig om. Git-historiken visar när varje fil skrevs. Före den första skarpa ögonblicksbilden visar sidan en rekonstruktion som är tydligt märkt: {esc(build['record']['recon_label'])}.</p>
<h2>Ärlighet om osäkerhet</h2>
<p>Kvartalsserier är korta och har regimbrott efter 2023. Grenar med fyra eller fem serier flyttas mycket av en enda serie. Om tillståndsregeln har något prognosvärde är inte prövat. Resultat och förbehåll står i <a href="{repo}/blob/main/docs/resultat/tillstand.md">docs/resultat/tillstand.md</a>.</p>
<h2>Inte investeringsrådgivning</h2>
<p class="banner">{NOT_INVESTMENT_ADVICE} Projektet håller inga innehav och kopplar inte måtten till placeringar.</p>
</section>
<section>
<h2>Datakällor och licenser</h2>
<p>{doc['n_published']} av {doc['n_series']} serier i katalogen får visas här. Bara serier vars licens är kontrollerad och tillåter vidarepublicering visas med värden. Från rapporter visas bara extraherade siffror med källhänvisning, aldrig text. Data committas inte till git, utan hämtas med skript.</p>
<div class="table-wrap"><table><thead><tr><th>Källa</th><th>Grenar</th><th>Licens</th><th>Visas</th><th></th></tr></thead><tbody>{rows}</tbody></table></div>
</section>
<section id="withheld">
<h2>Serier som inte visas</h2>
<p>För dessa serier visas på grenarnas sidor bara grenens summering (index, tillstånd och antal), om serien är en kärnserie.</p>
<div class="table-wrap"><table><thead><tr><th>Gren</th><th>Serie</th><th>Namn</th><th>Skäl</th></tr></thead><tbody>{withheld}</tbody></table></div>
</section>"""
    return page(f"Metod och källor – {SITE_TITLE}", "metod", body, None, build)
