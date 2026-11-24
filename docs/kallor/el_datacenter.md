# Källor: el och datacenter (L7): PJM, EIA-930 och ERCOT (G7)

Steg 2, spår A4 (våg 1). Byggt och hämtat 2026-11-23. Inga takter, trender eller jämförelser mellan prognos och
utfall är beräknade. Måtten och kärnserierna registreras i grind G-A. Kontrollerat är bara att nivåerna stämmer med
källornas egna tabeller.

| Källa | Serier | Historik | `known_from` | Publiceras | Status |
|---|---|---|---|---|---|
| PJM kapacitetsauktion (BRA) | `pjm_bra_rcp_rto_a`, `pjm_bra_rcp_dom_a`, `pjm_bra_cleared_rto_a` | leveransår 2007/08–2028/29 (pris RTO), 2025/26– (DOM), 2020/21– (MW) | dag då resultatet publicerades, med belägg per år | nej | OK |
| PJM lastprognos (januarirapporten) | `pjm_lf_{peak,energy}_{rto,dom}_h{1,5,10}`, `pjm_lf_adj_{rto,dom}_h{1,5,10}` | årgång 2017–2026 (justeringar 2025–2026) | rapportens publiceringsdag | nej | OK |
| EIA-930 timvis last | `eia930_{avg,peak}_{pjm,pjm_dom,erco,soco,azps,srp}_m` | 2015-07 (PJM, ERCOT, APS), 2018-08/10/11 (SRP, DOM, SOCO) till 2026-10 | backfill: max(månadsslut + 7 dagar, 2016-07-25); DOM max(månadsslut + 31 dagar, 2019-08-21) | ja | OK, flaggad (se nedan) |
| ERCOT kö för stora laster | inga | – | – | – | **PARTIAL** (siffrorna finns bara som diagram i PDF) |

Hämtning: `python -m ai_tracker.observations [nycklar]`. Kontroller: `python -m ai_tracker.warehouse`.
Moduler: `sources/pjm.py`, `series/pjm.py`, `sources/eia930.py`, `series/eia930.py`. Tester: `tests/test_pjm.py`,
`tests/test_eia930.py` (fixtures utan nätverk).

## PJM: villkor (publiceras inte)

- PJM har ingen öppen licens för webbplatsen. Sidan `www.pjm.com/about-pjm/legal.aspx`, som villkoren hänvisar till,
  omdirigeras till `/not-found` (2026-11-23), och `pjm.com` utan www nekas av proxyn.
- Villkoren för Data Miner 2 (`data-license-agreement-edata-feed-data-miner-2`, PDF på www.pjm.com) är de enda
  villkor för data som gick att läsa: *"you may use the Data and the Tools for your internal business use or
  commercial purposes, including publishing and making derivatives of the Data, Members may republish data,
  however non-members are specifically prohibited from republishing data."* Data Miner 2 används inte här, men
  villkoren visar PJM:s hållning.
- Rapporterna är märkta "For Public Use", vilket är PJM:s sekretessklass och ingen licens.
- **Beslut:** serierna lagras och används i analysen, men `publish=False`. Johannes kan be PJM om tillstånd
  (General Counsel enligt PJM:s juridiska sida) om nivåerna ska visas på den publika sidan.

## PJM kapacitetsauktion (RPM Base Residual Auction)

- **Filer** (alla länkade från `www.pjm.com/markets-and-operations/rpm`):
  - `rpm-auctions-resource-clearing-price-summary.xlsx`: clearingpriser (USD per MW-dag) för alla RPM-auktioner
    sedan leveransår 2007/08, per LDA. Bara BRA-raderna används. Där flera produkter clearades tas den produkt som
    PJM själv använder i sin historiktabell för RTO: Annual (2014/15–2017/18), Capacity Performance (2018/19–2019/20)
    och den enda produkten annars. `**` betyder att LDA:n inte modellerades och ger ingen rad.
  - `<DY>-bra-results.xlsx` eller `<DY>-base-residual-auction-results.xlsx`, bladet "BRA Resource Clearing Results":
    RTO "Total Annual Equivalent Resources Cleared" (MW UCAP).
