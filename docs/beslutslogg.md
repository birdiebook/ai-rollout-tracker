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

## 2026-11-23 – Fas 2, spår I4: Indeed, EIA och vast.ai

**Indeed (G8):** git-historiken i `hiring-lab/ai-tracker` används som vintagearkiv. `known_from` är
commit-tiden på standardgrenen (`--first-parent`) där värdet först fanns, och ändringar blir revideringar.
Bara rå dagdata lagras. Härledda mått kommer senare. **EIA (G7):** kommersiell elförsäljning i VA, TX,
GA, AZ, OR, OH och USA ur EPM:s arkivnummer (tabell 5.4.A) och EIA-861M. `known_from` är Last-Modified
+ 2 dagar, efter belägg att filer läggs upp dagen före release. 2010-01 till 2012-10 är backfill med
läckageflagga. **vast.ai (G6): BLOCKED.** Villkoren (version 2026-09-01) förbjuder automatiserad
insamling och prisindex utan skriftligt avtal, så ingen insamlare och inget dagligt arbetsflöde byggdes.
Detaljer: [kallor/indeed_vast_eia.md](kallor/indeed_vast_eia.md).
