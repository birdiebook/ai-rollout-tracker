# R25 – granskning av ägarbesluten 2026-11-25 (spärrregeln, R11-4, BB01RY)

Granskningsspår R25, 2026-11-25, gren `auto14k/r25-agarbeslut` från `auto14k/agarbeslut` (29e8a4c). Granskat:
spåret som genomförde de tre ägarbesluten, i fyra commits (`ed1eceb`, `180abb2`, `ad7b48f`, `29e8a4c`). Koden är
`sources/guidance_capex.py` (`published_companies`), `series/guidance_revisions.py` (`CSV_READS`, `_spec`),
`state/expectations.py` (`withhold` per bolag), `sources/bea_nipa.py` (delvis omhämtning av cachen) och
`series/bea_nipa.py` (`us_gdp_contrib_final_sales_computers`). Dokumenten är registerposten, beslutsloggen,
`kallor/guidance.md`, `kallor/makro_bea_bls.md`, `resultat/f1_revideringar.md`, `datakallor/licensniva.md` och
`steg3/datakontrakt.md`.

Underlag: den delade bastabellen plus spårets 493 rader för BB01RY (kopierade till granskningens egen `data/`),
den committade `curated/guidance_capex.csv`, tre arkiverade arbetsböcker för avsnitt 1 från BEA (andra releaser än
spårets fyra), hämtade till egna kataloger och lästa med openpyxl utan projektets kod, och BEA:s `SeriesRegister.txt`.
Allt som byggdes skrevs till en tillfällig katalog, aldrig till `snapshots/`, `web-data/` eller `site/`. Ingen
analys av förlopp gjordes.

## Sammanfattning

| Punkt | Dom |
|---|---|
| 1. Inga Microsoft-siffror i publika utdata | **OK.** Ögonblicksbilden (2026-10-31 och 2026-11-30), paketet, den gamla sidan och månadsbreven 2026-10 och 2026-11 har ingen siffra ur Microsofts rader och inte skälstexten |
| 2. Aggregat som läser Microsofts rader | **OK.** Alla sex revideringsserier är inhållna och har bara id-fält i ögonblicksbilden. De två avgränsade överraskningarna är bevisade med kod och test, också på verklig data. **Anmärkning (R25-1):** överraskningsindexet listar Microsofts serier som komponenter fast det inte läser dem |
| 3. publish följer licensklassen | **OK.** `publish` är lika med klassen `ja` för alla 15 `guid_capex_*`. De två publicerade överraskningarna är `ja`. `catalog.validate()` ger 0 fel |
| 4. BB01RY | **OK.** Registerposten committades före hämtningen. Samma arkiv och datering som de andra M1-bidragen. 21 kvartal i tre andra releaser stämmer för hand |
| 5. Dokument | **Anmärkning.** Amazons byte av definition 2026 syns inte i den publicerade serien (R25-2). Registret säger på ett ställe att offentlig sektor ingår, fast samma post säger att det inte är verifierat (R25-3) |

**Slutdom: GODKÄND MED ANMÄRKNINGAR.** Inget värde som ska hållas inne når en publik utdata, och reglerna är
genomförda som de beslutades. Två brister bör rättas: R25-1 och R25-2. Båda har ett strikt xfail-test.

## 1. Inga Microsoft-siffror i publika utdata – OK

Microsofts siffror togs ur den committade CSV:n och ur F1:s beräkning på den: värdena 30 000, 40 000, 50 000,
170 000, 175 000 och 190 000 MUSD, händelsens storlek −2,90, brottets storlek −8,22 och brottets tidigare värde
190 000. De poolade måtten (revideringsindex och median, båda fönstren, också bara siffror) togs med som jämförelse.
Sökningen gick på alla numeriska löv i JSON och på text i HTML och Markdown (bland annat "175 000", "175bn",
"about 175", "−8,2" och skälstexten i `DEFINITION_BREAKS`).

