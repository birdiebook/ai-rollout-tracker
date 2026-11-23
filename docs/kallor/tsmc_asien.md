# TSMC:s månadsintäkt och asiatisk export (G6, mål N2)

Fas 2, spår I2. Byggt och kontrollerat 2026-11-23 med projektets ärliga klient (`ai_tracker.http`).
Bara data: inga trender, samband eller prognosvärden är beräknade.

## Serier

| Nyckel | Innehåll | Enhet | Historik | Rader | Publiceras |
|---|---|---|---|---|---|
| `tsmc_revenue_m` | koncernens nettointäkt (consolidated), mål N2 | mn TWD | 2006-04 – 2026-10, 247 månader utan luckor | 263 (16 omräknade vintages) | ja |
| `tsmc_revenue_parent_m` | moderbolagets nettointäkt (unconsolidated), upphörde med IFRS | mn TWD | 2001-10 – 2012-12, 135 månader | 136 (1 omräknad) | ja |

Kod: `src/ai_tracker/sources/tsmc_sec.py` (hämtning och tolkning), `src/ai_tracker/series/tsmc.py` (`SPECS`),
tester i `tests/test_tsmc.py`. Hämta med `python -m ai_tracker.observations tsmc_revenue_m tsmc_revenue_parent_m`.

**Källa: SEC EDGAR, Form 6-K.** TSMC lämnar varje månadsrapport om intäkter som 6-K. Det är samma siffror
som går till TWSE/MOPS. Alla 1 314 elektroniska 6-K sedan 2002-10 gås igenom (tidigare inlämningar är på
papper). 289 är månadsrapporter, och varje period finns i exakt en rapport. Dokumenten ändras aldrig, så
råkopiorna i `data/raw/tsmc_sec/` återanvänds (cirka 250 MB). En ny körning hämtar bara nya inlämningar och
de två submissions-filerna, och tar cirka 8 sekunder.

Tolkningen klarar fem layouter: 2002–2004 (tabell utan etikett), 2004–2005 ("Net Sales for <månad>"),
2006–2012 (separata tabeller för moderbolag och koncern), och 2013– (koncern, kolumner för innevarande
månad, föregående månad och samma månad året innan). Rapporternas avsnitt i tusen NT$ ger exakta siffror:
för koncernen från 2013, för moderbolaget 2005–2012. Övriga värden är i mn NT$. Kända egenheter i källan:
rapporten för april 2014 skriver "49.956" i stället för 49,956 (hanteras), och en 6-K från 2013-03-15
(prospektliknande sammanställning) hoppas över eftersom den inte är en månadsrapport.

**Redovisningsbrott.** Fram till 2012 gäller R.O.C. GAAP och från 2013 IFRS. Från 2013 rapporteras bara
koncernen. Koncernsiffran finns i 6-K från 2006-04.

## known_from

**Regel: `known_from` = 6-K:ns inlämningsdatum i EDGAR (`filingDate`).** Raderna är release-daterade
(`source="release"`), så ingen schablon behövs.

Belägg (289 rapporter):

| Dag i månaden efter | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 | 15 | 16 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Antal rapporter | 2 | 14 | 44 | 57 | 160 | 1 | 3 | 4 | 2 | 1 | 1 |

- Medianen är dag 10, alltså MOPS-fristen. Senare dagar beror på helger (fristen flyttas till nästa
  arbetsdag) och nyår (t.ex. 2008-02-14, 2016-02-16, 2019-02-15).
- EDGAR:s `acceptanceDateTime` ligger för 275 av 289 rapporter mellan 10 och 13 UTC, alltså på kvällen
  i Taiwan. Datumet är därför konservativt: siffran var offentlig senast vid inlämningen, och oftast redan
  tidigare samma dag på MOPS. MOPS egen publiceringstid gick inte att kontrollera, eftersom MOPS blockerar
  klienten.
- **Kontroll mot TWSE.** `openapi.twse.com.tw/v1/opendata/t187ap05_L` (samma data som MOPS, men bara
  senaste månaden) ger 2026-10 = 586 890 319, 2026-09 = 511 857 399 och 2025-10 = 367 473 051 tusen NT$.
  Det stämmer exakt med 6-K. API:ets `出表日期` är tabellens datum och inte bolagets publiceringsdatum, så
  det duger inte som `known_from`. `tsmc_sec.twse_current()` finns för fortsatta stickprov.

**Flagga för förregistreringen (N2).** `docs/mattregister.md` sätter prognosdagen till dag 8. Men 61 av
289 rapporter (21 %) lämnades in dag 8 eller tidigare, och 16 av dem dag 6–7. Andelen är densamma före och
efter 2016. Med dag 8 finns utfallet alltså redan i ungefär var femte månad. **Rekommendation: prognosdag dag 5**
(den tidigaste observerade publiceringen är dag 6). Alternativet är "dagen före publicering", men det kräver
att publiceringsdagen är känd i förväg, vilket den inte alltid är.

## Revideringar

Varje rapport upprepar värdet för samma månad året innan, och från 2013 även för föregående månad. Ett
jämförelsetal sparas som ny vintage (med rapportens inlämningsdatum) bara om det skiljer sig mer än
1 mn NT$ (tabellens avrundning) från det som var känt. Om perioden inte var känd sedan tidigare sparas det också.

- **IFRS-omräkningen** 2013: alla månader 2012 räknades om med +0,09 till +0,19 %. Värdena blev kända
  2013-02-08 – 2013-12-10.
