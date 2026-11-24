# C4: teknisk specifikation för regim och strukturbrott

Tillägget till G-D enligt F-D7, F-E4 och F-E5 (`docs/granskning/r6_c0.md`, antagen ordagrant i måttregistret
2026-11-23). Skriven **2026-11-24, före den första körningen på verklig data** och innan holdouten har öppnats för C3
eller C4. Commit-hashen för den här filen är den daterade posten och C4:s lås. Efter den committen ändras ingenting
här. En ändring blir en ny metodfamilj (G-E), som bara utvärderas i det skarpa registret.

Tillägget gäller bara tekniska detaljer som G-D och F-D1–F-D8 inte avgör. Där registret är entydigt upprepas det här
bara för att specifikationen ska vara fullständig. Avviker texten nedan från registret gäller registret.

Före posten har ingen kod för C4 körts på verklig data. Inga faktorbanor, regimsannolikheter eller brott har beräknats
eller lästs. C3:s faktorbanor från C3:s utvecklingskörning har inte lästs av det här spåret.

Kod: `src/ai_tracker/regime/` (`ms.py`, `bocpd.py`, `realtime.py`, `guard.py`, `evaluate.py`).
Specifikationsversion i koden: `SPEC_VERSION = "c4-v1"`. Faktorerna kommer från C3 (`c3-v1`, `docs/steg2/c3_spec.md`).

## 1. Beräkningsdagar och data

- **Beräkningsdag** = sista dagen i en kalendermånad (F-D1). Månad t:s värden beräknas på t:s sista dag, på
  observationstabellen trunkerad till `known_from` ≤ dagen (`as_of(beräkningsdagen)`).
- **Utveckling:** beräkningsdagar 2012-01-31–2025-06-30, på tabellen med `known_from` ≤ 2025-06-30
  (`factor.guard.dev_table`). Första dagen är vald efter C3:s första capexfaktor (prognosdag 2012-02-05). Det är metadata,
  ingen faktorbana.
- **Holdout (G-E, F-E1, F-E2):** beräkningsdagar 2025-07-31–2026-10-31 (16 dagar). Den första skarpa ögonblicksbilden är
  2026-11-30, så holdouten slutar dagen före.
- **Skarpt:** från den första ögonblicksbilden efter att holdouten har öppnats. Det skarpa värdet lagras i
  ögonblicksbilden och räknas aldrig om (F-D1). Anslutningen till ögonblicksbilden byggs först då.

## 2. Markov-switching per faktorblock (G-D, F-D1, F-D3)

Ett block i taget, "capex" (capex och leverantörsled) och "demand" (efterfrågan), var för sig.

- **Indata:** på beräkningsdag d är serien y = C3:s **utjämnade faktorbana** för blocket, skattad på d
  (`factor.realtime.vintage(tabell, d).path[block]`, medelvärdet, inte variansen). Det är "faktorns hela historik som
  den är skattad på beräkningsdagen" (F-D3). Månad t:s faktorvärde på t:s sista dag är banans sista värde.
- **Historikens start:** den första månad där någon av blockets serier som ingick i skattningen på d har ett observerat
  z-värde (C3-panelen på d; ett kvartalsvärde räknas i sin observationsmånad, kvartalets sista månad). Banan före den
  månaden är bara en projektion av AR(1)-dynamiken utan data och används inte. Historiken går till och med d:s månad.
- **Krav:** blocket finns på d (C3: minst 2 valbara serier) och historiken har **minst 60 månader** (F-D3). Annars
  redovisas ingen sannolikhet den dagen (orsak lagras).
- **Modell MSIH(2)-AR(0):** y_t = μ_{S_t} + σ_{S_t} ε_t, ε_t ~ N(0, 1) oberoende, S_t ∈ {0, 1} en Markovkedja med fri
  övergångsmatris P (p_ij = P(S_t = j | S_{t−1} = i)). Inga AR-termer.
- **Startfördelning:** P(S_1 = j) = 0,5 för båda tillstånden, fast och inte skattad (gör EM exakt och monoton).
- **Skattning:** ML med EM (Baum–Welch: Hamilton-filter framåt, Kim-utjämnare bakåt), omskattad från samma start vid
  **varje** beräkningsdag på d:s bana. Ingen varmstart från en tidigare dag.
  - M-steg: μ_j = Σ γ_t(j) y_t / Σ γ_t(j); σ_j² = Σ γ_t(j) (y_t − μ_j)² / Σ γ_t(j), med golvet **0,01 × s²**;
    p_ij = Σ_{t≥2} ξ_t(i, j) / Σ_{t≥2} γ_{t−1}(i).
  - Startvärden (F-D3): μ = ȳ − s och ȳ + s, σ² = s² för båda, p_00 = p_11 = 0,95. ȳ och s (ddof = 1) över historiken.
  - Konvergens: |ΔlogL| < **1e-8 × (1 + |logL|)**, högst **1000** iterationer. `converged` och `n_iter` lagras.
    En skattning som inte konvergerar redovisas ändå, med flagga.
