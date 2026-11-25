# Pris vid rörlig förmågetröskel (G2), spår Q1

Körning 14, spår Q1, 2026-11-25. Förslag 6 i [riktning.md](../riktning.md). Definitionerna är låsta i
[måttregistret](../mattregister.md), posten "2026-11-25 – Q1: pris vid rörlig förmågetröskel". Serierna är
katalogserier, inte kärnserier. **Inga takter, halveringstider eller trender beräknas i spåret.**

## 1. Vad som tittades på före registreringen

Registerposten committades innan något värde för de nya serierna räknades. Före posten tittade spåret bara på detta:

- **Referensmodellerna.** För varje månad m till 2026-10 och L = 6 och 12: vilken modell som var etta i tavlan för
  m − L (både enligt det som var känt vid d och enligt det som var känt vid slutet av m − L), och om den finns i b(m)
  med exakt namn. Bara namn och närvaro, inga ratingar. Fynd: ettan saknas i b(m) i 31 av versionerna. Det är nästan
  alltid ett experiment- eller förhandsnamn som tagits bort när modellen släpptes (`gpt-4-turbo`,
  `chatgpt-4o-latest`, `gemini-exp-1121`, `gemini-exp-1206`, `gemini-2.0-flash-thinking-exp-01-21`, `early-grok-3`,
  `gemini-2.5-pro-exp-03-25`, `gemini-2.5-pro-preview-05-06`), ett namnbyte (`claude-opus-4-6-thinking` finns till
  2026-08-11, `claude-opus-4-6-high` från 2026-08-12) eller bytet till visningsnamn (`gemini-2.5-pro` finns till
  2026-10-15, "Gemini 2.5 Pro" från 2026-10-20). Efterföljarregeln är alltså central och inget undantag.
- **Kandidater till efterföljare.** För varje sådan version: de tio modellerna närmast under ettan i referenstavlan,
  om de finns i b(m) och i hur många tidigare tavlor de finns tillsammans med ettan. Varje version i API-eran hade en
  kandidat som finns i b(m) med minst 3 gemensamma tavlor. Inga ratingskillnader räknades.
- **Namnformer kring bytet till visningsnamn.** Vilka namn för Claude Opus 4.6/4.7, Gemini 2.5 Pro, 3 Pro och 3.1, och
  GPT-5.4/5.5 som finns i tavlorna från 2026-07 och i vilket datumintervall. Tavlan 2026-10-15 har båda formerna.
- **ECI-fronten per månad** (den publicerade serien `g1_epoch_eci_frontier`, ur dagens ZIP). Den är tröskeln i
  ECI-varianten. Den lästes för att sätta täckningsgolvet: `model_map` täcker modeller med ECI ≥ 128, och fronten når
  128 först 2024-05. Inga priser lästes.
- **Kolumnnamn** i alla filer i Epochs `benchmark_data.zip` (sökning efter token, cost, price) och i METR:s
  `benchmark_results_1_1.yaml`, och README-filen i ZIP-filen (licensen).
- **Arenas `agent`-delmängd:** kolumnerna, antalet modeller per tavla och antalet rader med `cost_per_task_p50`
  (0 till 2026-10-28, 53 – 64 per tavla från 2026-11-02). Inga kostnadsvärden.
- LiteLLM-ögonblicksbilderna och avvecklingsdatumen laddades, men inga priser lästes ut.