- **Övrigt:** 2006-06 −0,15 %, 2006-09 +0,13 % (räknades om ett år senare), 2011-07 +2 mn och 2020-07 +3 mn
  (månaden efter). För moderbolaget: 2002-12 +0,56 %.
- Största revidering i koncernserien: 0,19 %. `revised=True` är satt eftersom vintages finns, men nivån är
  mycket låg. MOPS egna rättelser (更正) gick inte att läsa, så det är inte verifierat att alla rättelser
  syns i 6-K.
- Moderbolagets serie 2001-10 – 2002-09 finns bara som jämförelsetal i rapporterna ett år senare. Därför har
  de raderna en senare inlämningsdag som `known_from`. Det ger inget läckage, men värdena var kända sent.
- N2:s mål är "första publicerade värdet". Det ges av den tidigaste vintagen per period.

## Licens

SEC: "Information presented on sec.gov is considered public information and may be copied or further
distributed by users of the web site without the SEC's permission. Please consider appropriate citation to
the SEC as the source." (https://www.sec.gov/privacy, avsnittet Website Dissemination, läst 2026-11-23).
Siffrorna kommer ur en lagstadgad inlämning, och bara extraherade siffror publiceras, med källhänvisning
(projektets regel för rapporter). TSMC:s IR-villkor gick inte att läsa (403). **`publish=True`**, men det
bör bekräftas vid granskningen. TWSE OpenAPI:s villkor är inte lästa. Källan används bara för kontroll och
publiceras inte.

## Korea och Taiwan: BLOCKED

Varje värd provades en gång med den ärliga klienten (och unipass/customs en gång till). Ingen serie
kunde byggas.

| Källa | Värd | Resultat | Skäl | Vad som löser det |
|---|---|---|---|---|
| MOPS (lagstadgad kanal för TSMC) | `mops.twse.com.tw`, `mopsov.twse.com.tw` | BLOCKED | WAF-sida "FOR SECURITY REASONS, THIS PAGE CAN NOT BE ACCESSED" på alla sökvägar, även roten. Samma svar med curls standard-UA, alltså IP-baserat | annan utgående IP (t.ex. GitHub Actions, ej testat). Behövs inte: 6-K räcker |
| TWSE OpenAPI | `openapi.twse.com.tw` | OK, men bara senaste månaden | ingen historik | – (används för kontroll) |
| MOTIE (export den 1:a i månaden efter) | `www.motie.go.kr`, `english.motie.go.kr` | BLOCKED | proxyn släpper igenom (CONNECT 200), men fjärrservern bryter TLS-handskakningen | annan utgående IP (troligen geoblockering) |
| KOSIS | `kosis.kr` | BLOCKED | TLS-reset från fjärrservern. API:t kräver dessutom gratis nyckel (`apiKey`) | annan IP och nyckel |
| KITA K-stat | `stat.kita.net` | BLOCKED | kösida med JavaScript ("TRACER", WELLCONN). En av dess texter säger att IP-adressen är spärrad. Grinden kringgås inte | – |
| Koreas tullverk (10/20-dagarsdata) | `unipass.customs.go.kr`, `www.customs.go.kr` | BLOCKED | TLS-reset. `www.customs.go.kr` svarade en gång av fyra (curl), aldrig via klienten | annan utgående IP |
| data.go.kr, tradedata.go.kr | `www.data.go.kr`, `tradedata.go.kr` | BLOCKED | proxyn nekar (inte öppnade). data.go.kr kräver dessutom `serviceKey` | allowlista och nyckel |
| **BOK ECOS** | `ecos.bok.or.kr` | **nåbar, nyckel krävs** | API:t svarar. Testnyckeln `sample` ger högst 10 rader per anrop, så den räcker inte för drift | gratis ECOS-nyckel (인증키, registrering på ecos.bok.or.kr/api med e-post). Förslag: `ECOS_API_KEY` i `.env` |
| Taiwan exportordrar (MOEA) | `www.moea.gov.tw` | BLOCKED | Cloudflare 403 | – |
| Taiwan tullstatistik | `portal.sw.nat.gov.tw` | BLOCKED | TLS-reset från fjärrservern | nätverksutredning |
| Taiwan MOF, statistikdatabaser | `www.mof.gov.tw`, `web02.mof.gov.tw`, `dmz26.moea.gov.tw`, `data.gov.tw`, `statdb.dgbas.gov.tw`, `www.trade.gov.tw` | BLOCKED | proxyn nekar (inte öppnade) | allowlista |

**ECOS-tabeller som är relevanta när en nyckel finns** (från tabellistan, hämtad med `sample`-nyckeln):
`403Y001` exportvärdeindex (수출금액지수) per produkt, 716 poster, månad från 1988-01, senast 2026-10
(alltså inom cirka tre veckor). `403Y002` exportvolymindex. `901Y118` export och import enligt
tullstatistik, totalt. `402Y014` exportprisindex. Det är månadsdata och inte 10/20-dagarsdata. Vilken
postkod som avser halvledare (반도체) är inte kontrollerat, eftersom bara de 40 första posterna lästes.

**Slutsats för N2.** Det enda koreanska alternativet som går att nå är ECOS (med nyckel, månadsdata). De mest
ledande serierna, alltså tullverkets 10/20-dagarsdata och MOTIE, kräver en annan utgående IP-adress än
sessionens. Det går inte att lösa med allowlistning.
