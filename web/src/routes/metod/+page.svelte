<!-- W11 Utforskbar metod: the method as figures the reader can move (vision 2.2 F). Five parts: diffusion index and
     dead band, intervals and calibration, as_of and known_from, pre-registration and the promotion rule, sources and
     licences. Registered values are always drawn and labelled "registrerat"; the reader's changes are "utforskning".
     The explorer's engine ($lib/method/engine.ts) is golden-tested against the Python engine. -->
<script lang="ts">
  import { GLOSSARY, Term, dataUrl, fmt, setChartData } from '$lib/design';
  import AsOfExplorer from '$lib/method/AsOfExplorer.svelte';
  import CalibrationExplorer from '$lib/method/CalibrationExplorer.svelte';
  import DeadbandExplorer from '$lib/method/DeadbandExplorer.svelte';
  import IntervalExplorer from '$lib/method/IntervalExplorer.svelte';
  import PromotionFigure from '$lib/method/PromotionFigure.svelte';
  import SourcesList from '$lib/method/SourcesList.svelte';
  import BacktestCalibration from '../prognoser/parts/BacktestCalibration.svelte';

  let { data } = $props();
  setChartData(() => dataUrl('method.json'));
  const status = $derived(data.record.status === 'live' ? ('live' as const) : ('recon' as const));
  const r = $derived(data.rules);
  const parts = [
    ['diffusion', 'Diffusionsindex'],
    ['intervall', 'Intervall och kalibrering'],
    ['as-of', 'as_of och known_from'],
    ['forregistrering', 'Förregistrering'],
    ['kallor', 'Källor och licenser'],
    ['ordlista', 'Ordlista']
  ];
</script>

<svelte:head><title>Metod – AI-utrullningen</title></svelte:head>

<p class="kicker">Metod · måttregistret som figurer</p>
<h1>Metoden, att röra vid</h1>
<p class="lede">
  Mått, tillståndsregler och intervall låstes i måttregistret innan data analyserades. Här kan du flytta parametrarna och se vad
  de gör. Det registrerade värdet är alltid markerat <span class="tag reg">registrerat</span>, och din ändring
  <span class="tag exp">utforskning</span>.
