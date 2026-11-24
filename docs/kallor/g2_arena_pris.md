# Pris vid fast Arena-förmåga (G2), spår G2A

Steg 2, spår G2A, 2026-11-24. Förslaget kommer från spår G12 (`docs/kallor/g1g2_nya.md`, "Pris vid fast
Arena-förmåga"). Serien ska ge G2 ett pris vid fast förmåga med mer än två års ärligt daterad historik. Förmågan
mäts relativt en fast referensmodell i samma Arena-tavla, så att skalbrott (Elo/BT, stilkontroll, omviktning,
förankring) tar ut varandra. **Inga takter, halveringstider eller trender beräknas i spåret.** Serien granskas
oberoende innan den registreras.

## 1. Referensregel (låst 2026-11-24, före beräkning av seriens värden)

Regeln nedan skrevs och committades innan något månadsvärde beräknades. Innan dess kontrollerades bara metadata:
att referensmodellerna finns i tavlorna och vilka namnformer de har. Inga priser eller trösklar tittades på.

### Tavlor

- Arena `text`, kategori `overall`, alla publicerade tavlor enligt `arena.subset_boards("text")`: Space-filer,
  datasetets titlade commits och bulkuppladdningen, med belägg och `source` enligt `docs/kallor/g1g2_nya.md`.
- **Bara Bradley–Terry-eran:** tavlor publicerade från 2024-01-09. Första månaden är 2024-01.
- Månad m använder den senaste tavlan publicerad ≤ månadens slut bland dem som är belagda vid versionens datum.
  Versioner och datum följer regeln i `sources/vintages.py`. Första versionen har `known_from` = månadsslut + 1 dag
  och tavlor med belägg ≤ månadsslut. En tavla som publicerades ≤ månadsslut men beläggs senare ger en ny version
  på beläggets datum, om värdet ändras.

### Referens och tröskel

Tröskeln i tavla b är referensens rating **i samma tavla b**. En modell kvalificerar om dess rating i b är ≥
tröskeln. Gränsen är inklusiv, så referensen själv kvalificerar.

| Variant | Nyckel | Referens r0 | Efterföljare, i ordning |
|---|---|---|---|
| A | `g2_price_at_arena_capability` | `gpt-4-0314` (GPT-4 vid lanseringen, mars 2023) | `gpt-4-0613`, `gpt-4-1106-preview` |
| B | `g2_price_at_arena_capability_4o` | `gpt-4o-2024-05-13` (etta i tavlan 2024-06-11) | `gpt-4o-2024-08-06`, `gpt-4-turbo-2024-04-09` |

- **Namnformer:** API-namn till och med 2026-10-19, visningsnamn från 2026-10-20. Referenserna matchas på båda:
  `gpt-4-0314` / "GPT-4 (0314)", `gpt-4-0613` / "GPT-4 (0613)", `gpt-4-1106-preview` / "GPT-4 Turbo Preview (1106)",
  `gpt-4o-2024-05-13` / "GPT-4o (2024-05-13)", `gpt-4o-2024-08-06` / "GPT-4o (2024-08-06)" och
  `gpt-4-turbo-2024-04-09` / "GPT-4 Turbo (2024-04-09)". Finns båda formerna i samma tavla, används API-namnet.
- **Efterföljare** väljs efter metadata, inte efter utfall: OpenAI-ögonblicksbilder nära referensen i tid och med
  lång närvaro i tavlorna. De används bara om r0 saknas i en tavla. I kontrollen 2026-11-24 fanns båda
  referenserna i varje BT-tavla från sin första förekomst (r0 för A från 2024-01-09, för B från 2024-05-15; 252 BT-tavlor till och med 2026-11-22). Kedjan
  är alltså en regel för framtiden, och historiken använder den inte.
- **Överlappsregel:** saknas r0 i tavla b, används den första efterföljaren s i listan som finns i b och som har
  minst 3 tidigare tavlor (publicerade före b och belagda vid versionens datum) där både r0 och s finns. Tröskeln
  blir rating_b(s) + Δ, där Δ = medianen av rating(r0) − rating(s) i de 3 senaste sådana tavlorna. Δ beräknas
  alltså bara ur tidigare tavlor, aldrig ur senare. Uppfyller ingen efterföljare villkoret, får tavlan ingen
  tröskel, och månaden får inget värde från den tavlan.
- Referenserna och kedjorna ändras inte i efterhand. Om både r0 och kedjan försvinner, tar serien slut tills
  registret beslutar om en ny kedja (med datum och motivering).

### Förmåga per prissatt nyckel

- Varje Arena-namn kopplas till en eller flera LiteLLM-nycklar i den handgranskade tabellen
  `src/ai_tracker/sources/arena_map.py` (avsnitt 3). Bara förstapartsnycklar för modellens utvecklare räknas,
  med regeln i `model_map.is_first_party`.
- **Bästa variant per prissatt modell:** en nyckel får den högsta ratingen bland de Arena-namn som är kopplade
  till den och finns i tavlan. Exempel: resonemangsnivåer som `o3-mini` och `o3-mini-high` säljs under samma
  nyckel och samma pris per token. Samma regel som I6:s GPQA-variant.
- **Rullande alias** (`deepseek-chat`, `deepseek-reasoner`) kopplas till varje modellversion de har serverat,
  med datum från när aliaset började peka på den. Vid månadsslut räknas bara den version som aliaset då
  serverade. Finns den inte i tavlan, har nyckeln ingen förmåga den månaden. Föregångarens rating används inte.
- Alias som byter modell utan dokumenterade datum (till exempel `gpt-4o`, `chatgpt-4o-latest`, `-latest`,
  `qwen-plus`, `qwen-max`, `mistral-medium`) kopplas inte.

### Pris och värde

- Pris = LiteLLM:s prisfil vid månadsslut (senaste urvalda commit på `main` med datum ≤ månadsslut), blandat
  3 input : 1 output, USD per miljon tokens. Samma regler för poster och resonemangspris som
  `g2_price_at_capability` (`docs/kallor/pris_formaga.md`).
- Värde för månad m = lägsta blandade pris bland kvalificerade nycklar.
- `known_from` = det senare av tavlans versionsdatum och prisets `known_from` (månadsslut + 1 dag). Priset vid
  månadsslut är fast, eftersom git-historiken inte ändras. Senare versioner av en månad uppstår bara av senare
  belagda tavlor.
- `source` = `backfill` om tavlan bara finns i datasetets bulkuppladdning (belägg 2026-04-02), annars `release`.
- Båda varianterna lagras. Ingen av dem väljs efter hur serierna ser ut.