| Utdata | Kommando | Resultat |
|---|---|---|
| Ögonblicksbild 2026-10-31 | `snapshot.write("2026-10-31", today="2026-10-31", out_dir=<tmp>)` | `values_withheld_companies = ["msft"]`. Brottraden `msft-r11f1` och händelsen 2026-10-28 har bara id-fält. Revideringsindexen, sammansättningen och överraskningsindexet har bara period och datum. 0 träffar på Microsofts siffror |
| Ögonblicksbild 2026-11-30 | samma, `today="2026-11-30"` (med C4, 493 s) | samma innehåll i `expectations`. Inga `guid_capex_*`- eller F1-rader i grenarna eller i C4. 0 träffar |
| Paketet | `site_bundle build --out <tmp> --today 2026-11-25`, `validate`, `scan-build` på en kopia med `--src web/src` | exit 0, `validate` 0 problem, `scan-build` 0 träffar. Microsofts sex nycklar finns bara i `withheld.json`. 0 träffar på siffrorna (bara slumpträffar, som filstorlekar i `manifest.json`) |
| Gamla sidan | `site build --out <tmp> --today 2026-11-25` | exit 0, 33 filer. Microsofts nycklar bara i tabellen över inhållna serier i `metod.html` och `metod.json`. 0 träffar |
| Månadsbrev 2026-10 och 2026-11 | `letter --month … --snapshots-dir <tmp> --out-dir <tmp>` | 0 träffar. Breven namnger inga av Microsofts serier. Antalet nya guidancevärden räknar Microsofts med (14 värden, 3 inte namngivna), som förut |

Ett nytt test kör samma kontroll på den committade CSV:n: avsnittet räknas med de riktiga reglerna, och efter
`withhold` med katalogens flaggor finns ingen av Microsofts siffror kvar. 175 000 söks inte där, eftersom Alphabets
lägsta värde för 2026 också är 175 000 (`googl-12`).

**Observation:** Microsofts siffror står i den committade CSV:n och i dokumenten (till exempel −8,2 i beslutsloggen).
CLAUDE.md tillåter extraherade siffror med källa i repot. Grinden gäller den publika sidan och ögonblicksbilden och
följer licensklassen `okänd`. Den håller inte siffrorna hemliga. Spåret skriver samma sak.

## 2. Aggregat och avgränsade komponenter – OK, med en anmärkning

- **Revideringsserierna** (`f1_rev_index_*`, `f1_rev_n_*`, `f1_rev_median_*`) listar alla bolags `guid_capex_*` och
  har `publish=False`. `capex_statements` läser alla rader. I ögonblicksbilden har de bara period och datum.
- **Avgränsningen till bolagets egna rader** gäller bara `f1_surprise_meta_capex` och `f1_surprise_googl_capex`. I
  koden väljer `capex_surprises` bolagets rader, `standardize` delar med bolagets egna tidigare överraskningar, och
  `_series` behåller bolagets rader. Spårets test ändrar de andra bolagens rader och kräver samma serie. Granskningen
  räknade också om på verklig data: med bara bolagets rader blir båda serierna identiska med hela CSV:n, och lika med
  raderna i bastabellen.
- **Ögonblicksbildens grind** (`company_public`) kräver att bolagets alla `guid_capex_*` och dess egna
  överraskningar får visas. Ett bolag som inte finns i `COMPANIES` hålls alltid inne, och `load` stoppar ett okänt
  bolag. De poolade måtten har bara id-fält så länge någon serie som läser CSV:n är inhållen.
- **R25-1 (bör).** `f1_surprise_index` och `f1_surprise_index_n` läser bara Metas och Alphabets rader (och TSMC:s och
  Nvidias SEC-serier). Det står i `licenses.CURATED_READS`, och omräkningen visar det: på verklig data är båda
  serierna identiska med bara Metas och Alphabets rader, och i ett syntetiskt test ändras de inte när Microsofts och
  Amazons rader ändras. Ändå listar katalogen Microsofts och Amazons `guid_capex_*` som komponenter. Följderna:
  - `withheld.json` och metodsidan säger offentligt att indexet är "härledd ur serier som inte publiceras:
    guid_capex_msft_…". Det stämmer inte.
  - Klassen blir `okänd` via Microsofts komponenter, fast alla rader som läses kommer från sec.gov.
  - `guidance_revisions.CSV_READS` och `licenses.CURATED_READS` säger olika saker om samma serie.

  Att indexet hålls inne är försiktigt och läcker inget. Men skälet ska vara det verkliga. Indexet går dessutom att
  räkna fram ur serier som redan är publika (z per bolag ur `f1_surprise_*`).

## 3. publish och licensklass – OK

| Serier | publish | Klass |
|---|---|---|
| `guid_capex_googl_*`, `guid_capex_meta_*`, `guid_capex_amzn_*` (9) | True | `ja` (alla bolagets rader på sec.gov) |
| `guid_capex_msft_*` (6) | False | `okänd` (www.microsoft.com) |
| `f1_surprise_meta_capex`, `f1_surprise_googl_capex` | True | `ja` |
| `f1_rev_*` (6), `f1_surprise_index`, `f1_surprise_index_n` | False | `okänd` |
| `us_gdp_contrib_final_sales_computers` | True | `ja` (public domain) |

