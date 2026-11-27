# Kreditlagret: följd fråga (KL1)

*Efter granskningen R29 (rättningsspår X26, `docs/mattregister.md`, 2026-11-27 X26, punkt 1): övergångsnotisen för F0:s räkning av prövade ursprung säger att bytet i S1, punkt 3, väntar på ägarens bekräftelse (R29-1). Inget annat ändrades, och KL1:s låsta avsnitt 1–7 är oförändrade.*


*Tillägg S1 (`docs/mattregister.md`, 2026-11-27 S1, punkt 1): rapporten har ett nytt avsnitt 8, en symmetrisk läsning med F0:s regel per pris- och beroendemått mot samma enhets capex-takt (tecken −), bredvid den låsta läsningen. Avsnitt 1–7 är byte för byte desamma som med koden före S1, och huvudläsningen är den låsta. Rapporterna nedan är genererade på nytt per 2026-11-27 och 2025-11-27. Utom datumen och avsnitt 8 är de desamma som per 2026-11-25 och 2025-11-25, så texten om de dagarna gäller också för de nya. Undantag: per 2026-11-27 saknar avsnitt 4 stycket om sedda data, eftersom den låsta rapporten avgör det av läsdagen (efter 2026-11-25) och inte per läsning. Inget kvartal i KL1:s serier blev känt efter 2026-11-25, så läsningen är fortfarande på sedda data.*

**Frågan:** Ändras finansieringens pris och tillgång i de yttre lagren, och följer investeringstakten där med?

Följd fråga, inte en gren. Måtten, läsregeln och gränserna låstes i registret före beräkningen
(`docs/mattregister.md`, 2026-11-25 KL1 och tillägget). Källor och kodning: `docs/kallor/kreditlagret.md`. Rapporten
byggs med

    python -m ai_tracker.followed kreditlagret --as-of 2026-11-27 [--json PATH] [--out PATH]

Den använder bara rader som var kända på dagen. Nedan står rapporten per 2026-11-27 och per 2025-11-27, så att
ändringen över ett år syns. Rapporterna är genererade av kommandot och inte redigerade. Rättade efter granskningen R26
(spår X23, registret 2026-11-25 X23): dateringen av fem rader från Anthropic, CoreWeaves obligation 2031, SpaceX (xAI)
i labbdelen, listan över okodade kandidater och förbehållen nedan. Rättade efter granskningen R27 (spår X24, registret
2026-11-25 X24): räntan för SpaceX:s övriga finansiering visas med förbehåll och med räntekostnaden för Valor-skulden.

**Läsningarna är gjorda på sedda data.** Alla kvartal i båda läsningarna var kända före registerposten 2026-11-25, och
flera av dem var sedda före posten (posten, avsnitt (e)). Utslagen är därför inga utfall på osedda data. Den första
läsningen på osedda kvartal kommer med inlämningar efter 2026-11-25, för Oracle omkring 2026-12-11.

## Vad som skiljer de två dagarna (beskrivning, inget test)

- **Läsregeln.** För Oracle mot det inre lagret gav regeln "talar emot (1)" per 2025-11-25 och "talar för
  mekanismen" per 2026-11-25. Beroendet steg vid *t* − 2 båda åren. Skillnaden är capex-takten: förändringen i takt
  var +33,5 per 2025Q3 och −15,8 per 2026Q3, medan det inre lagret låg på +2,0 och +9,6. Oracles capex växer
  fortfarande med cirka 100 log-punkter per år. Det som föll är tillväxten.
- **Regeln läser bara uppgång.** A kräver att pris eller beroende stiger med minst gränsen. För Oracle gällde A i 44
  av 58 kvartal med minst en takt (2012Q2–2026Q3). Oracles utslag avgörs därför i praktiken av capex-takten. Ett fall i
  pris och beroende följt av högre capex-takt ger "inget av mönstren". En regel åt båda hållen kräver en ny post.
- **CoreWeave** ger "talar emot (1)" per 2026-11-25: tecknade leasingavtal steg mot capex vid 2026Q1, och capex-takten
  steg efter det (+35,7). Per 2025-11-25 fanns inga fyra kvartal kända.
- **Yttre lagret som helhet** kan inte avgöras ännu. IREN:s capex finns från 2024Q3, så aggregatets förändring i takt
  finns först med 2026Q4 (inlämningarna i februari 2027). Nebius gav "inget av mönstren".
- **Inre lagret:** (capex − OCF) / capex gick från −62,8 % till −10,0 % och nettoemission från 1,6 % till 43,8 % av
  capex. Capex-takten ökade (förändring i takt +9,6). Microsofts effektiva ränta (8,2 %) innehåller ränta på finansiell
  leasing och är inte priset på skuld. Det gäller också inre lagrets ränta.
- **CoreWeaves vägda ränta** föll från 10,4 % till 7,9 %. Utan konvertibler föll den från 10,4 % till 9,5 %.
  Konvertiblerna, med 2–3 % ränta, är 22,7 % av utestående. Det mesta av fallet är alltså mixen.
- **Nytt i underlaget:** Anthropics S-1 (2026-10-26) med en säkerställd kreditfacilitet på 15 mdr, konvertibelramar
  och åtaganden, CoreWeaves nya obligationer och lånefaciliteter, och Metas datacenterbolag (största möjliga förlust
  från 46,0 till 68,4 mdr).
- **SpaceX (xAI)** ingår nu som tabellrader: 38,0 mdr i total skuld per 2026-09-30 för hela koncernen. Av det är
  25,0 mdr obligationer från 2026-06 med 6,07 % effektiv ränta, och 12,9 mdr misslyckade sale-leaseback av AI-hårdvara
  med Valor, som är närstående. Räntekostnaden för Valor-skulden var 351 MUSD under 2026Q3, cirka 10,7 % per år.
  Bolagets 6,3 % gäller enligt texten övriga finansieringsavtal med maskiner och utrustning som säkerhet, och det
  framgår inte om Valor-skulden ingår. xAI:s egna lån före köpet hade 12,5 % ränta. Anthropic har åtaganden på upp
  till 120,5 mdr till SpaceXAI.
- Varje mönster kan vara slump. Med 8–12 kvartal per mått och klumpig RPO är detta en beskrivning.

## Tillägg S1: vad de symmetriska raderna säger (beskrivning, inget test)

Avsnitt 8 i rapporterna nedan. Alla rader per 2026-11-27 vilar på värden som var kända före registerposten 2026-11-27,
och KL1:s takter vid *t* − 2 var sedda före den (S1, punkt 6). Utslagen är inga utfall på osedda data.

- **Riktningen nedåt kan nu läsas.** 12 av de 18 raderna har haft minst en impuls nedåt i historiken (15 rader har X
  alls). Den låsta regeln läser bara uppgång.
- **Oracle:** de tre beroendemåtten ger "talar för, uppåt" per 2026-11-27. Vid ursprunget 2026Q2 hade (capex − OCF) /
  capex stigit +40,7, nettoemission / capex +52,9 och leasing / capex +262,5 procentenheter, och Oracles capex-takt föll
  −15,8 vid 2026Q3. Det är samma capex-takt som i den låsta läsningen, så raderna är inget oberoende belägg för den.
  Räntan ger "inget av mönstren" (ingen impuls i fönstret). Per 2025-11-27 gav (capex − OCF) / capex och nettoemission
  "talar emot, uppåt" (capex-takten steg +33,5) och leasing "talar för, nedåt" (leasing −129,0, capex-takten +33,5).
- **Inre lagret:** de tre beroendemåtten ger "talar emot, uppåt" per 2026-11-27: beroendet steg och capex-takten steg
  +9,6. För (capex − OCF) / capex är det den mekaniska kopplingen i avsnitt 8. Per 2025-11-27 kunde de inte avgöras
  (capex-takten +2,0 vid 2025Q3, inom ±5, och fönstret var öppet).
- **CoreWeave och Nebius:** "talar för, nedåt": beroendet föll (CoreWeave (capex − OCF) / capex −26,2 och leasing −224,0
  vid 2026Q2, nettoemission −12,5 vid 2026Q1; Nebius −75,2) och capex-takten steg (+35,7 och +70,6; Nebius +44,0). För
  nettoemission och leasing är det samma mekaniska koppling åt andra hållet, och historiken är ett till tre ursprung.
- **Yttre lagret och IREN** kan inte avgöras: capex över fyra kvartal har ingen förändring i takt förrän 2026Q4. Räntan
  har ingen takt för yttre lagret, inre lagret och CoreWeave (tre eller fyra kvartal).
- **Räkningen (S1, punkt 3)** ändrar bara de korta raderna, till exempel Oracles ränta från 21 till 20 prövade ursprung av
  21 och CoreWeaves nettoemission från 2 till 1 av 3.
- Med 18 rader och korta serier väntas några utslag av en slump. Första osedda läsningen: Oracle 2026Q4 omkring
  2026-12-11.

## Kreditlagret per 2026-11-27

**Frågan:** Ändras finansieringens pris och tillgång i de yttre lagren, och följer investeringstakten där med?

Yttre lagret: Oracle, CoreWeave, Nebius och IREN, och labben som tabellrader. Inre lagret: Microsoft, Alphabet, Amazon och Meta. Takt = förändring över fyra kvartal (procentenheter för andelar och räntor, log × 100 för belopp). Förändring i takt = mot två kvartal tidigare. Överraskning = mot den naiva baslinjen B1 (samma takt som de fyra senaste kvartalen). Bara data kända på dagen. Registret: `docs/mattregister.md`, 2026-11-25 KL1.

### 1. Pris på skuld

Effektiv ränta = räntekostnad över fyra kvartal / genomsnittlig långfristig skuld (efter aktiverad ränta, så den blir lägre hos bolag som bygger mycket). Microsofts räntekostnad innehåller ränta på finansiell leasing, men nämnaren är bara skulden. Microsofts tal, och därmed inre lagrets, är alltså ränta på skuld och leasing tillsammans och inte priset på skuld.

| Vem | Nivå | Takt | Förändring i takt | Överraskning (B1) | Senaste kvartal | known_from | Serie |
|---|---|---|---|---|---|---|---|
| Yttre lagret | 5,2 % | – | – | – | 2026Q3 | 2026-11-12 | `kl_rate_eff_outer` |
| Oracle | 4,7 % | +0,5 | +0,7 | +0,5 | 2026Q3 | 2026-09-11 | `kl_rate_eff_orcl` |
| CoreWeave | 6,8 % | – | – | – | 2026Q3 | 2026-11-12 | `kl_rate_eff_crwv` |
| Inre lagret | 4,6 % | – | – | – | 2026Q3 | 2026-10-30 | `kl_rate_eff_inner` |
| Microsoft | 8,2 % | +2,5 | +1,4 | +0,4 | 2026Q3 | 2026-10-28 | `kl_rate_eff_msft` |
| Alphabet | 4,1 % | – | – | – | 2026Q3 | 2026-10-29 | `kl_rate_eff_googl` |
| Amazon | 3,8 % | +0,1 | +0,9 | +0,3 | 2026Q3 | 2026-10-30 | `kl_rate_eff_amzn` |
| Meta | 4,6 % | +1,5 | – | +1,3 | 2026Q3 | 2026-10-22 | `kl_rate_eff_meta` |

