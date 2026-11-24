# Holdoutlogg

Register: `docs/mattregister.md` "Steg 2", G-E med R6 (F-E1–F-E6, F-D6) antagen ordagrant. Holdouten öppnas **en gång
per metodfamilj** (F-E3). En post skrivs och committas **innan** körningen. Efter öppningen ändras inte familjens
specifikation. En ändring blir en ny familj som bara utvärderas i det skarpa registret.

Ägarens godkännande: `docs/beslutslogg.md` 2026-11-24, "Holdouten öppnas för C3 och C4" (commit `ded90b7`).
Öppningen görs i **en körning för båda familjerna** (F-E4): `python -m ai_tracker.holdout`.

## C3 – faktormodellen, variant DF för N1–N4

- **Öppnas:** 2026-11-24T08:18:56Z (UTC), spår H1, gren `auto9/h1-holdout`.
- **Git-sha före öppningen:** `089f70a` (utvärderingskoden, vakterna stängda). Specifikationen är låst i `5431f41`
  (`docs/steg2/c3_spec.md`, `SPEC_VERSION = "c3-v1"`).
- **Vakt:** `factor/guard.py` `HOLDOUT_OPEN = True`. `OPEN_FAMILIES` förblir tom, så D2 är fortsatt stängd.
- **Vad som utvärderas:** DF per mål på holdouten = prognosdagar från 2025-07-01 till dagen före målets första skarpa
  prognosdag (F-E1, F-E2): N1 och N4 till 2027-01-19, N2 till 2026-12-04, N3 till 2027-02-13, med utfall (första
  versionen) kända vid körningen. Utvecklingen är den registrerade utvecklingskörningen (prognosdag och utfall
  ≤ 2025-06-30).
- **Regel (F-E6, F-B9, F-B10):** n < 8 på holdouten ger inget test, och DF går in som skugga i det skarpa registret
  (väntat för N1, N3 och N4). För n ≥ 8 (N2): DM-test på absolutfel mot jämförelsemodellen = den bästa efter MAE på
  samma holdoutrader av B0, B1 och B2 (den låsta specifikationen, avsnitt 6). Holm i steg 2-familjen {B3, DF} med B3:s
  p = 0,0294 från den registrerade körningen (`experiments/runs/20261124T005428Z_n2_tsmc.csv`). Godkänd = Holm-p < 0,10
  och lägre MAE än jämförelsemodellen både på holdouten och i utvecklingsperioden. Huvudmodellen byts bara om DF också
  slår nuvarande huvudmodell (N2: B3) i båda perioderna (F-B10), och först efter ett oberoende granskningsspår
  (CLAUDE.md). Ett godkänt resultat rapporteras därför som **villkorat**, och `n2.CHAMPION` ändras inte i den här
  körningen.
- **Skugga:** DF skrivs som skugga (`variants.DF` och blocket `df`) i de skarpa filerna för N1–N4.

## C4 – regim och strukturbrott

- **Öppnas:** 2026-11-24T08:18:56Z (UTC), i samma körning som C3.
- **Git-sha före öppningen:** `089f70a`. Specifikationen är låst i `735dc64` (`docs/steg2/c4_spec.md`,
  `SPEC_VERSION = "c4-v1"`).
- **Vakt:** `regime/guard.py` `HOLDOUT_OPEN = True`.
- **Vad som utvärderas (F-D6, c4_spec avsnitt 5):** beräkningsdagar 2025-07-31–2026-10-31 (16 månadsslut), med
  realtidsföljden beräknad från 2012-01-31 så att rapporterade tillstånd och brott bärs över från utvecklingen.
  (a) frekvens av skiften och brott, (b) andel dagar där realtidstillståndet skiljer sig från det utjämnade tillståndet
  från banan på 2026-10-31, (c) Spearmans ρ mellan P(inbromsning) och absolutfelen för N1 B1 och N2 B3 (prognosdagar
  i holdouten enligt F-E2), bara information. C4 är beskrivande och befordras inte.
- **Skarpt:** P(inbromsning) och brottsflaggor läggs i den månatliga ögonblicksbilden som en egen sektion
  (`regim_c4`, inte en del av grenarnas tillstånd) från den första ögonblicksbilden efter öppningen, 2026-11-30.

## Not om läckage (F-E5)

Holdouten är **delvis känd**: baslinjefelen för 2025-07–2026-10 är publicerade i `docs/resultat/n1.md`–`n4.md`, och de
bakåtfyllda serierna (`us_constr_datacenter`, importserierna, BEA, EIA före arkivet, npm, PyPI, Wikipedia) har dagens
vintage. En torrkörning av utvärderingskoden gjordes före öppningen bara på utvecklingsfönstret (tabellen trunkerad
till 2025-06-30, låtsad holdout 2024-01–2025-06). Den återgav utvecklingssiffrorna i `docs/resultat/c3_utveckling.md`
och `c4_utveckling.md` och läste ingenting efter 2025-06-30.
