# Hemsidan i världsklass: vision, forskning och byggplan

Skriven 2026-11-24 (spår W1). Den här texten lägger grunden för en ny hemsida. Den befintliga sidan
(`src/ai_tracker/site/`, `docs/drift.md` "Hemsidan") rörs inte. Riktlinjerna från Johannes: **visuellt driven,
data och insikter i bilder snarare än text, intuitiv, och inbjudande till vidare utforskning.**

Tre fungerande prototyper med riktig, licensgrindad data finns i `prototypes/hemsida/` (avsnitt 8). Där en princip
nedan har prövats i en prototyp står det.

**Källäge.** Nätverket i sessionen nekade WebFetch för nästan alla värdar (epoch.ai, ourworldindata.org,
pudding.cool, ciechanow.ski, atlantafed.org m.fl.). WebSearch fungerade och har använts för att kontrollera de
centrala påståendena (märkta **[S]**). Det som bygger på min egen kunskap om verken, utan att jag kunnat öppna sidan
i dag, är märkt **[K]**. Sidornas nuvarande utseende kan ha ändrats.

---

## 1. Vision och designprinciper

> **En sida där man på fem sekunder ser hur hela AI-flödet rör sig den här månaden, på en minut förstår varför, och på
> tio minuter kan gräva sig ned till varje serie, varje version och varje prognos, och se vad vi visste ett visst datum.**

Sidan konkurrerar inte med nyhetsflödet. Den är ett **instrument**: samma vy varje månad, så att förändringen syns.
Det som gör projektet unikt, och som sidan därför ska bära fram visuellt, är fyra saker som nästan ingen annan
AI-spårare har: (1) kedjan L1→L9 med avstämningar mellan leden, (2) förregistrerade tillstånd i stället för
tyckande, (3) nowcasts med intervall och ett öppet facit, och (4) versionerad data, så att man kan resa i tiden.

### Principerna

| # | Princip | Så i vår sida betyder det… |
|---|---|---|
| P1 | **Bilden först, texten förklarar bilden.** Varje sida öppnar med en visuell helhet, inte med ett stycke. | Startsidan öppnar med kedjan L1→L9 som bild. Rubriken är en mening som genereras ur samma data ("Av 7 grenar med tillstånd: 4 accelererar, 3 är stabila, ingen bromsar in"), inte en redaktionell text. Prövat i prototyp (a). |
| P2 | **Samma vy varje månad.** Ett instrument blir läsbart genom upprepning. | Positioner, färger och ordning (L1→L9, G1→G9) är fasta. Tillstånd byter färg, aldrig plats. Sidan ser likadan ut i november och i maj, och skillnaden är budskapet. |
| P3 | **Neutral visuell grammatik.** Riktning är inte värdering. | Blått = mer takt, orange = mindre takt, grått = balans. Aldrig grönt/rött, aldrig larmikoner. Varje färg har en glyf (▲ ● ▼) och ett ord bredvid sig. Formuleringar räknas fram ur data och säger "accelererar", inte "oroande". |
| P4 | **Osäkerhet syns alltid, och i frekvenser.** Ingen punktprognos utan intervall. | Intervall som staplade band (50/80/95), kvantilprickdiagram ("20 lika sannolika utfall") för enskilda prognoser, kalibrering mot nominell nivå med slumpband. Prövat i prototyp (c). |
| P5 | **Tiden är en dimension man kan resa i.** `as_of` är vår unika tillgång. | En global tidsreglage: "Vad visste vi den …". Varje vy kan visas som den var känd ett datum, och skillnaden mot i dag (revideringar) är en egen vy. Prövat i prototyp (b). |
| P6 | **Lager av djup, aldrig återvändsgränd.** Från blick till rådata i fyra steg. | Blick (5 s) → förstå (1 min) → utforska (10 min) → verifiera (metod, data, git-commit). Varje diagram har tabellvy, källa, licens, nedladdning och permalänk. |
| P7 | **Kedjan är ryggraden.** Navigeringen följer flödet från användning till el. | L1→L9 finns som minikarta överst på varje led-, gren- och seriesida. Man vet alltid var i kedjan man är och kan gå uppströms och nedströms. |
| P8 | **Annotera i diagrammet.** Förklaringen sitter där ögat redan är. | Händelser (rapporter, nya serier, regimbyten, registerändringar) är markörer på tidsaxeln. Gränserna 0,33 och 0,67 ritas in. Direktetiketter i stället för förklaringsrutor när det går. |
| P9 | **Ärlighet är en del av designen.** Status syns, inte bara i fotnoter. | "Rekonstruerad historik" och "skarp ögonblicksbild" har olika visuell form (streckad mot hel ram). Serier som hålls inne av licensskäl syns som räknade men namngivna rutor utan värden. Backtest märks alltid "inte en skarp prognos". |
| P10 | **Utforskande ska kännas som lek, inte som formulär.** | Direkt manipulation: dra i tiden, klicka i diagrammet för att resa dit, tryck "Spela" för att se historien rulla. Inga "Sök"-knappar för att uppdatera en vy. |
| P11 | **Allt går att dela och citera.** | Varje vy och tillstånd har en URL (`#as_of=2023-06-30&serie=us_ip_semis_m`), en genererad delningsbild och en citeringsrad med datum och version. |
| P12 | **Snabb, tillgänglig och mobil först.** | Startsidan under 150 kB JavaScript (gzip), diagram som SVG redan i HTML, WCAG 2.2 AA, tangentbord, minskad rörelse respekteras, ljust och mörkt läge som egna, validerade paletter. |

---

## 2. Inspirationskatalog

### 2.1 Tabell (34 exempel)

