# Källa: bolagens fleråriga planer (steg 2, spår D1)

Status: under arbete. Avsnittet "Kodningsregler" skrevs och committades **innan** någon kandidatmening kodades.
Senare tillägg till reglerna dateras och motiveras i avsnittet "Ändringar i reglerna".

Program D (framåtblick), led L4 (kontrakterad efterfrågan) och L5 (investeringar). Löptidsprofilen för RPO finns
redan i A1 (`rpo_<bolag>_12m`/`_24m` och `_after*`, se `docs/kallor/rpo.md`) och dupliceras inte här.

## Kodningsregler (låsta 2026-11-23, före kodningen)

### Vad som kodas

En rad per uttalat värde i `curated/plans.csv`. Bolag: Microsoft (`msft`), Alphabet (`googl`), Amazon (`amzn`), Meta
(`meta`), Oracle (`orcl`) och CoreWeave (`crwv`). Bara bolagets egna planer och egna mått, aldrig uttalanden om
kunder, marknaden eller branschen ("hyperscalers will spend …").

| Mått (`measure`) | Innehåll | Enhet |
|---|---|---|
| `CAPEX` | Capex för en period **efter** innevarande räkenskapsår (år Y+1 och senare) eller en flerårssumma. För Oracle och CoreWeave, som inte finns i E1:s fil, också innevarande år | MUSD eller kod |
| `INFRA` | Ett aviserat investeringsbelopp i infrastruktur, datacenter eller AI-infrastruktur som inte uttryckligen är capex ("invest $80 billion to build out AI-enabled datacenters", "$X in the U.S. over the next four years"). `scope` = `global` eller landskod (ISO 3166-1 alfa-2) | MUSD |
| `CAPACITY` | Datacenterkapacitet i effekt. `kind` avgör om det är ett mål eller ett redovisat läge (nedan). Relativa mål ("double our total data center footprint over the next two years") får enheten `multiple` (2 = fördubbling, +80 % = 1,8) | MW eller multiple |
| `BACKLOG` | Orderstock som inte är bolagets totala RPO i XBRL: CoreWeaves "revenue backlog" och orderstock eller RPO för ett segment som bolaget anger i text (t.ex. Google Cloud, Microsofts kommersiella RPO, AWS). Bolagets totala RPO kodas inte (A1) | MUSD |
| `COMMIT` | Avtalade, icke uppsägningsbara åtaganden för infrastruktur som anges med belopp i text (servrar, nätverk, datacenterbyggen, utrustning). Leasingavtal som inte har börjat kodas inte (A3), och inte heller allmänna inköpsåtaganden utan koppling till infrastruktur | MUSD |