</p>
<nav class="toc" aria-label="Metodens delar">
  <ol>
    {#each parts as [id, label], i (id)}<li><a href="#{id}"><span class="num">{i + 1}</span> {label}</a></li>{/each}
  </ol>
</nav>

<section id="diffusion" aria-labelledby="h-diffusion">
  <h2 id="h-diffusion">1. Diffusionsindex: dra i dödbandet</h2>
  <p class="lede">
    Varje kärnserie får en riktning: ▲ om förändringen i takt är större än {fmt(r.deadband_sd, 2)} av seriens egen standardavvikelse (<Term id="dodband">dödbandet</Term>),
    ▼ om den är mindre än −{fmt(r.deadband_sd, 2)}, annars ●. Indexet är (antal ▲ + hälften av ●) / antal serier. Grenen
    accelererar vid index ≥ {fmt(r.accelerating_at_least, 2)} och bromsar in vid ≤ {fmt(r.braking_at_most, 2)}. Med färre än
    {r.min_series} serier visas inget tillstånd. Dödbandet låstes innan någon takt räknades: dra i det och se varför valet
    måste göras före, inte efter, att man sett utfallet.
  </p>
  <DeadbandExplorer branches={data.branches} initial={data.initial} rules={data.rules} {status} linkable={data.linkable} />
</section>

<section id="intervall" aria-labelledby="h-intervall">
  <h2 id="h-intervall">2. Vad ett 80 %-intervall betyder</h2>
  <p class="lede">
    En prognos får sitt intervall ur modellens egna tidigare fel utom stickprov: punktprognosen plus felens empiriska kvantiler.
    Ett fel räknas först från den dag utfallet blev känt. Med minst 40 fel används kvantilerna direkt, med 8–39 en
    t-fördelning. Ett 80 %-intervall ska i det långa loppet träffa 8 av 10 utfall, varken fler eller färre.
  </p>
  <p class="illu">Illustration: 40 påhittade fel och 80 påhittade utfall, inte projektets data.</p>
  <IntervalExplorer />
  <h3 class="sub">Kalibrering: för smalt, för brett, lagom</h3>
  <p class="note">
    Täckningen jämförs med <Term id="slumpband">slumpbandet</Term>: även ett perfekt kalibrerat 80 %-intervall träffar inte exakt 64 av 80. <Term id="pit">PIT</Term> visar var i
    fördelningen utfallet hamnade; jämnt fördelat betyder att hela fördelningen stämmer, inte bara en nivå.
  </p>
  <CalibrationExplorer />
  {#if data.calib}
    <h3 class="sub">Så ser det ut i projektet: {data.calib.label} {data.calib.title}</h3>
    <BacktestCalibration id="metod-{data.calib.id}" cal={data.calib.cal as never} roles={data.calib.roles} />
  {/if}
</section>

<section id="as-of" aria-labelledby="h-asof">
  <h2 id="h-asof">3. as_of och known_from: bara det som var känt</h2>
  <p class="lede">
    Varje värde har ett <code>known_from</code>: dagen det publicerades eller lämnades in. En beräkning per dag D använder bara
    rader med <code>known_from</code> ≤ D (<code>as_of(D)</code>). När en källa reviderar blir det en ny version, och den
    gamla finns kvar. Statistik över historiken, som standardavvikelsen bakom dödbandet, räknas också bara på det som var
    känt den dagen.
  </p>
  {#if data.asof}
    <AsOfExplorer data={data.asof} {status} />
  {:else}
    <p class="note">Ingen reviderad månadsserie i paketet.</p>
  {/if}
</section>

<section id="forregistrering" aria-labelledby="h-prereg">
  <h2 id="h-prereg">4. Förregistrering, holdout och befordringsregeln</h2>
  <p class="lede">
    Reglerna skrivs först och datan körs sedan. En ny modell blir huvudmodell bara om den slår jämförelsemodellen med marginal
    som tål många försök: <Term id="holm">Holm-justerat</Term> p under 0,10 (justerat för att många varianter prövas) och lägre MAE i båda perioderna. Annars följer den med som skugga.
  </p>
  <PromotionFigure registerFile={data.register.file} registerSha={data.register.sha256} registerHref={data.registerHref} />
</section>

<section id="kallor" aria-labelledby="h-kallor">
  <h2 id="h-kallor">5. Källor och licenser</h2>
  <p class="lede">
    {data.sources.length} källfamiljer. Länkarna går till källornas egna sidor och villkor; sidan hämtar aldrig något därifrån.
  </p>
  <SourcesList sources={data.sources} counts={data.counts} />
</section>

<section id="ordlista" aria-labelledby="h-ordlista">
  <h2 id="h-ordlista">6. Ordlista</h2>
  <p class="lede">Orden som sidorna använder, förklarade en gång. Länkarna med prickad understrykning på andra sidor går hit.</p>
  <dl class="glossary">
    {#each GLOSSARY as g (g.id)}
      <div id="ord-{g.id}"><dt>{g.term}</dt><dd>{g.text}</dd></div>
    {/each}
  </dl>
</section>

<style>
  .tag {
    display: inline-block;
    font-size: 12px;
    border-radius: 999px;
    padding: 0 8px;
    border: 1px solid var(--c-ink-2);
    color: var(--c-ink);
    white-space: nowrap;
  }
  .tag.exp {
    border-style: dashed;
  }
  .toc ol {
    list-style: none;
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    padding: 0;
    margin: 14px 0 0;
  }
  .toc a {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    min-height: var(--hit);
    padding: 4px 12px;
    border: 1px solid var(--c-ring);
    border-radius: var(--radius-pill);
    background: var(--c-surface);
    text-decoration: none;
    font-size: var(--fs-small);
  }
  .toc .num {
    font-weight: 700;
  }
  section {
    scroll-margin-top: 16px;
  }
  section > .lede {
    margin-bottom: 4px;
  }
  .sub {
    margin-top: 26px;
  }
  .illu {
    display: inline-block;
    font-size: var(--fs-small);
    color: var(--c-ink-2);
    border: 1px dashed var(--c-axis);
    border-radius: var(--radius-sm);
    padding: 2px 8px;
    margin: 8px 0 0;
  }
  code {
    font-size: 0.92em;
  }
  .glossary {
    display: grid;
    gap: 10px;
    margin: 12px 0 0;
    max-width: 80ch;
  }
  .glossary > div {
    scroll-margin-top: 16px;
  }
  .glossary dt {
    font-weight: 620;
  }
  .glossary dd {
    margin: 2px 0 0;
    color: var(--c-ink-2);
  }
  .glossary > div:target dt {
    text-decoration: underline;
  }
</style>
