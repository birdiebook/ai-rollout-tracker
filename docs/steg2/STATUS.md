# Status steg 2

Uppdateras av orkestreraren vid varje milstolpe. Senast: 2026-11-26 (körning 16, antenner, integrerad efter R28 och
X25).

## Läge

### Drift 2026-11-26: röd veckohämtning

- Veckohämtningen 2026-11-25 fallerade bara på aktualitet: Baidus fyra tabellserier (CN1) fick ingen data i
  Actions-cachen, eftersom EDGAR:s `index.json` för en 6-K från 2021 svarade 502. Hämtaren läser nu filingens
  `-index.htm` vid 5xx (beslutsloggen 2026-11-26). En manuell veckohämtning 2026-11-26 var grön, med alla
  fyra serierna (32 rader var) och aktualiteten ok.
- npm gav 429 för två serier 2026-11-25, men de gick igenom 2026-11-26.

### Körning 16: antenner, tre nya följda frågor (2026-11-26)

- **Status:** F0 (gemensam motor och symmetrisk läsregel), LT1 (ledtid), BG1 (betalningsgapet) och EL1 (elen som
  begränsning) är byggda, granskade (R28, GODKÄND MED ANMÄRKNINGAR, inget must_fix) och rättade (X25: R28-1 till R28-4,
  R28-5 delvis), och integrerade på grenen `auto16/integration16` med main. Tre nya katalogserier `lt1_*` med
  `publish=False`. BG1 och EL1 härleder sina storheter i rapporten. Ingen kärnserie och inget grentillstånd ändras, och
  KL1:s rapport är byte för byte densamma.
- **Läs:** [resultat/antenner.md](../resultat/antenner.md), en rad per följd fråga. Varje månad:
  `python -m ai_tracker.followed antenner --as-of <dag>` och `python -m ai_tracker.followed <fråga> --as-of <dag>`.
  Frågornas rapporter: [ledtid](../resultat/ledtid.md), [betalningsgapet](../resultat/betalningsgapet.md),
  [elflaskhalsen](../resultat/elflaskhalsen.md). Granskning: [granskning/r28_antenner.md](../granskning/r28_antenner.md).
- **Förbehåll:** alla utslag per 2026-11-26 är på kvartal som var sedda när registerposterna skrevs, och frågorna läser
  delvis samma capex-takt. LT1 och EL1 har samma huvudpar och är tillsammans en observation. I EL1 och BG1 har
  huvudläsningen hittills bara haft impulser uppåt, så riktningen nedåt är inte prövad. Första osedda läsningarna: Dell
  omkring 2026-12-09 (LT1), Oracle omkring 2026-12-11 (BG1 och KL1), inre lagret omkring 2027-01-31.
- **Väntar på ägarbeslut:** se punkt 7 under "Väntar på Johannes".

### Körning 15: KL1 Kreditlagret, en följd fråga (2026-11-25)

- **Status:** KL1 är byggd, granskad (R26 och R27) och rättad (X23 och X24), och integrerad på grenen
  `auto15/integration15` med main. 53 katalogserier `kl_*` med `publish=False` och klassen `ja`. Ingen kärnserie,
  och inget grentillstånd ändras. Data är inlagd i den delade basen ur X23:s arbetskopia. X24 ändrade ingen serie.
- **Frågan:** ändras finansieringens pris och tillgång i de yttre lagren (Oracle, CoreWeave, Nebius, IREN), och följer
  investeringstakten med? Det inre lagret (Microsoft, Alphabet, Amazon, Meta) är jämförelsen. Registret har posten
  "KL1" och tilläggen KL1, X23 och X24.
- **Läs:** [resultat/kreditlagret.md](../resultat/kreditlagret.md). Varje månad:
  `python -m ai_tracker.followed kreditlagret --as-of <dag>`. Källor: [kallor/kreditlagret.md](../kallor/kreditlagret.md).
  Granskning: [granskning/r26_kreditlagret.md](../granskning/r26_kreditlagret.md) och
  [granskning/r27_kreditlagret.md](../granskning/r27_kreditlagret.md).
