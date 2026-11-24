# R12 – granskning av datering och läckage i makroserierna (M1: BEA-vintages, BLS KPI och PPI)

Granskningsspår R12, 2026-11-24, gren `auto14/r12-makro` (från `auto13/m1-makro`). Granskat: registerposten
"M1: AI-relaterat bidrag till BNP-tillväxt och priser" och den daterade rättelsen (`docs/mattregister.md`),
`docs/kallor/makro_bea_bls.md`, `src/ai_tracker/sources/bea_nipa.py`, `series/bea_nipa.py`, `sources/bls.py`,
`series/bls.py`, `CONTACT_HOSTS` i `http.py`, `KNOWN_GAPS` i `warehouse.py`, `tests/test_makro_bea_bls.py` och
`git log -p main..auto13/m1-makro`. Spårets data lästes i `/home/user/wt/m1-makro/data`.

Underlag, hämtat på nytt 2026-11-24:
- **BEA:** arkivets kataloglista (`histdata`), arbetsböckerna för avsnitt 1 och 4 i 12 releaser, BEA:s nyhetsarkiv
  för BNP (alla releaser sedan 2014), releasetexterna för 2018Q3 förhand, 2023Q1 tredje och 2025Q3 initial,
  BNP-sidan och `SeriesRegister.txt`.
- **BLS:** arkiven över nyhetsreleaser för KPI och PPI, KPI-releaserna 2025-10-24, 2025-12-18, 2026-01-13,
  2026-02-13 och 2026-11-10, PPI-releaserna 2002-01-11, 2002-02-15 och 2026-11-13, PPI Detailed Report (xlsx,
  tabell 11) för september och november 2025 och januari, juni, juli och oktober 2026, flatfilerna och
  `cu.footnote`, `pc.footnote`, `cu.series` och `pc.series`. Allt från `download.bls.gov` och `www.bls.gov` med
  projektets generiska klientidentitet.
- **ALFRED/FRED:** vintages av `CUSR0000SEHF01` och `CUUR0000SEHF01`, och dagens FRED-kopior av alla fyra BLS-serier.

Blockerat: `data.bls.gov` (proxyn nekar) och `api.bls.gov` (dagskvoten för den delade IP-adressen är slut). Inget av
det behövdes.

**Ingen analys av förlopp gjordes.** Enskilda värden lästes bara för att kontrollera datum, belopp och påståenden.

## Sammanfattning

| Punkt | Dom |
|---|---|
| 1. BEA: known_from = "Data published" | **OK.** 12 releaser omlästa, alla 107 mot BEA:s nyhetsarkiv. Inget datum ligger före publiceringen |
| 2. `ai_invest_contrib_gross` och datering före 2017-10-27 | **OK för summan.** **Fel i `us_imp_computers_real`**: perioder som en omräknad release tar bort ligger kvar, så serien blandar basår (R-2) |
| 3. BLS-dateringsregler | **OK för KPI och PPI-reglerna**, bekräftade mot BLS texter, ALFRED och sex Detailed Reports. **Läckage i PPI 518210**: 2000-12 – 2001-08 dateras före indexets införande 2002-02-15 (R-1). Arkivet börjar 1994-01, inte 1999-05 (R-5) |
| 4. Serie-id och värden | **OK.** PPI 518210 är nu verifierad mot BLS Detailed Report: 10 av 10 värden lika. Alla fyra serier lika med FRED för alla månader |
| 5. Klientidentitet till `*.bls.gov` | **OK**, förenligt med CLAUDE.md och BLS regler. Suffixmatchningen är för bred (anmärkning) |
| 6. `KNOWN_GAPS` för hela KPI-serien | **Anmärkning.** En andra lucka döljs. Undantaget ska gälla perioden 2025-10 (R-4) |
| 7. "BEA publicerar inget BNP-bidrag för datorimport" | **Missvisande.** Påståendet stämmer bokstavligt, men BEA publicerar ett nettobidrag för datorer: "Final sales of computers" (`BB01RY`, tabell 1.2.2 rad 17), där importen ingår med minustecken (R-3) |

