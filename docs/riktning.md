# Riktning: vad projektet kan säga i dag och vad som ska byggas härnäst

**Status: beslutat 2026-11-24.** Johannes valde rekommendationerna och beslutspunkterna 1–3 (`docs/beslutslogg.md`). Skrivet av VD/riktningssessionen efter genomläsning av `CLAUDE.md`,
`docs/plan.md`, `docs/steg2/STATUS.md`, `docs/beslutslogg.md`, `docs/mattregister.md`, `docs/holdout_logg.md`,
`docs/granskning/r8_g2_arena.md`, `docs/resultat/` och katalogen (488 serier). Inga andra filer är ändrade.

## 0. Syfte (Johannes 2026-11-24)

Projektet byggs för ägarens egen skull: att ha bästa möjliga koll på **hela AI-flödet, lager för lager**. Lagren är förmåga och kostnad, användning, intäkter, capex och finansiering, chips, minne och nät, el och kylning, datacenter och effekter. Målet är att följa utvecklingen och se tidigt när något ändrar takt i något lager. Spårningen är neutral. Kopplingen till egna placeringar är indirekt och görs utanför repot: repot är publikt, och det innehåller inga innehav (`CLAUDE.md`). Målgrupperna i avsnitt 5 är en ribba för kvaliteten, inte en plan för spridning.

## 1. Kort svar

- **Projektet mäter AI:s investeringscykel bra:** pengar och chips i USA-noterade bolag (G4–G6), med riktiga
  vintages och en metod som håller för granskning. Det är projektets styrka.
- **Projektet mäter ännu inte AI-utrullningen i samhället.** Toppen av kedjan (förmåga, kostnad, användning) och
  botten (effekter på arbete och ekonomi) är tunna eller blinda. G1, G2 och i praktiken G8 och G9 har ingen bred bild.
- **Prognoserna ger ingen fördel utöver bolagens egen guidance.** Bästa N2-modellen är TSMC:s guidance korrigerad för
  bias, faktormodellen föll på holdouten, och N1 och N3–N6 slår inte drift. Värdet ligger i övervakningen och i
  förväntningar mot utfall, inte i att slå bolagen.
- **Rekommendation:** sluta bygga prognosmodeller. Bygg i stället de tre saker som saknas för alla fyra målgrupperna:
  att pengarna går att följa hela vägen (capex → avskrivningar → intäkter), makrokanalen (BNP, import, elpris, arbete)
  och förväntningar mot utfall (revideringar av guidance). Först en billig hygienåtgärd: diffusionsindexet ska räkna
  oberoende källor, inte serier, före första skarpa ögonblicksbilden 2026-11-30.

## 2. Gren för gren: välmätt, tunt eller blint

| Gren | Läge | Varför |
|---|---|---|
| **G5 Investeringar** | Välmätt | Capex för de fyra största och Oracle med SEC-vintages från 2017, capex/OCF, leasing och skuld (A3), Census C30 och BEA. N1 finns, men inget slår drift (n = 9) |
| **G6 Halvledare** | Välmätt | TSMC månadsvis från 2006 (6-K), segment för Nvidia, AMD, Broadcom, Marvell och ASML, G.17 med 135 riktiga vintages. N2 är projektets enda mål med statistisk styrka (n = 174). De snabbaste ledande serierna (Korea 10/20 dagar, Taiwans exportordrar) är blockerade |
| **G4 Intäkter** | Medel | Molnsegment, Nvidias datacenter och RPO. Men moln är inte AI, och AI-intäkter från slutkund saknas: labbens intäkter är bara Anthropics egna uttalanden. Backcastens "1,000 accelererar" vilar på fem korrelerade molnserier |
| **G7 El** | Medel till tunt | EIA:s kommersiella elförsäljning i sex delstater (en proxy, inte datacenterlast), EIA-930 och PJM (`publish=False`). Anslutningsköer är blockerade (LBNL). Elpriser saknas |
| **G3 Användning** | Tunt men bredare | 13 räknade serier, men mest utvecklarproxyer (npm, PyPI, Wikipedia, Cloudflare från 2024). BTOS har bytt fråga två gånger (v3 från 2026-10), och Eurostat är årsdata. Tokenvolymer, det bästa måttet, är blockerade (OpenRouter) eller oregelbundna (bolagens nyckeltal) |
| **G9 Forskning** | Tunt, en källa | De tre arXiv-kategorierna är en källa. Epoch är spärrat tills det finns 24 månader egna ögonblicksbilder. Prognosmarknaderna (D3) finns som serier men ingår inte i tillståndet |
| **G8 Effekter** | Tunt, en källa | Nio Indeed-länder är en källa med en metod. Det finns ingen serie för produktivitet, sysselsättning eller lön. "Accelererar 29 av 31 månader" är Indeeds serie, ingen bred bild |
| **G1 Förmåga** | Blint i tillstånd | De valda Epoch-benchmarks har ingen takt än (SpireClimb är känd först 2026-12-31), ECI är spärrad, METR uppdateras inte, och Arena har ett läckagefel (R8, rättas i X5). Benchmarks mättas, så långa serier är strukturellt svåra |
| **G2 Kostnad** | Blint i tillstånd | En kärnserie (GPQA-varianten) med för kort historik. Arena-priset underkändes (R8): tröskeln binder inte, så serien mäter golvet i den billigaste prisnivån. Pris per token är inte pris per uppgift när resonemangstokens ökar |