- **Förbehåll:** läsningarna per 2026-11-25 gäller kvartal som var sedda före registerposten. Den första läsningen på
  osedda data kommer med Oracle omkring 2026-12-11. Yttre lagret kan avgöras först med 2026Q4 (februari 2027).
  Självkontrollen mot nyhämtade dokument täcker alla 460 rader (R27 458 av 458, X24 SpaceX:s 46 av 46). R26 och R27
  har läst de 458 äldre raderna. X24:s två nya rader är de tal som R27 citerade från samma platser, men de har inte
  granskats separat. SpaceX:s ränta på övrig finansiering visas med räntekostnaden för Valor-skulden (cirka 10,7 % per
  år för 2026Q3), inte bara med bolagets 6,3 %.
- **Väntar på ägarbeslut:** ska läsregeln läsa åt båda hållen? Rekommendation: låt regeln vara till den första
  läsningen på osedda data. Ett byte kräver en ny daterad registerpost före den läsningen.

### Körning 14 (2026-11-25)

- **Status:** åtta spår är byggda, granskade (R17–R24) och rättade (X14–X21), och integrerade på grenen
  `auto14k/integration14` med main (ägarbesluten 2026-11-25 och WV2). 171 nya katalogserier, ingen ny kärnserie.
  Grenarnas tillstånd och index v2 är oförändrade i rekonstruktionen 2024-01 – 2026-11. Data är inlagd i den delade
  basen ur rättningsspårens arbetskopior.
- **Stacken via SEC:** nät, optik och servrar (S1, [kallor/sec_stack_nat.md](../kallor/sec_stack_nat.md)), kraft,
  kylning, elnät och datacenter (S2, [kallor/sec_stack_kraft.md](../kallor/sec_stack_kraft.md)) och order och
  orderstock ur 8-K (S3, [kallor/order_orderstock.md](../kallor/order_orderstock.md), `publish=False`).
- **Finansiering och Kina:** spread vid emission (KR1, [kallor/kredit_emission.md](../kallor/kredit_emission.md),
  `publish=False`) och Alibaba och Baidu via 6-K (CN1, [kallor/kina_sec.md](../kallor/kina_sec.md)).
- **Förmåga och kostnad:** pris vid rörlig förmågetröskel (Q1, [kallor/g2_rorlig_troskel.md](../kallor/g2_rorlig_troskel.md))
  och öppna mot stängda modeller och Kina-gapet (Q2, [kallor/g1_oppen_stangd.md](../kallor/g1_oppen_stangd.md)).
- **Tillståndsregeln prövad** (T1, [resultat/t1_tillstandsregeln.md](../resultat/t1_tillstandsregeln.md)): tillstånden
  är stabila mot revideringar, men att de förutsäger takten är inte visat (Holm-p 0,37). Regeln ändras inte.
- **Månadsgränsen i Arena:** en tavla från månadens sista dag, belagd dagen efter, räknas nu i sin månad i alla
  Arena-serier. Rättat i `vintages.monthly` och `open_gap` (X20), `price_rolling` (X19) och `arena_price`
  (integrationen, registerposten 2026-11-25). Inga rader i `g2_price_at_arena_capability*` ändrades.
- **Läsanvisningar** för webben: [steg3/datakontrakt.md](../steg3/datakontrakt.md), "Läsanvisningar för körning 14".
- **Väntar på ägarbeslut:** publicering av `f1_surprise_index`, Q1:s referens (N-1), `g2_price_rolling12_arena` som
  kärnserie, KR1 per emittent, CN1:s textserier för Baidu, S3:s `ob_*`, Vertivs externa segment och kärnkandidater i
  G6 och G7. Inget av detta är ändrat i integrationen.

### Körning 13 (2026-11-24)

- **Status:** alla spår i körning 13 är byggda, granskade (R9–R16) och rättade (X6–X13), och integrerade på grenen
  `auto14/integration13`. Riktning och beslut: [riktning.md](../riktning.md). Data för de nya serierna är hämtad med
  den sammanslagna koden och inlagd i den delade basen.