| # | Exempel | Länk | Teknik | Lärdom för oss |
|---|---|---|---|---|
| 1 | Our World in Data, Grapher **[S]** | ourworldindata.org/owid-grapher | Samma komponent för alla diagram: flikar för diagram/tabell/karta, källflik, nedladdning, inbäddning, URL-tillstånd | En enda seriekomponent för ~475 serier, med tabell, källa, licens, nedladdning och permalänk på varje |
| 2 | Our World in Data, AI-ämnessidan **[K]** | ourworldindata.org/artificial-intelligence | Ämnessida med nyckelinsikter som var och en är ett diagram, sedan fördjupning | Varje gren- och ledsida öppnar med 3–5 "nyckelbilder", inte en lista av serier |
| 3 | Epoch AI, Trends **[S]** | epoch.ai/trends | "Ett tal"-rutor med tillväxt i flera enheter (×/år, fördubblingstid, storleksordningar), citeringsknapp | G1 och G2 som stora tal (fördubblings- och halveringstid) med enhetsväxlare och färdig citering |
| 4 | Epoch AI, Data Hub **[S]** | epoch.ai/data | Databaser med insikter, interaktiva vyer och dokumentation om insamling | Varje serie har en "så här samlas den in"-del med `known_from`-regel och licens |
| 5 | New York Fed Staff Nowcast **[S]** | newyorkfed.org/research/policy/nowcast | Nowcastens utveckling under kvartalet och staplar för hur varje veckas datasläpp flyttade den | Visa *varför* en nowcast ändrades: bidrag per indikator (N1:s brygga, faktormodellen DF) |
| 6 | Atlanta Fed GDPNow **[K]** | atlantafed.org/cqer/research/gdpnow | Nowcastens väg mot konsensusintervallet, separat sida för track record, arkiv | Jämför alltid mot baslinjen (bolagens guidance) i samma diagram, och ha en egen facitsida |
| 7 | ALFRED, St. Louis Fed **[K]** | alfred.stlouisfed.org | Arkiv av datavintages: välj version och se serien som den publicerades | Vår `as_of` är samma idé, men vi gör den visuell och global för hela sidan |
| 8 | FT Covid-spåraren (John Burn-Murdoch) **[S]** | ft.com (2020–2022) | Logskala, gemensam startpunkt, referenslinjer för fördubbling varje dag/vecka/månad, daglig uppdatering, läsarförslag in i nästa version | Referenslinjer för fördubblingstid i G1/G2; logskala som standard för exponentiella storheter; iterera öppet |
| 9 | Ed Hawkins, #ShowYourStripes **[K]** | showyourstripes.info | Hela historien som en rad färgade streck, utan axlar | Tillståndsränder per gren och månad: hela historiken i en blick, och en delbar bild. Prövat i prototyp (a) |
| 10 | NYT Upshot, valnålen **[S]** | nytimes.com (2016–2020) | Osäkerhet som rörelse (jitter mellan 25:e och 75:e percentilen); kritik; 2018 gick jittret att stänga av, 2020 rörde sig nålen bara med ny data | Osäkerhet ska synas men inte stressa. Rörelse bara när data ändras. Föredra statiska frekvensbilder |
| 11 | FiveThirtyEight 2020, "ball swarm" **[S]** | fivethirtyeight.com/features/how-we-designed-the-look-of-our-2020-forecast | 100 representativa utfall som prickar; hover visar kartan i den simuleringen | Frekvensformat för sannolikheter: prickar i stället för en procentsats |
| 12 | Kay m.fl., "When(ish) is my bus?" **[S]** | idl.uw.edu/papers/when-ish-is-my-bus | Kvantilprickdiagram: lägre varians i sannolikhetsbedömningar än täthetskurvor | Standardvisning av en nowcast: 20 prickar. Prövat i prototyp (c) |
| 13 | Hullman/Kale, Hypothetical Outcome Plots **[S]** | hullmanlab.northwestern.edu | Animerade dragningar ur en fördelning | Som tillval för scenarier och regimsannolikhet, aldrig som standard (jfr nålen) |
| 14 | Kale, Kay, Hullman 2020 **[S]** | arxiv.org/abs/2007.14516 | Jämförelse av åtta osäkerhetsvisningar | Ingen enskild form är bäst för både storlek och beslut: kombinera intervallband och prickdiagram |
| 15 | The Economist, överdödlighetsmodellen **[S]** | economist.com (2021–) | Central skattning plus intervall; intervallet blir bredare där data är gles; länder utan data flaggas | Låt intervallbredden visa datakvalitet, och visa uttryckligen var data saknas |
| 16 | Bret Victor, "Up and Down the Ladder of Abstraction" **[S]** | worrydream.com/LadderOfAbstraction | Rör sig mellan abstraktionsnivåer med länkade kontroller | Index → serier → versioner av en serie, med samma tidsreglage på alla nivåer |
| 17 | Bret Victor, "Explorable Explanations" **[S]** | worrydream.com/ExplorableExplanations | Aktiv läsning: texten innehåller reglage | Metodsidan som utforskbar: dra i tröskeln och se tillståndet ändras |
| 18 | Bartosz Ciechanowski **[K]** | ciechanow.ski | Inbäddade interaktiva figurer som bygger upp förståelsen steg för steg | Förklara diffusionsindex och kalibrering med små figurer som byggs upp, inte med formler |
| 19 | Nicky Case **[S]** | ncase.me, explorabl.es | Lek först, förklaring sedan | "Spela"-knappen på tidsresan: historien rullar, användaren ser mönstret själv |
| 20 | Distill.pub **[S]** | distill.pub/2020/communicating-with-interactive-articles | Interaktiva artiklar som citerbar forskning; "research debt" | Metod och resultat (`docs/resultat/`) som citerbara, versionerade sidor med figurer |
| 21 | The Pudding **[K]** | pudding.cool | Visuella essäer med scrollytelling, en fråga per berättelse, Svelte-baserad mall | Månadsbrevet som scrollande berättelse: en fråga, 3–5 bilder, samma komponenter som instrumentet |
| 22 | NYT Graphics, annoteringslager **[K]** | nytimes.com/spotlight/graphics | Förklaringar skrivna direkt in i diagrammen, kort text vid datapunkten | Händelsemarkörer och korta etiketter i diagrammen i stället för fotnoter |
| 23 | Bloomberg Graphics, Billionaires Index **[K]** | bloomberg.com/billionaires | Daglig automatisk uppdatering, rik rad per enhet med spark-linje | Mallar som fylls helt automatiskt från pipelinen, varje rad med mini-diagram |
| 24 | Reuters Graphics **[K]** | graphics.reuters.com | Rena kartor och förklaringar, metodruta per grafik | Varje grafik har en kort "så gjorde vi"-ruta |
| 25 | FT Visual Vocabulary **[K]** | ft-interactive.github.io/visual-vocabulary | Diagramval utifrån relationstyp (förändring över tid, avvikelse, fördelning …) | Vår diagramgrammatik i avsnitt 4 är ett eget "visual vocabulary" per datatyp |
| 26 | Nadieh Bremer (Visual Cinnamon) **[S]** | visualcinnamon.com | Skräddarsydda, organiska former; skönhet som första hindret att passera | En signaturbild (kedjan) får vara skräddarsydd. Resten är standardformer |
| 27 | Federica Fragapane **[S]** | behance.net/FedericaFragapane | Minimala former och linjer som bär berättelser; förklaringen är en del av bilden | Glyfer (▲ ● ▼, enhetsrutor) som både data och förklaring |
| 28 | Giorgia Lupi, "Data humanism" / Dear Data **[K]** | giorgialupi.com | Små data, kontext och det kvalitativa runt siffrorna | Varje tillståndsbyte får en kort kontextrad (vilka serier vände) |
| 29 | Moritz Stefaner / Truth & Beauty, OECD Better Life Index **[K]** | oecdbetterlifeindex.org, truth-and-beauty.net | Användaren viktar dimensionerna själv; glyfer ("blommor") per land | Låt användaren filtrera vilka serier som räknas i ett utforskningsläge, tydligt skilt från det registrerade indexet |
| 30 | Shirley Wu **[S]** | shirleywu.studio | Börja i datautforskning, inte i kod; skräddarsydda glyfer | Prototyper med riktig data innan designsystemet låses (det här spåret) |
| 31 | Gapminder Trendalyzer (Hans Rosling) **[K]** | gapminder.org/tools | Tidsreglage med uppspelning och spår | Uppspelning och "spår" av tidigare positioner i tillståndsdiagrammen |
| 32 | Stanford AI Index **[K]** | aiindex.stanford.edu | Årsrapport med kapitel och nedladdningsbara data | Vi skiljer oss genom månadsfrekvens, `as_of` och prognoser med facit |
| 33 | State of AI Report **[K]** | stateof.ai | Årliga förutsägelser som poängsätts året efter | Offentligt facit för egna prognoser är trovärdighet. Scorecard på framträdande plats |
| 34 | Observable Framework och Mosaic **[S]** | observablehq.com/framework, idl.uw.edu/mosaic | Statisk sajt med dataladdare; länkade vyer över stora tabeller med DuckDB-WASM i webbläsaren | Utforskningsläget kan fråga de publicerade aggregaten direkt i webbläsaren, utan server |