**Slutdom: GODKÄND MED ANMÄRKNINGAR.** BEA-dateringen, summan ur samma vintage och BLS revideringsregler håller mot
primärkällorna. Två fel ska rättas innan serierna används i någon analys eller visas på sidan: läckaget i PPI 518210
(R-1) och de blandade basåren i `us_imp_computers_real` (R-2). Båda är lokala och kräver en ombyggnad av serien.
R-3 ändrar premissen för beslutet om ingen nettovariant. Det är ett ägarbeslut.

## 1. BEA: known_from = "Data published" – OK

Raden "Data published" i tabellhuvudet lästes om ur arbetsböckerna, för båda avsnitten och alla blad som spåret
läser. Den jämfördes med BEA:s eget datum för releasen.

| Release | Katalog | "Data published" | BEA (nyhetsarkiv eller releasetext) | known_from (spåret) |
|---|---|---|---|---|
| 2017Q3 förhand | 2017-10-27 | 2017-10-27 | 2017-10-27 | 2017-10-27 |
| 2018Q3 förhand | 2018-10-29 | 2018-10-26 | listan: 2018-10-25. Releasetexten: "Friday, October 26, 2018" | 2018-10-26 |
| 2018Q4 initial | 2019-03-01 | 2019-02-28 | 2019-02-28 | 2019-02-28 |
| 2019Q1 förhand | 2019-04-29 | 2019-04-26 | 2019-04-26 | 2019-04-26 |
| 2021Q2 tredje | 2021-10-01 | 2021-09-30 | 2021-09-30 | 2021-09-30 |
| **2023Q1 tredje** | **2023-06-20** | **2023-06-29** | 2023-06-29. Releasetexten: "Thursday, June 29, 2023" | 2023-06-29 |
| 2023Q2 tredje och omfattande revision | 2023-09-29 | 2023-09-28 | 2023-09-28 | 2023-09-28 |
| 2024Q4 förhand | 2025-01-31 | 2025-01-30 | 2025-01-30 | 2025-01-30 |
| **2025Q3 initial** | **2025-12-22** | **2025-12-23** | 2025-12-23. Releasetexten: "Tuesday, December 23, 2025" | 2025-12-23 |
| 2025Q3 uppdaterad | 2026-01-22 | 2026-01-22 | 2026-01-22 | 2026-01-22 |
| 2025Q4 andra | 2026-03-13 | 2026-03-13 | 2026-03-13 | 2026-03-13 |
| 2026Q3 förhand | 2026-10-29 | 2026-10-29 | BNP-sidan: "Current release: October 29, 2026" | 2026-10-29 |

- **Alla 107 releaser:** 105 har samma datum som BEA:s nyhetsarkiv. 2018Q3 förhand ligger en dag efter arkivlistan,
  men releasetexten bekräftar huvudets datum. 2026Q3 förhand är den aktuella releasen och finns ännu inte i arkivlistan.
  Inget known_from ligger före BEA:s publicering, och inget ligger efter den.
- Katalogen ligger före publiceringen i två fall (2023Q1 tredje 9 dagar, 2025Q3 initial 1 dag), som spåret skrev.
  Annars ligger katalogen 0–4 dagar efter (22 releaser 0, 77 releaser 1, 4 releaser 3, 2 releaser 4), inte 1–3 dagar
  som i källdokumentet och i kommentaren i `bea_nipa.py`.
- Delade tabeller som inte uppdateras i varje release har ett äldre huvud. Exempel: 4.2.5A har "October 30, 2024" i
  releasen 2025-01-30. `parse_workbook` tar det senaste datumet bland bladen, så ett äldre blad drar inte datumet
  bakåt (nytt test).
- Mina egna inläsningar av de 12 releaserna är lika med spårets utdrag i cachen för alla koder och kvartal, cirka
  19 000 celler och 0 skillnader. Real BNP-tillväxt (`A191RL`) stämmer med releasetexterna: 3,5 (2018Q3 förhand),
  2,0 (2023Q1 tredje) och 4,3 procent (2025Q3 initial).