- **Index v2** (en röst per källfamilj) är officiell regel från ögonblicksbilden 2026-11-30. Rekonstruktionen v1 mot v2:
  [resultat/tillstand.md](../resultat/tillstand.md), "Index v2 (källfamiljer)". Grenen måste vara på `main` före
  2026-11-30 22:41 UTC, annars skrivs den första skarpa ögonblicksbilden med v1 (R9). Webbsessionen lägger till
  tillståndet "för få källor".
- **Licensklass** per serie (`ja`, `nej`, `okänd`): [datakallor/licensniva.md](../datakallor/licensniva.md).
- **Pengarna:** avskrivningar och PP&E (P1, [kallor/sec_avskrivningar.md](../kallor/sec_avskrivningar.md)),
  nyttjandeperioder (P2a), intäktskravet (P2b, [resultat/intaktskrav.md](../resultat/intaktskrav.md), omräknat efter
  X11) och N7 som backtest ([resultat/n7.md](../resultat/n7.md), omkört efter X11).
- **Förväntningar:** revideringsindex och överraskningsindex (F1, [resultat/f1_revideringar.md](../resultat/f1_revideringar.md)).
  Serierna som läser den kurerade CSV:n har `publish=False` tills Johannes beslutar (R11-4).
- **Makro:** BNP-bidrag, elpris och PPI (M1, [kallor/makro_bea_bls.md](../kallor/makro_bea_bls.md)). Import per land
  (M2, [kallor/census_hs.md](../kallor/census_hs.md)): årsfilen finns, och HS-serierna är hämtade med `CENSUS_API_KEY` (2026-11-25).
- **Läsanvisningar** för webben: [steg3/datakontrakt.md](../steg3/datakontrakt.md), "Läsanvisningar för körning 13".
- **Efter granskningen av integrationen (2026-11-25):** `origin/main` (W12–W14, RW1-X, R-W1–R-W3, WX2 och
  aktualitetsgränsen för Nvidia) är mergad in. Paketet är 1.4.0. Den publika ögonblicksbilden bär inga värden för
  serier med `publish=False` (beslutsloggen 2026-11-25), paketets brev och rapporter klarar licensgrinden, och
  `snapshot.yml` skriver bilden även när bara serier är för gamla. Webbens röda tester står i
  [steg3/datakontrakt.md](../steg3/datakontrakt.md), "Webbgrindar efter integrationen".

### Tidigare

- **Steg 2:s våg 0–4 är klara.** Holdouten för C3 och C4 är öppnad och utvärderad: faktormodellen klarade inte regeln för
  TSMC och följer med som skugga. Regimmodellen ingår i månadsbilden från 2026-11-30. Flödesvyn och kvartalsrapporten
  är byggda.

- **Våg 0** klar: delad data, förregistrering C0 (granskad, R6), sannolikhetsprognoser (påslagna), månadsbrev.
- **Våg 1** nästan klar: allt utom PyPI/npm och GitHub är mergat, inklusive Cloudflare Radar och Wikipedia.
  **Granskning R3 (datum):** inget läckage. Två fel daterade för sent (Meta-skuld, Manifold-urval) rättas av spår X2.
  PyPI/npm är mergat (PyPI-historiken är onsdagsurval, eftersom exakt historik skulle kosta cirka 1,7 TB).
  **Granskning R5 (extraktion):** klar. Nvidias guidance är godkänd för N3. AI-nyckeltal, leasingåtaganden och planer är
  godkända med rättningar (F1–F14, 26 strikta xfail-tester). Rättningarna görs efter att kvoten återställts.
- **Våg 2:** N3–N6 är mergade (B1 är huvudmodell för alla fyra). **B3 för TSMC passerade regeln** (MAE 5,81 mot B2 6,42,
  Holm-p 0,038). B2 är huvudmodell tills den oberoende granskningen R7 är klar, före 2026-12-05. B3 för capex passerade inte. R3-rättningarna är mergade.