## 3. Var signalen är svag

1. **Indexet räknar serier, inte oberoende källor.** G8 har 9 serier från en källa, G9 har 3 från en, och G7 har 6
   delstater ur samma EIA-tabell. Korrelerade serier blåser upp en samstämmighet som inte finns. En analytiker på en
   fond eller bank ser det först.
2. **Tillståndsregeln är inte validerad.** Tillstånden byter ofta i backcasten. G9 gick 1,000 → 0,500 → 0,833 →
   0,167 på fyra månader (2026-05 till 2026-08), med arXiv som enda källa.
3. **Ingen prognosfördel utöver guidance.** DF klarade inte holdouten (N2 6,65 mot B2 6,45). B3 vinner genom att
   korrigera TSMC:s konstanta bias på cirka 1,6 %. Det är ärligt och användbart, men det är ingen ny insikt om efterfrågan.
4. **Backcasten är inget realtidstest.** C30, importen, BEA, EIA före arkivet, arXiv, npm, PyPI och Wikipedia bär
   dagens vintage.
5. **Korta serier och regimbrott.** BTOS v3 började 2026-10, Cloudflare 2024 och Arena BT 2024-01. Många takter blir
   tillgängliga först 2027.
6. **Regimmodellen omklassar i efterhand.** Efterfrågeblocket klassades om 25 % av holdout-dagarna.
7. **Urvalet är USA och börsnoterade bolag.** Kina saknas helt. Privata labb (OpenAI, xAI) syns bara indirekt, via RPO
   och leverantörer.

## 4. Frågor vi inte kan besvara alls i dag

| Fråga | Varför inte |
|---|---|
| Betalar sig investeringarna? | Capex kopplas inte till avskrivningar och AI-intäkter. AI-intäkter från slutkund saknas |
| Hur mycket AI används, i tokens eller uppgifter, och hur snabbt växer det? | Tokenvolymer är blockerade eller oregelbundna |
| Bromsar förmågeutvecklingen? | G1 har inget tillstånd |
| Hur snabbt faller kostnaden för en given uppgift? | G2 har inget tillstånd, och pris per token missvisar för resonemangsmodeller |
| Syns AI i produktivitet, sysselsättning eller löner? | Det finns ingen sådan serie |
| Hur stort är AI:s bidrag till BNP-tillväxten, netto efter import? | Komponenterna finns delvis, men bidraget är inte härlett |
| Hur finansieras utbyggnaden, och var sitter risken? | Volymerna finns delvis (A3), men kreditpriser och SPV-strukturer saknas |
| Har el blivit flaskhalsen? | Datacenterlast och köer observeras inte direkt. Elpriser saknas |
| Hur ser det ut i Kina? | Inga serier |

## 5. Vad de fyra målgrupperna behöver

