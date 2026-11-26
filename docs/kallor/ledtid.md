# Källor: Ledtid i stacken (LT1)

Följd fråga: "Rör sig order och orderstock hos leverantörerna (kraft, kylning, elnät, nät, servrar, datacenterleasing)
före eller efter capex-takten hos hyperskalarna och de yttre lagren, och ändras ledtiden?" Storheterna, läsregeln och
gränserna står i `docs/mattregister.md`, posten "2026-11-26 – LT1", som committades ensam (6fb0ccd) innan något mått
räknades. Mallen för läsregeln är F0 (posten "2026-11-26 – F0"). Rapporten står i `docs/resultat/ledtid.md`.

    python -m ai_tracker.followed ledtid --as-of YYYY-MM-DD [--json PATH] [--out PATH]
    python -m ai_tracker.observations lt1_rpo_power lt1_rpo_net lt1_dlr_bookings4   # de härledda serierna

Ingen ny källa, ingen ny hämtning från SEC och ingen ny extraktion. Allt bygger på serier som redan finns i katalogen.

## Underlaget

**Köpare.** Capex över fyra kvartal med KL1:s formel (`series.kreditlagret.formula("capex4", ...)`), ur `capex_*`
(SEC XBRL, `docs/kallor/sec.md`, `neoclouds.md`):

| Storhet | Serie | Medlemmar | Förändring i takt från |
|---|---|---|---|
| K-inre | `kl_capex4_inner` | Microsoft, Alphabet, Amazon, Meta | 2019Q4 |
| K-yttre | `kl_capex4_outer` | Oracle, CoreWeave, Nebius, IREN | saknas ännu (serien börjar 2025Q2) |

**Leverantörer.** Läsregelns X i "före" och Y i "efter":

| Rad | Serie | Innehåll | Källa | Förändring i takt från |
|---|---|---|---|---|
| L1 | `lt1_rpo_power` (ny) | `rpo_etn` + `rpo_pwr`: Eatons orderstock av fasta order (taggad som RPO) och Quantas RPO | S2, `sec_stack_kraft.md` | 2022Q1 |
| L2 | `lt1_rpo_net` (ny) | `rpo_csco` + `rpo_dell` + `rpo_smci` | S1, `sec_stack_nat.md` | 2020Q1 |
| L3 | `rpo_eqix` | Equinix RPO | S2 | 2019Q3 |
| O1 | `ob_etn_orders_electrical_americas_ttm_yoy_pct_organic_pct` | Eatons organiska ordertillväxt, Electrical Americas, tolv månader mot året före (%) | S3, `order_orderstock.md` | 2022Q2 |
| O2 | `lt1_dlr_bookings4` (ny) | `ob_dlr_leases_signed_total_dlr_share_q_level_musd` över fyra kvartal (hyra per år för nya avtal, Digital Realtys andel) | S3 | 2024Q1 |

**Sammanhang** (tabeller, ingår inte i läsregeln): medlemmarna var för sig, GE Vernovas RPO (`rpo_gev`, från 2024Q1),
Aristas RPO (`rpo_anet`, från 2022Q4), HPE:s RPO (`rpo_hpe`, från 2024Q2, förutbetalda intäkter), GE Vernovas order och
orderstock i USD, Dells AI-order och AI-orderstock och Digital Realtys nya avtal per kvartal (S3), leverantörernas
intäkter (`rev_*`), capex över fyra kvartal per köpare och köparnas capex-guidance för kalenderåret (KL1:s block).

## Kodning

- **Aggregaten** (`src/ai_tracker/series/ledtid.py`) är summor av medlemmarnas komponenter med `followed.aggregate`
  (`Formula`, `derive`). En version finns först när alla medlemmar har lämnat in för perioden, och `known_from` är den
  senaste komponenten (som A5 och KL1). Medlemmarna är valda efter definition och seriens start, inte efter värden.
- **Definitioner.** Medlemmarnas RPO har inga deklarerade definitionsbrott (S1 och S2 kör `sec_segment.definition_breaks`
  på balanserna). Eatons orderstock byter taggning 2024Q2 (utan dimension till en enda tidshink), men meningen i 10-Q
  är densamma, så det är samma definition (S2). HPE:s RPO är förutbetalda intäkter och ingår därför inte i L2. S3:s
  serier byter definition genom nya nycklar (organisk mot rapporterad, kvartal mot tolv månader) och skarvas aldrig.
  O1 är en definition utan stopp 2021Q4–2026Q3. Eatons orderstock utan angiven bas (en ny nyckel från 2025Q2) används
  inte.
- **O1 är en procentserie, inte en nivå.** Takten är 100 × ln(1 + v/100), alltså log × 100 över ett år av
  tolvmånadersorder, som takten för `kl_capex4`. Förändring i takt = takten nu minus takten två kvartal tidigare. Nivån
  är v. Överraskning mot B1 är inte registrerad för en tillväxttakt och visas som saknad (`followed.ledtid.yoy_measure`).
  Att läsa serien med `state.measures` hade gett takten som skillnaden mellan två tillväxttal (procentenheter), och
  det är fel storhet.