- **G-A registrerad** (2026-11-24): nya kärnserier i G3–G7. **G3 (användning) har nu ett tillstånd** med 13 räknade serier
  (npm, PyPI, Wikipedia, Cloudflare). Kör nu: GitHub (B2), granskning R7 (B3 för TSMC), rättning X3 (R5-fynd).
- **N2:s huvudmodell är B3** sedan 2026-11-24, efter granskning R7 och rättningen med Nvidia i gruppmedlet
  (MAE 5,83 mot B2 6,42, Holm-p 0,059). Första skarpa prognosen med B3 görs 2026-12-05.
- **R5-rättningarna är mergade.** Nyckeltal, leasingåtaganden och planer är publicerbara.
- **Faktormodellen (C3)** är utvecklad med holdouten stängd. Specifikationen är låst (`5431f41`). Utvecklingen visar
  inga säkra vinster (N1 sämre, N2 och N3 bättre men inom slumpen). **C4 (regim) är låst** (`735dc64`) och utvecklad.
  Holdouten för C3 och C4 kan nu öppnas i en körning, **efter ditt godkännande**. Avstämningarna (A5) är mergade.
  D2 (prognoser 1–8 kvartal) utvecklas.
- **Tidigare:** Datasnapshoten är klar och väntar på `DATA_KEY`. Avstämningarna (A5) och D2 är
  förregistrerade.

## Miljö

Miljön **ai-rollout-tracker** är klar: alla värdar, setup-skript och `SEC_USER_AGENT`. Den här sessionen kör där.
Kvar för nya sessioner: `DATA_KEY` (punkt 2 nedan).

## Väntar på Johannes

2. **`DATA_KEY`:** GitHub-secreten är satt. Veckohämtningen 2026-11-25 packade och laddade upp den krypterade
   snapshoten. Kvar: samma värde som miljövariabel `DATA_KEY` i molnmiljön ai-rollout-tracker, så att en ny session
   kan installera snapshoten.
3. **Cloudflare Radar har licensen CC BY-NC 4.0.** Serierna visas på hemsidan eftersom sidan är icke-kommersiell. Ska
   sidan någon gång användas kommersiellt måste de dras tillbaka.

5. **PyPI-historik i Actions-cachen** (cirka 176 GB av månadskvoten på 1 TB) kan vänta till nästa kvotmånad.

6. **Före 2026-11-30 22:41 UTC** (när integrationen pushas till `main`):
   - regeln att ögonblicksbilden inte bär värden för inhållna serier (beslutsloggen 2026-11-25). Rekommendation: behåll;
   - `/next/` försvinner från Pages efter pushen tills webbens vitest är grön, eftersom `pages.yml` bara tar med
     `/next/` när `pages-next.yml` lyckas. Den gamla sidan publiceras som förut. Alternativet är att webbrättningen
     landar först.

7. **Körning 16 (antenner):**
   - ska antennraden in i det publika månadsbrevet, fast LT1:s serier och KL1:s `kl_*` har `publish=False`?
     Rekommendation: inte än. Brevet visar i dag aldrig värden för `publish=False`-serier. Antennerna kan få en rad med
     bara utslagen (inga värden) efter den första osedda läsningen, i en egen post;
   - byta F0:s "kunde prövas" mot antalet ursprung där Y finns i fönstret (R28-5). Rekommendation: ja, en daterad post
     före läsningen omkring 2027-01-31;
   - EL1: en extra rad med förändring i takt för orderstockarna, så att riktningen nedåt kan prövas. Rekommendation:
     ja, i samma post;
   - KL1: en symmetrisk läsning bredvid den låsta, före Oracle omkring 2026-12-11. Rekommendation: ja;
   - läsa Quantas 10-Q för förvärv (R28-7), utanför körning 16 eftersom det är en ny läsning. Rekommendation: ja, före
     2027-01-31.

## Viktiga datum

- 2026-11-30: första skarpa ögonblicksbilden och månadsbrevet
- 2026-12-05: första skarpa TSMC-prognosen (B3, huvudmodell sedan 2026-11-24)
- 2027-01-20: första skarpa capex-prognosen