CoreWeave, angiven effektiv ränta på utestående skuld (vägd, hela procent i tabellen): **7,9 %** vid 2026Q3 (täckning 100 % av utestående, known_from 2026-11-12, `kl_coupon_out_crwv_q`). Takt: -2,5 procentenheter, förändring i takt +0,6. Konvertibler (angiven ränta 2–3 %) är 22,7 % av utestående. Utan konvertibler: 9,5 % vid 2026Q3 och 10,4 % vid 2025Q3. Med konvertibler: 7,9 % och 10,4 %. Skillnaden visar hur mycket mixen med konvertibler betyder.

Spread vid emission (KR1, registrerade obligationer, bp; oregelbundet, ingår inte i läsregeln):

- Oracle (yttre): 148 bp i 2026Q1, före: 106 bp (2025Q3); known_from 2026-04-01, `spread_issue_orcl_q`
- Meta (inre): 108 bp i 2026Q2, före: 84 bp (2025Q4); known_from 2026-07-01, `spread_issue_meta_q`
- Alphabet (inre): 87 bp i 2026Q3, före: 62 bp (2026Q1); known_from 2026-10-01, `spread_issue_googl_q`
- Amazon (inre): 80 bp i 2026Q3, före: 80 bp (2026Q1); known_from 2026-10-01, `spread_issue_amzn_q`

### 2. Beroende av extern finansiering

**(capex − OCF) / capex**, fyra kvartal, procent av capex:

| Vem | Nivå | Takt | Förändring i takt | Överraskning (B1) | Senaste kvartal | known_from | Serie |
|---|---|---|---|---|---|---|---|
| Yttre lagret | 50,9 % | +8,4 | – | -1,7 | 2026Q3 | 2026-11-12 | `kl_fcfgap_outer` |
| Oracle | 38,0 % | +16,5 | -73,7 | -14,8 | 2026Q3 | 2026-09-11 | `kl_fcfgap_orcl` |
| CoreWeave | 73,9 % | -8,8 | +18,1 | +14,1 | 2026Q3 | 2026-11-12 | `kl_fcfgap_crwv` |
| Nebius | 71,0 % | -49,8 | +27,9 | +37,0 | 2026Q3 | 2026-11-12 | `kl_fcfgap_nbis` |
| IREN | 49,7 % | +10,3 | – | +26,6 | 2026Q3 | 2026-11-05 | `kl_fcfgap_iren` |
| Inre lagret | -10,0 % | +52,8 | +10,1 | +9,3 | 2026Q3 | 2026-10-30 | `kl_fcfgap_inner` |
| Microsoft | -44,1 % | +68,9 | +30,8 | +0,4 | 2026Q3 | 2026-10-28 | `kl_fcfgap_msft` |
| Alphabet | -12,4 % | +82,1 | +11,0 | +13,0 | 2026Q3 | 2026-10-29 | `kl_fcfgap_googl` |
| Amazon | 21,8 % | +30,6 | +6,6 | +10,3 | 2026Q3 | 2026-10-30 | `kl_fcfgap_amzn` |
| Meta | -27,4 % | +44,0 | -11,7 | +5,9 | 2026Q3 | 2026-10-22 | `kl_fcfgap_meta` |

**(emitterad − amorterad skuld) / capex**, fyra kvartal, procent av capex:

| Vem | Nivå | Takt | Förändring i takt | Överraskning (B1) | Senaste kvartal | known_from | Serie |
|---|---|---|---|---|---|---|---|
| Yttre lagret | 57,4 % | +23,3 | +19,9 | -25,3 | 2026Q3 | 2026-11-12 | `kl_netdebt_outer` |
| Oracle | 47,6 % | +30,6 | +20,9 | -36,0 | 2026Q3 | 2026-09-11 | `kl_netdebt_orcl` |
| CoreWeave | 84,5 % | +2,0 | +14,5 | +2,6 | 2026Q3 | 2026-11-12 | `kl_netdebt_crwv` |
| Inre lagret | 43,8 % | +42,2 | +2,5 | -3,6 | 2026Q3 | 2026-10-30 | `kl_netdebt_inner` |
| Microsoft | -5,8 % | -2,5 | -25,6 | -3,8 | 2026Q3 | 2026-10-28 | `kl_netdebt_msft` |
| Alphabet | 60,4 % | +43,7 | -9,3 | -0,4 | 2026Q3 | 2026-10-29 | `kl_netdebt_googl` |
| Amazon | 58,6 % | +63,1 | +12,5 | +1,4 | 2026Q3 | 2026-10-30 | `kl_netdebt_amzn` |
| Meta | 52,5 % | +52,5 | +36,8 | -19,2 | 2026Q3 | 2026-10-22 | `kl_netdebt_meta` |

**tecknade leasingavtal som inte börjat / capex**, fyra kvartal, procent av capex:

| Vem | Nivå | Takt | Förändring i takt | Överraskning (B1) | Senaste kvartal | known_from | Serie |
|---|---|---|---|---|---|---|---|
| Yttre lagret | 324,8 % | -49,0 | -221,1 | -94,8 | 2026Q3 | 2026-11-12 | `kl_leases_outer` |
| Oracle | 380,7 % | +16,6 | -200,2 | -152,1 | 2026Q3 | 2026-09-11 | `kl_leases_orcl` |
| CoreWeave | 171,6 % | -229,5 | -236,9 | +55,0 | 2026Q3 | 2026-11-12 | `kl_leases_crwv` |
| Inre lagret | 135,8 % | +68,4 | +21,6 | -6,9 | 2026Q3 | 2026-10-30 | `kl_leases_inner` |
| Alphabet | 81,7 % | +27,0 | -11,8 | +10,1 | 2026Q3 | 2026-10-29 | `kl_leases_googl` |
| Amazon | 76,6 % | +14,2 | +16,0 | -6,5 | 2026Q3 | 2026-10-30 | `kl_leases_amzn` |
| Meta | 340,6 % | +247,9 | +87,0 | -24,6 | 2026Q3 | 2026-10-22 | `kl_leases_meta` |
| Microsoft | 202,2 % | +40,5 | +121,3 | +16,3 | 2026Q1 | 2026-04-29 | `kl_leases_msft` |
| Microsoft (inkl. villkorade, från 2026Q2) | 268,2 % | – | – | – | 2026Q3 | 2026-10-28 | `kl_leases_msft_cond` |

### 3. Vilja och förmåga att investera

**Capex över fyra kvartal** (takt = årsförändring i log × 100):

| Vem | Nivå | Takt | Förändring i takt | Överraskning (B1) | Senaste kvartal | known_from | Serie |
|---|---|---|---|---|---|---|---|
| Yttre lagret | 125,7 mdr | +113,9 | – | +7,1 | 2026Q3 | 2026-11-12 | `kl_capex4_outer` |
| Oracle | 75,7 mdr | +101,5 | -15,8 | +6,6 | 2026Q3 | 2026-09-11 | `kl_capex4_orcl` |
| CoreWeave | 27,6 mdr | +104,2 | +35,7 | +7,6 | 2026Q3 | 2026-11-12 | `kl_capex4_crwv` |
| Nebius | 17,5 mdr | +197,5 | +44,0 | -2,8 | 2026Q3 | 2026-11-12 | `kl_capex4_nbis` |
| IREN | 4,9 mdr | +203,3 | – | +8,8 | 2026Q3 | 2026-11-05 | `kl_capex4_iren` |
| Inre lagret | 615,4 mdr | +62,4 | +9,6 | +4,6 | 2026Q3 | 2026-10-30 | `kl_capex4_inner` |
| Microsoft | 135,9 mdr | +67,8 | +21,7 | +1,3 | 2026Q3 | 2026-10-28 | `kl_capex4_msft` |
| Alphabet | 159,8 mdr | +71,9 | +7,5 | +1,8 | 2026Q3 | 2026-10-29 | `kl_capex4_googl` |
| Amazon | 215,2 mdr | +58,3 | +9,9 | +9,9 | 2026Q3 | 2026-10-30 | `kl_capex4_amzn` |
| Meta | 104,4 mdr | +51,0 | -3,8 | +2,2 | 2026Q3 | 2026-10-22 | `kl_capex4_meta` |

**Tillskott till RPO över fyra kvartal** (takt = log av tillskottet mot de fyra kvartalen före; klumpigt):

| Vem | Nivå | Takt | Förändring i takt | Överraskning (B1) | Senaste kvartal | known_from | Serie |
|---|---|---|---|---|---|---|---|
| Yttre lagret | 291,0 mdr | – | – | – | 2026Q3 | 2026-11-12 | `kl_rpo_add4_outer` |
| Oracle | 208,7 mdr | -53,5 | -266,9 | -150,6 | 2026Q3 | 2026-09-11 | `kl_rpo_add4_orcl` |
| CoreWeave | 82,3 mdr | – | – | – | 2026Q3 | 2026-11-12 | `kl_rpo_add4_crwv` |
| Inre lagret | 1 073,0 mdr | +150,2 | -38,8 | -40,2 | 2026Q3 | 2026-10-30 | `kl_rpo_add4_inner` |
| Microsoft | 285,0 mdr | +77,0 | -60,4 | -36,3 | 2026Q3 | 2026-10-28 | `kl_rpo_add4_msft` |
| Alphabet | 410,0 mdr | +175,5 | -118,2 | -66,3 | 2026Q3 | 2026-10-29 | `kl_rpo_add4_googl` |
| Amazon | 378,0 mdr | +235,1 | +63,0 | -28,7 | 2026Q3 | 2026-10-30 | `kl_rpo_add4_amzn` |

**CoreWeaves effekt** (MW, takt = log × 100 över fyra kvartal):

| Vem | Nivå | Takt | Förändring i takt | Överraskning (B1) | Senaste kvartal | known_from | Serie |
|---|---|---|---|---|---|---|---|
| CoreWeave, kontrakterad | 4 600 MW | +46,1 | -32,1 | +8,8 | 2026Q3 | 2026-11-10 | `plan_crwv_contracted_power_asof_value` |
| CoreWeave, aktiv | 1 700 MW | +105,8 | +19,1 | -16,5 | 2026Q3 | 2026-11-10 | `plan_crwv_active_power_asof_value` |

**Capex-guidance för kalenderår** (mittpunkt; guidad takt mot föregående års utfall där F1:s definition finns):

- Microsoft 2026: 170,0 mdr–170,0 mdr; known_from 2026-10-28
- Alphabet 2026: 180,0 mdr–190,0 mdr, guidad takt +70,5; known_from 2026-06-04
- Amazon 2026: 220,0 mdr–220,0 mdr; known_from 2026-10-29
- Meta 2026: 135,0 mdr–145,0 mdr, guidad takt +66,2; known_from 2026-10-21

**Riktningskoder** för capex-planer (−2..+2 mot föregående år), uttalade det senaste året:

