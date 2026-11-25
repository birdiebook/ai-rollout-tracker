<!-- Visual catalogue of the W2 design system: every token and chart primitive, with demo values (not data).
     Owned by W2; wave-1 tracks add a section here when they add a shared component. Not linked from the menu. -->
<script lang="ts">
  import { scaleLinear, scalePoint } from 'd3-scale';
  import {
    Axis, Band, ChartFrame, DataTable, Glyph, Legend, Line, QuantileDots, StatusBadge, StripeCell, Stripes, TableToggle,
    contrast, deltaE, divergingFill, dotValues, fmt, palettes, periodLabel, signed, space, typography, type Palette
  } from '$lib/design';

  const roles: [keyof Palette, string][] = [
    ['acc', 'Mer takt (accelererar)'], ['brk', 'Mindre takt (bromsar in)'], ['stb', 'Balans (stabil)'],
    ['mid', 'Divergerande mitt'], ['model', 'Modell och intervall'], ['base', 'Naiv baslinje'],
    ['ink', 'Text'], ['ink2', 'Text 2'], ['muted', 'Dämpad text'], ['grid', 'Rutnät'], ['axis', 'Axel'],
    ['surface', 'Yta'], ['page', 'Sida']
  ];
  const isHex = (c: string) => /^#[0-9a-f]{6}$/i.test(c);

  // demo series: pace around zero, 30 months
  const months = Array.from({ length: 30 }, (_, i) => `${2024 + Math.floor((i + 4) / 12)}-${String(((i + 4) % 12) + 1).padStart(2, '0')}`);
  const pace = months.map((m, i) => ({ m, v: 18 * Math.sin(i / 5) + i * 0.6 - 6 }));
  const fan = months.slice(-14).map((m, i) => {
    const f = 100 + i * 2;
    return { m, f, lo50: f - 4, hi50: f + 4, lo80: f - 8, hi80: f + 8, lo95: f - 12, hi95: f + 13, y: f + 7 * Math.sin(i * 1.7) };
  });
  const stored: [number, number][] = [[0.025, 228], [0.1, 236.5], [0.25, 243], [0.5, 249], [0.75, 255.5], [0.9, 262], [0.975, 271]];
  const dots = dotValues(stored, 20);
  const stripeRows = ['G1', 'G2', 'G3'].map((code, j) => ({
    code,
    name: ['Förmåga', 'Kostnad', 'Användning'][j],
    index: months.map((_, i) => (j === 2 && i < 4 ? null : Math.max(0, Math.min(1, 0.5 + 0.45 * Math.sin(j + i / 4))))),
    state: months.map(() => null)
  }));
  const kinds = months.map((_, i) => (i >= months.length - 2 ? 'skarp' : 'rekonstruerad'));
  let pressed = $state(false);
  const demoTable = {
    caption: 'Exempel på tabellvy',
    columns: [{ key: 'm', label: 'Månad' }, { key: 'v', label: 'Takt' }],
    rows: pace.slice(-4).map((d) => ({ m: periodLabel(d.m), v: signed(d.v) }))
  };
</script>

<svelte:head><title>Komponentkatalog – AI-utrullningen</title></svelte:head>

<h1>Komponentkatalog</h1>
<p class="lede">Designsystemet (W2): färger, typografi, avstånd och diagramprimitiver. Värdena här är exempel, inte data.</p>