- **Period** = leveransårets startår, `freq="A"` (2025 = DY 2025/26, juni 2025–maj 2026).
- **Clearad kapacitet från 2020/21:** det första året med 100 % Capacity Performance, då PJM också började räkna
  matchade säsongsbud som årsekvivalenter. Äldre år finns som .xls eller med en annan definition och tas inte med.
- **DOM** (Dominion, Virginia) är egen LDA i RPM från 2025/26. Tidigare låg zonen i FRR (2022/23–2024/25) eller
  modellerades inte separat, så serien har fyra värden.
- **Kontroll mot rapporterna:** RTO-priserna stämmer med tabell 1 i rapporterna för 2014/15 och 2019/20 och med
  tabell 2 i 2028/29-rapporten (till exempel 2025/26 USD 269,92, 2026/27 329,17, 2027/28 333,44, 2028/29 325,00).
  Clearad MW stämmer med samma tabeller (135 684,0, 134 205,3, 134 478,1 och 138 317,8 MW). För 2024/25 ger filen
  147 477,4 MW, som i den ursprungliga rapporten. Senare rapporter anger 147 478,9.
- **`known_from` = dagen då BRA-resultatet publicerades** (`pjm.BRA_POSTED`). Sammanfattningsfilen skrivs om efter
  varje auktion (Last-Modified 2026-07-29), och de äldre resultatfilerna fick nya Last-Modified vid PJM:s
  CMS-flytt 2024 (2024-06-14 och 2024-12-12). Filernas datum säger alltså inget om äldre auktioner. Belägg:

  | Leveransår | Publicerat | Belägg |
  |---|---|---|
  | 2007/08–2013/14 | 2011-05-13 | eget datum hittades inte. Värdena står i tabell 1 i 2014/15-rapporten. Konservativt, alltså senare än verkligheten |
  | 2014/15 | 2011-05-13 | rapporten: "the results were posted on May 13, 2011" |
  | 2015/16–2018/19 | 2016-05-24 | eget datum hittades inte (rapporterna finns inte längre på pjm.com). Tabell 1 i 2019/20-rapporten. Konservativt |
  | 2019/20 | 2016-05-24 | "posted on May 24, 2016" |
  | 2020/21 | 2017-05-23 | "posted on May 23, 2017" |
  | 2021/22 | 2018-05-23 | "posted on May 23, 2018" |
  | 2022/23 | 2021-06-02 | "posted on June 2, 2021" |
  | 2023/24 | 2022-06-21 | "posted on June 21, 2022" |
  | 2024/25 | 2023-02-27 | PJM:s pressmeddelande `20230227-pjm-capacity-auction-procures-adequate-resources` och S&P Global samma dag. Rapporten på pjm.com är en odaterad revision från 2024. Pressmeddelandet gick inte att hämta i sessionen, och datumet bygger på filnamnet och S&P |
  | 2025/26 | 2024-07-30 | rapportens försättsblad "July 30, 2024" |
  | 2026/27 | 2025-07-22 | "July 22, 2025" |
  | 2027/28 | 2025-12-17 | "December 17, 2025" |
  | 2028/29 | 2026-07-14 | "July 14, 2026" |

  Resultaten läggs ut tidigast kl. 16 EPT (PJM:s auktionsschema). Med `as_of`-konventionen (dagens slut) räknas
  de som kända samma dag. **Nya auktioner** (till exempel 2029/30, resultat enligt schemat 2026-12-22) som saknas i
  tabellen får resultatfilens Last-Modified + 1 dag. Läggs datumet till i `BRA_POSTED` blir det exakt.
- **Revideringar:** BRA-priser revideras normalt inte. Ett undantag är DPL-South 2024/25 (USD 90,64 → 426,17 efter
  FERC-beslut 2024). Den LDA:n ingår inte. Ändrar PJM ett värde i filen blir det en revidering med hämtdatum.
- `lag_days = -1400` (resultat 10–43 månader före periodens slut). Aktualitet: `max_age_days = 30`. Den nyaste
  perioden ligger i framtiden, så serien blir gammal först om ingen ny auktion kommer före slutet av det senaste
  leveransets startår.

## PJM lastprognos (Load Forecast Report, januari varje år)