> **Fokus (Johannes 2026-11-24, samma dag):** projektet byggs för Johannes och några vänner, inte för många användare. Målgrupperna nedan är en ribba för kvaliteten på förståelsen, inte en plan för spridning. Arbete som bara gäller spridning prioriteras inte: engelsk version, separata vyer per målgrupp, nedladdningar och kommersiell användning. **Sidan är Johannes främsta sätt att ta in informationen och ska vara ambitiös**: intressant och givande att utforska. Månadsbrevet ligger kvar som det är (automatiskt), men prioriteras inte.

Det är en datakärna med fyra vyer, inte fyra produkter. Det som skiljer målgrupperna är vad de tittar på först.

| Målgrupp | Huvudfråga | Behöver | Har vi |
|---|---|---|---|
| Hedgefond | Vänder cykeln, och före vem? | Andraderivatan i capex, revideringar av guidance, överraskning mot förväntan, ledande leverantörsdata, finansieringsstress | Delvis: capex, TSMC, guidance. Revideringsindex, finansiering och Korea saknas |
| Bankens makroavdelning | Vad betyder AI för BNP, inflation och arbete? | BNP-bidrag netto efter import, elpris, investeringar i nationalräkenskaperna, arbetsmarknad | Komponenter i G5 och G6. Bidrag, elpris och arbete saknas |
| Strategi i ett bolag | Hur snabbt ska vi gå, och vad kostar det? | Kostnadskurva per uppgift, förmåga, användning per bransch och storlek, gapet mellan öppna och stängda modeller | Tunt: G1 och G2 är blinda, G3 har proxyer |
| Nyfiken människa | Accelererar det eller inte, och var är flaskhalsarna? | En berättelse som håller ihop: kedjan, glappen och vad som överraskade | Kedjan och månadsbrevet finns. Toppen och botten av kedjan saknas |

**Positionering:** *den ärliga, tidsstämplade balansräkningen för AI-ekonomin.* Den visar kedjan, glappen mellan leden
och förväntningar mot utfall. Den är ingen prognosmaskin. Det är vad ingen annan gör gratis, och det håller för alla
fyra målgrupperna.

**Licenser:** fonder och banker använder data kommersiellt. Cloudflare (CC BY-NC), npm (ingen licens) och PJM
(förbjuder vidarepublicering) går inte att använda kommersiellt. Nya spår bör välja öppna licenser (public domain,
CC0, CC BY) när det finns ett val, så att en kommersiellt ren delmängd alltid går att räkna fram (beslutspunkt 3).

## 6. Förslag, rangordnade

Rangordningen bygger på hur mycket ny, oberoende förståelse förslaget ger, gånger hur många målgrupper det hjälper,
delat med kostnaden i agentspår och de mänskliga flaskhalsarna (nycklar, licenser och kalendertid).

### 1. Oberoende källor i diffusionsindexet (hygien, 1 spår, före 2026-11-30)

- **Vad:** fältet `family` per kärnserie (samma källa och samma begrepp = en familj). Indexet v2 ger en röst per
  familj, och den rösten är medelvärdet av familjens riktningar. Tillstånd kräver minst 3 familjer. Ögonblicksbilden
  visar antalet serier och antalet familjer per gren.
- **Effekt, väntad efter konstruktion:** G8 och G9 får "för få källor" och G7 ligger på gränsen. Ändringen väljer
  ingen riktning.
- **Rättelse 2026-11-24, efter backcasten på riktiga data (rekonstruktion 2026-05 till 2026-10):** v2 är inte
  genomgående mer försiktig. G8 blir "för få källor" som väntat. Men G6 blir "accelererar" i två månader där v1 sa
  "stabil", eftersom importen och G.17 inte längre väger dubbelt. G7 blir "bromsar in" i två månader, eftersom de
  sex delstaterna ur EIA nu bara väger en tredjedel. Med få familjer väger varje familj tungt, så indexet kan röra sig
  mer. v2 mäter oberoende källor bättre, men den är inte mer försiktig.
- **Varför först:** första skarpa ögonblicksbilden är 2026-11-30. Det skarpa registret ska inte börja med ett
  tillstånd som vilar på en enda källa. Att byta regel senare ger ett brott i registret.
- **Ärlig not:** backcasten har redan setts. Ändringen motiveras av oberoende, inte av utfall, och loggas så.
  v1 räknas och redovisas bredvid.