- **Etikett (F-D3):** efter skattningen kallas tillståndet med **lägre μ** inbromsning. C3 vänder faktorns tecken så
  att högre faktor = högre takt, så inbromsning = regimen med lägre takt.
- **Utdata:** P(inbromsning)_t = den **filtrerade** sannolikheten P(S_T = inbromsning | y_1..y_T) för historikens sista
  månad T = d:s månad (F-D1). Dessutom μ, σ, P, logL, antal månader och historikens första månad.

## 3. Rapporterat regimskifte (G-D, F-D2)

Per block, på följden av lagrade realtidsvärden (ett per beräkningsdag, aldrig omräknade):

- Det rapporterade tillståndet är **expansion** från den första beräkningsdagen med en sannolikhet. Före den finns
  inget rapporterat tillstånd.
- Skifte till **inbromsning** när värdena från två på varandra följande beräkningsdagar båda är ≥ 0,8. Skifte tillbaka
  till **expansion** när två på varandra följande värden båda är ≤ 0,2. Mellan 0,2 och 0,8 behålls tillståndet.
- En beräkningsdag utan sannolikhet bryter följden: de två dagarna måste vara närliggande månader och båda ha värden.
  Tillståndet behålls över en sådan dag.

## 4. BOCPD per kärnserie (G-D, F-D4, F-D5, F-D8)

- **Serier:** på beräkningsdag d de kärnserier som **räknas i tillståndet** den dagen, alltså `series_used` i
  `state.branch.branch(gren, d, ctx)` för G1–G9, med samma undantag som `state` (inaktuella, bakåtfyllda med spärr,
  mättade eller avslutade benchmarks, för kort historik). `ctx` byggs på tabellen trunkerad till `known_from` ≤ d.
- **Data:** takten ur `state.measures.measure_path(serie, d, ctx)`, en version, `as_of(d)` (fas 5:s tolkning 1). För G1 och
  G2 är takten fördubblings- respektive halveringstiden. Banan börjar vid den första perioden med takt och slutar vid
  seriens senaste period.
- **Standardisering (F-D5):** x = (takt − m) / s, där m och s (ddof = 1) räknas över alla taktvärden i banan på d
  (expanderande till och med d). Med färre än 2 värden eller s = 0 körs ingen BOCPD.
- **Modell (Adams–MacKay):** konstant hazard per period efter taktens frekvens (F-D4): **1/36** för månad, **1/12** för
  kvartal och **1/3** för år. Inom ett segment är x normalfördelad med okänt medel och okänd varians, med
  normal–gamma-priorn **μ0 = 0, κ0 = 1, α0 = 1, β0 = 1** (β som rate) (F-D5). Prediktiv fördelning: Student-t med 2α
  frihetsgrader, läge μ och skala² β(κ + 1)/(ακ).
- **Körlängd:** r_t = antal perioder i det pågående segmentet före period t (r_t = 0: segmentet börjar i t). Första
  perioden har r = 0. Rekursion: P(r_t = 0) ∝ H × Σ_r P(r_{t−1} = r) × π_prior(x_t), och P(r_t = r + 1) ∝ (1 − H) ×
  P(r_{t−1} = r) × π(x_t | segmentets tidigare värden). Körlängden räknas i seriens egna perioder: en period utan takt
  inne i banan (lucka) tillämpar bara hazard-steget, utan likelihood och utan att statistiken uppdateras. Ingen
  trunkering av körlängden.
- **Mått:** P(r_T ≤ 2 | x_1..x_T) vid seriens senaste period T (segmentet började i T, T − 1 eller T − 2).
- **Rapporterat brott (F-D4):** när P(r_T ≤ 2) ≥ **0,8** på beräkningsdag d, och inget brott har rapporterats för samma
  serie på en tidigare beräkningsdag med senaste period p′ där T − p′ ≤ 3 perioder (det innefattar samma period, som
  kvartals- och årsserier har på flera månadsdagar i rad). Bara lagrade realtidsvärden används.
- **Förhållande till tillståndet (F-D5, F-D8):** ett brott eller en regimsannolikhet påverkar **inte** diffusionsindex
  eller tillstånd i avsnitt 2. Avstämningsserierna (A5) ingår inte.

## 5. Holdouten och utvärderingen (G-E, F-D6, F-E3, F-E4, F-E6)

