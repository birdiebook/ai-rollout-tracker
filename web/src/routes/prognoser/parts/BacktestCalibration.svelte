<!-- Backtest calibration (W8): always marked "backtest, inte skarpa prognoser" (datakontrakt 8). Coverage per level
     and model against the nominal level with the binomial band, the PIT moments against a uniform distribution, and
     CRPS per model with its sample size (section 4.1: never rank models without showing n). The registered
     comparison between models (Diebold–Mariano, Holm) lives in the results document, not here. -->
<script lang="ts">
  import { scaleLinear } from 'd3-scale';
  import { Axis, ChartFrame, Legend, fmt, periodLabel } from '$lib/design';
  import type { BacktestCalibration } from '$lib/data';
  import { LEVELS, roleOf, type Roles } from './model';

  let { id, cal, roles }: { id: string; cal: BacktestCalibration; roles: Roles } = $props();

  const rank = (m: string) => ['champion', 'baseline', 'guidance', 'shadow'].indexOf(roleOf(roles, m));
  const rows = $derived([...cal.rows].sort((a, b) => rank(a.model) - rank(b.model)));
  const fillOf = (m: string) => (m === roles.champion ? 'var(--c-model)' : 'var(--c-base)');
  const label = (m: string) => (m === roles.champion ? `${m} (huvudmodell)` : m === roles.baseline ? `${m} (baslinje)` : m === roles.guidance ? `${m} (guidance)` : m);
  const span = $derived(cal.first && cal.last ? `${periodLabel(cal.first)}–${periodLabel(cal.last)}` : '');
  const champ = $derived(cal.rows.find((r) => r.model === roles.champion));
  const crpsRows = $derived([...cal.rows].filter((r) => r.crps !== null && r.crps !== undefined).sort((a, b) => (a.crps as number) - (b.crps as number)));
  const crpsMax = $derived(Math.max(1e-9, ...crpsRows.map((r) => r.crps as number)));
  const rowH = 17;
  const groupH = $derived(rows.length * rowH + 14);
</script>