- **Rapporten härleder själv.** `followed.ledtid.table_on` skär tabellen vid läsdagen och räknar fram `lt1_*` och
  `kl_capex4_*` ur komponenterna med katalogens egna formler. Rapporten beror alltså inte på när de lagrade härledda
  raderna senast hämtades. På den delade datan 2026-11-26 är de framräknade raderna lika med de lagrade (25, 33 och 17
  rader för `lt1_*`, 66 och 6 för `kl_capex4_inner` och `_outer`), och ett test visar det på syntetiska data.
- **Läsregeln** är F0:s `common.read_measures` med X = förändring i takt, Y = förändring i takt, *g* = *h* = 5 för
  köparna och 10 för leverantörerna, *k* = 2 och 4, tecken +. Varje ursprung i historiken räknas med
  `common.origin_outcome`, samma funktion som regeln använder, så att ledtiden per ursprung kan visas.
- **Ledtiden** är kvartalet som avgjorde ett "talar för" minus ursprunget, i läsningarna med *k* = 4.

### Tolkningar (regeln ändras inte)

1. **Förvärvsmärket i "efter".** Posten säger att ursprung i kvartalen *a*, *a* + 1, *a* + 4 och *a* + 5 märks. Avsikten
   är att märka där leverantörens förändring i takt läses. I "före" är leverantören X, så märket sätts på ursprunget. I
   "efter" är leverantören Y, så märket sätts på kvartalet som avgjorde utfallet. Utslaget påverkas inte. En granskning
   bör pröva tolkningen.
2. **Ursprung i följd.** Ursprung med impuls åt samma håll i flera kvartal i rad avgörs ofta av samma kvartal för Y.
   Ledtiderna räknar då ned (4, 3, 2, 1). Posten räknar varje ursprung för sig, och rapporten säger att en sådan följd
   är en händelse.
3. **Nästa osedda läsning.** En rad får ett nytt *t* när Y får nästa kvartal, alltså när alla medlemmar i Y har lämnat
   in. Dagen uppskattas med `common.next_filings` (nästa kvartals slut plus medianen av avståndet för de åtta senaste
   inlämningarna) per medlem, och den senaste medlemmen avgör.

## Datering och kalender

- `known_from` är inlämningsdagen för 10-Q och 10-K (RPO, capex) och för resultat-8-K:et (S3). Aggregatens
  `known_from` är den senaste komponenten. Tabellen skärs vid läsdagen innan något räknas, så en rad som blir känd
  efter dagen påverkar inte rapporten (test).
- Eaton, Quanta, Equinix, Super Micro och köparna utom Oracle har balansdag och kvartal på kalenderkvartalets slut.
  Ciscos och Dells balanser har räkenskapskvartalets kalenderkvartal (S1), alltså upp till en månad efter
  kalenderkvartalets slut. Oracles capex har kvartal som slutar en månad före (KL1).
- Dell lämnar sin 10-Q 63–90 dagar efter kvartalet. L2 har därför ofta ett kvartal mindre än de andra raderna, och
  rapporten säger vilken medlem som saknas.

## Licens och publicering

Alla underliggande serier är SEC-data (sec.gov/privacy: offentlig information som får spridas) och har klassen `ja`
för kommersiell användning (`ai_tracker.licenses`, regeln `sec`, de härledda via sina komponenter). De tre nya
serierna har `publish=False`, som KL1:s. O1 och O2 kommer ur S3:s extraktion, som har `publish=False` i väntan på den
oberoende granskningen av extraktionen. Rapporten säger det vid varje rad där de används.

## Förbehåll

- **Kort historik.** 10–27 ursprung per rad, och färre med impuls. Detta är en beskrivning och inget test. Inget
  p-värde räknas, och ingen korrektion för flera prövningar görs (24 utslag). Ett mönster kan vara slump.
- **Före och efter är inte varandras motsats.** Två utjämnade serier som rör sig ihop ger ofta "talar för" i båda
  riktningarna. Då säger regeln inte vilken som kom först.
- **RPO och orderstock är inte orderingång.** Förändringen är order minus leveranser, plus valuta och förvärv (S2).
  Ciscos och Dells RPO har stora tjänstedelar (support och prenumerationer, S1).
- **Leverantörerna säljer till fler än AI-köparna.** Quanta och Eaton till elbolag och industri, Cisco och Dell till
  företag. Datacenterandelen går inte att skilja ut i XBRL (S2).
- **Förvärv.** Belagda: Cisco–Splunk (2024-03), Eaton–Fibrebond (2025-04-01) och Eaton–Boyd Thermal (2026-03-12).
  Förvärv hos Quanta, Dell, Super Micro och Equinix är inte kontrollerade. O1 är organisk och påverkas inte.
- **Digital Realtys andel** är obelagd 2021Q4–2024Q1 (S3, tolkning 9). Nya avtal är klumpiga: förändringen i takt för
  summan över fyra kvartal kan bli nära ±100 log × 100 när ett stort kvartal går in i eller ut ur fönstret.
- **BLOCKED och utanför ramen.** Vertiv: inget RPO i XBRL, och S3:s orderserier slutar 2025Q4. GE Vernova: RPO från
  2024Q1 och order från 2024Q1 (för korta för läsregeln, sammanhang). Schneider Electric, Siemens Energy och ABB finns
  inte på EDGAR. Privata datacenterbyggare och kraftbolagens egna investeringar ingår inte.
