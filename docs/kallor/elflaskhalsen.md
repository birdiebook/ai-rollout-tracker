# Källor: Elflaskhalsen (EL1)

Följd fråga i körning 16: "Blir el den bindande begränsningen för utbyggnaden?" Ingen ny källa och ingen ny extraktion.
Allt räknas ur serier som redan finns i katalogen. Måtten, aggregaten, gränserna och läsregeln låstes i registret
innan något räknades (`docs/mattregister.md`, "2026-11-26 – EL1", commit `f8f0046`). Modulen är
`src/ai_tracker/followed/elflaskhalsen.py`, testerna `tests/test_followed_elflaskhalsen.py` och rapporten
`docs/resultat/elflaskhalsen.md`.

## Serier som används

| Roll | Serie | Källa | Frekv. | Historik i tabellen | `known_from` | Klass | `publish` |
|---|---|---|---|---|---|---|---|
| X1 elpris | `us_ppi_elec_commercial_m` | BLS PPI (M1, `docs/kallor/makro_bea_bls.md`) | M | 1958-01– | regeldaterad (backfill): slutligt värde vid PPI-releasen m + 4, den senaste filens preliminära månader filens datum | ja | True |
| X2 last | `eia930_avg_{pjm,erco,soco,azps,srp}_m` | EIA-930 (A4, `docs/kallor/el_datacenter.md`) | M | 2015-07– (SOCO 2018-11, SRP 2018-08) | backfill: månadsslut + 7 dagar | ja | True |
| beskrivning | `eia930_avg_pjm_dom_m` (Dominion, delregion av PJM) | EIA-930 | M | 2018-10– | backfill: månadsslut + 31 dagar | ja | True |
| X3 orderstock elnät | `rpo_pwr`, `rpo_etn` | SEC XBRL (S2, `docs/kallor/sec_stack_kraft.md`) | Q | 2018Q1–, 2020Q3– | inlämningsdag | ja | True |
| X4 gasturbiner | `ob_gev_backlog_and_slot_reservations_gas_power_equipment_end_level_gw` | GE Vernovas pressmeddelanden (S3, `docs/kallor/order_orderstock.md`) | Q | 2025Q1– | inlämningsdag för 8-K | ja | False |
| Y1 capex | `kl_capex4_inner` | KL1:s lageraggregat (`docs/kallor/kreditlagret.md`) | Q | 2018Q2– | senaste komponenten | ja | False |
| Y2 tecknade MW | `ob_dlr_leases_signed_total_dlr_share_q_level_mw` | Digital Realtys pressmeddelanden (S3) | Q | 2021Q4– | inlämningsdag för 8-K | ja | False |

Beskrivning utan läsregel: `rpo_gev_equipment`, GE Vernovas orderstock och reservationer i GW var för sig,
`ob_gev_backlog_electrification_equipment_end_level_musd`, `kl_capex4_outer`, `lease_uncommenced_{googl,amzn,meta,orcl}`,
`capex_{pwr,etn,gev}` och kraftplanerna `plan_crwv_contracted_power_asof_value`, `plan_crwv_active_power_asof_value`,
`plan_amzn_power_added_12m_asof_value` och `plan_orcl_power_added_q_asof_value`. Microsofts kraftplan
(`plan_msft_power_added_q_asof_value`) har klassen `okänd` och visas inte.

## Härledda storheter (inte katalogserier)

Storheterna räknas i rapporten med F0:s `aggregate.derive` på tabellen kapad vid läsdagen, och de mäts med
`common.path_measures(method="log")`, samma formler som `state.measures`. De sparas inte i observationstabellen.

| Nyckel | Definition |
|---|---|
| `el1_pris4` | medel av PPI för de tolv månader som slutar med kvartalets sista månad |
| `el1_last4` | medel över tolv månader av summan av de fem områdenas medellast |
| `el1_last4_dom` | samma för Dominion (beskrivning) |
| `el1_ob_nat` | `rpo_pwr` + `rpo_etn` vid kvartalets slut |
| `el1_dlr_mw4` | summan av Digital Realtys tecknade MW för kvartalet och de tre före |

**Månad till kvartal.** `derive` med månadsfrekvens ger ett tolvmånadersmedel per månad, och bara kvartalets sista månad
(mars, juni, september och december) används. Ett värde finns först när alla tolv månader har ett värde känt på dagen,
för lasten i alla fem områdena. Ingen interpolation. Säsongen försvinner i tolvmånadersmedlet, och takten jämför med
samma tolv månader ett år tidigare. `known_from` är den senaste månaden som ingår.

**Summor.** En version finns först när alla komponenter finns, och `known_from` är den senaste komponenten. Rapporten
listar vad nästa kvartal saknar på dagen (`aggregate.missing`).

**as_of.** Tabellen kapas vid läsdagen innan något räknas, och varje rad tas i sin senaste vintage på dagen. Testet
`test_a_row_known_after_the_day_changes_nothing` lägger till rader som blir kända efter dagen (en ny vintage, ett nytt
kvartal och nya månader) och kräver att rapporten blir densamma.