<p class="note">
  Backtesten är rullande: varje månad eller kvartal prognostiseras bara med data som var kända då, och felpoolen
  innehåller bara fel som var kända vid prognosdagen. {span ? `Period ${span}, ${cal.n_periods ?? '–'} perioder.` : ''}
  {#if cal.champion_mae}Huvudmodellens MAE {fmt(cal.champion_mae.mae, 2)} (n {cal.champion_mae.n}).{/if}
</p>

<div class="three">
  <ChartFrame
    id="{id}-cov"
    title="Träffar intervallen?"
    description={champ
      ? `${roles.champion}: ${LEVELS.map((l) => `${fmt((champ[`coverage_${l}`] as number) * 100)} % inom ${l} %-intervallet`).join(', ')} (n ${champ.n}). Strecket är den nominella nivån, det grå bandet vad slumpen ger.`
      : 'Täckning per intervallnivå och modell. Strecket är den nominella nivån, det grå bandet vad slumpen ger.'}
    height={3 * groupH + 26}
    margin={{ top: 6, right: 34, bottom: 22, left: 92 }}
    status="backtest"
    table={{
      columns: [
        { key: 'm', label: 'Modell', align: 'left' },
        { key: 'n', label: 'n', align: 'right' },
        ...LEVELS.map((l) => ({ key: l, label: `${l} %`, align: 'right' as const })),
        ...LEVELS.map((l) => ({ key: `h${l}`, label: `Holm ${l}`, align: 'right' as const }))
      ],
      rows: rows.map((r) => ({
        m: label(r.model),
        n: r.n,
        ...Object.fromEntries(LEVELS.map((l) => [l, `${fmt(((r[`coverage_${l}`] as number | null) ?? NaN) * 100)} %`])),
        ...Object.fromEntries(LEVELS.map((l) => [`h${l}`, fmt(r[`holm_${l}`] as number | null, 2)]))
      }))
    }}
  >
    {#snippet children(d)}
      {@const x = scaleLinear().domain([0.2, 1]).range([d.left, d.right])}
      <Axis scale={x} dims={d} tickValues={[0.2, 0.5, 0.8, 1]} format={(v) => `${fmt(v * 100)} %`} />
      {#each LEVELS as l, g (l)}
        {@const y0 = d.top + g * groupH}
        <text class="ink" x={0} y={y0 + 12}>{l} %</text>
        <line x1={x(+l / 100)} x2={x(+l / 100)} y1={y0 + 1} y2={y0 + rows.length * rowH + 3} stroke="var(--c-ink-2)" stroke-width="1.5" />
        {#each rows as r, i (r.model)}
          {@const cy = y0 + 9 + i * rowH}
          {@const b = r[`band_${l}`] as [number | null, number | null] | null | undefined}
          {@const c = r[`coverage_${l}`] as number | null | undefined}
          <text x={d.left - 8} y={cy + 4} text-anchor="end">{r.model}</text>
          {#if b && b[0] !== null && b[1] !== null}
            <rect x={x(Math.max(0.2, b[0]))} y={cy - 5} width={Math.max(1, x(b[1]) - x(Math.max(0.2, b[0])))} height="10" rx="3" fill="var(--c-grid)" />
          {/if}
          {#if c !== null && c !== undefined}
            <circle class="mark" cx={x(Math.max(0.2, c))} {cy} r={r.model === roles.champion ? 5.5 : 4.5} fill={fillOf(r.model)} stroke="var(--c-surface)" stroke-width="2" />
            <text class="ink2" x={d.right + 30} y={cy + 4} text-anchor="end">{fmt(c * 100)}</text>
          {/if}
        {/each}
      {/each}
    {/snippet}
    {#snippet legend()}
      <Legend items={[{ label: `huvudmodell ${roles.champion}`, fill: 'var(--c-model)' }, { label: 'övriga', fill: 'var(--c-base)' }, { label: 'slumpband', fill: 'var(--c-grid)' }]} />
    {/snippet}
  </ChartFrame>

  <ChartFrame
    id="{id}-pit"
    title="Var hamnade utfallen? (PIT)"
    description={champ && champ.pit_mean !== null && champ.pit_mean !== undefined
      ? `${roles.champion}: PIT-medel ${fmt(champ.pit_mean, 2)} (jämn fördelning 0,50) och varians ${fmt(champ.pit_var, 3)} (jämn 0,083). Lägre varians betyder för breda intervall, högre för smala.`
      : 'PIT-medel och varians per modell mot en jämn fördelning.'}
    height={2 * (rows.length * rowH + 30) + 6}
    margin={{ top: 4, right: 14, bottom: 4, left: 92 }}
    status="backtest"
    table={{
      columns: [{ key: 'm', label: 'Modell', align: 'left' }, { key: 'a', label: 'PIT-medel', align: 'right' }, { key: 'v', label: 'PIT-varians', align: 'right' }, { key: 'c', label: 'Kalibrerad (registrets test)', align: 'left' }],
      rows: rows.map((r) => ({ m: label(r.model), a: fmt(r.pit_mean, 2), v: fmt(r.pit_var, 3), c: r.calibrated === true ? 'ja' : r.calibrated === false ? 'nej' : '–' }))
    }}
  >
    {#snippet children(d)}
      {@const blockH = rows.length * rowH + 30}
      {#each [{ key: 'pit_mean', name: 'medel', dom: [0.25, 0.75], ref: 0.5, digits: 2 }, { key: 'pit_var', name: 'varians', dom: [0.03, 0.14], ref: 1 / 12, digits: 3 }] as m, g (m.key)}
        {@const y0 = d.top + g * blockH}
        {@const x = scaleLinear().domain(m.dom).range([d.left, d.right]).clamp(true)}
        <text class="ink" x={0} y={y0 + 12}>PIT-{m.name}</text>
        <line x1={x(m.ref)} x2={x(m.ref)} y1={y0 + 2} y2={y0 + rows.length * rowH + 6} stroke="var(--c-ink-2)" stroke-width="1.5" />
        <text class="ink2" x={x(m.ref) + 4} y={y0 + rows.length * rowH + 20}>jämn {fmt(m.ref, m.digits)}</text>
        {#each rows as r, i (r.model)}
          {@const cy = y0 + 10 + i * rowH}
          {@const v = r[m.key] as number | null | undefined}
          <text x={d.left - 8} y={cy + 4} text-anchor="end">{r.model}</text>
          <line class="gridline" x1={d.left} x2={d.right} y1={cy} y2={cy} />
          {#if v !== null && v !== undefined}
            <circle class="mark" cx={x(v)} {cy} r={r.model === roles.champion ? 5.5 : 4.5} fill={fillOf(r.model)} stroke="var(--c-surface)" stroke-width="2" />
          {/if}
        {/each}
      {/each}
    {/snippet}
  </ChartFrame>

  <ChartFrame
    id="{id}-crps"
    title="Precision per modell (CRPS)"
    description={crpsRows.length
      ? `Lägre är skarpare och träffsäkrare. Lägst: ${crpsRows[0].model} ${fmt(crpsRows[0].crps, 2)} (n ${crpsRows[0].n}). Modellerna har olika antal perioder, så jämför med n i åtanke.`
      : 'CRPS per modell saknas.'}
    height={crpsRows.length * 26 + 12}
    margin={{ top: 4, right: 92, bottom: 8, left: 92 }}
    status="backtest"
    table={{
      columns: [{ key: 'm', label: 'Modell', align: 'left' }, { key: 'c', label: 'CRPS', align: 'right' }, { key: 'n', label: 'n', align: 'right' }],
      rows: crpsRows.map((r) => ({ m: label(r.model), c: fmt(r.crps, 2), n: r.n }))
    }}
  >
    {#snippet children(d)}
      {@const x = scaleLinear().domain([0, crpsMax * 1.05]).range([d.left, d.right])}
      {#each crpsRows as r, i (r.model)}
        {@const cy = d.top + 12 + i * 26}
        <text class={r.model === roles.champion ? 'ink' : ''} x={d.left - 8} y={cy + 4} text-anchor="end">{label(r.model).replace(' (huvudmodell)', ' huvud')}</text>
        <line class="mark" x1={d.left} x2={x(r.crps as number)} y1={cy} y2={cy} stroke={fillOf(r.model)} stroke-width="2" />
        <circle class="mark" cx={x(r.crps as number)} {cy} r="5" fill={fillOf(r.model)} stroke="var(--c-surface)" stroke-width="2" />
        <text class="ink2" x={x(r.crps as number) + 9} y={cy + 4}>{fmt(r.crps, 2)} · n {r.n}{r.n < 12 ? ' (få)' : ''}</text>
      {/each}
    {/snippet}
  </ChartFrame>
</div>

<style>
  .note {
    margin: 0 0 12px;
    max-width: 75ch;
  }
  .three {
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    gap: 22px;
  }
  @media (min-width: 981px) {
    .three {
      grid-template-columns: repeat(3, minmax(0, 1fr));
    }
  }
</style>