- `regime/guard.py`: samma vakt som C3 (`factor.guard.DEV_END = 2025-06-30`, undantaget `HoldoutClosed`) med en egen
  flagga `HOLDOUT_OPEN = False` för familjen C4. Varje MS-skattning, BOCPD-körning, rapporterat skifte eller brott och
  utvärdering med beräkningsdag efter 2025-06-30 ger `HoldoutClosed`. C3:s faktorer har dessutom C3:s egen vakt.
  Utvecklingskörningen läser bara rader med `known_from` ≤ 2025-06-30.
- Holdouten öppnas en gång för C4, i samma körning som C3 (STATUS), efter ägarens godkännande. Öppningen loggas i
  `docs/holdout_logg.md`.
- **C4 är beskrivande och befordras inte (F-D6).** Användning som variant kräver en egen G-B-post.
- **Utvärdering på holdouten** (beräkningsdagar 2025-07-31–2026-10-31), fastställd nu:
  - (a) **Frekvens:** per block antal rapporterade skiften till inbromsning och tillbaka, och antal månader i varje
    rapporterat tillstånd. För BOCPD antal rapporterade brott totalt, per gren och per serie, och brott per 100
    serie-beräkningsdagar.
  - (b) **Omklassning:** per block andelen beräkningsdagar i fönstret där det realtidsrapporterade tillståndet (avsnitt
    3) skiljer sig från det **utjämnade** tillståndet. Det utjämnade tillståndet = regeln i avsnitt 3 tillämpad på de
    utjämnade sannolikheterna P(S_t = inbromsning | hela historiken) från MS skattad på banan för fönstrets sista dag
    (2026-10-31), från historikens första månad. Samma etikettregel.
  - (c) **Samband med fel (bara information):** Spearmans ρ, och n, mellan P(inbromsning) per block på den senaste
    beräkningsdagen ≤ prognosdagen och huvudmodellens absoluta fel |e| för prognosen. Huvudmodeller vid låset:
    **N1 B1** och **N2 B3**. Prognoser med prognosdag i fönstret (F-E1, F-E2). Inget test avgör något.
- **Utvecklingsperioden** redovisar samma (a)–(c) på beräkningsdagarna till och med 2025-06-30, med (b) mot banan på
  2025-06-30 och (c) på utvecklingsraderna (prognosdag och utfall kända ≤ 2025-06-30). Ingenting justeras efter att
  utfallen har setts.

## 6. Utdata

- `regime.realtime.compute(tabell, d)` ger posten för en beräkningsdag: per block P(inbromsning) med parametrar och
  orsak när den saknas, och per räknad kärnserie P(r_T ≤ 2), senaste period, frekvens, hazard och antal perioder.
- `regime.realtime.run(tabell, start, slut)` ger följden av poster, och `regime.realtime.reported_states` och
  `reported_breaks` tillämpar reglerna i avsnitt 3 och 4 på den.
- `python -m ai_tracker.regime` kör utvecklingen. Resultaten cachas i `data/cache/regime/c4-v1/` och skrivs till
  `data/derived/c4/` (committas inte). Sammanfattningen står i `docs/resultat/c4_utveckling.md`.

## 7. Kända svagheter, redovisade i förväg

- **Autokorrelation (F-D5):** årstakt är kraftigt autokorrelerad (månad: MA(11), kvartal: MA(3)). BOCPD med oberoende
  normalfördelade observationer ger då fler brott än nominellt. G-D anger takten och alternativet med
  icke-överlappande förändringar är inte registrerat, så takten används och svagheten redovisas.
- **MS på nivån av en persistent faktor:** regimerna blir "lägre takt" och "högre takt", inte "fallande" och "stigande".
  Inbromsning kan alltså betyda en lägre men positiv takt.
- **Faktorbanan revideras:** varje beräkningsdag har sin egen bana (C3 skattas om). Den filtrerade sannolikheten är
  realtid med avseende på dagen, men historiken den skattas på är utjämnad över data kända den dagen.
- **Efterfrågeblocket** är i stort sett en interpolerad kvartalsfaktor fram till 2023 och finns först från 2020-06
  (C3). Historiken på 60 månader nås bara genom att `rev_aws` har z-värden från 2015.
- **Holdouten är delvis känd (F-E5):** baslinjefelen för 2025-07–2026-10 är publicerade, och de bakåtfyllda serierna har
  dagens vintage. Det gäller både faktorerna och BOCPD-serierna.
- **Litet antal regimer:** med 10–13 års månadsdata och persistenta regimer finns få skiften att lära av. Sambandet i
  (c) bygger på n = 6 (N1) och 16–17 (N2) på holdouten.
