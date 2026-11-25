// R-W3: the technical words the pages use, explained once on /metod#ordlista and linked where they stand
// (Term.svelte). Plain Swedish, no internal track or register codes.
export interface GlossaryEntry {
  id: string;
  term: string;
  text: string;
}

export const GLOSSARY: GlossaryEntry[] = [
  { id: 'diffusionsindex', term: 'Diffusionsindex', text: 'Hur stor del av en grens källor som ökar takten, från 0 till 1. Varje källfamilj har en röst: andelen av familjens serier som ökar takten, där oförändrad räknas som en halv. Indexet är medel av familjernas röster. 0,5 betyder lika mycket ökning som minskning.' },
  { id: 'kallfamilj', term: 'Källfamilj', text: 'Serier från samma källa som mäter samma sak och bara skiljer sig i land, delstat, kategori eller liknande, till exempel nio länder ur Indeeds platsannonser. De rör sig ofta tillsammans, så de får en röst tillsammans i indexet. Med färre än tre räknade familjer visas indexet men inget tillstånd: för få källor.' },
  { id: 'v1', term: 'Regel v1', text: 'Den första indexregeln: en röst per serie och minst tre serier för ett tillstånd ("för få serier"). Den visas bredvid som jämförelse. Från ögonblicksbilden i november 2026 är regeln en röst per källfamilj (v2).' },
  { id: 'dodband', term: 'Dödband', text: 'Gränsen för när en förändring i takt räknas. Inom ±0,25 standardavvikelser av seriens egen historik räknas takten som oförändrad (●), utanför som ökande (▲) eller minskande (▼).' },
  { id: 'percentil', term: 'Percentil', text: 'Var ett värde ligger i seriens egen historik fram till beräkningsdagen, 0–100. Percentil 95 betyder att 95 % av de tidigare värdena var lägre. Ytterzonerna är ≤ 5 och ≥ 95: där hamnar i snitt en av tio serier av en slump.' },
  { id: 'log100', term: 'log ×100 per år', text: 'Årsförändringen i den naturliga logaritmen gånger 100. För små tal är det ungefär procent per år (+10 ≈ +10,5 %). För stora tal blir procenten större (+69 ≈ +100 %, en fördubbling).' },
  { id: 'pe', term: 'Procentenheter (pe)', text: 'Skillnaden mellan två andelar som är angivna i procent. Från 20 % till 25 % är +5 procentenheter.' },
  { id: 'slumpband', term: 'Slumpband', text: 'Det område där en täckning hamnar 90 % av gångerna av ren slump, även när intervallen är perfekt kalibrerade.' },
  { id: 'pit', term: 'PIT', text: 'Var utfallet hamnade i den egna prognosfördelningen, från 0 (lägst) till 1 (högst). Med väl kalibrerade prognoser är PIT jämnt fördelad: medel 0,5 och varians 0,083.' },
  { id: 'crps', term: 'CRPS', text: 'Genomsnittligt avstånd mellan prognosfördelningen och utfallet, i målets enhet. Lägre är bättre: prognosen är både skarpare och träffsäkrare.' },
  { id: 'holm', term: 'Holm-justering', text: 'När många varianter prövas samtidigt justeras p-värdena uppåt (Holms metod), så att en av många inte ser bättre ut bara av en slump.' },
  { id: 'msih', term: 'MSIH(2)', text: 'En modell med två dolda tillstånd, var och ett med eget medel och egen varians. Den uppskattar varje månad sannolikheten att blocket ligger i en period med lägre takt (inbromsning) eller högre takt (expansion).' },
  { id: 'bocpd', term: 'BOCPD', text: 'En metod för strukturbrott: efter varje ny period skattas sannolikheten att takten nyss bytt nivå, alltså att den senaste "körlängden" är kort.' },
  { id: 'rekonstruerad', term: 'Rekonstruerad månad', text: 'Räknad i efterhand med dagens kod och dagens urval av serier, på data som var kända vid månadsslutet. Den är inte en skarp ögonblicksbild som sparades då, och den kan därför se säkrare ut än det som gick att se i realtid.' },
  { id: 'skarp', term: 'Skarp ögonblicksbild', text: 'Läget sparat och committat vid månadsslutet. Den skrivs aldrig om, eftersom tidsstämpeln är beviset.' },
  { id: 'molnbolag', term: 'De fyra största molnbolagen', text: 'Microsoft, Alphabet, Amazon och Meta (ibland kallade hyperscalers): de som bygger flest datacenter.' }
];

export const GLOSSARY_IDS = new Set(GLOSSARY.map((g) => g.id));