- `guid_capex_amzn_cy_dir_yoy` 2026: +1 (known_from 2025-10-31)
- `guid_capex_amzn_cy_dir_yoy` 2027: +2 (known_from 2026-10-30)
- `guid_capex_googl_cy_dir_yoy` 2026: +2 (known_from 2025-10-30)
- `guid_capex_googl_cy_dir_yoy` 2027: +2 (known_from 2026-06-04)
- `plan_orcl_capex_y_dir_yoy` 2027: +1 (known_from 2026-06-22)
- `plan_orcl_capex_y_dir_yoy` 2029: -1 (known_from 2026-10-28)
- `plan_googl_capex_y_dir_yoy` 2027: +2 (known_from 2026-06-04)
- `plan_amzn_cash_capex_y_dir_yoy` 2026: +1 (known_from 2025-10-31)
- `plan_amzn_cash_capex_y_dir_yoy` 2027: +2 (known_from 2026-10-30)
- `guid_capex_msft_fy_dir_prior_fy` 2027: +1 (known_from 2026-07-29)

**F1: revideringar av capex-guidance de senaste 365 dagarna** (upp / oförändrad / ned):

- Amazon: 0 / 4 / 0 (senast 2026-07-31)
- Alphabet: 1 / 4 / 0 (senast 2026-10-29)
- Meta: 3 / 0 / 0 (senast 2026-10-21)
- Microsoft: 0 / 0 / 1 (senast 2026-10-28)

### 4. Läsregeln, mekaniskt

Gränser (låsta): A = vid t − 2 har den effektiva räntan en takt ≥ +0,25 procentenheter eller ett beroendemått ≥ +5. Capex-takten föll om förändringen i takt ≤ -5. Lika fall: inre ≤ 0,5 × yttre. En negativ förändring i takt betyder att tillväxten avtar, inte att capex minskar. Utslaget är en beskrivning, inget test.

Regeln läser bara uppgång i pris och beroende: A kräver en takt på minst gränsen. Ett fall i pris och beroende följt av högre capex-takt blir "inget av mönstren". Hur ofta A har gällt står under varje utslag. När A nästan alltid gäller, avgörs utslaget i praktiken av capex-takten. En regel som läser båda riktningarna kräver en ny daterad registerpost.

- **Yttre lagret (huvudläsning):** kan inte avgöras (ett mått som regeln behöver saknas). t = 2026Q3; A = True (takt vid 2026Q1: rate_eff –, fcfgap –, netdebt +3,4, leases +172,1); förändring i capex-takt yttre –, inre +9,6 (2026Q3).
  A har gällt i 4 av 4 kvartal med minst en takt (2025Q4–2026Q3).
  Saknas: kl_rate_eff_outer (takt vid 2026Q1); kl_fcfgap_outer (takt vid 2026Q1); kl_capex4_outer (förändring i takt vid 2026Q3).
- **Oracle mot inre lagret:** talar för mekanismen (pris eller beroende steg först, sedan föll takten i yttre lagret medan det inre höll). t = 2026Q3; A = True (takt vid 2026Q1: rate_eff -0,2, fcfgap +90,2, netdebt +9,7, leases +216,8); förändring i capex-takt yttre -15,8, inre +9,6 (2026Q3).
  A har gällt i 44 av 58 kvartal med minst en takt (2012Q2–2026Q3).
- **CoreWeave mot inre lagret:** talar emot (1): pris eller beroende steg, men takten i yttre lagret höll eller steg. t = 2026Q3; A = True (takt vid 2026Q1: rate_eff –, fcfgap -26,8, netdebt -12,5, leases +7,4); förändring i capex-takt yttre +35,7, inre +9,6 (2026Q3).
  A har gällt i 2 av 4 kvartal med minst en takt (2025Q4–2026Q3).
- **Nebius mot inre lagret:** inget av mönstren. t = 2026Q3; A = False (takt vid 2026Q1: fcfgap -77,7); förändring i capex-takt yttre +44,0, inre +9,6 (2026Q3).
  A har gällt i 0 av 4 kvartal med minst en takt (2025Q4–2026Q3).
- **IREN mot inre lagret:** kan inte avgöras (ett mått som regeln behöver saknas). t = 2026Q3; A = None (takt vid 2026Q1: fcfgap –); förändring i capex-takt yttre –, inre +9,6 (2026Q3).
  A har gällt i 1 av 2 kvartal med minst en takt (2026Q2–2026Q3).
  Saknas: kl_fcfgap_iren (takt vid 2026Q1); kl_capex4_iren (förändring i takt vid 2026Q3).

### 5. Labben och utvecklar- och SPV-kanalen (tabellrader ur inlämningarna)

- **Anthropic** (S-1 och ändringar, första 2026-10-26). Läge 2026-09-30:
  - säkerställd revolverande kreditfacilitet: 15,0 mdr (2026-09; known_from 2026-11-02)
  - konvertibelram för hyra (Broadcom), PIK: 42,0 mdr (2026-09-30, kupong 9,00 %; known_from 2026-11-02)
  - ram Google 2026: 20,0 mdr (2026-09-30, kupong 9,00 % för lån före noteringen; efter noteringen ska villkoren avtalas; known_from 2026-11-02)
  - ram Amazon 2026: 15,0 mdr (2026-09-30, kupong 8,00 % för lån före noteringen; efter noteringen regleras dragningar i aktier; known_from 2026-11-02)
  - utestående konvertibla lån till Amazon: 6,2 mdr, räntefria (known_from 2026-11-02)
  - köpåtaganden i tabellen: 313,8 mdr (known_from 2026-11-02)
  - leasingavtal som inte börjat, cirka: 451,2 mdr (known_from 2026-11-02)
  - åtaganden totalt enligt bolaget, cirka: 900,9 mdr (known_from 2026-11-10)
  - köpåtaganden per år 2026–2030: 5,1 mdr, 28,4 mdr, 43,5 mdr, 46,9 mdr, 44,2 mdr
  - åtaganden för beräkningskraft per motpart (avtalsmånad): Microsoft minst 47,2 mdr (2025-11), Google minst 121,3 mdr (2026-03), Amazon minst 110,0 mdr (2026-04), SpaceXAI (SpaceX) upp till 120,5 mdr (2026-05), Nscale upp till 44,6 mdr (2026-08), Lambda cirka 41,3 mdr (2026-05); known_from senast 2026-11-10
- OpenAI: ingen registreringsansökan på EDGAR (sökning på namnet 2026-11-25: bara fonder och SPV med Form D).
- **SpaceX** (äger xAI sedan 2026-02-02; 10-Q). Skulden gäller hela koncernen: uppskjutning, Starlink och xAI. Läge 2026-09-30:
  - total skuld 38,0 mdr; SpaceX Notes 25,0 mdr (effektiv ränta 6,07 %, vägd kupong 5,855 %, emitterade 2026-06); övrig finansiering 13,0 mdr, varav misslyckade sale-leaseback av AI-hårdvara med Valor (närstående) 12,9 mdr; known_from 2026-10-22
  - ränta på övrig finansiering: räntekostnaden för Valor-avtalen var 351 MUSD under 2026Q3, cirka 10,7 % per år av Valor-skulden i snitt (2026-06-30 och 2026-09-30). Bolaget anger 6,3 % i vägd fast ränta för sina övriga finansieringsavtal, som oftast har maskiner och utrustning som säkerhet. Om Valor-skulden ingår i den räntan framgår inte (known_from 2026-10-22)
  - kreditfacilitet upp till 5,0 mdr (2026-05, utan säkerhet; known_from 2026-08-04)
  - xAI:s egna lån före köpet (2025-06): säkerställda obligationer 3,0 mdr med 12,5 %, terminslån 1,0 mdr med 12,50 % och 1,0 mdr med SOFR + 725 bp; inte kvar i tabellen per 2026-09-30
- **Meta, datacenterbolag** (Louisiana, med fonder förvaltade av Blue Owl; Texas från 2026-07). Per balansdag:
  - 2025-12-31: största möjliga förlust 46,0 mdr (known_from 2026-01-29)
  - 2026-03-31: största möjliga förlust 46,0 mdr (known_from 2026-04-30)
  - 2026-06-30: största möjliga förlust 46,0 mdr (known_from 2026-07-30)
  - 2026-09-30: leasingåtaganden 18,5 mdr, restvärdesgarantier 41,5 mdr, största möjliga förlust 68,4 mdr (known_from 2026-10-22)
- Oracle: inga belopp för datacenter-SPV eller samriskbolag i 10-Q och 10-K 2025–2026.
- **CoreWeave, nya obligationer** (8-K, senaste sex; konvertibler ingår inte i kupongmåttet):
  - 2026-04-14: 2031 9 75 senior notes, 1 750 MUSD, kupong 9,750 % (known_from 2026-04-21)
  - 2026-04-14: 2032 convertible senior notes, 4 000 MUSD, kupong 1,750 % (known_from 2026-04-14)
  - 2026-04-21: 2031 9 75 senior notes addon, 1 000 MUSD, kupong 9,750 % (known_from 2026-04-21)
  - 2026-06-18: 2032 9 625 senior notes, 1 250 MUSD, kupong 9,625 % (known_from 2026-06-18)
  - 2026-06-18: 2032 eur senior notes, 2 000 MEUR, kupong 8,500 % (known_from 2026-06-18)
  - 2026-09-22: 2033 convertible senior notes, 4 200 MUSD, kupong 2,875 % (known_from 2026-09-22)
- CoreWeave, marginal över SOFR för lånefaciliteter (bp): ddtl 3 0 facility 400, ddtl 2 0 facility 1 300 (före femte tillägget och utan investment grade; med investment grade 600–650), ddtl 2 0 facility incremental 425, ddtl 4 0 facility 225, ddtl 5 0 facility 450, ddtl 5 5 facility 550

### 6. Att bevaka

Nästa inlämning per bolag, uppskattad som nästa kvartals slut plus medianen av avståndet för de åtta senaste inlämningarna:

- Nvidia: 2026Q3 omkring 2026-11-25 (väntas nu, inte i tabellen ännu; därefter 2026Q4 omkring 2027-02-25) (median 56 dagar, spann 50–58, senast 2026-08-26)
- Oracle: 2026Q4 omkring 2026-12-11 (median -20 dagar, spann -21–-8, senast 2026-09-11)
- Microsoft: 2026Q4 omkring 2027-01-29 (median 29 dagar, spann 28–30, senast 2026-10-28)
- Alphabet: 2026Q4 omkring 2027-01-29 (median 29 dagar, spann 23–36, senast 2026-10-29)
- Meta: 2026Q4 omkring 2027-01-30 (median 30 dagar, spann 22–31, senast 2026-10-22)
- Amazon: 2026Q4 omkring 2027-01-31 (median 31 dagar, spann 30–38, senast 2026-10-30)
- IREN: 2026Q4 omkring 2027-02-06 (median 37 dagar, spann 36–58, senast 2026-11-05)
- Nebius: 2026Q4 omkring 2027-02-12 (median 43 dagar, spann 38–129, senast 2026-11-12)
- CoreWeave: 2026Q4 omkring 2027-02-13 (median 44 dagar, spann 38–61, senast 2026-11-12)
- Anthropic: första periodrapporten efter börsnoteringen; ingen historik att uppskatta från.

### 7. Förbehåll