- Ordningen i git stämmer med förregistreringen. Registret committades 20:19, koden 20:25 och den första hämtningen
  skedde 20:25–20:31 (rå-cachens tider). Efter hämtningen ändrades sökvägen till den senaste releasen, en kontroll av
  HTML-svar, gränsen för katalogavståndet (10 till 14 dagar), lagringsstarten 1952-01 och `KNOWN_GAPS`. Sökvägen,
  lagringsstarten och luckan står i den daterade rättelsen. Ingen dateringsregel ändrades.

## 2. Summa ur samma vintage och datering före 2017-10-27 – OK, men fel i `us_imp_computers_real`

**`ai_invest_contrib_gross`:** alla 644 rader är lika med `Y034RY + B985RY` ur den vintage som raden är daterad till
(0 avvikelser). `archive_rows` adderar kolumn för kolumn, alltså release för release, och en saknad del ger ingen rad.
Ett nytt test kontrollerar egenskapen när delarna revideras i olika releaser.

**Före 2017-10-27:** inget värde i någon av de 8 BEA-serierna har known_from före 2017-10-27. Alla kvartal före
2017Q3 får 2017-10-27 som första datum. Det är konservativt, eftersom releaserna 2002–2017 finns som .xls i arkivet men
inte läses. Valet står i dokumentet.

**Fel (R-2): `us_imp_computers_real` blandar basår.** `vintage_rows` behåller ett värde som en senare release tar bort.
Det är rimligt för bidrag och löpande priser, men inte för kedjade dollar. Tabell 4.2.6 (från 2023-09-28 4.2.6B)
började 1999Q1 (2009 års dollar), 2002Q1 från 2018-07-27 (2012 års dollar) och 2007Q1 från 2023-09-28 (2017 års
dollar). Bara `B852RX` har sådana borttagna perioder. Dagens vy (`as_of`) ger därför:

| Period | Värde | Basår | known_from |
|---|---|---|---|
| 2001Q4 | 41 889 | 2009 | 2017-10-27 |
| 2002Q1 | 42 660 | 2012 | 2018-07-27 |
| 2006Q4 | 80 963 | 2012 | 2018-07-27 |
| 2007Q1 | 82 231 | 2017 | 2023-09-28 |

Förändringen 2006Q4–2007Q1 blir +1,6 procent i vyn, men +8,3 procent inom samma vintage (2012 års dollar). Vid
2001Q4–2002Q1 blir den +1,8 procent i stället för +11,1 procent. Seriens `note` säger att nivåer bara ska jämföras inom
en vintage, men lagringen gör det omöjligt. Serien har `publish=True`. Felet gäller varje `as_of` efter 2018-07-27.
Strikt xfail-test i `tests/test_r12_makro.py`.

## 3. BLS dateringsregler – OK, men läckage i PPI 518210

**KPI NSA.** "The CPI-U and CPI-W are considered final when released" (KPI-releasen 2026-11-10). ALFRED visar ingen
ändring av `CUUR0000SEHF01` i någon månad mellan vintage 2019-01-01 och i dag. `cu.footnote` har bara R (Revised) och X
(oktober 2025). Elserien har ingen R-rad. Releasedagarna stämmer med arkivet:

| Referensmånad | Release (arkivet) | known_from (spåret) |
|---|---|---|
| 2025-08 | 2025-09-11 | 2025-09-11 |
| 2025-09 | 2025-10-24 (försenad av nedstängningen) | 2025-10-24 |
| 2025-10 | "Not published because of 2025 lapse in federal government appropriations" | ingen rad (`-`, X) |
| 2025-11 | 2025-12-18 | 2025-12-18 |
| 2025-12 | 2026-01-13 | 2026-01-13 |
| 2026-01 | 2026-02-13 | 2026-02-13 |
| 2026-10 | 2026-11-10 | 2026-11-10 |

