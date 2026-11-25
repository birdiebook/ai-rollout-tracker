<!-- The state stripes, branch × month (Hawkins; lesson 1): the whole history in one picture. The design system's
     Stripes draws the cells (live months outlined, reconstructed ones lighter); the rail above names the two. -->
<script lang="ts">
  import { ChartFrame, Legend, Stripes, divergingFill, fmt, periodLabel } from '$lib/design';
  import StatusRail from './StatusRail.svelte';
  import type { StartData } from './model';

  let { start }: { start: StartData } = $props();
  const s = $derived(start.stripes);
  const rail = 22;
  const allSame = $derived(new Set(s.kind).size === 1);
  const nLive = $derived(s.kind.filter((k) => k === 'skarp').length);
  const description = $derived(
    `Diffusionsindex per gren och månad, ${periodLabel(s.months[0])}–${periodLabel(s.months.at(-1) ?? '')}. ` +
      `Blått: fler serier ökar takten, orange: fler minskar den, grått: balans. En gren med för få serier har inget tillstånd och ingen färg. ` +
      (nLive ? `${nLive} ${nLive === 1 ? 'månad är skarp' : 'månader är skarpa'}, de övriga rekonstruerade.` : 'Alla månader är rekonstruerade.')
  );
  const table = $derived({
    caption: 'Diffusionsindex per gren och månad (r = rekonstruerad, s = skarp)',
    columns: [{ key: 'b', label: 'Gren' }, ...s.months.map((m, i) => ({ key: m, label: `${periodLabel(m)} ${s.kind[i] === 'skarp' ? 's' : 'r'}` }))],
    rows: s.rows.map((r) => ({ b: `${r.code} ${r.name}`, ...Object.fromEntries(s.months.map((m, i) => [m, fmt(r.index[i], 2)])) }))
  });
</script>

<ChartFrame
  id="stripes"
  title="Diffusionsindex per gren och månad"
  {description}
  height={rail + s.rows.length * 24 + 24}
  width={1128}
  margin={{ top: 0, right: 0, bottom: 24, left: 0 }}
  {table}
  status={allSame ? (s.kind[0] === 'skarp' ? 'live' : 'recon') : undefined}
>
  {#snippet children(d)}
    <StatusRail {d} kind={s.kind} />
    <g transform="translate(0 {rail})">
      <Stripes dims={d} months={s.months} kind={s.kind} rows={s.rows} />
    </g>
  {/snippet}
  {#snippet legend()}
    <Legend
      items={[
        { label: '0 · alla minskar takten', fill: divergingFill(0) },
        { label: `${fmt(start.thresholds.low, 2)}`, fill: divergingFill(start.thresholds.low) },
        { label: '0,5 · balans', fill: divergingFill(0.5) },
        { label: `${fmt(start.thresholds.high, 2)}`, fill: divergingFill(start.thresholds.high) },
        { label: '1 · alla ökar takten', fill: divergingFill(1) },
        { label: 'inget index', border: 'var(--c-grid)' },
        { label: 'för få serier: index utan tillstånd, ingen färg', border: 'var(--c-axis)', dashed: true }
      ]}
    />
  {/snippet}
</ChartFrame>