## Läsregeln

F0:s symmetriska regel, X:s takt mot Y:s förändring i takt, tecken −1, *k* = 2. Gränser: elpris ±5, last ±2,
orderstockarna ±10 (log × 100 per år), capex ±5 och Digital Realtys MW ±10 (log × 100). Åtta rader, en per par.
Huvudläsningen är orderstock för elnät mot capex i det inre lagret. Antennen (`python -m ai_tracker.followed antenner`)
visar huvudläsningen som radens utslag och de sju andra som fakta.

## Förbehåll

- **Mer än datacenter.** Quantas RPO omfattar förnybart, telekom och rörledningar. Eatons orderstock gäller hela
  bolaget, också flyg och fordon. GE Vernova säljer gasturbiner globalt, till elbolag och industri. En växande
  orderstock är därför inte efterfrågan från datacenter ensam.
- **Förvärv.** GE Vernovas orderstock innehåller Prolec GE från 2026Q1, och Eatons Electrical Global köpte Boyd Thermal
  2026-03-12 (R19). Det blåser upp orderstockens takt och rättas inte. Quanta köper bolag nästan varje kvartal: fem
  bolag 2026Q2–Q3 (köpeskilling 1 799,7 MUSD för 2026Q1–Q3), Dynamic Systems 2025Q3 och tre bolag 2025Q4 (QA1,
  `docs/kallor/ledtid.md`, avsnittet "Quantas förvärv", med källor). Quanta anger inte tillförd RPO, och skriver att
  ökningen till 2026-09-30 i första hand berodde på nya uppdrag och volym och i mindre utsträckning på förvärv. EL1 har
  inget förvärvsmärke, och utslaget ändras inte. Som beskrivning: huvudläsningens X (takten +45,3 vid 2026Q2) hamnar
  under gränsen 10 först om förvärven 2025Q3–2026Q2 hos Quanta och Eaton tillsammans fanns kvar i orderstocken med mer
  än omkring 17,1 mdr USD, cirka 30 % av orderstocken vid 2026Q2.
- **Elpriset** är reglerade tariffer för kommersiella kunder. Det speglar bränslekostnader och nätens kostnader med
  fördröjning, inte knapphetspriset på marginalen. Priset har en nominell drift uppåt: 62 impulser uppåt och ingen nedåt
  sedan 1959. PJM:s kapacitetspriser ligger närmare knappheten, men de har klassen `nej` och visas inte.
- **PPI-dateringen** är konservativ. Rader för de senaste månaderna blir kända först med nästa fil, så det senaste
  kvartalet släpar. Per 2025-11-26 slutade serien vid 2025Q1.
- **Lasten** är medellast, inte topplast. Den påverkas av väder, och de fem områdena täcker inte hela USA. EIA-930 har
  inga daterade versioner före 2026-11-23: äldre värden är dagens (backfill, revideringar läcker in), och när den
  justerade kolumnen först publicerades är inte belagt (`docs/kallor/el_datacenter.md`).
- **`ob_*`** är en extraktion som R19 godkände med anmärkningar, med `publish=False`. Digital Realtys andel före 2025
  är inte belagd (R19, F-4), så fyrakvartalssummorna över 2024Q4–2025Q3 kan blanda baser. Tecknade MW är klumpiga.
- **Capex** är hela capex, där servrar och chip är största delen. En begränsning i el syns troligen tidigare i byggen
  och leasing.
- **Regeln läser i praktiken bara Y för orderstockarna.** Orderstocken för elnät har haft en impuls uppåt i varje
  kvartal sedan 2021Q3. Riktningen nedåt har aldrig kunnat prövas. En regel på förändring i takt för X, eller på realt
  elpris, kräver en ny daterad post.
- **Historiken för elpriset** räknar ursprung från 1959, långt före Y. F0:s mall räknar ett ursprung utan impuls som
  prövat ("inget av mönstren") även när Y saknas. Rapporten anger därför från vilket kvartal Y finns under varje rad.
- **"Bindande" kan inte visas.** Regeln ser samvariation i riktning, inte ett skuggpris, och X och Y har en gemensam
  drivkraft.

## Utanför ramen (förslag med licensfråga, inte hämtade)

| Källa | Vad den ger | Licensfråga |
|---|---|---|
| LBNL "Queued Up" | köer för nätanslutning per region och år | villkoren för återpublicering ska läsas |
| ERCOT, kö för stora laster | MW i kö per status | PARTIAL: siffrorna finns bara i diagram (A4). Villkoren tillåter rådata i analyser |
| PJM, kapacitetsauktioner | pris per MW-dag (`pjm_bra_*`, redan i katalogen) | klass `nej`, kräver tillstånd från PJM för att visas |
| EIA-860M | planerade kraftverk per månad | public domain, kräver ett hämtspår |

## Kommandon

    python -m ai_tracker.followed elflaskhalsen --as-of 2026-11-26 [--json PATH] [--out PATH]
    python -m ai_tracker.followed antenner --as-of 2026-11-26
    python -m pytest -q tests/test_followed_elflaskhalsen.py
