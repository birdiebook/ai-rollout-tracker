"""Company-disclosed AI KPIs (step 2, track B4): a curated CSV of agent-extracted values, loaded as release-dated series.

Leads L2 (usage: tokens, users, developers, customers) and L3 (revenue: AI run-rates, Azure and cloud growth,
backlog), plus coded capacity statements. The agent read every candidate sentence (ai_kpis_corpus) and recorded one
row per stated value in curated/ai_kpis.csv: number(s), unit, kind, definition code, period, the document's date,
URL / accession, locator and the SHA-256 of the exact sentence. The sentence itself is kept only in data/raw
(gitignored). Coding rules: docs/kallor/ai_nyckeltal.md (written before the coding).

Definition code = series: every change of definition ("monthly" vs "weekly" users, "AI business" vs "AI revenue",
growth as reported vs in constant currency) is a separate code and therefore a separate series.

known_from = `filed`. The loader refuses a row whose known_from is before the start of its period (a value cannot
be stated before its period begins) and a row whose acceptance time does not match the filing date.
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from ai_tracker import config

PATH = config.REPO / "curated" / "ai_kpis.csv"
SENTENCES_DIR = config.REPO / "data" / "raw" / "ai_kpis_sentences"  # gitignored

COLUMNS = ["id", "company", "definition", "kind", "value_lo", "value_hi", "unit", "code", "capacity_time", "freq",
           "period", "period_basis", "filed", "accepted", "doc_type", "source_url", "accession", "locator",
           "sentence_sha256", "note"]
COMPANIES = ("msft", "googl", "amzn", "meta", "nvda")
KINDS = ("point", "approx", "min", "range", "code")
PERIOD_BASES = ("reported_quarter", "fiscal_year", "stated_date", "quarter_end", "document_date", "forward")
CAPACITY_TIMES = ("current", "forward")


@dataclass(frozen=True)
class Definition:
    company: str
    lead: str  # "L2" usage, "L3" revenue, "cap" capacity
    unit: str
    freq: str  # "M" (point-in-time value: month it refers to), "Q" (reported quarter) or "A" (fiscal year)
    label: str  # Swedish, for the catalog
    text: str  # what the number measures, in the company's terms (English)


# Series that have ended (the company stopped stating the KPI on this definition), and why.
CLOSED: dict[str, str] = {}

_U = {"users": "miljoner användare", "count": "antal", "musd": "MUSD", "pct": "%", "pp": "procentenheter",
      "tn": "biljoner tokens", "bn_min": "miljarder tokens per minut"}

# code: (company, lead, unit key, freq, Swedish label, what the company's number measures)
_DEFS = {
    # ---- L2 usage: tokens
    "GOOGL_API_TOKENS_PER_MIN": ("googl", "L2", "bn_min", "M", "Alphabet: tokens per minut via API för egna modeller",
                                 "tokens processed per minute by Google's first-party models via direct API use by "
                                 "customers ('first-party model APIs', 'Gemini models ... API tokens')"),
    "MSFT_TOKENS_QUARTER": ("msft", "L2", "tn", "Q", "Microsoft: tokens bearbetade under kvartalet",
                            "tokens processed in the fiscal quarter, all Microsoft AI services (call)"),
    "MSFT_TOKENS_MONTH": ("msft", "L2", "tn", "M", "Microsoft: tokens bearbetade under en månad",
                          "tokens processed in one month, all Microsoft AI services (call)"),
    "MSFT_FOUNDRY_TOKENS_FY": ("msft", "L2", "tn", "A", "Microsoft: tokens via Foundry-API:er under räkenskapsåret "
                               "(period = året då det slutar)", "tokens served by Foundry APIs in the fiscal year "
                               "(July-June; stored as the calendar year in which it ends)"),
    "MSFT_FOUNDRY_CUST_1T_TOKENS": ("msft", "L2", "count", "M",
                                    "Microsoft: kunder på väg mot över en biljon tokens på Foundry i år",
                                    "customers on track to process over one trillion tokens on Foundry this year"),
    # ---- L2 usage: users
    "GOOGL_GEMINI_APP_MAU": ("googl", "L2", "users", "M", "Alphabet: Gemini-appen, månatligt aktiva användare",
                             "Gemini app monthly active users"),
    "GOOGL_GEMINI_APP_USERS": ("googl", "L2", "users", "M", "Alphabet: Gemini-appen, användare (ospecificerat)",
                               "Gemini app 'users' (no activity window stated)"),
    "GOOGL_AI_OVERVIEWS_MONTHLY_USERS": ("googl", "L2", "users", "M", "Alphabet: AI Overviews, användare per månad",
                                         "AI Overviews in Search, users per month"),
    "GOOGL_MODEL_DEVELOPERS_MONTHLY": ("googl", "L2", "users", "M",
                                       "Alphabet: utvecklare som bygger med Googles modeller per månad",
                                       "developers building with Google's models monthly"),
    "META_AI_MAU": ("meta", "L2", "users", "M", "Meta: Meta AI, månatligt aktiva", "Meta AI monthly actives"),
    "MSFT_COPILOT_APPS_MAU": ("msft", "L2", "users", "M", "Microsoft: Copilot-familjen, månatligt aktiva användare",
                              "monthly active users of Microsoft's first-party family of Copilot apps, commercial and "
                              "consumer"),
    "MSFT_AI_FEATURES_MAU": ("msft", "L2", "users", "M",
                             "Microsoft: månatligt aktiva användare av AI-funktioner i alla produkter",
                             "monthly active users of AI features across Microsoft's products"),
    "MSFT_GHCP_USERS": ("msft", "L2", "users", "M", "Microsoft: GitHub Copilot, användare",
                        "GitHub Copilot users (free and paid)"),
    "MSFT_GHCP_PAID_USERS": ("msft", "L2", "users", "M", "Microsoft: GitHub Copilot, betalande användare",
                             "paid (GitHub) Copilot users"),
    "MSFT_GHCP_PAID_SUBS": ("msft", "L2", "users", "M", "Microsoft: GitHub Copilot, betalande prenumeranter",
                            "paid GitHub Copilot subscribers"),
    "MSFT_GHCP_BUSINESS_ORGS": ("msft", "L2", "count", "M", "Microsoft: organisationer med GitHub Copilot for Business",
                                "organizations signed up for / subscribed to GitHub Copilot for Business"),
    "MSFT_GHCP_ORGS": ("msft", "L2", "count", "M", "Microsoft: organisationer som använder GitHub Copilot",
                       "organizations that have adopted / use GitHub Copilot (any plan)"),
    "MSFT_M365_COPILOT_PAID_SEATS": ("msft", "L2", "users", "M", "Microsoft: betalda platser i Microsoft 365 Copilot",
                                     "paid Microsoft 365 Copilot seats (millions)"),
    "MSFT_AZURE_OPENAI_CUSTOMERS": ("msft", "L2", "count", "M", "Microsoft: kunder i Azure OpenAI Service",
                                    "customers / organizations using Azure OpenAI Service"),
    "MSFT_AZURE_AI_CUSTOMERS": ("msft", "L2", "count", "M", "Microsoft: Azure AI-kunder", "Azure AI customers"),
    "MSFT_FOUNDRY_ENTERPRISES": ("msft", "L2", "count", "M", "Microsoft: företag vars utvecklare använder Foundry",
                                 "enterprises and digital natives whose developers use (Azure AI) Foundry"),
    "MSFT_FOUNDRY_CUSTOMERS": ("msft", "L2", "count", "M", "Microsoft: Foundry-kunder", "Foundry customers"),
    "MSFT_FOUNDRY_AGENT_SERVICE_CUSTOMERS": ("msft", "L2", "count", "M", "Microsoft: kunder i Foundry Agent Service",
                                             "organizations / customers using (Foundry) Agent Service"),
    "MSFT_COPILOT_STUDIO_ORGS": ("msft", "L2", "count", "M", "Microsoft: organisationer som har använt Copilot Studio",
                                 "organizations / customers that have used Copilot Studio to date"),
    "MSFT_POWER_PLATFORM_AI_ORGS": ("msft", "L2", "count", "M",
                                    "Microsoft: organisationer som har använt AI-funktioner i Power Platform",
                                    "organizations that have used AI(-powered) capabilities in Power Platform to date"),
    "MSFT_POWER_PLATFORM_COPILOT_ORGS": ("msft", "L2", "count", "M",
                                         "Microsoft: organisationer som har använt Copilot i Power Platform",
                                         "organizations that have used Copilot in Power Platform to date"),
    "AMZN_BEDROCK_CUSTOMERS": ("amzn", "L2", "count", "M", "Amazon: företag som använder Bedrock",
                               "companies using Amazon Bedrock"),
    "AMZN_RUFUS_CUSTOMERS_YTD": ("amzn", "L2", "users", "M", "Amazon: kunder som har använt Rufus i år",
                                 "customers using Rufus this year (year to date)"),
    "AMZN_ALEXA_SHOPPING_CUSTOMERS_TTM": ("amzn", "L2", "users", "M",
                                          "Amazon: kunder som har använt Alexa for Shopping senaste 12 månaderna",
                                          "customers using Alexa for Shopping in the last 12 months"),
    # ---- L3 revenue
    "MSFT_AI_BUSINESS_RUNRATE": ("msft", "L3", "musd", "M", "Microsoft: AI-verksamhetens intäkt i årstakt",
                                 "annual revenue run rate of Microsoft's AI business"),
    "MSFT_AI_BUSINESS_RUNRATE_EXPECTED": ("msft", "L3", "musd", "M",
                                          "Microsoft: väntad intäkt i årstakt för AI-verksamheten (framåtblickande)",
                                          "expected annual revenue run rate of the AI business at the end of the "
                                          "stated (future) quarter"),
    "MSFT_LINKEDIN_AI_RUNRATE": ("msft", "L3", "musd", "M",
                                 "Microsoft: AI-produkter i LinkedIn Talent Solutions, intäkt i årstakt",
                                 "annualized revenue run rate of AI-powered products in LinkedIn Talent Solutions"),
    "AMZN_AWS_AI_RUNRATE": ("amzn", "L3", "musd", "M", "Amazon: AWS AI-verksamhet, intäkt i årstakt",
                            "annual revenue run rate of AWS's AI business"),
    "AMZN_CHIPS_RUNRATE_TRN_GRV": ("amzn", "L3", "musd", "M", "Amazon: Trainium och Graviton, intäkt i årstakt",
                                   "combined annual revenue run rate of Trainium and Graviton"),
    "AMZN_CHIPS_RUNRATE": ("amzn", "L3", "musd", "M", "Amazon: chipverksamheten (Graviton, Trainium, Nitro), årstakt",
                           "annual revenue run rate of Amazon's chips business incl. Graviton, Trainium and Nitro"),
    "GOOGL_CLOUD_BACKLOG": ("googl", "L3", "musd", "M", "Alphabet: Google Clouds orderstock (backlog)",
                            "Google Cloud backlog at the end of the quarter (press-release wording)"),
    "MSFT_AZURE_GROWTH_V1": ("msft", "L3", "pct", "Q", "Microsoft: Azure and other cloud services, tillväxt å/å "
                             "(definition före FY25)", "Azure and other cloud services revenue growth y/y as reported, "
                             "metric basis until FY24 (incl. EMS and Power BI per-user revenue)"),
    "MSFT_AZURE_GROWTH_CC_V1": ("msft", "L3", "pct", "Q", "Microsoft: Azure and other cloud services, tillväxt å/å i "
                                "konstant valuta (definition före FY25)", "as MSFT_AZURE_GROWTH_V1, constant currency"),
    "MSFT_AZURE_GROWTH_V2": ("msft", "L3", "pct", "Q", "Microsoft: Azure and other cloud services, tillväxt å/å "
                             "(definition FY25–FY26)", "Azure and other cloud services revenue growth y/y as reported, "
                             "metric basis FY25-FY26 (EMS and Power BI moved out; restated FY24 in the 8-K of "
                             "2024-08-21)"),
    "MSFT_AZURE_GROWTH_CC_V2": ("msft", "L3", "pct", "Q", "Microsoft: Azure and other cloud services, tillväxt å/å i "
                                "konstant valuta (definition FY25–FY26)", "as MSFT_AZURE_GROWTH_V2, constant currency"),
    "MSFT_AZURE_GROWTH_V3": ("msft", "L3", "pct", "Q", "Microsoft: Azure, tillväxt å/å (definition från FY27)",
                             "'Azure revenue' growth y/y as reported, metric basis from FY27 (restated FY26 in the 8-K "
                             "of 2026-09-02)"),
    "MSFT_AZURE_GROWTH_CC_V3": ("msft", "L3", "pct", "Q", "Microsoft: Azure, tillväxt å/å i konstant valuta "
                                "(definition från FY27)", "as MSFT_AZURE_GROWTH_V3, constant currency"),
    "MSFT_AZURE_AI_PTS_V1": ("msft", "L3", "pp", "Q", "Microsoft: AI-tjänsternas bidrag till Azures tillväxt "
                             "(definition före FY25)", "points of Azure growth from AI services, metric basis until FY24"),
    "MSFT_AZURE_AI_PTS_V2": ("msft", "L3", "pp", "Q", "Microsoft: AI-tjänsternas bidrag till Azures tillväxt "
                             "(definition FY25–)", "points of Azure growth from AI services, metric basis from FY25 "
                             "(restated FY24 in the 8-K of 2024-08-21)"),
}

DEFINITIONS: dict[str, Definition] = {
    code: Definition(c, lead, _U[unit], freq, label, text) for code, (c, lead, unit, freq, label, text) in _DEFS.items()
}


def capacity_code(company: str, time: str) -> str:
    return f"{company.upper()}_CAPACITY_{time.upper()}"


# Series that ended: their metric basis was replaced (a new definition code continues the KPI).
CLOSED.update({
    "MSFT_AZURE_GROWTH_V1": "Microsoft changed the Azure metric for FY25 (MSFT_AZURE_GROWTH_V2)",
    "MSFT_AZURE_GROWTH_CC_V1": "Microsoft changed the Azure metric for FY25 (MSFT_AZURE_GROWTH_CC_V2)",
    "MSFT_AZURE_GROWTH_V2": "Microsoft changed the Azure metric for FY27 (MSFT_AZURE_GROWTH_V3)",
    "MSFT_AZURE_GROWTH_CC_V2": "Microsoft changed the Azure metric for FY27 (MSFT_AZURE_GROWTH_CC_V3)",
    "MSFT_AZURE_AI_PTS_V1": "Microsoft changed the Azure metric for FY25 (MSFT_AZURE_AI_PTS_V2)",
})

for _c, _name in (("msft", "Microsoft"), ("googl", "Alphabet"), ("amzn", "Amazon"), ("meta", "Meta"),
                  ("nvda", "Nvidia")):
    for _t, _sv in (("current", "läget nu"), ("forward", "förväntan")):
        DEFINITIONS[capacity_code(_c, _t)] = Definition(
            _c, "cap", "kod", "Q", f"{_name}: kapacitet mot efterfrågan, {_sv} (kod −2..+2)",
            f"{_name}: coded statement on own AI/cloud capacity vs demand ({_t}); rules in docs/kallor/ai_nyckeltal.md")


class CsvError(ValueError):
    pass


def _float(x: str) -> float | None:
    return float(x) if str(x).strip() not in ("", "nan", "None") else None


def _period(freq: str, period: str) -> pd.Period:
    if freq == "M":
        if not re.fullmatch(r"\d{4}-\d{2}", period):
            raise CsvError(f"monthly period must be YYYY-MM, not {period!r}")
        return pd.Period(period, freq="M")
    if freq == "Q":
        if not re.fullmatch(r"\d{4}Q[1-4]", period):
            raise CsvError(f"quarterly period must be YYYYQn, not {period!r}")
        return pd.Period(period, freq="Q-DEC")
    if freq == "A":  # a fiscal year, stored as the calendar year in which it ends (as guidance_capex)
        if not re.fullmatch(r"\d{4}", period):
            raise CsvError(f"annual period must be YYYY, not {period!r}")
        return pd.Period(period, freq="Y-DEC")
    raise CsvError(f"freq must be M, Q or A, not {freq!r}")


def load(path: Path | None = None) -> pd.DataFrame:
    """Validated rows of the curated CSV, with known_from (= filed) as Timestamp."""
    path = path or PATH
    with open(path, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    if rows and list(rows[0]) != COLUMNS:
        raise CsvError(f"columns {list(rows[0])} != {COLUMNS}")
    seen = set()
    for r in rows:
        where = f"{path.name} id={r.get('id')}"
        try:
            if r["id"] in seen:
                raise CsvError("duplicate id")
            seen.add(r["id"])
            d = DEFINITIONS.get(r["definition"])
            if d is None:
                raise CsvError(f"unknown definition {r['definition']!r}")
            if r["company"] != d.company or r["unit"] != d.unit or r["freq"] != d.freq:
                raise CsvError(f"company/unit/freq {r['company']}/{r['unit']}/{r['freq']} != definition "
                               f"{d.company}/{d.unit}/{d.freq}")
            if r["kind"] not in KINDS or r["period_basis"] not in PERIOD_BASES:
                raise CsvError("kind/period_basis not in the scheme")
            if not re.fullmatch(r"[0-9a-f]{64}", r["sentence_sha256"]):
                raise CsvError("sentence_sha256 must be 64 hex characters")
            if not r["source_url"].startswith("https://") or not re.search(r"sentence #\d+", r["locator"]):
                raise CsvError("source_url and a locator with 'sentence #k' are required")
            period = _period(r["freq"], r["period"])
            filed = pd.Timestamp(r["filed"])
            if filed < period.start_time and r["period_basis"] != "forward":
                raise CsvError(f"filed {filed.date()} before its period {period} began")
            if r["accepted"] and not -4 <= (pd.Timestamp(r["accepted"][:10]) - filed).days <= 1:
                raise CsvError(f"accepted {r['accepted']} does not match the filing date {r['filed']}")
            lo, hi = _float(r["value_lo"]), _float(r["value_hi"])
            if d.lead == "cap":
                if r["kind"] != "code" or r["code"] not in ("-2", "-1", "0", "1", "2"):
                    raise CsvError("a capacity row has kind 'code' and code in -2..2")
                if r["capacity_time"] != d.text.split("(")[-1].split(")")[0]:
                    raise CsvError("capacity_time does not match the definition")
            else:
                if r["kind"] == "code" or r["code"] or r["capacity_time"]:
                    raise CsvError("code/capacity_time are only for capacity rows")
                if lo is None or (r["kind"] == "range") != (hi is not None and hi != lo):
                    raise CsvError(f"kind {r['kind']} needs value_lo (and value_hi > value_lo only for a range)")
                if hi is not None and lo > hi:
                    raise CsvError("value_lo > value_hi")
        except (CsvError, ValueError) as exc:
            raise CsvError(f"{where}: {exc}") from None
    df = pd.DataFrame(rows, columns=COLUMNS)
    for c in ("value_lo", "value_hi"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["code"] = pd.to_numeric(df["code"], errors="coerce")
    df["known_from"] = pd.to_datetime(df["filed"])
    return df


def series_frame(df: pd.DataFrame, definition: str) -> pd.DataFrame:
    """Release-dated rows (period, value, known_from) for one definition.

    Value = value_lo (a range's lower end; the upper end is kept in the CSV), or the code for capacity rows. A value
    repeated in a later document adds no row; several rows for one period in one document: the last in file order.
    """
    d = df[df["definition"] == definition].copy()
    col = "code" if DEFINITIONS[definition].lead == "cap" else "value_lo"
    d = d.dropna(subset=[col]).sort_values("known_from", kind="stable")
    out, last = [], {}
    for p, v, kf in d[["period", col, "known_from"]].itertuples(index=False):
        if p in last and last[p] == v:
            continue
        last[p] = v
        out.append((p, float(v), kf))
    res = pd.DataFrame(out, columns=["period", "value", "known_from"])
    return res.drop_duplicates(["period", "known_from"], keep="last").reset_index(drop=True)


def series_key(definition: str) -> str:
    return "kpi_" + definition.lower()