- **Samordning:** ändringen rör ögonblicksbildens schema, som `site_bundle` läser. Den behöver samordnas med
  webbsessionen.

### 2. Revideringsindex för guidance (1 spår, data finns)

- **Vad:** för varje guidad storhet (bolag × period × mått) med flera vintages räknas revideringen som
  log(ny mittpunkt) − log(förra mittpunkten). Varje månad redovisas andelen revideringar uppåt (som i PMI) och
  medianstorleken. Källor: `curated/guidance_capex.csv` (Meta i alla kvartal, Alphabet, Amazon och Microsoft
  delvis), TSMC:s och Nvidias kvartalsguidance, och TSMC:s årliga capex-guidance (ny extraktion med citat).
  Dessutom ett överraskningsindex: utfall minus guidancens mittpunkt, standardiserat per bolag.
- **Varför:** de som vet mest, bolagens CFO:er, uppdaterar sina planer här, och det är den tidigaste rena signalen
  om att investeringstakten ändras. Det ligger rakt i projektets uppdrag: att se när takten ändras.
- **Ärlig not:** cirka 10–20 revideringar per år. Måttet är beskrivande och inget test.

### 3. Följ pengarna hela vägen: avskrivningar och intäktskrav (2 spår + granskning)

- **Vad:** avskrivningar och bruttovärdet av anläggningstillgångar ur XBRL för de fyra största, Oracle och CoreWeave
  (taggen per bolag låses i registret), och nyttjandeperioder för servrar ur 10-K med citat. Flera bolag har ändrat
  dem sedan 2022, åt båda hållen. Härlett:
  - avskrivningar / molnintäkter;
  - **intäktskrav** = avskrivningar + avkastningskrav på nettot av anläggningstillgångar (ett registrerat intervall
    för avkastningskravet, inte en punkt), jämfört med molnintäkter och bolagens AI-nyckeltal;
  - **N7, avskrivningar 1–8 kvartal framåt:** en strukturell modell (capexhistorik × nyttjandeperioder) mot drift.
- **Varför:** det besvarar frågan alla fyra målgrupperna ställer, om investeringarna betalar sig, utan att vi tar
  ställning. Det är också det enda stället där en prognos har en mekanisk grund. Avskrivningarna 2027–2030 är till
  stor del redan bestämda av capex 2024–2026. N7 kan bli projektets första mål där en modell faktiskt slår det naiva.
- **Ärlig not:** avskrivningarna omfattar alla anläggningstillgångar, inte bara AI-servrar, och nyttjandeperioden är
  ett redovisningsval. Glappet redovisas med sin takt, utan bubbel- eller tillväxtetikett.

### 4. Makrokanalen: BNP-bidrag, serverimport och elpris (2 spår + granskning, Census-nyckel)

- **Vad:**
  - BEA:s nationalräkenskaper: bidraget till real BNP-tillväxt från informationsbearbetningsutrustning och mjukvara,
    och importen av datorer och tillbehör. Härlett: ett AI-relaterat bidrag netto efter import, med en registrerad
    definition;
  - Census-import på HS-nivå (8471, 8473 och 8542) per land: Taiwan, Mexiko och Vietnam. Kräver en gratis
    Census-nyckel;
  - BLS: KPI för el och PPI för databehandling och hosting (api.bls.gov är tillåten).
- **Varför:** det är makroavdelningens första fråga. Serverimporten är den mest direkta bilden av AI-capex i
  handelsdata, och elpriset är den kanal där AI når hushållen.
- **Ärlig not:** BEA:s kategorier är bredare än AI. Definitionen registreras före beräkningen och redovisas med
  den förbehållet.

### 5. G8 från en källa till tre (licenskartläggning 1 spår, därefter 2 spår + granskning)

- **Vad:**
  - BLS CES-sysselsättning i exponerade branscher (datortjänster, mjukvara, databehandling, kundtjänst) mot mindre
    exponerade;
  - Indeeds platsannonser per yrke (Hiring Labs index, till exempel mjukvaruutveckling);
  - användning bland arbetstagare (St. Louis Feds Real-Time Population Survey);
  - Anthropic Economic Index (användning per uppgift).
  Licenserna för de två sista ska verifieras först.