### 2.2 Fördjupningar: varför de fungerar

**A. Our World in Data, Grapher.** Styrkan är inte ett enskilt diagram utan att *alla* diagram är samma komponent.
Läsaren lär sig gränssnittet en gång: diagram, tabell, karta, källor, ladda ned, dela. Varje tillstånd (land, år,
flik) ligger i URL:en, så att en länk återger exakt vyn. Källan står alltid vid diagrammet. **För oss:** en
seriekomponent ("serieinstrumentet") som visar nivå, takt, förändring i takt och versioner för vilken som helst av
de ~475 serierna, med licensgrind inbyggd. En agent kan bygga den en gång. Därefter får varje ny serie i katalogen en
sida utan extra arbete.

**B. NY Fed Staff Nowcast och GDPNow.** Två idéer gör dem till förebilder för vår prognossida. Den första:
nowcasten visas som en *väg* över tiden, där varje uppdatering är en punkt, så att man ser hur bilden förändrades
när ny data kom. Den andra: NY Fed delar upp varje veckas förändring i bidrag från datasläppen (överraskning ×
vikt), färgkodade per kategori, och staplarna summerar till veckans revidering **[S]**. GDPNow ställer dessutom
nowcasten mot konsensusintervallet och har en separat sida för hur modellen träffat historiskt **[K]**. **För oss:**
för N1 (brygga) och DF (faktormodell) går bidragen per indikator att räkna. Prognossidan visar vägen från första
indikatorn till prognosdagen, staplar för bidragen och guidance-intervallet som referens. Facit är en egen vy.

**C. FT:s Covid-spårare.** Burn-Murdoch valde logskala för att spridningen var exponentiell och menade att oron för
att läsare inte förstår logskalor var överdriven. Referenslinjer för "fördubbling varje dag, vecka, månad" gav
skalan mening **[S]**. Spåraren ändrades löpande efter läsarnas förslag. **För oss:** G1 och G2 mäts redan som
fördubblings- och halveringstid. Diagrammen får referenslinjer för till exempel "halvering var 6:e / 12:e månad",
så att lutningen kan läsas utan siffror. Förändringar i diagrammen loggas öppet, på samma sätt som registret.

**D. Osäkerhet: valnålen, 538 och kvantilprickdiagram.** Nålen visade att rörelse gör osäkerhet konkret men också
ångestframkallande. Kritiken ledde till att jittret blev valbart och sedan bara följde ny data **[S]**. 538 gick 2020
till 100 utfall som prickar **[S]**. Forskningen (Kay m.fl. 2016, Kale m.fl. 2020) visar att kvantilprickdiagram ger
mest träffsäkra uppskattningar av sannolikheter, men att ingen form är bäst för allt **[S]**. **För oss:** en nowcast
visas med två samverkande former: staplade intervallband över tid (för mönstret) och 20 prickar för den aktuella
prognosen (för sannolikheten). Ingen rörelse som inte motsvarar ny data. Prövat i prototyp (c), där prickdiagrammet
direkt visar "6 av 20 prickar under utfallet".

**E. Ed Hawkins klimatränder.** Ingen axel, ingen text, bara färg per år, och ändå förstår alla. Formen är så enkel
att den blev en symbol som delas. **För oss:** diffusionsindex per gren och månad som ränder (blått–grått–orange).
Prototyp (a) visar att den här bilden ensam berättar historien 2023–2026: G4, G5 och G8 skiftar från orange till blått,
G3 går åt andra hållet 2024. Den blir också sidans naturliga delningsbild.