- **Filer:** `<år>-load-report-data.xlsx` (2017–2018: `<år>-load-forecast-report-data.xlsx`) länkas från
  `www.pjm.com/library/reports-notices`. Månadsvis 50/50-topp (MW) och nettoenergi (GWh) per zon i 15 år (från
  2026: 20 år). Prognosen inkluderar PJM:s lastjusteringar (datacenter med mera). `<år>-load-report-tables.xlsx`
  (från 2025) länkas från `.../load-forecast-dev-process`. Tabell B-9 "Adjustments Above Embedded to Summer Peak Load"
  är justeringarna för stora laster, till största delen datacenter.
- **Definitioner (kontrollerat för 2026):** sommartopp = max över juni–augusti, vilket ger exakt tabell B-1.
  Årsenergi = summan av årets tolv månader, vilket ger exakt tabell E-1. Ett år utan tolv månader i filen tas inte med.
- **Seriedesign:** en serie per (storhet, område, horisont h). **Period = rapportens årgång V, och värdet =
  prognosen för år V + h.** h = 1 (nästa år, relevant för auktionerna), 5 och 10. Varje ny rapport blir en ny
  period, så serien visar hur synen h år framåt har flyttats mellan rapporterna, och `as_of` ger bara rapporter som
  fanns på dagen. Alternativet med en serie per målår gav många korta serier med en punkt per rapport.
  Alternativet med period = målår gjorde att olika horisonter blandades i samma serie. Därför valdes årgång som period.
- **Områden:** PJM RTO och DOM (Dominion, Virginia). Justeringarna (B-9) finns maskinläsbart bara för 2025 och 2026.
  Äldre rapporter (stora lastjusteringar från omkring 2022) har dem bara i PDF och tas inte med.
- **Kontroll:** DOM-energi 10 år fram går från 104 167 GWh (2017) till 297 069 GWh (2026). B-9 för RTO 2031 i
  2026-rapporten är 41 477 MW. Båda stämmer med rapporttabellerna.
- **`known_from` = rapportens publiceringsdag** (`pjm.LF_POSTED`):
  - 2025: "Posted Date: January 24, 2025". 2026: "Posted Date: January 14, 2026".
  - 2024: "Revised 2/1/2024" på försättsbladet. Datafilen på nätet sparades 2024-01-31 och är alltså den reviderade
    versionen. Den ursprungliga januariversionen finns inte kvar, så `known_from` = 2024-02-01.
  - 2017–2023: bara "January YYYY" på försättsbladet, och filerna fick nya Last-Modified 2024-12-04 (CMS-flytt).
    Därför används den sista januari, alltså ett senare datum än det verkliga. Datafilernas interna sparningsdatum
    ligger alla före den 31 januari.
  - Ny årgång som saknas i tabellen: Last-Modified + 1 dag. Tabellfilerna (B-9): Last-Modified + 1 dag, och aldrig
    före rapporten. 2026 års tabellfil rättades 2026-02-06 ("table updated 2/6/2026") och bara den versionen finns,
    så justeringarna för 2026 är kända från 2026-02-07.
- `lag_days = -366` (rapporten kommer i januari i sitt årgångsår). Aktualitet: `max_age_days = 60` från årgångens
  slut, alltså senast i början av mars.
- **Tekniskt:** datafilerna för 2024 och 2025 har ett ogiltigt datum i `docProps/core.xml` (`2024- 1-31T19:36: 1Z`),
  som openpyxl inte kan läsa. `pjm.clean_xlsx` tar bort datumen i minnet, och bladen lämnas orörda.

## EIA-930 (Hourly Electric Grid Monitor)