- **Design:** en skillnad i trend mellan exponerade och mindre exponerade grupper, förregistrerad, med MDE angiven i
  förväg.
- **Ärlig not:** det bästa troliga resultatet är en övre gräns: "ingen effekt större än X syns ännu". Det är ändå
  värdefullt för makroavdelningen och den nyfikne, och det sägs rakt ut.

### 6. Förmåga och kostnad med mått som inte mättas (2 spår + granskning, efter X5)

- **G2 med rörlig tröskel:** det lägsta priset för den förmåga som var fronten för 12 månader sedan. Tröskeln binder
  per konstruktion, vilket svarar direkt på R8:s huvudfynd. Kostnad per uppgift där tokenantal per körning finns.
- **G1, gapet mellan öppna och stängda modeller:** tiden det tar för den bästa öppna modellen att nå den stängda
  frontens nivå, ur Arena och Epoch. Det är strategiskt viktigt (handelsvara eller vallgrav) och mättas inte på
  samma sätt som enskilda benchmarks.
- **Varför inte högre:** källorna finns, men måtten kräver nya definitioner och granskning. Läckaget i `arena.py`
  (R-1) måste rättas först.

### 7. Kina via SEC (2 spår + granskning)

- **Vad:** Alibaba och Baidu lämnar in 6-K och 20-F. Därifrån tas capex och molnintäkter (Cloud Intelligence, AI
  Cloud) med samma 6-K-teknik som för TSMC, ASML och Nebius. Dessutom de kinesiska modellernas andel av öppna
  nedladdningar och Arena-toppen, ur befintliga källor.
- **Varför:** utan Kina är "världen" i visionen inte sann. Det är också en geopolitisk fråga som alla fyra
  målgrupperna bryr sig om. Tencent finns inte hos SEC och ingår inte.

### 8. Finansieringsskörhet: spread vid emission (2 spår + granskning)

- **Vad:** belopp, kupong och löptid ur prospekt (424B) för AI-tunga emittenter (Oracle, Meta, CoreWeave och de
  andra hyperscalers), och spreaden mot statsobligationen med samma löptid (treasury.gov, public domain, värden behöver
  öppnas).
- **Varför:** krediten är vägen från AI-risk till banker. Det är ett pris och inte bara en volym, ur gratis data.
- **Ärlig not:** privata placeringar (144A, SPV) syns inte i 424B. Täckningen redovisas.

### Utanför rangordningen: kräver en åtgärd av Johannes

| Åtgärd | Ger | Tid för Johannes |
|---|---|---|
| Census API-nyckel (`CENSUS_API_KEY`) | Förslag 4 (HS-import) och M3 från primärkällan | 5 min |
| Bank of Korea ECOS-nyckel (`ECOS_API_KEY`) | Koreas halvledarexport, den mest ledande leverantörsserien | 5 min |
| `DATA_KEY` (väntar redan, `STATUS.md`) | Datasnapshoten | 5 min |
| Fråga OpenRouter om skriftligt tillstånd för tokenvolymer | Det enda breda användningsmåttet i tokens | ett mejl, osäkert utfall |

## 7. Vad vi slutar med eller pausar

- **Nya prognosvarianter för N1–N6.** Den statistiska budgeten är förbrukad, och guidance är taket. Det skarpa
  registret får arbeta i kalendertid. Undantaget är N7 (förslag 3), som har en mekanisk grund.
- **Fler serier ur samma familj** (fler paket, delstater eller länder ur samma källa). De lägger inte till oberoende
  information.
- **Arena-priset som kärnserie.** X5 rättar läckaget, eftersom det rör G1, men serien lappas inte mer. Förslag 6
  ersätter begreppet.
- **Världsklasskriteriet "bättre än bolagen själva"** i `steg2/plan.md`. Det går inte att nå med gratis data.
  Ersätt det med: *"bolagens systematiska avvikelser från guidance redovisas öppet, och huvudmodellerna slår de naiva
  modellerna i det skarpa registret"*.

## 8. Rekommendation och körplan

**Nästa körning** (cirka 8 spår och 2–3 granskningar, ett 5-timmarsfönster, parallellt med webbsessionen och X5):

