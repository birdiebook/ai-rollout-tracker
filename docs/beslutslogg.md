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

## 2026-11-23 – SEC-serier: kalendermappning, Amazons capex och omräkningar

**Kalenderkvartal = kvartalet som innehåller räkenskapskvartalets mittpunkt.** För MSFT, GOOGL, AMZN och
META är det samma som slutdatumets kvartal, eftersom alla deras kvartal slutar på kalenderkvartalets
sista dag. För Nvidia blir aug–okt Q3, så Nvidia ligger ungefär en månad efter. **Varför inte
slutdatum:** då blir aug–okt "Q4", och värdet blir känt före periodens slut, vilket bryter
läckagekontrollen.
**Amazons capex = brutto (`PaymentsToAcquireProductiveAssets`), från 2017Q3.** De äldre taggarna är
netto efter incitament, och en av dem bytte definition 2018. **Varför:** att skarva brutto mot netto
ger ett definitionsbrott, och bruttot matchar de andra tre bolagens rader. Därför börjar `capex_hyp4`
2017Q3. En nettoserie med historik från 2008 går att bygga om måttregistret väljer netto.
**Omräkningar som inte bryts ned per kvartal läggs inte i ett enda kvartal.** Kvartalet behåller då
sin tidigare version. Det är konservativt, och några helår summerar därför inte till det senaste
helårsvärdet. Detaljer: [kallor/sec.md](kallor/sec.md).
