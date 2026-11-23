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

## 2026-11-23 – Fas 2, spår I5: Epoch, METR och arXiv

**Val:** Benchmarkfronten lagras som en månadsserie, härledd as-of: bara körningar med `Started at` före månadens
slut räknas, och värdet får `known_from` = dagen efter månadsslut. Ändrade källvärden blir nya rader daterade
hämtdagen. ECI och modelldatabasen lagras som återfyllda serier (`source=backfill`) som de veckovisa
ögonblicksbilderna sedan bygger vidare på. arXiv räknas på **primär kategori**, eftersom API:ets `cat:` också
träffar korslistningar och saknar filter för primär kategori. Alla poster per månad hämtas därför och räknas,
och unionen inklusive korslistningar sparas som en egen serie. **Varför:** varje värde ska gå att spela upp
`as_of()` utan att en senare körning eller korslistning läcker in. Benchmarkurvalet följer regeln exakt. Problemet
med ersatta benchmarks är flaggat i måttregistret för beslut. Detaljer: [kallor/epoch_arxiv.md](kallor/epoch_arxiv.md).