| Spår | Förslag | Storlek | Beror på |
|---|---|---|---|
| K1 källfamiljer och index v2 | 1 | 1 | beslutspunkt 2, samordning med webbsessionen |
| F1 revideringsindex | 2 | 1 + kort granskning | – |
| P1 avskrivningar och anläggningstillgångar (XBRL) | 3 | 1 | – |
| P2 nyttjandeperioder (extraktion med citat) och intäktskrav | 3 | 1 + R | P1 för intäktskravet |
| P3 förregistrering och backtest av N7 | 3 | 1 | P1, registerpost före körning |
| M1 BEA-bidrag och BLS (el, PPI) | 4 | 1 + R | – |
| M2 Census HS-import | 4 | 1 | Census-nyckel |
| L1 licenskartläggning för G8 (RPS, Economic Index, Indeeds yrken, BLS CES) | 5 | 1 | – |

**Körning 14, omprioriterad efter syftet (avsnitt 0):**

1. **Stackens saknade lager via SEC:** minne (Micron), nät (Arista), kraft och kylning (Vertiv, GE Vernova, Eaton: order och orderstock/RPO) och datacenterbolag (Equinix, Digital Realty). Det mesta går med befintlig XBRL-teknik (segment och RPO). Orderstock för kraft och kylning är en ledande indikator för den fysiska utbyggnaden. **Klart i körning 14:** S1 (nät, optik och servrar, [kallor/sec_stack_nat.md](kallor/sec_stack_nat.md)), S2 (kraft, kylning, elnät och datacenter, [kallor/sec_stack_kraft.md](kallor/sec_stack_kraft.md)) och S3 (order och orderstock ur 8-K, [kallor/order_orderstock.md](kallor/order_orderstock.md)). Micron fanns redan (`capex_mu`).
2. **Finansieringsskörhet** (förslag 8): spread vid emission, skuld, leasing utanför balansräkningen. **Spreaden vid emission är klar i körning 14** (KR1, [kallor/kredit_emission.md](kallor/kredit_emission.md), inhållen tills ägaren beslutar). **Skuld, leasing och capex-takt i de yttre lagren mot de inre följs från körning 15** som en följd fråga (KL1, [resultat/kreditlagret.md](resultat/kreditlagret.md), `publish=False`, rapport varje månad).
3. **Förmåga och kostnad** (förslag 6). De styr efterfrågan och var marginalerna hamnar i stacken. **Klart i körning 14:** Q1 ([kallor/g2_rorlig_troskel.md](kallor/g2_rorlig_troskel.md)) och Q2 ([kallor/g1_oppen_stangd.md](kallor/g1_oppen_stangd.md)). Kostnad per uppgift är BLOCKED.
4. **Kina via SEC** (förslag 7). **Klart i körning 14:** CN1 ([kallor/kina_sec.md](kallor/kina_sec.md)).
5. **Test av själva tillståndsregeln** (förregistrerat). **Klart i körning 14:** T1 ([resultat/t1_tillstandsregeln.md](resultat/t1_tillstandsregeln.md)). Inget positivt resultat (Holm-p 0,37), och regeln ändras inte.
6. **G8 v2** (förslag 5, efter L1). Den har lägre prioritet för syftet.
7. **Korea via ECOS**, när nyckeln finns.
8. **Följda frågor (antenner), körning 16.** Utöver KL1 finns nu följda frågor för ledtid i stacken (LT1,
   [resultat/ledtid.md](resultat/ledtid.md)), betalningsgapet (BG1, [resultat/betalningsgapet.md](resultat/betalningsgapet.md))
   och elen som begränsning (EL1, [resultat/elflaskhalsen.md](resultat/elflaskhalsen.md)), på en gemensam motor med
   symmetrisk läsregel (F0). En rad per fråga i [resultat/antenner.md](resultat/antenner.md), granskad i
   [granskning/r28_antenner.md](granskning/r28_antenner.md). Utslagen per 2026-11-26 är på sedda kvartal.
9. **Körning 17:** symmetriska rader bredvid de låsta (S1), Anthropics GAAP-tal i BG1 (AN1), Quantas förvärv i LT1:s märke (QA1) och pris mot volym som följd fråga (PV1, [resultat/prisvolym.md](resultat/prisvolym.md)), granskade i [granskning/r29_korning17.md](granskning/r29_korning17.md) och rättade i X26. Utslagen per 2026-11-27 är på sedda kvartal.