`published_companies` och licensregeln läser samma kolumn på samma sätt (trimmad och gemen värd). En rad utan
källadress ger inte sec.gov i någon av dem. `SEC_HOSTS` finns i två moduler, och ett test kräver att de är lika.
Skälet till kopian (en importcykel) stämmer.

## 4. BB01RY – OK

**Ordning (git och filtider, UTC):** registerposten `ed1eceb` 09:13:37. Cachens 107 extrakt skrevs om från 09:16:02.
Spårets `observations.parquet` och hämtloggen skrevs 09:18. Koden committades 09:21:26 (`180abb2`). Enligt posten hade
bara R12 läst BB01RY före posten, i tre releaser. Begränsning: git och filtiderna visar bara att inget skrevs
före posten, inte att inget räknades lokalt. Inget i spårets filer tyder på det.

**Samma regler som de andra M1-bidragen:** serien ligger i samma lista (`ARCHIVE_SERIES`) och hämtas med samma kod.
Alla 95 olika `known_from` är releasedatum för syskonserierna. För varje period är första `known_from` densamma som
för `us_gdp_contrib_computers`. Ingen rad är känd före kvartalets slut. Perioderna är 1978Q2–2026Q3, som i senaste
vintage (194 kvartal). BB01RY finns i alla 107 extrakt.

**Handkontroll** mot tabell 1.2.2 (bladet `T10202-Q`), tre releaser som spåret inte läste. Raden är 17, koden
`BB01RY` och etiketten "Final sales of computers\3\" i alla tre. Fotnot 3: "Some components of final sales of
computers include computer parts".

| Release ("Data published") | Kvartal och värde i arbetsboken | Vyn på publiceringsdagen |
|---|---|---|
| 2019-07-26 (katalog 2019-07-30, årlig revidering) | 2014Q1 0,01; 2016Q4 −0,02; 2018Q2 0,05; 2018Q3 −0,08; 2018Q4 0,16; 2019Q1 0,19; 2019Q2 0,09 | 7 av 7 lika. 2019Q2 finns inte dagen före |
| 2021-11-24 (2021Q3 Second) | 2008Q4 0,07; 2020Q2 −0,08; 2020Q3 0,27; 2020Q4 −0,02; 2021Q1 0,24; 2021Q2 −0,05; 2021Q3 −0,13 | 7 av 7 lika |
| 2025-07-30 (katalog 2025-07-31, årlig revidering) | 1978Q2 0,44; 2024Q1 −0,05; 2024Q2 −0,13; 2024Q3 −0,04; 2024Q4 0,14; 2025Q1 −0,33; 2025Q2 0,20 | 7 av 7 lika. 2025Q2 finns inte dagen före |

**Vad serien omfattar.** I `SeriesRegister.txt` har `BB01RC` fyra delar: `B935RC` (privata investeringar), `DCPPRC`
(hushåll), `B850RC` (export) och `B852RC` (import). Ingen offentlig serie för datorer finns i registret. Spårets
seriebeskrivning (privata investeringar, hushåll, export minus import) stämmer. **R25-3 (not):** registerpostens
avsnitt "Hur den läses" säger att BB01RY "tar med hushållens och den offentliga sektorns köp". Samma post säger att
resten troligen är offentliga investeringar och att det inte är verifierat. Det första ska också stå som troligt.

**Cachen (not, R25-4).** Extrakten i den delade rå-cachen skrivs nu om när en kod läggs till. Skrivningen är atomär
(`os.replace`), och äldre kod läser en överuppsättning, eftersom den bara kräver sina egna koder. Ett ändrat värde
eller datum stoppar hämtningen (testat). Men `docs/drift.md` räknar inte upp extrakten bland de föränderliga filerna
under `RAW_DIR`.

## 5. Dokument – anmärkning

- **R25-2 (bör).** Amazons publicerade serier `guid_capex_amzn_cy_lo/hi` har två versioner för 2026: 200 000
  (`AMZN_CAPEX_UNSPEC`, 2026-02-05) och 220 000 (`AMZN_CASH_CAPEX`, 2026-10-29). Registret (F1) säger uttryckligen att
  220 mdr som `AMZN_CASH_CAPEX` efter 200 mdr som `AMZN_CAPEX_UNSPEC` *inte* är en revidering. Den publika
  presentationen säger motsatsen:
  - Paketets seriesida räknar perioden som reviderad (`n_revised_periods: 1`) och har ingen not om definitionen.
  - Månadsbrevet 2026-10 skriver "2026: 220 000 MUSD (tidigare 200 000)".

  Innan beslutet syntes det inte, eftersom serien var inhållen. Andra perioder byter inte definition med ett nytt
  värde. Alphabets riktningar 2025 blandar `GOOGL_CAPEX` och `GOOGL_TECH_INFRA`, men alla är +1.
