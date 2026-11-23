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

## 2026-11-23 – Spår I3: Census, BEA, ALFRED, Eurostat och SCB

**Val:** regimbrott blir egna serier som aldrig skarvas. BTOS får tre serier: v1 "producing goods or services",
v2 "business functions" och v3 "Super Intelligence or SI (formerly … AI)" från cykel 202622. Det sista är ett
brott enligt frågeformuläret som fältades från 2026-10-19. SCB delas också i två serier, TAB6405 och TAB6814, i stället för att fogas
ihop, eftersom 2026 byter till NACE 2.1 och omfattar fler branscher. **Ny frekvens `2W`** (ISO-fjortondag) så att
`no_gaps` hittar saknade BTOS-cykler. **ALFRED** används för G.17 och M3 eftersom det ger riktiga vintages utan
nyckel och primärkällan inte nås: federalreserve.gov nekas, och api.census.gov kräver nyckel. ALFRED används också
som belägg för publiceringsdagar. **Beslutspunkt feb 2027:** BTOS byter exempel igen från cykel 202702, och
rekommendationen är en ny serie v4. Detaljer: [kallor/census_eu.md](kallor/census_eu.md).