<section aria-labelledby="k-colors">
  <h2 id="k-colors">Färger i båda lägena</h2>
  <p class="note">Färg betyder bara riktning. Blått/orange: ΔE vid färgblindhet (protan) {fmt(deltaE(palettes.light.acc, palettes.light.brk, 'protan'), 1)} ljust, {fmt(deltaE(palettes.dark.acc, palettes.dark.brk, 'protan'), 1)} mörkt.</p>
  <div class="themes">
    {#each ['light', 'dark'] as const as t (t)}
      <div class="theme panel" data-theme={t}>
        <h3>{t === 'light' ? 'Ljust' : 'Mörkt'}</h3>
        <ul class="swatches">
          {#each roles as [k, label] (k)}
            {@const c = palettes[t][k]}
            <li>
              <span class="chip-sw" style:background={c} aria-hidden="true"></span>
              <span>{label}<br /><code>{c}</code>{#if isHex(c) && k !== 'surface' && k !== 'page'} · {fmt(contrast(c, palettes[t].surface), 1)}:1{/if}</span>
            </li>
          {/each}
        </ul>
        <p class="glyphs"><Glyph state="accelererar" /> <Glyph state="stabil" /> <Glyph state="bromsar in" /> <Glyph state="för få källor" /></p>
      </div>
    {/each}
  </div>
</section>

<section aria-labelledby="k-type">
  <h2 id="k-type">Typografi och avstånd</h2>
  <div class="panel">
    <p style:font-size={typography.headline} style:font-weight="680" style:line-height="1.1" style:margin="0">Rubrikmening 26–40 px</p>
    <p style:font-size="{typography.section}px" style:font-weight="650" style:margin="8px 0 0">Sektionsrubrik 20 px</p>
    <p style:margin="4px 0 0">Brödtext 16 px. Tal: {fmt(1234567.891, 1)} · {signed(-4.4)} · {signed(4.8)} · {fmt(0.0, 2)}</p>
    <p class="note">Liten text 13 px · diagramtext 11–13 px · system-ui, inga externa typsnitt</p>
    <p style:font-size={typography.bigNumber} style:font-weight="650" style:margin="6px 0 0" class="num">249,0 <small style="font-size:14px">mdr TWD</small></p>
    <div class="spaces">
      {#each Object.entries(space).slice(1) as [k, v] (k)}<span style:width="{v}px" title="space-{k}: {v}px"></span>{/each}
    </div>
  </div>
</section>

<section aria-labelledby="k-glyph">
  <h2 id="k-glyph">Glyf, status och växlare</h2>
  <div class="panel row">
    <Glyph direction={1} /> <Glyph direction={0} /> <Glyph direction={-1} /> <Glyph state="accelererar" word={false} />
    <StatusBadge status="recon" /> <StatusBadge status="live" /> <StatusBadge status="backtest" />
    <TableToggle bind:pressed controls="k-demo-table" />
  </div>
  <div id="k-demo-table" class="panel" style:margin-top="10px" hidden={!pressed}><DataTable table={demoTable} /></div>
</section>

<section aria-labelledby="k-charts">
  <h2 id="k-charts">Diagramprimitiver</h2>
  <div class="grid2">
    <div class="panel">
      <ChartFrame
        id="k-line"
        title="Axel och linje"
        description="Takten kring nollinjen, med dagens version streckad och en direktetikett. Exempeldata."
        height={200}
        table={demoTable}
        source="exempel"
        license="–"
      >
        {#snippet children(d)}
          {@const x = scalePoint<string>().domain(months).range([d.left, d.right - 40])}
          {@const y = scaleLinear().domain([-30, 30]).range([d.bottom, d.top])}
          <Axis scale={y} dims={d} orient="left" tickValues={[-20, 0, 20]} format={(v) => signed(v, 0)} grid baseline={0} />
          <Axis scale={x} dims={d} tickValues={months.filter((m) => m.endsWith('-01'))} format={(v) => v.slice(0, 4)} />
          <Line data={pace} x={(p) => x(p.m) ?? 0} y={(p) => y(p.v + 4)} dashed color="var(--c-muted)" width={1.5} />
          <Line data={pace} x={(p) => x(p.m) ?? 0} y={(p) => y(p.v)} endDot endLabel={signed(pace.at(-1)?.v)} />
        {/snippet}
        {#snippet legend()}
          <Legend items={[{ label: 'version vid datumet', fill: 'var(--c-ink)', line: true }, { label: 'dagens version', fill: 'var(--c-muted)', line: true }]} />
        {/snippet}
      </ChartFrame>
    </div>
    <div class="panel">
      <ChartFrame id="k-band" title="Band 50/80/95 (yta)" description="Prognos med tre intervallnivåer i samma färg och utfall som punkter. Exempeldata." height={200} status="backtest">
        {#snippet children(d)}
          {@const x = scalePoint<string>().domain(fan.map((f) => f.m)).range([d.left, d.right])}
          {@const y = scaleLinear().domain([80, 145]).range([d.bottom, d.top])}
          <Axis scale={y} dims={d} orient="left" ticks={4} grid />
          <Band data={fan} x={(f) => x(f.m) ?? 0} center={(f) => y(f.f)} levels={[
            { level: '95', lo: (f) => y(f.lo95), hi: (f) => y(f.hi95) },
            { level: '80', lo: (f) => y(f.lo80), hi: (f) => y(f.hi80) },
            { level: '50', lo: (f) => y(f.lo50), hi: (f) => y(f.hi50) }
          ]} />
          {#each fan as f (f.m)}
            {@const inside = f.y >= f.lo80 && f.y <= f.hi80}
            <circle class="mark" cx={x(f.m)} cy={y(f.y)} r="4" fill={inside ? 'var(--c-ink)' : 'var(--c-surface)'} stroke="var(--c-ink)" stroke-width="1.6" />
          {/each}
        {/snippet}
        {#snippet legend()}
          <Legend items={[{ label: '50 %', fill: 'var(--c-model-50)' }, { label: '80 %', fill: 'var(--c-model-80)' }, { label: '95 %', fill: 'var(--c-model-95)' }, { label: 'prognos', fill: 'var(--c-model)', line: true }]} />
        {/snippet}
      </ChartFrame>
    </div>
    <div class="panel">
      <ChartFrame id="k-bars" title="Band 50/80/95 (staplar)" description="Ett intervall per månad, prognosstreck i modellfärg. Exempeldata." height={200}>
        {#snippet children(d)}
          {@const x = scalePoint<string>().domain(fan.map((f) => f.m)).range([d.left, d.right]).padding(0.5)}
          {@const y = scaleLinear().domain([80, 145]).range([d.bottom, d.top])}
          <Axis scale={y} dims={d} orient="left" ticks={4} grid />
          <Band variant="bars" barWidth={12} data={fan} x={(f) => x(f.m) ?? 0} center={(f) => y(f.f)} levels={[
            { level: '95', lo: (f) => y(f.lo95), hi: (f) => y(f.hi95) },
            { level: '80', lo: (f) => y(f.lo80), hi: (f) => y(f.hi80) },
            { level: '50', lo: (f) => y(f.lo50), hi: (f) => y(f.hi50) }
          ]} />
        {/snippet}
      </ChartFrame>
    </div>
    <div class="panel">
      <ChartFrame
        id="k-dots"
        title="Kvantilprickdiagram"
        description="20 lika sannolika utfall; varje prick är 5 %. Hovra en prick för värdet. Exempeldata."
        height={170}
        margin={{ top: 8, right: 10, bottom: 24, left: 10 }}
        table={{ columns: [{ key: 'i', label: 'Prick' }, { key: 'v', label: 'Värde' }], rows: dots.map((v, i) => ({ i: String(i + 1), v: fmt(v, 1) })) }}
      >
        {#snippet children(d)}
          {@const x = scaleLinear().domain([220, 280]).range([d.left, d.right])}
          <Axis scale={x} dims={d} ticks={6} format={(v) => fmt(v)} />
          <QuantileDots values={dots} x={(v) => x(v)} dims={d} outcome={252.4} format={(v) => fmt(v, 1)} />
        {/snippet}
      </ChartFrame>
    </div>
  </div>
  <div class="panel" style:margin-top="14px">
    <ChartFrame
      id="k-stripes"
      title="Tillståndsränder (StripeCell)"
      description="Diffusionsindex per gren och månad; de två sista månaderna är skarpa (hel ram). Exempeldata."
      height={3 * 24 + 24}
      margin={{ top: 0, right: 0, bottom: 24, left: 0 }}
    >
      {#snippet children(d)}
        <Stripes dims={d} {months} kind={kinds} rows={stripeRows} />
      {/snippet}
      {#snippet legend()}
        <Legend items={[...[0, 0.33, 0.5, 0.67, 1].map((v) => ({ label: fmt(v, 2), fill: divergingFill(v) })), { label: 'inget index', border: 'var(--c-grid)' }]} />
      {/snippet}
    </ChartFrame>
    <svg width="220" height="34" role="img" aria-label="Enskilda celler: index 0, 0,5, 1 och saknat">
      {#each [0, 0.5, 1, null] as v, i (i)}<StripeCell x={i * 54} y={0} width={50} height={34} value={v} />{/each}
    </svg>
  </div>
</section>

<style>
  .themes,
  .grid2 {
    display: grid;
    gap: 14px;
    grid-template-columns: minmax(0, 1fr);
  }
  @media (min-width: 861px) {
    .themes,
    .grid2 {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }
  .theme {
    background: var(--c-page);
    color: var(--c-ink);
  }
  .swatches {
    list-style: none;
    padding: 0;
    margin: 8px 0;
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
    gap: 8px;
    font-size: 12px;
    color: var(--c-ink-2);
  }
  .swatches li {
    display: flex;
    gap: 8px;
    align-items: center;
  }
  .chip-sw {
    width: 28px;
    height: 28px;
    border-radius: 6px;
    border: 1px solid var(--c-ring);
    flex: none;
  }
  .glyphs {
    display: flex;
    flex-wrap: wrap;
    gap: 6px 14px;
    margin: 0;
  }
  .row {
    display: flex;
    flex-wrap: wrap;
    gap: 10px 16px;
    align-items: center;
  }
  .spaces {
    display: flex;
    gap: 8px;
    align-items: end;
    margin-top: 10px;
  }
  .spaces span {
    display: inline-block;
    height: 16px;
    background: var(--c-axis);
    border-radius: 2px;
  }
</style>