**Kodas inte:** redovisade utfall för capex, intäktsmål (t.ex. Oracles mål för OCI-intäkter, de hör till L3),
enskilda kundavtal (de ingår i backlog och RPO), hypotetiska formuleringar och riskfaktorer ("we may need to make
significant investments") utan belopp eller period, capex för innevarande år och nästa kvartal för MSFT, GOOGL,
AMZN och META (E1:s domän i `curated/guidance_capex.csv`), och riktningar utan identifierbar period ("capital
expenditures will increase in coming years").

### Typ (`kind`)

- `point` exakt värde, `range` intervall, `approx` "about", "approximately", "roughly", "nearly", "~", `min` "over",
  "more than", "at least", "in excess of", "exceed", `max` "up to", "no more than".
- `direction`: kvalitativ riktning, `direction_code` −2..+2 som i E1: +2 kraftig ökning ("significantly",
  "meaningfully", "notably larger", "well in excess of double"), +1 ökning, 0 i nivå med, −1 minskning, −2 kraftig
  minskning. `direction_base`: `yoy` (perioden mot föregående period av samma längd) eller `growth_vs_prior`
  (tillväxten, i takt eller i dollar som det står, mot föregående periods tillväxt).
- `reported`: ett redovisat läge vid ett datum (CoreWeaves backlog, aktiv eller kontrakterad effekt, kapacitet som
  bolaget säger att det har lagt till). Värdet är ett faktum i dokumentet, inte en plan. `value_lo = value_hi`.

### Horisont

- `horizon`: `Y` ett räkenskaps- eller kalenderår, `SPAN` en flerårsperiod (summa över perioden), `BY` ett läge som
  ska nås senast ett datum ("by the end of 2027"), `ASOF` ett läge vid ett datum (för `reported`), `OPEN` ingen
  identifierbar slutpunkt (sparas i CSV:n men laddas inte som serie).
- `period_start` och `period_end` anges alltid för `Y`, `SPAN`, `BY` och `ASOF`. "Over the next N years" i ett
  dokument från datum d ges `period_start` = d och `period_end` = d + N år (sista dagen i månaden). "By 2028" eller
  "by the end of 2028" ger `period_end` = 2028-12-31. "In 2027" är kalenderåret 2027, "fiscal 2027" bolagets
  räkenskapsår (Microsoft juli–juni, Oracle juni–maj, övriga kalenderår).
- `year_basis`: `CY` eller `FY`. Ett räkenskapsår lagras med frekvens A och perioden = kalenderåret då det slutar
  (som i E1).
- Om perioden står i en annan mening i samma stycke (t.ex. "for fiscal 2026" i föregående mening) anges det i
  noten.

### Definition (`definition`)

Kod för vad talet mäter, med bolagets ordalydelse. Samma kod som i E1 när ordalydelsen är densamma
(`META_CAPEX_INCL_FL`, `MSFT_CAPEX_INCL_FL`, `GOOGL_CAPEX`, `AMZN_CASH_CAPEX`, `AMZN_CAPEX_UNSPEC`,
`GOOGL_TECH_INFRA`). Ny ordalydelse ger en ny kod, och koder slås aldrig ihop i en serie. Koderna listas i
`sources/plans.py` (`DEFINITIONS`) och nedan när de har använts.

### Datum

- `known_from` = `filed`: EDGAR:s `filingDate` för SEC-dokument (`acceptanceDateTime` sparas). För Microsofts
  samtal: samtalsdagen, som är samma dag som 8-K:n med resultatet (Item 2.02). För S-1 och 424B dagen för just det
  dokumentet.
- Samma värde i ett senare dokument ger en ny rad i CSV:n men ingen ny version i serien (första dokumentet räknas).
  Ett ändrat värde blir en ny version.
- Ett mål vars period redan har slutat när dokumentet kom är inget mål och avvisas av inläsningen, utom `reported`.

### Urval av kandidater (brett, efter R2-F1)

En mening är kandidat om den har ett **nyckelord** (capex, capital expenditure, capital spending, capital investment,
infrastructure, data center/datacenter, capacity, power, gigawatt, megawatt, GW, MW, backlog, remaining performance
obligation, commitment, committed, build-out, compute, eller "invest … in" följt av infrastruktur-, datacenter-,
AI- eller kapacitetsord) **och** något av följande, i alla tempus:

- ett dollarbelopp,
- ett effekttal (MW, GW, megawatt, gigawatt),
- ett årtal efter dokumentets år, eller en flerårsfras ("next N years", "multi-year", "through 20xx", "by 20xx",
  "coming years", "over time"),
- ett framåtblickande ord (expect, anticipate, plan, will, intend, target, on track, guide, outlook) tillsammans med
  capex- eller kapacitetsord.

Agenten läser alla kandidater. Antalet dokument, kandidater och kodade rader redovisas nedan.

### Korpus

- SEC EDGAR från 2022-01-01: varje 8-K med Item 2.02, 7.01 eller 8.01 (alla EX-99-bilagor och huvuddokumentet),
  varje 10-Q och 10-K, och för CoreWeave också S-1, S-1/A och 424B.
- microsoft.com: Microsofts sidor för resultatsamtalen (samma adresser som E1 och B4).
- Övriga IR-värdar provas en gång. Nekas de listas de, och inget kringgås.

### Stickprov

`python -m ai_tracker.plans_check --frac 0.2` hämtar om dokumenten för 20 % av raderna och kontrollerar att
meningen finns på angiven plats (SHA-256) och att talet eller riktningsordet står i den. Felandelen redovisas. Ett
oberoende granskningsspår (R5) läser om källorna innan serierna används.