- Med cirka 8–12 kvartal per mått är detta en beskrivning och inget test. Ett mönster kan vara slump.
- RPO är klumpig: enstaka mycket stora avtal flyttar ett kvartal.
- Neomolnens serier börjar 2024, så yttre lagrets takt och förändring i takt finns bara för de senaste kvartalen. Nebius och IREN saknar skuldserier och ingår bara i capex och (capex − OCF) / capex.
- Den effektiva räntan är efter aktiverad ränta. Microsofts räntekostnad innehåller ränta på finansiell leasing. CoreWeaves räntor i skuldtabellen står i hela procent. Konvertiblerna sänker den vägda räntan (avsnitt 1).
- Regeln läser bara uppgång i pris och beroende. Hur ofta A har gällt står i avsnitt 4.
- Utanför ramen: privat kredit utanför EDGAR, labbens oregistrerade skuld, spreadar på andrahandsmarknaden (licens) och 144A-affärer utan 8-K. OpenAI har ingen registreringsansökan på EDGAR. SpaceX:s skuld gäller hela koncernen (uppskjutning, Starlink och xAI).
- Nyhetsuppgifter om kreditbetyg (KBRA, Moody's) är sekundära och används inte som data.
### 8. Tillägg S1: symmetrisk läsning bredvid den låsta

Registret: `docs/mattregister.md`, 2026-11-27 S1, punkt 1. F0:s symmetriska regel per pris- och beroendemått: X = måttets takt (gräns ±0,25 procentenheter för räntan och ±5 för beroendemåtten, KL1:s gränser), Y = förändringen i capex-takt för samma enhet (gräns ±5), fönster 2 kvartal efter ursprunget, tecken −. En rad per mått, ingen sammanslagning med "eller". Avsnitt 1–7 ovan är den låsta läsningen och är oförändrade, och huvudläsningen är fortfarande den låsta (avsnitt 4). Det här avsnittet är ett tillägg.

- **Talar för, uppåt:** pris eller beroende steg (X ≥ +g) och capex-takten föll sedan (Y ≤ −5). **Talar för, nedåt:** pris eller beroende föll (X ≤ −g) och capex-takten steg sedan (Y ≥ +5).
- **Talar emot:** capex-takten följde X åt samma håll.
- En negativ förändring i takt betyder att tillväxten avtar, inte att capex minskar. Utslaget är en beskrivning, inget test.

Beroendemåtten har capex över samma fyra kvartal i sig. (capex − OCF) / capex stiger när capex växer snabbare än kassaflödet, så en acceleration i capex ger lätt "talar emot, uppåt". Nettoemission och leasing har capex i nämnaren och faller när capex accelererar, så samma acceleration ger lätt "talar för, nedåt". Utslagen för beroendemåtten är därför svaga belägg åt båda hållen. Räntan har ingen sådan koppling men kort historik.

Impulser nedåt i historiken: i 12 av 18 rader (15 rader har X i historiken). Antalet per rad och riktning står under varje rad.

Alla rader vilar bara på värden som var kända före registerposten 2026-11-27, och KL1:s takter vid t − 2 var sedda före posten (S1, punkt 6). Ingen av raderna är därför ett utfall på osedda data (S1, punkt 4).

**Yttre lagret** (Y = `kl_capex4_outer`):

- **Effektiv ränta:** kan inte avgöras. t = 2026Q3 (X saknas vid 2026Q1; X saknas vid 2026Q2). X = kl_rate_eff_outer (takt), Y = kl_capex4_outer (förändring i takt); fönster 2 kvartal, tecken −.
  Regeln kunde inte prövas: X saknas i hela historiken.
  `kl_capex4_outer` har ingen förändring i takt på dagen (serien är för kort), så Y saknas i varje fönster.
- **(capex − OCF) / capex:** kan inte avgöras. t = 2026Q3; ursprung 2026Q2, X +15,2 (gräns ±5,0), uppgång (Y saknas vid 2026Q3). X = kl_fcfgap_outer (takt), Y = kl_capex4_outer (förändring i takt); fönster 2 kvartal, tecken −.
  Regeln kunde prövas i 0 av 1 ursprung med X (2026Q2–2026Q2). Impulser uppåt 1 (för 0, emot 0, inget 0, kan inte avgöras 1), nedåt 0 (för 0, emot 0, inget 0, kan inte avgöras 0), utan impuls 0.
  Y var känt i hela fönstret i 0 av 1 ursprung, och 0 av 1 impulser kunde läsas mot Y. Riktningen nedåt har inte prövats: X har inte haft någon impuls nedåt.
  Övergång (registret 2026-11-27 S1, punkt 3): ett ursprung räknas nu som prövat bara när Y finns i fönstret. Med F0:s räkning före S1: 0 av 1; med den nya: 0 av 1. Bytet väntar på ägarens bekräftelse (R29-1, registret 2026-11-27 X26, punkt 1).
  `kl_capex4_outer` har ingen förändring i takt på dagen (serien är för kort), så Y saknas i varje fönster.
- **(emitterad − amorterad skuld) / capex:** kan inte avgöras. t = 2026Q3; ursprung 2026Q2, X +36,0 (gräns ±5,0), uppgång (Y saknas vid 2026Q3). X = kl_netdebt_outer (takt), Y = kl_capex4_outer (förändring i takt); fönster 2 kvartal, tecken −.
  Regeln kunde prövas i 0 av 3 ursprung med X (2025Q4–2026Q2). Impulser uppåt 2 (för 0, emot 0, inget 0, kan inte avgöras 2), nedåt 0 (för 0, emot 0, inget 0, kan inte avgöras 0), utan impuls 1.
  Y var känt i hela fönstret i 0 av 3 ursprung, och 0 av 2 impulser kunde läsas mot Y. Riktningen nedåt har inte prövats: X har inte haft någon impuls nedåt.
  Övergång (registret 2026-11-27 S1, punkt 3): ett ursprung räknas nu som prövat bara när Y finns i fönstret. Med F0:s räkning före S1: 1 av 3; med den nya: 0 av 3. Bytet väntar på ägarens bekräftelse (R29-1, registret 2026-11-27 X26, punkt 1).
  `kl_capex4_outer` har ingen förändring i takt på dagen (serien är för kort), så Y saknas i varje fönster.
- **Leasingavtal som inte börjat / capex:** kan inte avgöras. t = 2026Q3; ursprung 2026Q2, X +127,8 (gräns ±5,0), uppgång (Y saknas vid 2026Q3). X = kl_leases_outer (takt), Y = kl_capex4_outer (förändring i takt); fönster 2 kvartal, tecken −.
  Regeln kunde prövas i 0 av 2 ursprung med X (2026Q1–2026Q2). Impulser uppåt 2 (för 0, emot 0, inget 0, kan inte avgöras 2), nedåt 0 (för 0, emot 0, inget 0, kan inte avgöras 0), utan impuls 0.
  Y var känt i hela fönstret i 0 av 2 ursprung, och 0 av 2 impulser kunde läsas mot Y. Riktningen nedåt har inte prövats: X har inte haft någon impuls nedåt.
  Övergång (registret 2026-11-27 S1, punkt 3): ett ursprung räknas nu som prövat bara när Y finns i fönstret. Med F0:s räkning före S1: 0 av 2; med den nya: 0 av 2. Bytet väntar på ägarens bekräftelse (R29-1, registret 2026-11-27 X26, punkt 1).
  `kl_capex4_outer` har ingen förändring i takt på dagen (serien är för kort), så Y saknas i varje fönster.

**Inre lagret** (Y = `kl_capex4_inner`):

- **Effektiv ränta:** kan inte avgöras. t = 2026Q3 (X saknas vid 2026Q1; X saknas vid 2026Q2). X = kl_rate_eff_inner (takt), Y = kl_capex4_inner (förändring i takt); fönster 2 kvartal, tecken −.
  Regeln kunde inte prövas: X saknas i hela historiken.
- **(capex − OCF) / capex:** talar emot, uppåt. t = 2026Q3; ursprung 2026Q2, X +40,0 (gräns ±5,0), uppgång, Y +9,6 vid 2026Q3 (gräns ±5,0). X = kl_fcfgap_inner (takt), Y = kl_capex4_inner (förändring i takt); fönster 2 kvartal, tecken −.
  Regeln kunde prövas i 28 av 29 ursprung med X (2019Q2–2026Q2). Impulser uppåt 19 (för 8, emot 8, inget 3, kan inte avgöras 0), nedåt 9 (för 5, emot 3, inget 0, kan inte avgöras 1), utan impuls 1.
  Y var känt i hela fönstret i 27 av 29 ursprung, och 27 av 28 impulser kunde läsas mot Y.
  Övergång (registret 2026-11-27 S1, punkt 3): ett ursprung räknas nu som prövat bara när Y finns i fönstret. Med F0:s räkning före S1: 28 av 29; med den nya: 28 av 29. Bytet väntar på ägarens bekräftelse (R29-1, registret 2026-11-27 X26, punkt 1).
- **(emitterad − amorterad skuld) / capex:** talar emot, uppåt. t = 2026Q3; ursprung 2026Q2, X +33,8 (gräns ±5,0), uppgång, Y +9,6 vid 2026Q3 (gräns ±5,0). X = kl_netdebt_inner (takt), Y = kl_capex4_inner (förändring i takt); fönster 2 kvartal, tecken −.
  Regeln kunde prövas i 28 av 29 ursprung med X (2019Q2–2026Q2). Impulser uppåt 14 (för 4, emot 7, inget 3, kan inte avgöras 0), nedåt 9 (för 5, emot 3, inget 0, kan inte avgöras 1), utan impuls 6.
  Y var känt i hela fönstret i 27 av 29 ursprung, och 22 av 23 impulser kunde läsas mot Y.
  Övergång (registret 2026-11-27 S1, punkt 3): ett ursprung räknas nu som prövat bara när Y finns i fönstret. Med F0:s räkning före S1: 28 av 29; med den nya: 28 av 29. Bytet väntar på ägarens bekräftelse (R29-1, registret 2026-11-27 X26, punkt 1).
- **Leasingavtal som inte börjat / capex:** talar emot, uppåt. t = 2026Q3; ursprung 2026Q2, X +62,9 (gräns ±5,0), uppgång, Y +9,6 vid 2026Q3 (gräns ±5,0). X = kl_leases_inner (takt), Y = kl_capex4_inner (förändring i takt); fönster 2 kvartal, tecken −.
  Regeln kunde prövas i 19 av 19 ursprung med X (2021Q4–2026Q2). Impulser uppåt 11 (för 0, emot 9, inget 2, kan inte avgöras 0), nedåt 7 (för 0, emot 7, inget 0, kan inte avgöras 0), utan impuls 1.
  Y var känt i hela fönstret i 18 av 19 ursprung, och 18 av 18 impulser kunde läsas mot Y.
  Övergång (registret 2026-11-27 S1, punkt 3): ett ursprung räknas nu som prövat bara när Y finns i fönstret. Med F0:s räkning före S1: 19 av 19; med den nya: 19 av 19. Bytet väntar på ägarens bekräftelse (R29-1, registret 2026-11-27 X26, punkt 1).

**Oracle** (Y = `kl_capex4_orcl`):

- **Effektiv ränta:** inget av mönstren. t = 2026Q3 (ingen impuls i fönstret). X = kl_rate_eff_orcl (takt), Y = kl_capex4_orcl (förändring i takt); fönster 2 kvartal, tecken −.
  Regeln kunde prövas i 20 av 21 ursprung med X (2021Q2–2026Q2). Impulser uppåt 3 (för 3, emot 0, inget 0, kan inte avgöras 0), nedåt 1 (för 1, emot 0, inget 0, kan inte avgöras 0), utan impuls 17.
  Y var känt i hela fönstret i 20 av 21 ursprung, och 4 av 4 impulser kunde läsas mot Y.
  Övergång (registret 2026-11-27 S1, punkt 3): ett ursprung räknas nu som prövat bara när Y finns i fönstret. Med F0:s räkning före S1: 21 av 21; med den nya: 20 av 21. Bytet väntar på ägarens bekräftelse (R29-1, registret 2026-11-27 X26, punkt 1).
- **(capex − OCF) / capex:** talar för mekanismen, uppåt. t = 2026Q3; ursprung 2026Q2, X +40,7 (gräns ±5,0), uppgång, Y -15,8 vid 2026Q3 (gräns ±5,0). X = kl_fcfgap_orcl (takt), Y = kl_capex4_orcl (förändring i takt); fönster 2 kvartal, tecken −.
  Regeln kunde prövas i 56 av 57 ursprung med X (2012Q2–2026Q2). Impulser uppåt 38 (för 14, emot 23, inget 0, kan inte avgöras 1), nedåt 17 (för 9, emot 8, inget 0, kan inte avgöras 0), utan impuls 2.
  Y var känt i hela fönstret i 55 av 57 ursprung, och 54 av 55 impulser kunde läsas mot Y.
  Övergång (registret 2026-11-27 S1, punkt 3): ett ursprung räknas nu som prövat bara när Y finns i fönstret. Med F0:s räkning före S1: 56 av 57; med den nya: 56 av 57. Bytet väntar på ägarens bekräftelse (R29-1, registret 2026-11-27 X26, punkt 1).
- **(emitterad − amorterad skuld) / capex:** talar för mekanismen, uppåt. t = 2026Q3; ursprung 2026Q2, X +52,9 (gräns ±5,0), uppgång, Y -15,8 vid 2026Q3 (gräns ±5,0). X = kl_netdebt_orcl (takt), Y = kl_capex4_orcl (förändring i takt); fönster 2 kvartal, tecken −.
  Regeln kunde prövas i 41 av 41 ursprung med X (2016Q2–2026Q2). Impulser uppåt 17 (för 5, emot 12, inget 0, kan inte avgöras 0), nedåt 24 (för 12, emot 12, inget 0, kan inte avgöras 0), utan impuls 0.
  Y var känt i hela fönstret i 40 av 41 ursprung, och 41 av 41 impulser kunde läsas mot Y.
  Övergång (registret 2026-11-27 S1, punkt 3): ett ursprung räknas nu som prövat bara när Y finns i fönstret. Med F0:s räkning före S1: 41 av 41; med den nya: 41 av 41. Bytet väntar på ägarens bekräftelse (R29-1, registret 2026-11-27 X26, punkt 1).
- **Leasingavtal som inte börjat / capex:** talar för mekanismen, uppåt. t = 2026Q3; ursprung 2026Q2, X +262,5 (gräns ±5,0), uppgång, Y -15,8 vid 2026Q3 (gräns ±5,0). X = kl_leases_orcl (takt), Y = kl_capex4_orcl (förändring i takt); fönster 2 kvartal, tecken −.
  Regeln kunde prövas i 7 av 7 ursprung med X (2024Q4–2026Q2). Impulser uppåt 5 (för 3, emot 2, inget 0, kan inte avgöras 0), nedåt 2 (för 2, emot 0, inget 0, kan inte avgöras 0), utan impuls 0.
  Y var känt i hela fönstret i 6 av 7 ursprung, och 7 av 7 impulser kunde läsas mot Y.
  Övergång (registret 2026-11-27 S1, punkt 3): ett ursprung räknas nu som prövat bara när Y finns i fönstret. Med F0:s räkning före S1: 7 av 7; med den nya: 7 av 7. Bytet väntar på ägarens bekräftelse (R29-1, registret 2026-11-27 X26, punkt 1).

**CoreWeave** (Y = `kl_capex4_crwv`):

- **Effektiv ränta:** kan inte avgöras. t = 2026Q3 (X saknas vid 2026Q1; X saknas vid 2026Q2). X = kl_rate_eff_crwv (takt), Y = kl_capex4_crwv (förändring i takt); fönster 2 kvartal, tecken −.
  Regeln kunde inte prövas: X saknas i hela historiken.
- **(capex − OCF) / capex:** talar för mekanismen, nedåt. t = 2026Q3; ursprung 2026Q2, X -26,2 (gräns ±5,0), nedgång, Y +35,7 vid 2026Q3 (gräns ±5,0). X = kl_fcfgap_crwv (takt), Y = kl_capex4_crwv (förändring i takt); fönster 2 kvartal, tecken −.
  Regeln kunde prövas i 2 av 3 ursprung med X (2025Q4–2026Q2). Impulser uppåt 0 (för 0, emot 0, inget 0, kan inte avgöras 0), nedåt 2 (för 2, emot 0, inget 0, kan inte avgöras 0), utan impuls 1.
  Y var känt i hela fönstret i 1 av 3 ursprung, och 2 av 2 impulser kunde läsas mot Y. Riktningen uppåt har inte prövats: X har inte haft någon impuls uppåt.
  Övergång (registret 2026-11-27 S1, punkt 3): ett ursprung räknas nu som prövat bara när Y finns i fönstret. Med F0:s räkning före S1: 3 av 3; med den nya: 2 av 3. Bytet väntar på ägarens bekräftelse (R29-1, registret 2026-11-27 X26, punkt 1).
- **(emitterad − amorterad skuld) / capex:** talar för mekanismen, nedåt. t = 2026Q3; ursprung 2026Q1, X -12,5 (gräns ±5,0), nedgång, Y +70,6 vid 2026Q2 (gräns ±5,0). X = kl_netdebt_crwv (takt), Y = kl_capex4_crwv (förändring i takt); fönster 2 kvartal, tecken −.
  Regeln kunde prövas i 1 av 3 ursprung med X (2025Q4–2026Q2). Impulser uppåt 1 (för 0, emot 0, inget 0, kan inte avgöras 1), nedåt 1 (för 1, emot 0, inget 0, kan inte avgöras 0), utan impuls 1.
  Y var känt i hela fönstret i 1 av 3 ursprung, och 1 av 2 impulser kunde läsas mot Y.
  Övergång (registret 2026-11-27 S1, punkt 3): ett ursprung räknas nu som prövat bara när Y finns i fönstret. Med F0:s räkning före S1: 2 av 3; med den nya: 1 av 3. Bytet väntar på ägarens bekräftelse (R29-1, registret 2026-11-27 X26, punkt 1).
- **Leasingavtal som inte börjat / capex:** talar för mekanismen, nedåt. t = 2026Q3; ursprung 2026Q2, X -224,0 (gräns ±5,0), nedgång, Y +35,7 vid 2026Q3 (gräns ±5,0). X = kl_leases_crwv (takt), Y = kl_capex4_crwv (förändring i takt); fönster 2 kvartal, tecken −.
  Regeln kunde prövas i 2 av 2 ursprung med X (2026Q1–2026Q2). Impulser uppåt 1 (för 0, emot 1, inget 0, kan inte avgöras 0), nedåt 1 (för 1, emot 0, inget 0, kan inte avgöras 0), utan impuls 0.
  Y var känt i hela fönstret i 1 av 2 ursprung, och 2 av 2 impulser kunde läsas mot Y.
  Övergång (registret 2026-11-27 S1, punkt 3): ett ursprung räknas nu som prövat bara när Y finns i fönstret. Med F0:s räkning före S1: 2 av 2; med den nya: 2 av 2. Bytet väntar på ägarens bekräftelse (R29-1, registret 2026-11-27 X26, punkt 1).

**Nebius** (Y = `kl_capex4_nbis`):

- **(capex − OCF) / capex:** talar för mekanismen, nedåt. t = 2026Q3; ursprung 2026Q2, X -75,2 (gräns ±5,0), nedgång, Y +44,0 vid 2026Q3 (gräns ±5,0). X = kl_fcfgap_nbis (takt), Y = kl_capex4_nbis (förändring i takt); fönster 2 kvartal, tecken −.
  Regeln kunde prövas i 2 av 3 ursprung med X (2025Q4–2026Q2). Impulser uppåt 0 (för 0, emot 0, inget 0, kan inte avgöras 0), nedåt 3 (för 2, emot 0, inget 0, kan inte avgöras 1), utan impuls 0.
  Y var känt i hela fönstret i 1 av 3 ursprung, och 2 av 3 impulser kunde läsas mot Y. Riktningen uppåt har inte prövats: X har inte haft någon impuls uppåt.
  Övergång (registret 2026-11-27 S1, punkt 3): ett ursprung räknas nu som prövat bara när Y finns i fönstret. Med F0:s räkning före S1: 2 av 3; med den nya: 2 av 3. Bytet väntar på ägarens bekräftelse (R29-1, registret 2026-11-27 X26, punkt 1).

**IREN** (Y = `kl_capex4_iren`):

- **(capex − OCF) / capex:** kan inte avgöras. t = 2026Q3; ursprung 2026Q2, X -27,2 (gräns ±5,0), nedgång (Y saknas vid 2026Q3). X = kl_fcfgap_iren (takt), Y = kl_capex4_iren (förändring i takt); fönster 2 kvartal, tecken −.
  Regeln kunde prövas i 0 av 1 ursprung med X (2026Q2–2026Q2). Impulser uppåt 0 (för 0, emot 0, inget 0, kan inte avgöras 0), nedåt 1 (för 0, emot 0, inget 0, kan inte avgöras 1), utan impuls 0.
  Y var känt i hela fönstret i 0 av 1 ursprung, och 0 av 1 impulser kunde läsas mot Y. Riktningen uppåt har inte prövats: X har inte haft någon impuls uppåt.
  Övergång (registret 2026-11-27 S1, punkt 3): ett ursprung räknas nu som prövat bara när Y finns i fönstret. Med F0:s räkning före S1: 0 av 1; med den nya: 0 av 1. Bytet väntar på ägarens bekräftelse (R29-1, registret 2026-11-27 X26, punkt 1).
  `kl_capex4_iren` har ingen förändring i takt på dagen (serien är för kort), så Y saknas i varje fönster.

## Kreditlagret per 2025-11-27

**Frågan:** Ändras finansieringens pris och tillgång i de yttre lagren, och följer investeringstakten där med?

Yttre lagret: Oracle, CoreWeave, Nebius och IREN, och labben som tabellrader. Inre lagret: Microsoft, Alphabet, Amazon och Meta. Takt = förändring över fyra kvartal (procentenheter för andelar och räntor, log × 100 för belopp). Förändring i takt = mot två kvartal tidigare. Överraskning = mot den naiva baslinjen B1 (samma takt som de fyra senaste kvartalen). Bara data kända på dagen. Registret: `docs/mattregister.md`, 2026-11-25 KL1.

### 1. Pris på skuld

Effektiv ränta = räntekostnad över fyra kvartal / genomsnittlig långfristig skuld (efter aktiverad ränta, så den blir lägre hos bolag som bygger mycket). Microsofts räntekostnad innehåller ränta på finansiell leasing, men nämnaren är bara skulden. Microsofts tal, och därmed inre lagrets, är alltså ränta på skuld och leasing tillsammans och inte priset på skuld.

| Vem | Nivå | Takt | Förändring i takt | Överraskning (B1) | Senaste kvartal | known_from | Serie |
|---|---|---|---|---|---|---|---|
| Yttre lagret | – | – | – | – | – | – | `kl_rate_eff_outer` |
| Oracle | 4,2 % | +0,1 | +0,4 | +0,2 | 2025Q3 | 2025-09-10 | `kl_rate_eff_orcl` |
| CoreWeave | – | – | – | – | – | – | `kl_rate_eff_crwv` |
| Inre lagret | – | – | – | – | – | – | `kl_rate_eff_inner` |
| Microsoft | 5,7 % | -0,9 | -0,7 | +0,5 | 2025Q3 | 2025-10-29 | `kl_rate_eff_msft` |
| Alphabet | – | – | – | – | – | – | `kl_rate_eff_googl` |
| Amazon | 3,8 % | -0,2 | +0,5 | +0,1 | 2025Q3 | 2025-10-31 | `kl_rate_eff_amzn` |
| Meta | – | – | – | – | – | – | `kl_rate_eff_meta` |

CoreWeave, angiven effektiv ränta på utestående skuld (vägd, hela procent i tabellen): **10,4 %** vid 2025Q3 (täckning 92 % av utestående, known_from 2025-11-13, `kl_coupon_out_crwv_q`). Takt: – procentenheter, förändring i takt –. Inga konvertibler i skuldtabellen.

Spread vid emission (KR1, registrerade obligationer, bp; oregelbundet, ingår inte i läsregeln):

- Oracle (yttre): 106 bp i 2025Q3, före: 98 bp (2025Q1); known_from 2025-10-01, `spread_issue_orcl_q`
- Meta (inre): 101 bp i 2024Q3, före: 150 bp (2023Q2); known_from 2024-10-01, `spread_issue_meta_q`
- Alphabet (inre): 56 bp i 2025Q2, före: 73 bp (2020Q3); known_from 2025-07-01, `spread_issue_googl_q`
- Amazon (inre): 65 bp i 2022Q4, före: 75 bp (2022Q2); known_from 2023-01-01, `spread_issue_amzn_q`

### 2. Beroende av extern finansiering

**(capex − OCF) / capex**, fyra kvartal, procent av capex:

| Vem | Nivå | Takt | Förändring i takt | Överraskning (B1) | Senaste kvartal | known_from | Serie |
|---|---|---|---|---|---|---|---|
| Yttre lagret | – | – | – | – | – | – | `kl_fcfgap_outer` |
| Oracle | 21,4 % | +164,9 | -1,1 | -23,9 | 2025Q3 | 2025-09-10 | `kl_fcfgap_orcl` |
| CoreWeave | – | – | – | – | – | – | `kl_fcfgap_crwv` |
| Nebius | – | – | – | – | – | – | `kl_fcfgap_nbis` |
| IREN | – | – | – | – | – | – | `kl_fcfgap_iren` |
| Inre lagret | -62,8 % | +49,7 | -14,6 | -9,0 | 2025Q3 | 2025-10-31 | `kl_fcfgap_inner` |
| Microsoft | -113,0 % | +33,8 | -31,6 | -16,0 | 2025Q3 | 2025-10-29 | `kl_fcfgap_msft` |
| Alphabet | -94,5 % | +18,8 | -33,4 | -4,2 | 2025Q3 | 2025-10-30 | `kl_fcfgap_googl` |
| Amazon | -8,8 % | +52,8 | -10,4 | -13,4 | 2025Q3 | 2025-10-31 | `kl_fcfgap_amzn` |
| Meta | -71,5 % | +100,5 | +33,1 | +5,3 | 2025Q3 | 2025-10-30 | `kl_fcfgap_meta` |

**(emitterad − amorterad skuld) / capex**, fyra kvartal, procent av capex:

| Vem | Nivå | Takt | Förändring i takt | Överraskning (B1) | Senaste kvartal | known_from | Serie |
|---|---|---|---|---|---|---|---|
| Yttre lagret | – | – | – | – | – | – | `kl_netdebt_outer` |
| Oracle | 17,0 % | +74,3 | -49,7 | -17,6 | 2025Q3 | 2025-09-10 | `kl_netdebt_orcl` |
| CoreWeave | – | – | – | – | – | – | `kl_netdebt_crwv` |
| Inre lagret | 1,6 % | +5,9 | +17,6 | -6,4 | 2025Q3 | 2025-10-31 | `kl_netdebt_inner` |
| Microsoft | -3,3 % | +19,4 | +63,8 | +0,3 | 2025Q3 | 2025-10-29 | `kl_netdebt_msft` |
| Alphabet | 16,8 % | +18,2 | +9,9 | -11,0 | 2025Q3 | 2025-10-30 | `kl_netdebt_googl` |
| Amazon | -4,6 % | +5,4 | +9,2 | +1,2 | 2025Q3 | 2025-10-31 | `kl_netdebt_amzn` |
| Meta | 0,0 % | -34,3 | -26,3 | -25,0 | 2025Q3 | 2025-10-30 | `kl_netdebt_meta` |

**tecknade leasingavtal som inte börjat / capex**, fyra kvartal, procent av capex:

| Vem | Nivå | Takt | Förändring i takt | Överraskning (B1) | Senaste kvartal | known_from | Serie |
|---|---|---|---|---|---|---|---|
| Yttre lagret | – | – | – | – | – | – | `kl_leases_outer` |
| Oracle | 364,0 % | -96,8 | -106,6 | +191,7 | 2025Q3 | 2025-09-10 | `kl_leases_orcl` |
| CoreWeave | – | – | – | – | – | – | `kl_leases_crwv` |
| Inre lagret | 67,4 % | +17,3 | -4,8 | -3,0 | 2025Q3 | 2025-10-31 | `kl_leases_inner` |
| Alphabet | 54,7 % | +42,3 | +21,8 | +13,0 | 2025Q3 | 2025-10-30 | `kl_leases_googl` |
| Amazon | 62,4 % | -9,7 | -13,0 | -0,8 | 2025Q3 | 2025-10-31 | `kl_leases_amzn` |
| Meta | 92,7 % | +31,9 | -25,5 | -27,9 | 2025Q3 | 2025-10-30 | `kl_leases_meta` |
| Microsoft | 153,9 % | -80,8 | +0,8 | +40,1 | 2025Q3 | 2025-10-29 | `kl_leases_msft` |
| Microsoft (inkl. villkorade, från 2026Q2) | – | – | – | – | – | – | `kl_leases_msft_cond` |

### 3. Vilja och förmåga att investera

**Capex över fyra kvartal** (takt = årsförändring i log × 100):

| Vem | Nivå | Takt | Förändring i takt | Överraskning (B1) | Senaste kvartal | known_from | Serie |
|---|---|---|---|---|---|---|---|
| Yttre lagret | – | – | – | – | – | – | `kl_capex4_outer` |
| Oracle | 27,4 mdr | +125,0 | +33,5 | -2,6 | 2025Q3 | 2025-09-10 | `kl_capex4_orcl` |
| CoreWeave | – | – | – | – | – | – | `kl_capex4_crwv` |
| Nebius | – | – | – | – | – | – | `kl_capex4_nbis` |
| IREN | – | – | – | – | – | – | `kl_capex4_iren` |
| Inre lagret | 329,8 mdr | +50,5 | +2,0 | -0,1 | 2025Q3 | 2025-10-31 | `kl_capex4_inner` |
| Microsoft | 69,0 mdr | +33,3 | -10,6 | -2,6 | 2025Q3 | 2025-10-29 | `kl_capex4_msft` |
| Alphabet | 77,9 mdr | +45,8 | +3,9 | +4,7 | 2025Q3 | 2025-10-30 | `kl_capex4_googl` |
| Amazon | 120,1 mdr | +54,4 | -1,1 | -3,8 | 2025Q3 | 2025-10-31 | `kl_capex4_amzn` |
| Meta | 62,7 mdr | +72,4 | +22,6 | +3,5 | 2025Q3 | 2025-10-30 | `kl_capex4_meta` |

**Tillskott till RPO över fyra kvartal** (takt = log av tillskottet mot de fyra kvartalen före; klumpigt):

| Vem | Nivå | Takt | Förändring i takt | Överraskning (B1) | Senaste kvartal | known_from | Serie |
|---|---|---|---|---|---|---|---|
| Yttre lagret | – | – | – | – | – | – | `kl_rpo_add4_outer` |
| Oracle | 356,2 mdr | +234,3 | +131,6 | +211,8 | 2025Q3 | 2025-09-10 | `kl_rpo_add4_orcl` |
| CoreWeave | – | – | – | – | – | – | `kl_rpo_add4_crwv` |
| Inre lagret | 238,9 mdr | +84,2 | +44,5 | +19,4 | 2025Q3 | 2025-10-31 | `kl_rpo_add4_inner` |
| Microsoft | 132,0 mdr | +97,1 | +31,5 | +8,3 | 2025Q3 | 2025-10-29 | `kl_rpo_add4_msft` |
| Alphabet | 70,9 mdr | +117,5 | +56,4 | +76,0 | 2025Q3 | 2025-10-30 | `kl_rpo_add4_googl` |
| Amazon | 36,0 mdr | +15,0 | +28,1 | -17,7 | 2025Q3 | 2025-10-31 | `kl_rpo_add4_amzn` |

**CoreWeaves effekt** (MW, takt = log × 100 över fyra kvartal):

| Vem | Nivå | Takt | Förändring i takt | Överraskning (B1) | Senaste kvartal | known_from | Serie |
|---|---|---|---|---|---|---|---|
| CoreWeave, kontrakterad | 2 900 MW | – | – | – | 2025Q3 | 2025-11-10 | `plan_crwv_contracted_power_asof_value` |
| CoreWeave, aktiv | 590 MW | – | – | – | 2025Q3 | 2025-11-10 | `plan_crwv_active_power_asof_value` |

**Capex-guidance för kalenderår** (mittpunkt; guidad takt mot föregående års utfall där F1:s definition finns):

- Alphabet 2025: 91,0 mdr–93,0 mdr, guidad takt +56,0; known_from 2025-10-29
- Meta 2025: 70,0 mdr–72,0 mdr, guidad takt +59,3; known_from 2025-10-29

**Riktningskoder** för capex-planer (−2..+2 mot föregående år), uttalade det senaste året:

- `guid_capex_amzn_cy_dir_yoy` 2025: +1 (known_from 2025-02-07)
- `guid_capex_amzn_cy_dir_yoy` 2026: +1 (known_from 2025-10-31)
- `guid_capex_googl_cy_dir_yoy` 2025: +1 (known_from 2025-02-05)
- `guid_capex_googl_cy_dir_yoy` 2026: +2 (known_from 2025-10-30)
- `guid_capex_meta_cy_dir_yoy` 2026: +2 (known_from 2025-07-30)
- `plan_amzn_cash_capex_y_dir_yoy` 2026: +1 (known_from 2025-10-31)
- `guid_capex_msft_fy_dir_prior_fy` 2026: +1 (known_from 2025-04-30)

**F1: revideringar av capex-guidance de senaste 365 dagarna** (upp / oförändrad / ned):

- Amazon: 0 / 3 / 0 (senast 2025-10-31)
- Alphabet: 2 / 2 / 0 (senast 2025-10-29)
- Meta: 3 / 1 / 0 (senast 2025-10-29)
- Microsoft: 2 / 2 / 0 (senast 2025-10-29)

### 4. Läsregeln, mekaniskt

Gränser (låsta): A = vid t − 2 har den effektiva räntan en takt ≥ +0,25 procentenheter eller ett beroendemått ≥ +5. Capex-takten föll om förändringen i takt ≤ -5. Lika fall: inre ≤ 0,5 × yttre. En negativ förändring i takt betyder att tillväxten avtar, inte att capex minskar. Utslaget är en beskrivning, inget test.

Regeln läser bara uppgång i pris och beroende: A kräver en takt på minst gränsen. Ett fall i pris och beroende följt av högre capex-takt blir "inget av mönstren". Hur ofta A har gällt står under varje utslag. När A nästan alltid gäller, avgörs utslaget i praktiken av capex-takten. En regel som läser båda riktningarna kräver en ny daterad registerpost.

Alla kvartal i den här läsningen var kända före registerposten 2026-11-25, och flera av dem var sedda före posten (posten, avsnitt (e)). Läsningen är därför inget utfall på osedda data. Den första läsningen på osedda kvartal kommer med inlämningar efter 2026-11-25.

- **Yttre lagret (huvudläsning):** kan inte avgöras (ett mått som regeln behöver saknas). t = –; A = None (takt vid –: rate_eff –, fcfgap –, netdebt –, leases –); förändring i capex-takt yttre –, inre +2,0 (2025Q3).
  Saknas: kl_capex4_outer (inget kvartal känt på dagen).
- **Oracle mot inre lagret:** talar emot (1): pris eller beroende steg, men takten i yttre lagret höll eller steg. t = 2025Q3; A = True (takt vid 2025Q1: rate_eff -0,2, fcfgap +166,0, netdebt +124,0, leases +9,8); förändring i capex-takt yttre +33,5, inre +2,0 (2025Q3).
  A har gällt i 40 av 54 kvartal med minst en takt (2012Q2–2025Q3).
- **CoreWeave mot inre lagret:** kan inte avgöras (ett mått som regeln behöver saknas). t = –; A = None (takt vid –: rate_eff –, fcfgap –, netdebt –, leases –); förändring i capex-takt yttre –, inre +2,0 (2025Q3).
  Saknas: kl_capex4_crwv (inget kvartal känt på dagen).
- **Nebius mot inre lagret:** kan inte avgöras (ett mått som regeln behöver saknas). t = –; A = None (takt vid –: fcfgap –); förändring i capex-takt yttre –, inre +2,0 (2025Q3).
  Saknas: kl_capex4_nbis (inget kvartal känt på dagen).
- **IREN mot inre lagret:** kan inte avgöras (ett mått som regeln behöver saknas). t = –; A = None (takt vid –: fcfgap –); förändring i capex-takt yttre –, inre +2,0 (2025Q3).
  Saknas: kl_capex4_iren (inget kvartal känt på dagen).

### 5. Labben och utvecklar- och SPV-kanalen (tabellrader ur inlämningarna)

- Anthropic: ingen registreringsansökan känd på dagen.
- OpenAI: ingen registreringsansökan på EDGAR (sökning på namnet 2026-11-25: bara fonder och SPV med Form D).
- **Meta, datacenterbolag i Louisiana med fonder förvaltade av Blue Owl**, bildat 2025-10: Metas insats 4,3 mdr, leasingåtagande cirka 12,3 mdr, restvärdesgaranti från 28,0 mdr (known_from 2025-10-30)
- Oracle: inga belopp för datacenter-SPV eller samriskbolag i 10-Q och 10-K 2025–2026.
- **CoreWeave, nya obligationer** (8-K, senaste sex; konvertibler ingår inte i kupongmåttet):
  - 2025-05-27: 2030 senior notes, 2 000 MUSD, kupong 9,250 % (known_from 2025-05-28)
  - 2025-07-25: 2031 9 00 senior notes, 1 750 MUSD, kupong 9,000 % (known_from 2025-07-28)
- CoreWeave, marginal över SOFR för lånefaciliteter (bp): ddtl 3 0 facility 400, ddtl 2 0 facility 1 300 (före femte tillägget och utan investment grade; med investment grade 600–650), ddtl 2 0 facility incremental 425

### 6. Att bevaka

Nästa inlämning per bolag, uppskattad som nästa kvartals slut plus medianen av avståndet för de åtta senaste inlämningarna:

- Oracle: 2025Q4 omkring 2025-12-12 (median -19 dagar, spann -21–-10, senast 2025-09-10)
- Alphabet: 2025Q4 omkring 2026-01-28 (median 28 dagar, spann 24–36, senast 2025-10-30)
- Microsoft: 2025Q4 omkring 2026-01-30 (median 30 dagar, spann 25–30, senast 2025-10-29)
- Meta: 2025Q4 omkring 2026-01-31 (median 31 dagar, spann 25–33, senast 2025-10-30)
- Amazon: 2025Q4 omkring 2026-02-01 (median 32 dagar, spann 31–38, senast 2025-10-31)
- IREN: 2025Q4 omkring 2026-02-06 (median 37 dagar, spann 37–37, senast 2025-11-06)
- Nebius: 2025Q4 omkring 2026-02-12 (median 43 dagar, spann 38–129, senast 2025-11-12)
- CoreWeave: 2025Q4 omkring 2026-02-13 (median 44 dagar, spann 44–45, senast 2025-11-13)
- Nvidia: 2025Q4 omkring 2026-02-26 (median 57 dagar, spann 50–59, senast 2025-11-19)
- Anthropic: första periodrapporten efter börsnoteringen; ingen historik att uppskatta från.

### 7. Förbehåll

- Med cirka 8–12 kvartal per mått är detta en beskrivning och inget test. Ett mönster kan vara slump.
- RPO är klumpig: enstaka mycket stora avtal flyttar ett kvartal.
- Neomolnens serier börjar 2024, så yttre lagrets takt och förändring i takt finns bara för de senaste kvartalen. Nebius och IREN saknar skuldserier och ingår bara i capex och (capex − OCF) / capex.
- Den effektiva räntan är efter aktiverad ränta. Microsofts räntekostnad innehåller ränta på finansiell leasing. CoreWeaves räntor i skuldtabellen står i hela procent.
- Regeln läser bara uppgång i pris och beroende. Hur ofta A har gällt står i avsnitt 4.
- Utanför ramen: privat kredit utanför EDGAR, labbens oregistrerade skuld, spreadar på andrahandsmarknaden (licens) och 144A-affärer utan 8-K. OpenAI har ingen registreringsansökan på EDGAR.
- Nyhetsuppgifter om kreditbetyg (KBRA, Moody's) är sekundära och används inte som data.
### 8. Tillägg S1: symmetrisk läsning bredvid den låsta

Registret: `docs/mattregister.md`, 2026-11-27 S1, punkt 1. F0:s symmetriska regel per pris- och beroendemått: X = måttets takt (gräns ±0,25 procentenheter för räntan och ±5 för beroendemåtten, KL1:s gränser), Y = förändringen i capex-takt för samma enhet (gräns ±5), fönster 2 kvartal efter ursprunget, tecken −. En rad per mått, ingen sammanslagning med "eller". Avsnitt 1–7 ovan är den låsta läsningen och är oförändrade, och huvudläsningen är fortfarande den låsta (avsnitt 4). Det här avsnittet är ett tillägg.

- **Talar för, uppåt:** pris eller beroende steg (X ≥ +g) och capex-takten föll sedan (Y ≤ −5). **Talar för, nedåt:** pris eller beroende föll (X ≤ −g) och capex-takten steg sedan (Y ≥ +5).
- **Talar emot:** capex-takten följde X åt samma håll.
- En negativ förändring i takt betyder att tillväxten avtar, inte att capex minskar. Utslaget är en beskrivning, inget test.

Beroendemåtten har capex över samma fyra kvartal i sig. (capex − OCF) / capex stiger när capex växer snabbare än kassaflödet, så en acceleration i capex ger lätt "talar emot, uppåt". Nettoemission och leasing har capex i nämnaren och faller när capex accelererar, så samma acceleration ger lätt "talar för, nedåt". Utslagen för beroendemåtten är därför svaga belägg åt båda hållen. Räntan har ingen sådan koppling men kort historik.

Impulser nedåt i historiken: i 7 av 18 rader (7 rader har X i historiken). Antalet per rad och riktning står under varje rad.

Alla rader vilar bara på värden som var kända före registerposten 2026-11-27, och KL1:s takter vid t − 2 var sedda före posten (S1, punkt 6). Ingen av raderna är därför ett utfall på osedda data (S1, punkt 4).

**Yttre lagret** (Y = `kl_capex4_outer`):

- **Effektiv ränta:** kan inte avgöras. t = – (kl_capex4_outer: inget kvartal känt på dagen). X = kl_rate_eff_outer (takt), Y = kl_capex4_outer (förändring i takt); fönster 2 kvartal, tecken −.
  Regeln kunde inte prövas: X saknas i hela historiken.
  `kl_capex4_outer` har ingen förändring i takt på dagen (serien är för kort), så Y saknas i varje fönster.
- **(capex − OCF) / capex:** kan inte avgöras. t = – (kl_capex4_outer: inget kvartal känt på dagen). X = kl_fcfgap_outer (takt), Y = kl_capex4_outer (förändring i takt); fönster 2 kvartal, tecken −.
  Regeln kunde inte prövas: X saknas i hela historiken.
  `kl_capex4_outer` har ingen förändring i takt på dagen (serien är för kort), så Y saknas i varje fönster.
- **(emitterad − amorterad skuld) / capex:** kan inte avgöras. t = – (kl_capex4_outer: inget kvartal känt på dagen). X = kl_netdebt_outer (takt), Y = kl_capex4_outer (förändring i takt); fönster 2 kvartal, tecken −.
  Regeln kunde inte prövas: X saknas i hela historiken.
  `kl_capex4_outer` har ingen förändring i takt på dagen (serien är för kort), så Y saknas i varje fönster.
- **Leasingavtal som inte börjat / capex:** kan inte avgöras. t = – (kl_capex4_outer: inget kvartal känt på dagen). X = kl_leases_outer (takt), Y = kl_capex4_outer (förändring i takt); fönster 2 kvartal, tecken −.
  Regeln kunde inte prövas: X saknas i hela historiken.
  `kl_capex4_outer` har ingen förändring i takt på dagen (serien är för kort), så Y saknas i varje fönster.

**Inre lagret** (Y = `kl_capex4_inner`):

- **Effektiv ränta:** kan inte avgöras. t = 2025Q3 (X saknas vid 2025Q1; X saknas vid 2025Q2). X = kl_rate_eff_inner (takt), Y = kl_capex4_inner (förändring i takt); fönster 2 kvartal, tecken −.
  Regeln kunde inte prövas: X saknas i hela historiken.
- **(capex − OCF) / capex:** kan inte avgöras. t = 2025Q3; ursprung 2025Q2, X +62,3 (gräns ±5,0), uppgång (fönstret öppet till 2025Q4). X = kl_fcfgap_inner (takt), Y = kl_capex4_inner (förändring i takt); fönster 2 kvartal, tecken −.
  Regeln kunde prövas i 23 av 25 ursprung med X (2019Q2–2025Q2). Impulser uppåt 15 (för 8, emot 5, inget 1, kan inte avgöras 1), nedåt 9 (för 5, emot 3, inget 0, kan inte avgöras 1), utan impuls 1.
  Y var känt i hela fönstret i 23 av 25 ursprung, och 22 av 24 impulser kunde läsas mot Y.
  Övergång (registret 2026-11-27 S1, punkt 3): ett ursprung räknas nu som prövat bara när Y finns i fönstret. Med F0:s räkning före S1: 23 av 25; med den nya: 23 av 25. Bytet väntar på ägarens bekräftelse (R29-1, registret 2026-11-27 X26, punkt 1).
- **(emitterad − amorterad skuld) / capex:** kan inte avgöras. t = 2025Q3; ursprung 2025Q2, X +11,2 (gräns ±5,0), uppgång (fönstret öppet till 2025Q4). X = kl_netdebt_inner (takt), Y = kl_capex4_inner (förändring i takt); fönster 2 kvartal, tecken −.
  Regeln kunde prövas i 23 av 25 ursprung med X (2019Q2–2025Q2). Impulser uppåt 10 (för 4, emot 4, inget 1, kan inte avgöras 1), nedåt 9 (för 5, emot 3, inget 0, kan inte avgöras 1), utan impuls 6.
  Y var känt i hela fönstret i 23 av 25 ursprung, och 17 av 19 impulser kunde läsas mot Y.
  Övergång (registret 2026-11-27 S1, punkt 3): ett ursprung räknas nu som prövat bara när Y finns i fönstret. Med F0:s räkning före S1: 23 av 25; med den nya: 23 av 25. Bytet väntar på ägarens bekräftelse (R29-1, registret 2026-11-27 X26, punkt 1).
- **Leasingavtal som inte börjat / capex:** kan inte avgöras. t = 2025Q3; ursprung 2025Q2, X +25,4 (gräns ±5,0), uppgång (fönstret öppet till 2025Q4). X = kl_leases_inner (takt), Y = kl_capex4_inner (förändring i takt); fönster 2 kvartal, tecken −.
  Regeln kunde prövas i 14 av 15 ursprung med X (2021Q4–2025Q2). Impulser uppåt 7 (för 0, emot 6, inget 0, kan inte avgöras 1), nedåt 7 (för 0, emot 7, inget 0, kan inte avgöras 0), utan impuls 1.
  Y var känt i hela fönstret i 14 av 15 ursprung, och 13 av 14 impulser kunde läsas mot Y.
  Övergång (registret 2026-11-27 S1, punkt 3): ett ursprung räknas nu som prövat bara när Y finns i fönstret. Med F0:s räkning före S1: 14 av 15; med den nya: 14 av 15. Bytet väntar på ägarens bekräftelse (R29-1, registret 2026-11-27 X26, punkt 1).

**Oracle** (Y = `kl_capex4_orcl`):

- **Effektiv ränta:** inget av mönstren. t = 2025Q3 (ingen impuls i fönstret). X = kl_rate_eff_orcl (takt), Y = kl_capex4_orcl (förändring i takt); fönster 2 kvartal, tecken −.
  Regeln kunde prövas i 16 av 17 ursprung med X (2021Q2–2025Q2). Impulser uppåt 3 (för 3, emot 0, inget 0, kan inte avgöras 0), nedåt 1 (för 1, emot 0, inget 0, kan inte avgöras 0), utan impuls 13.
  Y var känt i hela fönstret i 16 av 17 ursprung, och 4 av 4 impulser kunde läsas mot Y.
  Övergång (registret 2026-11-27 S1, punkt 3): ett ursprung räknas nu som prövat bara när Y finns i fönstret. Med F0:s räkning före S1: 17 av 17; med den nya: 16 av 17. Bytet väntar på ägarens bekräftelse (R29-1, registret 2026-11-27 X26, punkt 1).
- **(capex − OCF) / capex:** talar emot, uppåt. t = 2025Q3; ursprung 2025Q2, X +173,8 (gräns ±5,0), uppgång, Y +33,5 vid 2025Q3 (gräns ±5,0). X = kl_fcfgap_orcl (takt), Y = kl_capex4_orcl (förändring i takt); fönster 2 kvartal, tecken −.
  Regeln kunde prövas i 52 av 53 ursprung med X (2012Q2–2025Q2). Impulser uppåt 34 (för 11, emot 22, inget 0, kan inte avgöras 1), nedåt 17 (för 9, emot 8, inget 0, kan inte avgöras 0), utan impuls 2.
  Y var känt i hela fönstret i 51 av 53 ursprung, och 50 av 51 impulser kunde läsas mot Y.
  Övergång (registret 2026-11-27 S1, punkt 3): ett ursprung räknas nu som prövat bara när Y finns i fönstret. Med F0:s räkning före S1: 52 av 53; med den nya: 52 av 53. Bytet väntar på ägarens bekräftelse (R29-1, registret 2026-11-27 X26, punkt 1).
- **(emitterad − amorterad skuld) / capex:** talar emot, uppåt. t = 2025Q3; ursprung 2025Q2, X +68,4 (gräns ±5,0), uppgång, Y +33,5 vid 2025Q3 (gräns ±5,0). X = kl_netdebt_orcl (takt), Y = kl_capex4_orcl (förändring i takt); fönster 2 kvartal, tecken −.
  Regeln kunde prövas i 37 av 37 ursprung med X (2016Q2–2025Q2). Impulser uppåt 13 (för 2, emot 11, inget 0, kan inte avgöras 0), nedåt 24 (för 12, emot 12, inget 0, kan inte avgöras 0), utan impuls 0.
  Y var känt i hela fönstret i 36 av 37 ursprung, och 37 av 37 impulser kunde läsas mot Y.
  Övergång (registret 2026-11-27 S1, punkt 3): ett ursprung räknas nu som prövat bara när Y finns i fönstret. Med F0:s räkning före S1: 37 av 37; med den nya: 37 av 37. Bytet väntar på ägarens bekräftelse (R29-1, registret 2026-11-27 X26, punkt 1).
- **Leasingavtal som inte börjat / capex:** talar för mekanismen, nedåt. t = 2025Q3; ursprung 2025Q2, X -129,0 (gräns ±5,0), nedgång, Y +33,5 vid 2025Q3 (gräns ±5,0). X = kl_leases_orcl (takt), Y = kl_capex4_orcl (förändring i takt); fönster 2 kvartal, tecken −.
  Regeln kunde prövas i 3 av 3 ursprung med X (2024Q4–2025Q2). Impulser uppåt 2 (för 0, emot 2, inget 0, kan inte avgöras 0), nedåt 1 (för 1, emot 0, inget 0, kan inte avgöras 0), utan impuls 0.
  Y var känt i hela fönstret i 2 av 3 ursprung, och 3 av 3 impulser kunde läsas mot Y.
  Övergång (registret 2026-11-27 S1, punkt 3): ett ursprung räknas nu som prövat bara när Y finns i fönstret. Med F0:s räkning före S1: 3 av 3; med den nya: 3 av 3. Bytet väntar på ägarens bekräftelse (R29-1, registret 2026-11-27 X26, punkt 1).

**CoreWeave** (Y = `kl_capex4_crwv`):

- **Effektiv ränta:** kan inte avgöras. t = – (kl_capex4_crwv: inget kvartal känt på dagen). X = kl_rate_eff_crwv (takt), Y = kl_capex4_crwv (förändring i takt); fönster 2 kvartal, tecken −.
  Regeln kunde inte prövas: X saknas i hela historiken.
  `kl_capex4_crwv` har ingen förändring i takt på dagen (serien är för kort), så Y saknas i varje fönster.
- **(capex − OCF) / capex:** kan inte avgöras. t = – (kl_capex4_crwv: inget kvartal känt på dagen). X = kl_fcfgap_crwv (takt), Y = kl_capex4_crwv (förändring i takt); fönster 2 kvartal, tecken −.
  Regeln kunde inte prövas: X saknas i hela historiken.
  `kl_capex4_crwv` har ingen förändring i takt på dagen (serien är för kort), så Y saknas i varje fönster.
- **(emitterad − amorterad skuld) / capex:** kan inte avgöras. t = – (kl_capex4_crwv: inget kvartal känt på dagen). X = kl_netdebt_crwv (takt), Y = kl_capex4_crwv (förändring i takt); fönster 2 kvartal, tecken −.
  Regeln kunde inte prövas: X saknas i hela historiken.
  `kl_capex4_crwv` har ingen förändring i takt på dagen (serien är för kort), så Y saknas i varje fönster.
- **Leasingavtal som inte börjat / capex:** kan inte avgöras. t = – (kl_capex4_crwv: inget kvartal känt på dagen). X = kl_leases_crwv (takt), Y = kl_capex4_crwv (förändring i takt); fönster 2 kvartal, tecken −.
  Regeln kunde inte prövas: X saknas i hela historiken.
  `kl_capex4_crwv` har ingen förändring i takt på dagen (serien är för kort), så Y saknas i varje fönster.

**Nebius** (Y = `kl_capex4_nbis`):

- **(capex − OCF) / capex:** kan inte avgöras. t = – (kl_capex4_nbis: inget kvartal känt på dagen). X = kl_fcfgap_nbis (takt), Y = kl_capex4_nbis (förändring i takt); fönster 2 kvartal, tecken −.
  Regeln kunde inte prövas: X saknas i hela historiken.
  `kl_capex4_nbis` har ingen förändring i takt på dagen (serien är för kort), så Y saknas i varje fönster.

**IREN** (Y = `kl_capex4_iren`):

- **(capex − OCF) / capex:** kan inte avgöras. t = – (kl_capex4_iren: inget kvartal känt på dagen). X = kl_fcfgap_iren (takt), Y = kl_capex4_iren (förändring i takt); fönster 2 kvartal, tecken −.
  Regeln kunde inte prövas: X saknas i hela historiken.
  `kl_capex4_iren` har ingen förändring i takt på dagen (serien är för kort), så Y saknas i varje fönster.