Även 2013-09 (2013-10-30, nedstängningen 2013) stämmer.

**KPI SA.** Releasetexten för januari 2026 säger att "revised seasonal factors and seasonally adjusted indexes for
2021 to 2025 were calculated and published". ALFRED bekräftar regeln exakt. Releasen 2018-02-14 ändrade 2013-01 –
2017-12 (60 månader) men inte 2012-12. Releasen 2026-02-13 ändrade 2021-01 – 2025-12 (59 månader, oktober saknas).
Inget värde har ändrats efter releasen 2026-02-13 (vintage 2026-02-14 och 2026-07-15 mot i dag, alla månader), och
2013-09 har samma värde 2018-02-15 som i dag. Spårets datum följer regeln: 2013-09 2018-02-14, 2019-12 2024-02-13, 2020-06 2025-02-12, 2021-06 och 2025-12 2026-02-13, 2026-01 och
senare sin egen release.

**PPI.** `pc.footnote`: "P Preliminary. All indexes are subject to monthly revisions up to four months after original
publication", och C = Correction. PPI-releasen 2026-11-13 reviderade juni–september. De sex Detailed Reports visar
samma mönster för båda serierna: månad m är preliminär i releaserna för m till m + 3 och slutlig i releasen för m + 4.
Preliminära värden ändras, till exempel 518210 för oktober 2025: 126,45 i rapporten 2026-01-14 och 124,462 i rapporten
2026-02-27. I stickproven ändras inget efter m + 4.

| Månad (518210) | Slutlig första gången | known_from (spåret) |
|---|---|---|
| 2025-05 | rapporten för september 2025, 2025-11-25 | 2025-11-25 |
| 2025-06 | preliminär 2025-11-25, inte med i rapporten för november 2025 (2026-01-14) | 2026-01-14 |
| 2025-07 | rapporten för november 2025, 2026-01-14 | 2026-01-14 |
| 2025-09 | rapporten för januari 2026, 2026-02-27 | 2026-02-27 |
| 2026-02 | rapporten för juni 2026, 2026-07-15 | 2026-07-15 |
| 2026-03 | rapporten för juli 2026, 2026-08-13 | 2026-08-13 |
| 2026-06 | rapporten för oktober 2026, 2026-11-13 | 2026-11-13 |

Oktober 2025 publicerades inte i egen release men finns som preliminär i rapporten för november 2025 (2026-01-14).
Spårets regel ("nästa release") ger rätt datum. Preliminära värden (2026-07 – 10) får filens datum 2026-11-13, som är
`Last-Modified` och releasedagen. Det är inte för konservativt: varje preliminärt värde kan ha reviderats i den
senaste releasen, och releasen 2026-11-13 reviderade juni–september.

**Fel (R-1): PPI 518210 dateras före indexets införande.** PPI-releasen 2002-02-15 listar "7374 Data processing
services*" med "* denotes newly introduced PPI", och den tekniska noten i releasen 2026-11-13 listar "Data processing
services 7374, January 2002". Releasen 2002-01-11 nämner inte indexet. Flatfilen har värden från 2000-12 (bas
12/00 = 100), och m + 4-regeln daterar dem från 2001-05-11. Nio värden, 2000-12 – 2001-08, får known_from 2001-05-11 –
2002-01-11, alltså före 2002-02-15. Det är läckage enligt definitionen. Det påverkar knappast någon analys i dag (25 år
gamla värden i en beskrivande serie), men regeln saknar en första publiceringsdag per serie. Strikt xfail-test.

**För konservativt (R-5): arkivet börjar 1994-01.** Arkivet listar KPI- och PPI-releaser från referensmånad 1994-01.
Före 1999-05 har filnamnen sex siffror (`cpi_051499.txt`), och `parse_news_archive` läser bara åtta. 64 KPI-månader
och 63 PPI-månader hoppas därför över (för PPI 62 sexsiffriga och juli 1994 utan länk). KPI för 1994-01 – 1999-04 får
1999-06-16 i stället för sin releasedag. PPI före 1998-11 får 1998-12-11 och PPI för 1998-12 – 1999-04 får
1999-06-11. Det läcker inte, men rättelsen i registret ("arkivet börjar med referensmånad 1999-05") är fel i sak.
Strikt xfail-test.