**F. Explorable explanations (Victor, Ciechanowski, Case).** Läsaren förstår en modell genom att röra den. Victors
abstraktionsstege rör sig mellan en enskild körning och hela parameterrymden med länkade kontroller **[S]**. **För
oss:** metodsidan ska inte vara en text om diffusionsindex utan en figur där man drar i dödbandet (0,25 sd) och ser
seriernas riktning och grenens tillstånd ändras, och en figur där intervallnivån dras och täckningen ritas om. Det
gör förregistreringen begriplig: man ser varför tröskeln låstes innan data sågs.

**G. Epoch AI Trends.** Den AI-specifika förebilden. Stora tal överst, tillväxt i flera enheter som man växlar mellan,
och citering med ett klick **[S]**. Siffrorna uppdateras och skiljer sig mellan ögonblicksbilder, vilket är en
påminnelse om att datum och version måste stå vid varje tal **[S]**. **För oss:** "ett tal"-rutor för G1/G2 och för
avstämningarna, alltid med `known_from` och version, och med länk till "så såg talet ut för en månad sedan".

**H. ALFRED och vintages.** Ekonomer har länge kunnat hämta "data som de var kända då" men nästan aldrig *se* det.
Vår tabell har samma information för alla serier. **För oss:** det här är sidans mest originella möjlighet.
Prototyp (b) visar det på riktigt: enligt versionen från 30 juni 2023 var takten i amerikansk halvledarproduktion
(Fed G.17) −4,4 för december 2022. Enligt dagens version är den +4,8. Revideringsbilden (en tunn linje per
månadsversion) visar hur uppfattningen flyttade sig, och det är en insikt man inte får någon annanstans.

---

## 3. Informationsarkitektur

### 3.1 Ingången: "AI-flödet denna månad"

Startsidan svarar på de tre frågorna i en bild, uppifrån och ned. Prototyp (a) är en tidig version.