**Kalender som inte går att snabba på:** 2026-11-30 första ögonblicksbilden, 2026-12-05 första TSMC-prognosen med B3,
2027-01-20 första capex-prognosen, och Anthropics första periodiska rapport till SEC, som ger de första reviderade
intäkterna för ett frontlabb.

## 9. Beslutspunkter för Johannes

1. **Riktning:** pengarna, makron och förväntningarna först, och inga fler prognosmodeller utom N7.
   **Rekommendation: ja.**
2. **Index v2 med källfamiljer:** officiell regel från första skarpa ögonblicksbilden 2026-11-30, med v1 bredvid,
   eller bara som skugga? **Rekommendation: officiell från 2026-11-30.** Det skarpa registret börjar då, och att byta
   senare ger ett brott. Ändringen väljer ingen riktning. *Rättelse:* den gör inte tillstånden genomgående mer
   försiktiga. Se rättelsen i avsnitt 6, förslag 1. Johannes informerades 2026-11-24, och beslutet står.
3. **Licensnivå:** ska utdata kunna användas kommersiellt av en fond eller bank? **Rekommendation:** sidan förblir
   icke-kommersiell. Lägg till ett fält för kommersiell användbarhet per serie, och välj öppna licenser i nya spår,
   så att en kommersiellt ren delmängd alltid går att räkna fram.

## 10. Tokenekonomi: det som ger Johannes värde går först (beslutat 2026-11-25)

Projektet byggs i första hand för Johannes, inte för att spridas. Tokens ska därför gå till det han läser och
använder. De ska inte gå till att göra saker publicerbara utöver vad licenserna kräver.

**Var tokens gick i körning 13–14 (grov uppskattning):** bygga cirka 45 %, granska cirka 25 %, rätta cirka 20 % och
integrera cirka 10 %. Det publika repot (licensklasser, publiceringsgrindar, inhållna värden, fixturer, webbkontrakt)
stod för uppskattningsvis 15–25 %. Driften i CI kostar inga tokens. Undantaget är serier som extraheras ur text, eftersom
de kräver agentarbete varje kvartal.

**Värdefilter före varje spår:**
1. Ändrar det vad Johannes läser på sidan inom en månad? En katalogserie som inte visas ger inget värde ännu.
2. Är det ledande eller en överraskning (order, orderstock, guidance, capex, TSMC)? Eller är det släpande och finns
   redan fritt på annat håll?
3. Vad kostar det att hålla vid liv: gratis i CI (XBRL, API) eller tokens varje kvartal (extraktion ur text)?

**Regler från 2026-11-25:**
- **Granskning efter hur mycket Johannes förlitar sig på resultatet.** Full oberoende granskning görs för kärnserier,
  tillståndsregeln, prognoser och extraktioner som Johannes agerar på. Katalogserier får spårets egna kontroller och
  automatiska datatester. CLAUDE.md:s krav står kvar: stickprov för extraherade värden och ett granskningsspår per
  positivt resultat.
- **Färre och större spår,** 4–5 per körning, så att samordning och upprepad kontext kostar mindre.
- **Budget för löpande kostnad:** serier som kräver extraktion varje kvartal behålls bara om Johannes skulle sakna dem.
  Listan tas fram i nästa körning.
- **Användning loggas.** Tabellen "Värde för Johannes" i `docs/agentkalibrering.md` fylls i en månad efter leverans:
  används det, och vad betydde det? Det som inte används byggs inte vidare.

**Personligt läslager** (inga innehav i repot):
1. Först "mina lager" på sidan: Johannes väljer lager i webbläsaren och valet sparas bara lokalt. Det är billigt och
   kräver ingen ändring av licensreglerna.
2. Sedan en privat byggning för Johannes som också visar de inhållna serierna (personligt bruk, publiceras aldrig),
   till exempel som en privat sida.

**Nästa körning efter 14:** läsprodukten. En lagervy med "vad ändrades den här månaden" per lager i stacken, där ledande
signaler och överraskningar står först. Efter körning 14 finns det mesta av stacken som data, så fler serier ger mindre.