**Latent läckage (R-6).** Om `Last-Modified` saknas och filen har en månad som arkivlistan ännu inte har, blir filens
datum arkivets senaste releasedag. Den nya månaden dateras då till föregående release. Skyddet i `new_rows` (inte före
en hämtning som saknade perioden) begränsar felet till tiden sedan förra hämtningen, men inte vid första laddningen.
`download.bls.gov` skickar `Last-Modified` i dag, så felet har inte inträffat. Strikt xfail-test.

**Inte verifierat:**
- Om 518210:s historik 2000-12 – 2001-12 publicerades redan vid införandet 2002-02-15 eller senare. Bara att den inte
  kan ha publicerats tidigare.
- PPI publicerades efter SIC fram till releasen för januari 2004 (2004-03-18). Om dagens NAICS-serier har samma värden
  som SIC-serierna före det går inte att kontrollera här. `PCU22112222112242` har bas 12/90 men värden från 1958, och
  allt före 1998-11 dateras 1998-12-11.
- När BLS först publicerade den säsongsrensade elserien bakåt till 1952. Värden före 1994 dateras 1999-06-16.

## 4. Serie-id och värden – OK

| Serie | Kontroll | Resultat |
|---|---|---|
| `CUUR0000SEHF01` | `cu.series`: "Electricity in U.S. city average, all urban consumers, not seasonally adjusted", 1982-84=100. KPI-releaserna 2025-10-24, 2026-01-13, 2026-02-13, 2026-11-10 | 10 av 10 index lika (t.ex. 296,887, 295,121, 299,731, 307,673) |
| `CUSR0000SEHF01` | releasernas SA-förändringar | oktober 2026 +0,9 mot vår +0,94, januari 2026 −0,1 mot vår −0,107 |
| `PCU518210518210` | `pc.series`: "Data processing, hosting and related services", bas 200012. **Detailed Report tabell 11** (industrikod 518210), sex nummer | 10 av 10 värden lika, och de slutliga värdenas known_from = rapportens releasedag |
| `PCU22112222112242` | `pc.series`: "Electric power distribution-Commercial electric power", bas 199012. Detailed Report tabell 11 (produktkod 221122-42) | 10 av 10 värden lika |
| alla fyra | FRED, alla månader | 311, 826, 897 och 897 månader lika (största skillnad 0,0) |

Källdokumentets kontroll av PPI för kommersiell el jämförde med råvaruindexet 05-42 i releasens tabell 2. Det är en
annan serie än industriindexet 221122-42, så kontrollen bevisade inte värdet. Tabell 11 i Detailed Report är rätt
källa, och den finns som xlsx på `www.bls.gov/ppi/detailed-report/`. Enheten för `us_ppi_elec_commercial_m` saknar
basen ("index dec 1990=100").

## 5. Klientidentitet till `*.bls.gov` – OK

- BLS regler (`www.bls.gov/bls/pss.htm`, "Automated retrieval program (robot) activity"): "BLS also reserves the right
  to block robots that do not contain information that can be used to contact the owner." I praktiken svarar
  `download.bls.gov` och `www.bls.gov` 403 "Access Denied" utan kontaktuppgift och 200 med projektets identitet
  (provat).
- Det är precis fallet i CLAUDE.md: "API:er som kräver kontaktuppgift i User-Agent (SEC) får en generisk
  klientidentitet från .env." Identiteten läses ur `.env` eller Actions-secret, och inget värde finns i repot.
  `fetch-weekly.yml`, `nowcast.yml` och `snapshot.yml` sätter redan `SEC_USER_AGENT`, så veckojobbet går inte sönder.