- **Licens:** public domain ("U.S. government publications are in the public domain ... You may use and/or
  distribute any of our data ...", `www.eia.gov/about/copyrights_reuse.php`). `publish=True`.
- **Filer:** sexmånadersfilerna på `www.eia.gov/electricity/gridmonitor/sixMonthFiles/`.
  `EIA930_BALANCE_<år>_<Jan_Jun|Jul_Dec>.csv` (från 2015 jul–dec, 30–42 MB per fil) och
  `EIA930_SUBREGION_<år>_<halvår>.csv` (från 2018 jul–dec, cirka 25 MB). `api.eia.gov` behövs inte, så ingen
  nyckel registrerades. `EBA.zip` (706 MB) används inte.
- **Storlek:** filerna sparas inte hela. Varje fil hämtas en gång, och bara raderna för de sex områdena sparas som
  gzip-CSV i `data/raw/eia930/hourly/` (3 MB för hela historiken), med filens metadata. Filerna för innevarande och
  föregående halvår hämtas om vid varje körning (`REFRESH_DAYS = 200`), eftersom BA:erna reviderar de senaste
  timmarna. Det är cirka 130 MB per körning. Första hämtningen var cirka 1,3 GB.
- **Områden:** PJM (BA), PJM:s delregion DOM (Dominion, ur SUBREGION), ERCOT (`ERCO`), Southern Company (`SOCO`,
  med Georgia Power), Arizona Public Service (`AZPS`) och Salt River Project (`SRP`, Phoenix).
- **Mått:** månadens medellast (MW, medel av timvärden) och högsta timlast (MW). Månaden är lokal kalendermånad
  ("Data Date"). BALANCE använder "Demand (MW) (Adjusted)", EIA:s rensade serie. SUBREGION har bara "Demand (MW)".
- **Rensning (`drop_glitches`):** timmar med last ≤ 0 och timmar som avviker mer än 25 % från medianen av de fem
  timmar som är centrerade kring dem tas bort. Det behövs eftersom filerna har enstaka felvärden som annars blir
  månadens topp: PJM 224 345 MW 2020-07-13 kl. 19 (PJM:s rekord är cirka 165 GW), DOM 1,5·10⁹ MW 2021-10-18,
  nollor för SOCO och AZPS, och spikar vid midnatt för SRP 2015. Regeln tar bort 0–56 timmar per område under
  hela perioden. Riktiga lasttoppar (värmeböljor i Arizona) är jämna över flera timmar och berörs inte.
- **Fullständighet:** en månad används bara om minst 95 % av timmarna har värde efter rensningen och månaden
  slutade minst två dagar före hämtningen. Serien börjar vid den sammanhängande följd som slutar med den senaste
  månaden. Därför börjar SRP 2018-08, SOCO 2018-11 och DOM 2018-10: EIA:s justerade serie har luckor före
  juli 2018 för de områdena, och DOM-filerna börjar 2018-07.
- **Kontroll:** ERCOT:s högsta timme i augusti 2023 blir 85 432 MW. ERCOT:s officiella rekord 2023-08-10 är 85 508 MW,
  och EIA-930 och ERCOT definierar last något olika.
- **`known_from` och revideringar:** EIA skriver om alla filer dagligen (Last-Modified = hämtdagen), så det finns
  inga daterade versioner. Historiken är **backfill**: månadsslut + 7 dagar (`lag_days = 7`), med dagens värden.
  Timdata kommer normalt dagen efter. Sju dagar är ett antaget, konservativt mått på när en månad är komplett, och
  det är inte verifierat mot EIA:s dokumentation. **Läckagerisk:** BA:ernas revideringar och EIA:s omräkning av den
  justerade serien läcker in i backfillen. Från första hämtningen (2026-11-23) får nya månader och ändrade värden
  hämtdatum (`fetch`/`revision`), alltså riktiga versioner framåt.
- **Datering av backfillen efter R3 (rättning X2, 2026-11-23):** belagt på eia.gov med den ärliga klienten.
  - **Första publicering, BA-data:** 2016-07-25 (pressmeddelande press437 och Today in Energy 27212, *"Hourly
    information on U.S. electricity supply, demand, and flows is now available"*, verktyget U.S. Electric System
    Operating Data). Data finns bakåt till 2015-07-01, men månaderna 2015-07 – 2016-06 var inte offentliga förrän
    då och får `known_from` = 2016-07-25.
  - **Första publicering, delregioner:** 2019-08-21 (Today in Energy 40993, betaversionen av Hourly Electric Grid
    Monitor *"incorporates two new data elements: hourly electricity generation by energy source and hourly
    subregional demand"*). EIA började samla in delregionsdata 2018-07-01, men de publicerades först då. DOM-raderna
    2018-10 – 2019-07 får `known_from` = 2019-08-21.
  - **Fördröjning för DOM: 31 dagar** (`lag_days = 31`). Om-sidan (`930-content/about.html`) säger *"Demand by
    subregion, where available, is available on a lag of 1–30 days"*, och blanketten ger en månad. Det är den
    konservativa tolkningen. Följd: oktober 2026 för DOM har `known_from` 2026-12-01, alltså efter hämtningen
    2026-11-23, och syns inte i `as_of` förrän då. BA-serierna behåller 7 dagar (EIA: total last ungefär en timme
    efter timmen, och hämtningen visar BALANCE till dagen före).
  - **Inte belagt: när kolumnen "Demand (MW) (Adjusted)" infördes.** Varken om-sidan, Today in Energy 27212, 40993
    och 43295 eller pressmeddelandet nämner när EIA:s justerade efterfrågan började publiceras i sexmånadersfilerna,
    och webbarkiv (web.archive.org) och PUDL:s dokumentation (docs.catalyst.coop) nås inte från sessionen. Serierna
    `eia930_{avg,peak}_{pjm,erco,soco,azps,srp}_m` är därför **flaggade**: backfillen kan vara daterad före den första
    publiceringen av just den justerade serien (samma riskklass som C30 i R1). Värdena är EIA:s nuvarande justerade
    serie, så detta är en del av det kända revideringsläckaget i backfillen. Använd inte backfillen av BA-serierna i en
    backtest utan att först belägga datumet eller byta till den ojusterade kolumnen "Demand (MW)".

## ERCOT: kö för stora laster (PARTIAL, ingen serie)

- **Villkor (lästa 2026-11-23, `www.ercot.com/help/terms`, senast uppdaterade 2023-07-20), punkt 5:** *"The publicly
  available contents of this website may be used, reproduced, and redistributed, provided that the contents are not
  modified and that you maintain all copyright and other notices contained in the contents, including this
  Agreement. Notwithstanding the foregoing, raw data provided in public portions of this website may be used,
  reproduced, and redistributed in compilations, charts, and analyses without maintaining such notices."* Siffror ur
  ERCOT:s rapporter får alltså publiceras med källhänvisning.
- **Vad som finns:** kön (MW per status och driftsättningsår) publiceras i presentationer, inte som data:
  - "LLI Queue Status Update" (2023–2024, ungefär månadsvis, `www.ercot.com/files/docs/<åååå>/<mm>/<dd>/...pdf`)
    till TAC och Large Load Working Group. Där finns köns storlek **bara som diagram (bild)**. I texten finns bara
    förändringen ("increased total queue capacity by 4,439 MW") och "Approved to Energize" (till exempel "Of the
    total 5,496 MW Approved to Energize", 2024-09-06).
  - Från 2025 ingår uppdateringen i TAC- och styrelsepaket (zip) och i "ERCOT Monthly" (PDF). Där nämns totalen
    ibland i text, med olika formuleringar och avgränsningar: "approximately 205 GW" (oktober 2025), "more than
    225 gigawatts" (december 2025) och "445.8 gigawatts (GW) by 2033" (april 2026). I ERCOT Monthly för juli 2025,
    november 2025, januari, februari, maj och juni 2026 finns ingen sådan mening.
  - Sidan Large Load Integration (`/services/rq/large-load-integration`) har bara formulär och Batch Zero-dokument.
- **Varför ingen serie nu:** en serie kräver extraktion ur cirka 30–40 presentationer i mötespaket, där totalen
  ofta bara finns i diagram. Det är en extraktion som ska granskas (som B4), inte en deterministisk tolkare.
  Siffrorna i text har dessutom olika definitioner (med eller utan driftsatt last, olika horisont), vilket ger
  definitionsbrott. Spåret prioriterade PJM och EIA-930 enligt briefen.
- **Vad som löser det:** ett eget extraktionsspår med granskning som går igenom TAC- och LLWG-paketen 2023–2026,
  läser diagrammens värden (MW per status och år) och sparar dokument, sida och SHA-256 av meningen eller etiketten.
  `known_from` = mötets publiceringsdatum (sökvägen `files/docs/<åååå>/<mm>/<dd>`). Ett alternativ med enhetlig
  definition är ERCOT:s Capacity, Demand and Reserves-rapporter (xlsx, två gånger per år) och den långsiktiga
  lastprognosen, som anger TSP-bekräftade stora laster. De är inte undersökta här.

## Värdar

Alla värdar i briefen svarade: `www.pjm.com`, `www.ercot.com`, `www.eia.gov` och `eia.gov`. `dataminer2.pjm.com`
behövdes inte. `pjm.com` (utan www) nekas av proxyn, och PJM:s egna länkar till villkorssidan går dit. `api.eia.gov`
användes inte. Inga nycklar behövs.