1. **Rubrik som mening ur data**, med månadsetikett och status ("skarp ögonblicksbild" eller "rekonstruerad
   historik"). Under den en rad om vad som ändrades sedan förra månaden.
2. **Kedjan L1→L9** som signaturbild. Varje led visar tillstånd (färg + glyf + ord), en ruta per räknad serie
   (▲ ● ▼, enhetsdiagram), diffusionsindex 24 månader bakåt med gränserna inritade, och vilka nowcasts som hör till
   ledet. Ledet är klickbart.
3. **Tre frågekort:**
   - *Var står vi nu?* Diffusionsindex per gren som prickar på 0–1, med förra månaden som ring och en linje mellan:
     läget och förändringen i samma bild.
   - *Vart är vi på väg?* Kalendern för skarpa prognoser som tidslinje, senaste skarpa prognos med intervall
     (kvantilprickar) och kalibreringen i en rad.
   - *Har något fundamentalt ändrats?* Regimsannolikheten per block som en mätare 0–100 % med den registrerade
     tröskeln, strukturbrott som markörer, och avstämningarna mellan leden som "var ligger takten i sin egen historik".
4. **Tillståndsränderna** (gren × månad) för hela historiken.
5. **Månadens berättelse:** ingång till månadsbrevet (3.4).

### 3.2 Kedjan som ryggrad

```
/                         Läget: kedjan, tre frågor, ränder, månadens berättelse
/flode/L1 … /flode/L9     Ett led: grenarnas tillstånd, nyckelserier, nowcasts, avstämningar uppströms/nedströms
/gren/G1 … /gren/G9       En gren: index över tid, alla kärnserier som små multiplar, ej räknade och inhållna serier
/serie/<nyckel>           Serieinstrumentet: nivå, takt, förändring i takt, versioner, källa, licens, nedladdning
/prognos/n1 … /prognos/n6 En nowcast: nästa prognos, väg mot prognosdagen, bidrag, band över tid, kalibrering, facit
/avstamning/<nyckel>      En avstämning: kvoten, dess komponenter (länkar till serierna) och tolkningen av ett glapp
/regim                    Regimsannolikhet per block, strukturbrott, metod
/brev/<YYYY-MM>           Månadens berättelse (scrollytelling)
/rapport/<YYYYqN>         Kvartalsrapporten
/metod                    Utforskbar metod: register, tillstånd, intervall, as_of, licenser
/data                     Nedladdning (publicerbara aggregat), frågor i webbläsaren, schema
```

Varje led-, gren- och seriesida har kedjan som **minikarta** överst (nio små rutor i tillståndsfärg, aktuellt led
markerat). Brödsmulor följer L → G → serie. En sökruta (⌘K) når alla serier, nowcasts och avstämningar via namn,
nyckel, källa och gren.

### 3.3 Lager av djup

| Lager | Tid | Fråga | Form |
|---|---|---|---|
| 0 Blick | 5 s | Hur rör sig flödet? | Kedjan, rubrikmeningen, ränderna |
| 1 Förstå | 1 min | Varför? Vilka serier, vilket led? | Ledsidor, frågekort, annoteringar, tooltips |
| 2 Utforska | 10 min | Hur såg det ut förut, vad visste vi då, hur bra är prognoserna? | Tidsresa, jämförelser, filter, revideringar, kalibrering |
| 3 Verifiera | obegränsat | Kan jag lita på det? | Metod, register, `known_from`, git-commit för varje ögonblicksbild, data att ladda ned |

Regel: varje element på ett lager länkar till nästa. Inget diagram slutar i en återvändsgränd.

### 3.4 Ögonblicksbilder, brev och nowcasts blir berättelser

- **Månadens berättelse** genereras från ögonblicksbilden. Urvalet av vad som lyfts fram följer en **förregistrerad
  regel**, inte redaktionellt omdöme, så att sidan inte väljer berättelser efter riktning: (1) alla tillståndsbyten,
  (2) de tre serier vars förändring i takt flyttat sig mest i percentil, (3) nya utfall mot nowcast (överraskningar),
  (4) de största revideringarna, (5) nya serier och datakällor. Regeln läggs i måttregistret innan den används.
- Varje punkt blir ett **kort** med samma komponent som på instrumentet (ingen specialgrafik), en mening genererad
  ur data, och länk till den levande vyn med `as_of` satt till ögonblicksbildens datum.
- Brevtexten (`ai_tracker.letter`) ligger som scrollande berättelse: texten till vänster, diagrammet fast till höger
  och uppdaterat steg för steg (The Pudding). På mobil kommer bilden före texten för varje steg.
- **Nowcasts blir berättelser i tre akter:** före (prognosen med intervall och kalender), utfallet (var det landade i
  prickdiagrammet) och efter (scorecard och kalibrering uppdaterade). Varje skarp prognos får en permanent sida med
  commit-länk, eftersom tidsstämpeln är beviset.
- **Kvartalsrapporten** blir en längre visuell essä med samma komponenter, och samma URL-tillstånd, så att varje
  figur kan öppnas som levande vy.

---

## 4. Visuellt språk

### 4.1 Diagramgrammatik per datatyp

| Datatyp i projektet | Primär form | Sekundär/fördjupning | Undvik |
|---|---|---|---|
| **Nivå** (capex, intäkter, volymer) | Linje, logskala för exponentiella storheter, med händelsemarkörer | Stapel per kvartal för flöden | Dubbla y-axlar (två skalor i ett diagram) |
| **Takt** (årsförändring i log ×100) | Linje kring nollinje, nollan som tydlig baslinje | Percentil av egen historik som prick på 0–100 | Att färga linjen efter tecken (blandar takt och förändring i takt) |
| **Förändring i takt** | Pil eller linje från takt för 6 mån sedan till nu ("slope"), riktning ▲ ● ▼ med dödbandet inritat | Små multiplar per serie i grenen | Ensamt tal utan referens |
| **Fördubblings-/halveringstid** (G1, G2) | "Ett tal" + logdiagram med referenslinjer (6/12/24 mån) | Förändring i fördubblingstid mot 12 mån sedan | Linjär skala för exponentiella förlopp |
| **Diffusionsindex** | Prick på 0–1 med banden 0,33/0,67 inritade; linje över tid; ränder för historik | Enhetsdiagram (en ruta per serie, ▲ ● ▼) | Mätare/speedometer (antyder bra/dåligt) |
| **Tillstånd** | Färg + glyf + ord, alltid alla tre | Ränder gren × månad | Trafikljus |
| **Intervall och nowcast** | Staplade band 50/80/95 och prognosstreck, utfall som prick (fylld inom 80 %, ring utanför) | Kvantilprickdiagram (20 prickar) för en enskild prognos; vy "avvikelse från prognos i %" | Punktprognos utan intervall |
| **Kalibrering** | Täckning per nivå som prick mot nominellt streck och binomialband | PIT-histogram mot jämn fördelning; CRPS per modell som prickdiagram | Att rangordna modeller utan att visa urvalsstorlek |
| **Regimsannolikhet** | Area 0–100 % över tid med den registrerade tröskeln, en rad per block | Glidande sannolikhet som ränder; strukturbrott som markörer på serierna | Larmröda zoner |
| **Avstämningskvoter** | Kvoten över tid med komponenterna som små multiplar under; percentil-prick för "var i historiken" | Uppdelning i täljare och nämnare (indexerade till samma bas på en axel) | Två axlar för täljare och nämnare |
| **Nowcast mot utfall** | Väg från första indikator till prognosdag, utfallet som slutpunkt; guidance-intervallet som referens | Bidrag per indikator (staplar som summerar till revideringen, NY Fed) | Att visa backtest utan märkning |
| **Revideringar och versioner** | En tunn linje per version (äldre ljusare), versionen på datumet tjock, dagens streckad | Revisionstriangel (period × version) som värmekarta; antal reviderade månader | Att bara visa senaste versionen |
| **Inhållna serier** (publish=False) | Räknade rutor utan värde, med namn och skäl | Länk till licensstatus | Att dölja att de räknas |

### 4.2 Osäkerhet

- **Alltid intervall.** Tre nivåer (50/80/95) som band av samma färg med fallande täckning, aldrig tre färger.
- **Frekvens före procent.** "14 av 18 utfall inom 80 %-intervallet", "6 av 20 prickar under utfallet".
- **Bredd = kunskap.** När intervallet är brett är det budskapet. Prototyp (c) visar att B3:s intervall för N2 är
  lika breda 2024 som 2026, eftersom felpoolen går tillbaka till 2007, medan de senaste årens fel är små. Det syns
  direkt i bilden och är ett ärligt underlag för en framtida registrerad ändring, inte något sidan ska dölja.
- **Små urval märks.** Under ~12 skarpa utfall står "för få utfall för att bedöma kalibreringen" vid facit.
- **Rekonstruerat mot skarpt.** Rekonstruerade månader ritas med streckad ram eller lägre mättnad, skarpa med hel.

### 4.3 Annotering

- Händelsemarkörer på tidsaxeln: kvartalsrapporter, nya serier i registret, registerändringar, regimbyten och
  skarpa prognoser. Markörerna kommer ur pipelinen (register, kalender i `publication.py`), inte för hand.
- Direktetiketter vid linjens slut i stället för förklaringsruta, högst fyra etiketter per diagram.
- Varje diagram har en genererad mening i klartext ("Takten var +43,6, den 94:e percentilen") som också är dess
  tillgänglighetsbeskrivning.

### 4.4 Färgsystem

Neutralt, tillgängligt och validerat (datavisualiseringsskillens validerare, OKLab):

| Roll | Ljust | Mörkt | Användning |
|---|---|---|---|
| Mer takt (accelererar) | `#2a78d6` | `#3987e5` | Riktning uppåt, index mot 1 |
| Mindre takt (bromsar in) | `#c25a00` | `#d46600` | Riktning nedåt, index mot 0 |
| Balans (stabil) | `#8a8880` | `#8f8d85` | Riktning 0 |
| Divergerande mittpunkt | `#f0efec` | `#383835` | Index 0,5 |
| Modell och intervall | `#6250d6` | `#9085e9` | Prognos, band (50/80/95 med opacitet) |
| Naiv baslinje | `#5e5d58` | `#bdbbb2` | B0/B1 |

Paret blått/orange klarar alla kontroller i båda lägena: CVD ΔE 26,7 (ljust) och 27,5 (mörkt), normalseende ΔE
30,9/31,8, kontrast ≥ 3:1 mot ytan. Ändrat 2026-11-25 efter R-W3: orange i ljust läge ligger lika långt från mitten
som blått (39,6 mot 41,2, förut 35,1), mörkt orange har nyansen 51° i stället för 40° (drog mot rött), och den naiva
baslinjen har en egen grå (ΔE 14,8 mot stabil, förut 0,4). Grönt och rött används aldrig för riktning (de betyder bra och dåligt). Serie-
identitet i små multiplar bärs av rubriken, inte av färg, så att blått och orange bara betyder riktning. Mörkt läge
är en egen vald palett, inte en automatisk invertering. Mönster (45°-linjer) som alternativ kanal för utskrift och
`forced-colors`.

### 4.5 Typografi

- Systemets sans-serif (`system-ui`) för allt, inga typsnitt från externa värdar. Tabellsiffror
  (`font-variant-numeric: tabular-nums`) i alla tal som jämförs.
- Svensk talformatering: mellanslag som tusentalsavgränsare, komma som decimaltecken, äkta minustecken (−).
- Skala: rubrikmening 26–40 px (flytande), sektionsrubrik 20 px, brödtext 16 px, diagramtext 11–13 px.
- Ett tal per "ett tal"-ruta, 34–52 px, med enhet och datum i liten text intill.

### 4.6 Rörelse

- **Rörelse förklarar förändring, aldrig dekoration.** Övergångar (200–400 ms) när ett tillstånd ändras eller när
  tidsreglaget flyttas, så att ögat kan följa samma punkt.
- **Uppspelning bara på användarens initiativ** ("Spela"), aldrig autostart.
- **Ingen jitter eller pulsering** för osäkerhet (lärdomen från valnålen).
- `prefers-reduced-motion`: alla övergångar blir omedelbara.

---

## 5. Interaktionsmönster för utforskning

| Mönster | Beskrivning | Var |
|---|---|---|
| **Tidsresa** (`as_of`) | Globalt reglage "Vad visste vi den …" med dag som upplösning, knappar ±1 månad, "I dag" och "Spela". Allt som visas filtreras på `known_from ≤ datum`. Framtiden efter datumet tonas ned men visas som "dagens version" för jämförelse | Alla sidor. Prövat i prototyp (b) |
| **Ögonblicksbild som tidsresa** | För tillstånd och index: välj månad och se den committade ögonblicksbilden exakt som den publicerades, med commit-länk | Startsidan, gren- och ledsidor |
| **Revideringsvy** | Tunn linje per version, versionen vid datumet tjock, dagens streckad; antal reviderade månader | Seriesidan, gren-multiplar. Prövat i prototyp (b) |
| **Klicka för att resa** | Klick i ett tidsdiagram sätter tidsreglaget till den månaden | Indexdiagram, ränder |
| **Hover-detalj** | Tooltip med värde, period, `known_from`, version, status (rekonstruerad/skarp) och revidering sedan dess | Alla diagram (träffyta större än markören) |
| **Jämför** | Lägg serier från olika grenar i samma vy, indexerade till samma bas på en axel; jämför två datum (A/B) för samma vy | Seriesidan, utforskningsläget |
| **Filter** | Gren, led, frekvens, källa, licens, "bara kärnserier". En rad med filter ovanför diagrammen. Filter färgar aldrig om överlevande serier | Seriekatalogen, utforskningsläget |
| **Modell- och skalväxlare** | Huvudmodell mot baslinje; nivå mot avvikelse från prognos | Prognossidor. Prövat i prototyp (c) |
| **Utforskningsläge med egna vikter** | Användaren kan välja bort serier och se ett eget index, tydligt märkt "ditt urval, inte det registrerade" | `/data`, efter granskning |
| **Djuplänkar** | Allt tillstånd i URL:en (`#as_of=…&serie=…&modell=…&skala=…`), och varje vy kan delas med genererad bild | Alla. Prövat i alla tre prototyper |
| **Frågor i webbläsaren** | SQL (DuckDB-WASM) mot de publicerade aggregaten, med färdiga exempel ("serier vars takt ligger över 90:e percentilen") | `/data` |
| **Tabellvy och nedladdning** | Varje diagram kan visas som tabell och laddas ned som CSV/Parquet med källa och licens i filen | Alla diagram |

Tidsresan är den unika tillgången och förtjänar en designregel: **det man ser vid ett datum ska vara exakt det som
fanns.** Det innebär att sidan läser versioner, aldrig räknar om historiken med dagens data, och att rekonstruerade
månader (före den första skarpa ögonblicksbilden) alltid är märkta.

---

## 6. Teknikrekommendation

### 6.1 Krav

Statisk sajt på GitHub Pages, helt automatiskt byggd från vecko- och månadskörningarna, inga externa värdar i
körtid (dagens regel i `tests/test_site.py`), licensgrind på ett ställe, svensk text, mobil först och snabb.

### 6.2 Alternativ

| Alternativ | Styrkor | Svagheter | Bedömning |
|---|---|---|---|
| **A. Dagens Python-generator + egen JS** | Inga beroenden, fungerar redan, allt i Python | Varje interaktion handskriven, svårt med global tidsresa och komponenter, ingen förrendering av interaktiva diagram | Bra som datakälla, för tunt som gränssnitt |
| **B. Observable Framework** | Markdown-sidor med dataladdare (Python-laddare kan anropa vår pipeline), Observable Plot, inbyggd DuckDB-WASM och Mosaic-stöd **[S]**, mycket snabb start | Mindre kontroll över global tillståndshantering och skräddarsydda signaturbilder; framtiden för projektet är osäker **[K, ej verifierat]** | Starkt för utforskningsläget och `/data`, svagare för signaturupplevelsen |
| **C. SvelteKit (statisk adapter) + D3-moduler + Observable Plot** | Full kontroll, förrendering av SVG vid bygget (diagram syns utan JS), liten körtid, komponentmodell som passar ett designsystem. Svelte används i stor utsträckning inom datajournalistik (The Pudding, NYT) **[K]** | Mer kod att underhålla, eget byggsteg i Node | **Rekommenderas** |
| D. Astro med öar | Bra för innehållssajter, förrendering | Två komponentmodeller att hålla ihop | Möjligt, men ger inget som C saknar |

### 6.3 Rekommendation

**SvelteKit med `adapter-static`, D3-moduler (skalor, former) för skräddarsydda diagram, Observable Plot för
standarddiagram, och DuckDB-WASM laddat bara på `/data` och i utforskningsläget.** Python förblir ensam ägare av data:

```
observations.parquet, snapshots/, forecasts/
        │  Python: site bundle (licensgrinden i ai_tracker.site.data, en plats)
        ▼
site_bundle/            schema-validerad (JSON Schema + pytest), versionsnummer
  index.json            ögonblicksbild, kedjan, frågorna, ränderna
  gren/G*.json, led/L*.json, prognos/n*.json, avstamning/*.json
  serie/<nyckel>.json   bara publish=True: versioner (period, värde, known_from), mått
  vintages/*.parquet    för tidsresa och /data
        │  SvelteKit-bygge (förrenderar alla sidor och deras SVG)
        ▼
site/  →  GitHub Pages
```

- **Licensgrinden** stannar i Python (`publishable`), och ett test skannar hela paketet efter nycklar med
  `publish=False` innan något publiceras. Frontend läser aldrig observationstabellen direkt.
- **Kontrakt:** paketet har ett schema och ett versionsnummer. Frontend och Python byggs och testas mot samma
  fixtures. Ett schemabrott stoppar bygget, på samma sätt som datatesterna gör i dag.
- **Automatik:** `pages.yml` kör Python-paketet och sedan SvelteKit-bygget efter veckohämtningen och efter
  ögonblicksbilden vid månadsslut. Inget manuellt steg.
- **Prestanda (budgetar i CI):** startsida ≤ 150 kB JS gzip, ≤ 100 kB data, LCP < 1,5 s på mellanklassmobil över 4G,
  CLS < 0,05. DuckDB-WASM (flera MB) laddas bara på begäran. Diagram förrenderas som SVG, och JS lägger på
  interaktion (progressiv förbättring).
- **Tillgänglighet:** WCAG 2.2 AA, axe och Playwright i CI, tabellvy för varje diagram, genererade beskrivningar,
  tangentbordsnavigering i tidsreglaget och diagrammen.
- **Mobil först:** kedjan blir en lodrät lista med en rad per led; små multiplar en kolumn; reglage med träffytor
  ≥ 32 px.
- **Delningsbilder** genereras vid bygget per sida och tillstånd (Playwright finns redan i miljön).
- **Övergång:** den nya sidan byggs under `/next/` parallellt med den gamla. Den gamla tas bort först när en
  checklista visar att all information från dagens sidor finns i den nya, och när testerna i `tests/test_site.py`
  har motsvarigheter.

**Beslutspunkt för Johannes:** stacken (C), och om den nya sidan ska byggas under `/next/` och ersätta den gamla
efter paritetskontroll (rekommendation: ja).

---

## 7. Byggplan som agentspår

Storlek i agentspår enligt `docs/agentkalibrering.md` (ett spår ≈ 13–18 min, 40–60 verktygsanrop). "+R" betyder ett
oberoende granskningsspår.

### Våg 0: grund (parallellt)

| Spår | Leverans | Beror på | Storlek |
|---|---|---|---|
| **W2 Designsystem** | Färgtokens (avsnitt 4.4, validerade i båda lägena), typografi, diagramprimitiver (axlar, band, prickar, glyfer, tooltip, tabellvy), komponentkatalog med visuella tester | beslut om stack | 1 |
| **W3 Datakontrakt** | `site_bundle` med JSON Schema, exporterare som bygger på `ai_tracker.site.data`, versioner för publish=True-serier, licensskanning, fixtures, pytest | – | 1 +R (licens) |
| **W4 Skelett och CI** | SvelteKit-projekt, `pages-next.yml` till `/next/`, budgetar för prestanda och tillgänglighet, Playwright-skärmbilder i CI, test att inga externa värdar laddas | beslut om stack | 1 |

### Våg 1: sidorna (helt parallellt, egna kataloger)

| Spår | Leverans | Beror på | Storlek |
|---|---|---|---|
| **W5 Startsidan** | Kedjan, tre frågekort, ränder, rubrikmening ur data (vidare från prototyp a) | W2, W3, W4 | 1 |
| **W6 Led- och grensidor** | Minikarta, index över tid, små multiplar, inhållna serier som räknade rutor | W2, W3, W4 | 1 |
| **W7 Serieinstrumentet** | En komponent för alla serier: nivå/takt/förändring, versioner, tabell, källa, licens, nedladdning, permalänk | W2, W3, W4 | 2 |
| **W8 Prognossidor** | N1–N6: kvantilprickar, band över tid, kalibrering, PIT, CRPS, facit, sida per skarp prognos med commit-länk (vidare från prototyp c) | W2, W3, W4 | 1 |
| **W9 Tidsresa** | Globalt `as_of`-tillstånd, ögonblicksbilder som tidsresa, revideringsvy, uppspelning (vidare från prototyp b) | W3, W7 | 1 +R (läckage: visas bara det som var känt?) |
| **W10 Avstämningar och regim** | Kvoter med komponenter, regimsannolikhet per block, strukturbrott som markörer | W2, W3 | 1 |
| **W11 Utforskbar metod** | Figurer för diffusionsindex (dra i dödbandet), intervall och kalibrering, `as_of` | W2 | 1 |
| **W12 Navigering och delning** | Sök (⌘K), djuplänkar, delningsbilder per sida, citeringsrad | W4 | 1 |

### Våg 2: berättelser och data

| Spår | Leverans | Beror på | Storlek |
|---|---|---|---|
| **W13 Månadens berättelse** | Förregistrerad urvalsregel (i måttregistret först), korten, scrollytelling för månadsbrevet | W5–W8, regeln låst | 1 +R (neutralitet) |
| **W14 Kvartalsrapporten** | Visuell essä från `ai_tracker.quarterly` med levande figurer | W13 | 1 |
| **W15 Data och utforskningsläge** | `/data` med nedladdning och DuckDB-WASM-frågor mot aggregaten, utforskningsläge med egna vikter, tydligt märkt | W3, W7 | 1 |

### Granskning och övergång

| Spår | Leverans | När |
|---|---|---|
| **R-W1 Licens och läckage** | Oberoende kontroll att paketet bara innehåller publiceringsbart och att tidsresan aldrig visar data före `known_from` | Efter W3 och W9 |
| **R-W2 Tillgänglighet och prestanda** | axe, skärmläsare, tangentbord, budgetar på riktig mobilprofil, mörkt läge | Efter våg 1 |
| **R-W3 Neutralitet och läsbarhet** | Formuleringar, färger, urvalsregel; "fem sekunders test" på skärmbilder (vad uppfattas först?) | Efter W5 och W13 |
| **W16 Övergång** | Paritetschecklista mot dagens sida, flytt från `/next/` till roten, gamla generatorn tas bort | Efter granskningarna |

**Storlek totalt:** 15 byggspår (16 spårenheter, W7 räknas som 2) + 3–4 granskningar ≈ 20 spår. Det ryms i ett
5-timmarsfönster med 5–6 parallella spår. Kritisk väg: beslut → W3 → W7 → W9 → R-W1 → W16. Den kalendertid som inte
går att korta: första skarpa ögonblicksbilden (2026-11-30) och första skarpa nowcast (N2, 2026-12-05) ger startsidan
och facit riktigt innehåll. Kalibreringen på facitsidan blir meningsfull först efter cirka 12 skarpa utfall.

**Inom en våg** rör spåren inte samma filer: varje sida är en egen route-katalog, delade komponenter ägs av W2 och
ändras därefter bara genom W2-uppföljningar.

---

## 8. Prototyperna och vad de lärde oss

`prototypes/hemsida/` (statisk HTML/JS, inga bibliotek, inga externa värdar). Data byggs med
`PYTHONPATH=src python prototypes/hemsida/build_data.py --site <utdata från python -m ai_tracker.site build>`
och hamnar i `prototypes/hemsida/data/` (gitignorerad, data committas aldrig). Skriptet kopierar den befintliga
sidans licensgrindade JSON och läser versionerna för G6:s kärnserier (alla `publish=True`) och N2:s backtest med
den registrerade koden. Titta med `python -m http.server -d prototypes/hemsida`.

| Prototyp | Fil | Vad den prövar |
|---|---|---|
| (a) AI-flödet denna månad | `index.html` | Rubrikmening ur data, kedjan L1→L9 med enhetsdiagram och index-spark, tre frågekort (prickar med förra månaden, kalender, kalibrering, avstämningar som percentil), tillståndsränder |
| (b) Gren G6 med tidsresa | `gren.html` | Globalt datumreglage med uppspelning, grenindex med klick-för-att-resa, små multiplar av takt enligt versionen vid datumet mot dagens version, revideringsbild, djuplänkar |
| (c) Nowcast N2 med osäkerhet | `nowcast.html` | Stort tal med intervall, kvantilprickdiagram, band 50/80/95 över tid i nivå eller avvikelse, modellväxlare (B3 mot B1), täckning mot binomialband, PIT, CRPS, tomt skarpt register |

**Lärdomar från egen granskning av skärmbilderna (dator 1280 px och mobil 375 px, ljust och mörkt):**

1. **Ränderna bär mest information per pixel.** De berättar hela 2023–2026 utan text. De ska upp högt på startsidan
   och bli delningsbilden.
2. **Revideringsbilden är det mest originella.** G.17-exemplet (−4,4 då, +4,8 nu för december 2022) går inte att
   se någon annanstans. Tidsresan bör vara ett huvudnummer, inte en dold funktion.
3. **Kedjan behöver en egen mobilform.** Nio kort under varandra blir för långt på 375 px. Mobilversionen bör vara
   en rad per led (glyf, namn, index-prick), med kortet som utfällning.
4. **Frågekorten måste vara bilder.** Första versionen av "Vart är vi på väg?" var en textlista och kändes tung. Som
   tidslinje plus kalibreringsrad blev den läsbar på några sekunder. Samma sak för "Var står vi nu?": prickar med
   förra månaden som ring visar både läge och förändring.
5. **Prickdiagrammet behöver rätt klassbredd.** Med för små prickar spreds de ut till en rad och slutade fungera som
   frekvensbild. Klassbredden ska sättas från fördelningens mitt, inte från skärmbredden.
6. **Kalibreringsproblem syns direkt.** N2:s huvudmodell har 43 % täckning på 50 %-nivån i backtesten, under
   slumpbandet, medan 95 % träffar. I bilden ser man varför: intervallen är lika breda hela tiden. Sidan ska visa
   sådant rakt, och det är ett underlag för registret, inte för sidan att lösa.
7. **Statusmärkningen måste synas överallt.** Allt före 2026-11-30 är rekonstruerat, och N2-exemplet är backtest.
   Märkningen fungerade bäst som streckad etikett intill rubriken, inte som fotnot.
8. **Färgen ska bara betyda riktning.** När serierna i små multiplar fick neutral bläckfärg blev blått och orange
   entydiga i hela gränssnittet.

**Begränsningar i prototyperna:** takt och riktning i (b) räknas i webbläsaren enligt måttregistret på varje version
(för visning). Den riktiga sidan läser pipelinens mått. Grenens index i (b) är sajtens rekonstruktion per månadsslut.
Regimsannolikheten finns inte i dagens bygge (den kommer från den första skarpa ögonblicksbilden), så (a) visar bara
status för den.