- Anmärkningar: `host.endswith(("sec.gov", "bls.gov"))` matchar även en värd som `notbls.gov`. Använd
  `host == d or host.endswith("." + d)` (R-8). `docs/drift.md` säger att `SEC_USER_AGENT` krävs för sec.gov, men inte
  att BLS-serierna också kräver den (R-7). Namnet `SEC_USER_AGENT` stämmer inte längre. Ett byte kräver att
  Actions-secret byts samtidigt, så det kan vänta.

## 6. `KNOWN_GAPS` för hela KPI-serien – anmärkning

`run_checks` tar bort varje serie i `KNOWN_GAPS` ur `no_gaps`. För KPI-serierna betyder det att en andra lucka, till
exempel en månad som en framtida hämtning eller tolkning tappar, aldrig syns. Förslag: undantag per period,
till exempel `KNOWN_GAP_PERIODS = {"us_cpi_electricity_nsa_m": {"2025-10"}, "us_cpi_electricity_sa_m": {"2025-10"}}`.
`no_gaps` räknar då de saknade perioderna inom seriens spann och godkänner serien bara om de är en delmängd av listan.
De befintliga undantagen för hela serier (planer, KPI:er från bolag, GH Archive) kan stå kvar tills vidare. Ett
passerande test visar att oktober 2025 ensam godtas, och ett strikt xfail-test att en andra lucka ska rapporteras.

## 7. "BEA publicerar inget BNP-bidrag för datorimport" – missvisande

- Bokstavligt stämmer det. Det finns ingen kod `B852RY`. Importen finns i tabell 1.5.2 bara som varor och tjänster
  (rad 49–51, `A021RY`, `A255RY`, `A656RY`), och datorimporten bara som bidrag till importens tillväxt (`B852RZ`).
- Men tabell 1.2.2 rad 17, **"Final sales of computers" (`BB01RY`)**, är ett av BEA publicerat bidrag till real
  BNP-tillväxt för datorer *netto efter handel*. Enligt BEA:s `SeriesRegister.txt` har `BB01RC` delarna `B935RC`
  (privata investeringar i datorer), `DCPPRC` (hushållens datorer), `B850RC` (export) och `B852RC` (import).
  Kontroll i löpande priser 2026Q3: 504 127 + 114 151 + 144 932 − 751 292 = 11 918 MUSD, mot `BB01RC` 42 790. Resten,
  cirka 31 mdr, är troligen offentliga investeringar i datorer. Den delen är inte verifierad.
- Serien finns i stickproven 2017-10-27, 2023-06-29 och 2026-10-29, i samma arbetsbok (avsnitt 1) som spåret redan
  laddar ned. Den kan dateras på exakt samma sätt.
- Skillnaden är inte liten. I releasen 2026-10-29 är bidraget från privata investeringar i datorer (`B935RY`) +0,72
  procentenheter för 2026Q3, och bidraget från slutlig försäljning av datorer (`BB01RY`) −0,61. Siffrorna lästes bara
  för att visa att premissen spelar roll. Ingen takt är räknad.
- Begränsningar: `BB01RY` omfattar datorer och kringutrustning, inte programvara och inte övrig
  informationsbehandlingsutrustning. Hushållens datorer ingår. Ett nettomått för hela `ai_invest_contrib_gross` finns
  alltså fortfarande inte.

Slutsatsen "ingen nettovariant" i registret, källdokumentet och beslutsloggen vilar därför på en ofullständig premiss.
Om ett nettomått ska finnas är `BB01RY` BEA:s eget och kräver ingen approximation. Det är en ny registrering och ett
ägarbeslut (R-3).

## Rättningar (för ett rättningsspår)

