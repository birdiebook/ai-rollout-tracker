# Status steg 2

Uppdateras av orkestreraren vid varje milstolpe. Senast: 2026-11-25 (körning 13, rättning efter granskningen av integrationen).

## Läge

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

2. **`DATA_KEY`** (datasnapshoten är byggd):
   - skapa en nyckel med `python -c "import secrets; print(secrets.token_urlsafe(32))"` och spara den i en lösenordshanterare;
   - lägg in den som GitHub-secret `DATA_KEY` och som miljövariabel `DATA_KEY` i miljön ai-rollout-tracker;
   - kör sedan "Weekly data fetch" en gång för hand.
3. **Cloudflare Radar har licensen CC BY-NC 4.0.** Serierna visas på hemsidan eftersom sidan är icke-kommersiell. Ska
   sidan någon gång användas kommersiellt måste de dras tillbaka.

5. **PyPI-historik i Actions-cachen** (cirka 176 GB av månadskvoten på 1 TB) kan vänta till nästa kvotmånad.

6. **Före 2026-11-30 22:41 UTC** (när integrationen pushas till `main`):
   - regeln att ögonblicksbilden inte bär värden för inhållna serier (beslutsloggen 2026-11-25). Rekommendation: behåll;
   - `/next/` försvinner från Pages efter pushen tills webbens vitest är grön, eftersom `pages.yml` bara tar med
     `/next/` när `pages-next.yml` lyckas. Den gamla sidan publiceras som förut. Alternativet är att webbrättningen
     landar först.

## Viktiga datum

- 2026-11-30: första skarpa ögonblicksbilden och månadsbrevet
- 2026-12-05: första skarpa TSMC-prognosen (B2)
- 2027-01-20: första skarpa capex-prognosen
