# Källa: bolagens AI-nyckeltal (steg 2, spår B4)

Status: under arbete. Avsnittet "Kodningsregler" skrevs och committades **innan** någon kandidatmening kodades.

## Kodningsregler (låsta 2026-11-23, före kodningen)

### Gemensamt för alla nyckeltal

- **En rad per uttalat värde** i `curated/ai_kpis.csv`: siffra, enhet, typ (`point` = exakt, `approx` = "about",
  "approximately", "nearly"; `min` = "over", "more than", "surpassed", "exceeds"; `range`), definitionskod,
  period, `filed`, URL, accession, plats (`sentence #k` i `guidance_capex.sentences(tsmc_sec.to_text(doc))`),
  SHA-256 av meningen och en kort not. Meningen sparas bara i `data/raw/ai_kpis_sentences/<id>.txt`.
- **Definitionskod = serie.** Varje ändring av definitionen blir en ny kod och därmed en ny serie, även om bolaget
  kallar det samma sak: "monthly" mot "weekly" användare, "monthly active users" mot "users", tokens per månad mot
  tokens per kvartal, run-rate för "AI business" mot "AI revenue", Azure med och utan "other cloud services",
  tillväxt i rapporterad valuta mot konstant valuta. Serier med olika koder slås aldrig ihop.
- **Period.** Flöden som bolaget redovisar för ett kvartal (Azures tillväxt, tokens "this quarter") får
  kalenderkvartalet för räkenskapskvartalets mittpunkt (samma regel som `sec.calendar_quarter`; Microsofts FY Q1 =
  juli–sept = kalender-Q3). Ögonblicksvärden ("now", "currently", "as of", "surpassed") får **månaden** för det
  datum de avser: ett angivet datum eller en angiven månad om texten har det, annars kvartalets sista månad om
  texten säger "at the end of the quarter", annars dokumentets månad. Run-rate är ett ögonblicksvärde.
- **known_from** = dokumentets `filed` (EDGAR) eller, för Microsofts samtal, samma dag som 8-K:n med resultatet.
  Ett värde som upprepas i ett senare dokument ger ingen ny rad i serien (första dokumentet räknas). Ett värde som
  först nämns i ett senare dokument än det som det avser dateras till det senare dokumentet.
- **Bara bolagets egna siffror** om bolagets egna produkter. Siffror om kunder, partner, marknaden eller enskilda
  kundavtal (t.ex. OpenAI:s åtaganden) kodas inte. Procentuella andelar ("X % of the Fortune 500 use ...") kodas
  bara om de är ett återkommande nyckeltal.
- **Inga beräkningar.** Ett värde kodas så som det står. "Doubled" eller "up 5x" utan nivå kodas inte (det är en
  takt, inte en nivå). Tillväxttal kodas bara för Azure (där bolaget redovisar talet varje kvartal) och för molnet
  (Google Cloud, AWS), eftersom de är de uttryckliga nyckeltalen för L3.

### Kapacitetsuttalanden (−2..+2)

Avgränsning: uttalanden om **bolagets egen kapacitet för AI eller moln** (datacenter, GPU/accelerator, Azure, AWS,
Google Cloud; för Nvidia utbudet av datacenterprodukter) i förhållande till efterfrågan. Komponentbrist för annat
(spelkonsoler, PC, Surface, gaming-GPU, logistik) kodas inte. Allmänna ord om investeringar ("we are investing to
add capacity") utan ett påstående om balansen kodas inte.

| Kod | Regel | Exempel på ordalydelse |
|---|---|---|
| **+2** | Efterfrågan överstiger kapaciteten med en uttrycklig förstärkning, eller brist som uttryckligen begränsar intäkten kraftigt | "significantly capacity constrained", "demand significantly exceeds supply", "sold out", "well short of demand" |
| **+1** | Kapacitets- eller utbudsbegränsad, eller efterfrågan överstiger utbudet, utan förstärkning; också "we remain constrained", "constraints impacted revenue" | "capacity constrained", "demand continues to exceed supply", "supply constraints" |
| **0** | Uttryckligen i balans | "supply and demand in balance", "roughly in line with demand" |
| **−1** | Begränsningen är uttryckligen borta eller lättar så att den inte längre styr; "sufficient capacity" | "no longer capacity constrained", "constraints have eased", "we have enough capacity" |
| **−2** | Överkapacitet eller kapacitet som inte används | "excess capacity", "underutilized", "demand below supply" |

- **Tid.** `capacity_time = current` för läget nu eller under det redovisade kvartalet, `forward` för förväntningar
  ("we expect to remain capacity constrained through the fiscal year" = +1 forward, period = perioden som anges
  eller, om ingen anges, dokumentets kvartal). Läget nu och förväntningen är olika serier.
- **En kod per dokument, bolag och tid.** Har dokumentet flera meningar kodas den mening som är mest uttrycklig
  (högst absolutbelopp). Om meningar i samma dokument har olika tecken blir koden 0 och noten säger varför. Den kodade
  meningen sparas, de övriga meningarna räknas i noten.
- **Bristande omnämnande kodas inte.** Att ett dokument inte nämner kapacitet är ingen nolla, utan en lucka.
- **Riktning är inte beräknad**: koden anger vad bolaget säger, inte vår bedömning av läget.
- Period för `current`: kalenderkvartalet för det redovisade räkenskapskvartalet (för 8-K med resultat, 10-Q,
  10-K och samtal). För ett dokument utan redovisat kvartal (8-K Item 7.01/8.01): kvartalet för `filed`.

### Urval av kandidater

Brett, efter lärdomen R2-F1: en mening är kandidat om den har en siffra och ett nyckelord för AI, moln eller
användning (`KPI_RE` i `sources/ai_kpis_corpus.py`), eller om den nämner kapacitet, utbud eller begränsning
tillsammans med ord om efterfrågan, AI, moln eller datacenter (`CAPACITY_RE`), med eller utan siffra. Agenten läser
alla kandidater i de dokument som berörs. Antalet kandidater och kodade rader redovisas nedan.