| # | Allvar | Var | Rättning |
|---|---|---|---|
| R-1 | must_fix | `sources/bls.py` | Inför en första publiceringsdag per serie, med belägg: `PCU518210518210` 2002-02-15 (PPI-releasen 2002-02-15, "newly introduced PPI"). known_from = max(regeldatum, första publiceringsdag). Bygg om `us_ppi_data_processing_m` (`drop_series`), eftersom `new_rows` inte daterar om lagrade rader. Det strikta xfail-testet slår om |
| R-2 | must_fix | `sources/bea_nipa.py` `archive_rows` | Visa bara perioder som finns i den senaste vintage som har koden, och avbryt med ett tydligt fel om en ny release tar bort perioder, så att serien byggs om medvetet. Bygg om `us_imp_computers_real` (då 2007Q1–). Ett alternativ är att byta nivån mot `B852RL` (procentuell förändring), som inte beror på basåret |
| R-3 | should_fix | `docs/mattregister.md`, `docs/kallor/makro_bea_bls.md`, `docs/beslutslogg.md` | Rätta premissen i en daterad post: BEA publicerar `BB01RY` "Final sales of computers" (tabell 1.2.2 rad 17), netto efter import och export. Ägaren avgör om `BB01RY` ska förregistreras som nettobidrag för datorer, ur samma arkiv och med samma datering |
| R-4 | should_fix | `warehouse.py`, `series/bls.py` | Undantag per period i `no_gaps` (avsnitt 6). KPI-serierna listar bara 2025-10 |
| R-5 | should_fix | `sources/bls.py` `parse_news_archive`, registret, källdokumentet | Läs även sexsiffriga filnamn (`MMDDYY`, år 94–99 = 1994–1999). Rätta "arkivet börjar med referensmånad 1999-05" till 1994-01 i en daterad post. PPI-hålet 1998-12 – 1999-04 försvinner |
| R-6 | should_fix | `sources/bls.py` `release_rows` | Om filen har en månad efter arkivlistans senaste och `Last-Modified` saknas: använd hämtdagen som filens datum |
| R-7 | should_fix | `docs/kallor/makro_bea_bls.md`, `docs/drift.md`, `bea_nipa.py` | Byt kontrollraderna för PPI mot Detailed Report tabell 11 (avsnitt 4), markera 518210 som verifierad, rätta katalogavståndet till 0–4 dagar, lägg till basen i enheten för kommersiell el och skriv i `docs/drift.md` att BLS-serierna också kräver `SEC_USER_AGENT` |
| R-8 | note | `http.py` | Matcha domäner med punktgräns: `host == d or host.endswith("." + d)` |

## Tester

`tests/test_r12_makro.py` (fixturer, inget nät):
- release dateras med huvudet, inte med en katalog nio dagar tidigare, och ett äldre delblad drar inte datumet bakåt
  (passerar)
- bruttobidraget är alltid en summa ur samma vintage, och äldre perioder får första vintagens datum (passerar)
- KPI NSA-datum kring nedstängningen 2025 (passerar)
- KPI SA-fönstret stämmer med revideringarna i ALFRED (passerar)
- PPI slutliga värden dateras till release m + 4 genom nedstängningen (passerar)
- oktober 2025 ensam godtas som lucka (passerar)
- strikt xfail: R-1, R-2, R-4, R-5, R-6, R-8

`python -m pytest -q tests/test_r12_makro.py tests/test_makro_bea_bls.py`: 27 passerade, 6 xfail. Hela sviten: se
spårets slutrapport.

## Rättat i auto14/x9-makro

Rättningsspåret X9 (2026-11-24) rättade R-1, R-2 och R-4 till R-8 i kod och dokument, och R-3 i dokumenten. De sex
strikta xfail-testerna passerar nu som vanliga tester, med oförändrade påståenden. Omräknat: `us_ppi_data_processing_m`
(9 värden får 2002-02-15) och `us_imp_computers_real` (2007Q1–, 52 rader borta). Med R-5 får KPI- och PPI-värden
1994-01 – 1999-04 sin releasedag, och värden före 1994 får arkivets första releasedag (1994-02-17 och 1994-02-11).
Den delen av historiken är fortfarande inte verifierad (N-1). `BB01RY` är inte registrerad, eftersom det är ett
ägarbeslut. Se den daterade posten i `docs/mattregister.md`.
