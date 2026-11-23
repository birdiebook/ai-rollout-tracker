# Beslutslogg

## 2026-11-23 – Projektet startas

**Val:** eget publikt repo med fullt fokus på AI-utrullningen. Kopplingen till placeringar tas upp senare
och ligger då utanför repot. Spårningen är neutral, med takt och förändring i takt per gren (G1–G9) och
inga larmnivåer. Förregistreringen låser mått och beräkningssätt. Kodlicens MIT.
Plan: [plan.md](plan.md).

## 2026-11-23 – Fas 0: ramverket kopieras från kpif-nowcast

Katalog, versionerad observationstabell, publiceringskalender, DuckDB-datatester och utvärdering
(DM, Holm) kopierades och generaliserades. **Varför kopiera och inte paketera:** ett gemensamt bibliotek
ger beroenden mellan repona innan det är klart vad som faktiskt är gemensamt. **Viktigaste ändringen:**
blandade frekvenser och källdaterade rader. SEC:s companyfacts har en post per inlämnat dokument med
datum, vilket ger riktiga versioner från första hämtningen, till skillnad från SCB-backfillen i kpif-nowcast.
Detaljer: [plan.md](plan.md), avsnitt 7.

## 2026-11-23 – G2: pris vid fast förmåga byggs själva (fas 2, spår I6)

**Val:** `g2_price_at_capability` byggs av LiteLLM:s git-historik (MIT, commit-datum på `main` som
`known_from`) och Epochs ECI (CC BY), med bara förstapartspriser och en explicit mappningstabell. Tröskeln
141,16 (o1) låstes i måttregistret vid första bygget. **Varför förstapart:** återförsäljares priser för
öppna modeller beror på hosting och inte på modellen, och urvalet av återförsäljare i LiteLLM ändras över
tid. **Variant:** `g2_price_at_capability_gpqa` med Epochs egna GPQA-körningar har ärliga tidsstämplar för
förmågan, men är en brusig benchmark nära taket. Båda redovisas, och huvudmåttet är fortfarande ECI-varianten.
Detaljer: [kallor/pris_formaga.md](kallor/pris_formaga.md).