- **R25-5 (not).** Beslutsloggen och `kallor/guidance.md` hänvisar till R5 som granskning av extraktionen för
  Amazon, Alphabet och Meta. R5 granskade andra filer. Mot E1 kontrollerade R5 bara fullständigheten för planer för
  nästa år, och Microsofts rad (R5-F14). Stickprovet för Amazon (5 av 5) är R2. Det ändrar inte beslutet.
- Övrigt stämmer med koden och körningarna: torrkörningens siffror (Meta 2025: guidance 71 000, utfall 72 215,
  s +1,70, z 1,90; Alphabet 92 000 och −0,60; revideringarna 2026), att Microsofts brottrad saknar storlek och
  skälstext, och att `licensniva.md`:s tabeller är från före beslutet.
- **Granskningstestet i R11 (not, R25-6).** `test_series_from_the_curated_csv_respect_its_publish_gate` ändrades från
  allt-eller-inget till per bolag. Det är godtagbart. R11-4 ställde själv villkoret "tills ägaren beslutar", och
  testet läser nu vilka rader en serie läser ur licensdeklarationen (`CURATED_READS`), inte ur F1-koden. Det är alltså
  fortfarande oberoende av koden det kontrollerar.

## Rättningar (för ett rättningsspår)

| # | Var | Rättning |
|---|---|---|
| R25-1 | `series/guidance_revisions.py` (`CSV_READS`) | Låt överraskningsindexets komponenter vara de rader det läser, Metas och Alphabets, som i `licenses.CURATED_READS`. Ägaren avgör om indexet då publiceras. Med `("meta", "googl")` i `CSV_READS` följer `publish` och klassen (`ja`). Ska det vänta, sätt `publish=False` uttryckligen med skälet "väntar på ägarbeslut". Det strikta xfail-testet slår om när komponenterna är rätt |
| R25-2 | `sources/guidance_capex.py` (`specs`), eventuellt `letter.py` | Markera definitionsbytet i Amazons serier: en not med "definitionsbyte 2026: AMZN_CAPEX_UNSPEC → AMZN_CASH_CAPEX (2026-10-29)". Bättre: dela serien per definition, så att en version aldrig byter definition. Brevet ska då inte skriva "tidigare" mellan två definitioner. Det strikta xfail-testet slår om när noten finns eller serien är delad |
| R25-3 | `docs/mattregister.md` (ny daterad post) | "tar med hushållens och den offentliga sektorns köp" → "tar med hushållens köp, exporten och troligen offentliga investeringar (inte verifierat)" |
| R25-4 | `docs/drift.md`, Delad data | Lägg BEA-extrakten (`bea/vintages/`) till listan över föränderliga filer under `RAW_DIR`: de skrivs om atomärt som överuppsättning när en kod läggs till |
| R25-5 | `docs/beslutslogg.md`, `docs/kallor/guidance.md` | Hänvisa till R2 för stickproven. R5 bara för fullständigheten |

## Tester

`tests/test_r25_agarbeslut.py` (syntetiska tabeller och den committade CSV:n, inget nät):
- ingen av Microsofts siffror i den committade CSV:n finns kvar i avsnittet efter `withhold` (passerar)
- överraskningsindexet och dess antal ändras inte när Microsofts och Amazons rader ändras, men indexet ändras
  med Metas (passerar, 2 fall)
- Amazons serie byter definition 2026 (passerar, faktum bakom R25-2)
- en publicerad `guid_capex_*`-serie som byter definition inom en period säger det i noten (strikt xfail, R25-2)
- överraskningsindexet listar bara de bolag vars rader det läser (strikt xfail, R25-1, 2 fall)

`python -m pytest -q tests/test_r25_agarbeslut.py`: 4 passerade, 3 xfail. Hela sviten (en körning, med spårets
493 BB01RY-rader i vyn): 2 185 passerade, 1 fallerade, 1 överhoppad, 5 xfail. Det som fallerar är det kända
`test_committed_fixtures_are_the_current_synthetic_bundle`, och bara registrets SHA-256 skiljer. Fixturerna är
inte omgenererade. 2 185 + 1 = basen 2 168 + spårets 14 + granskningens 4.
