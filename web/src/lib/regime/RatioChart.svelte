<!-- One reconciliation over time, two modes. "ratio": the ratio's level as known on the record date (neutral ink,
     end dot in the direction colour). "sides": numerator and denominator indexed to 100 on one axis (never two
     axes, section 4.1), log scale when they grow more than fourfold. Track W10. -->
<script lang="ts">
  import { scaleLinear, scaleLog } from 'd3-scale';
  import { Axis, ChartFrame, DIRECTIONS, Line, fmt, periodLabel } from '$lib/design';
  import { periodTime } from '$lib/flow';
  import { levelText, ratioSentence, sidesSentence, yearTicks } from './recon';
  import type { ReconView } from './types';

  let { r, mode, height = 200 }: { r: ReconView; mode: 'ratio' | 'sides'; height?: number } = $props();

  const t = $derived(r.periods.map(periodTime));
  const n = $derived(r.periods.length);
  const a = $derived(r.periods.map((_, i) => ({ t: t[i], v: mode === 'ratio' ? r.ratio[i] : r.num_idx[i] })));
  const b = $derived(mode === 'sides' ? r.periods.map((_, i) => ({ t: t[i], v: r.den_idx[i] })) : []);
  const vals = $derived([...a, ...b].map((p) => p.v).filter((v): v is number => v !== null && v > 0));
  const useLog = $derived(mode === 'sides' && vals.length > 1 && Math.max(...vals) / Math.min(...vals) > 4);
  const yDomain = $derived.by((): [number, number] => {
    if (!vals.length) return [0, 1];
    const lo = Math.min(...vals);
    const hi = Math.max(...vals);
    return lo === hi ? [lo * 0.9, hi * 1.1] : [lo, hi];
  });
  const dirColor = $derived(r.direction === null ? 'var(--c-muted)' : DIRECTIONS[r.direction].color);
  const short = (v: number) => (mode === 'ratio' ? levelText(v, r.unit) : fmt(v, 0));
  const title = $derived(mode === 'ratio' ? 'Kvoten över tid' : 'Täljare och nämnare, index');
</script>

<ChartFrame
  id="c-{r.key}-{mode}"
  {title}
  description={mode === 'ratio' ? ratioSentence(r) : sidesSentence(r)}
  {height}
  width={380}
  margin={{ top: 22, right: mode === 'sides' ? 62 : 12, bottom: 22, left: 44 }}
  prerenderTable={false}
  table={{
    caption: mode === 'ratio' ? `${r.short}: nivå per kvartal, som den var känd på postens datum` : `${r.short}: täljare och nämnare, index`,
    columns:
      mode === 'ratio'
        ? [
            { key: 'p', label: 'Kvartal' },
            { key: 'v', label: `Nivå (${r.unit})` }
          ]
        : [
            { key: 'p', label: 'Kvartal' },
            { key: 'n', label: 'Täljaren, index' },
            { key: 'd', label: 'Nämnaren, index' }
          ],
    rows: [...r.periods.keys()].reverse().map((i) => ({
      p: periodLabel(r.periods[i]),
      v: levelText(r.ratio[i] ?? null, r.unit),
      n: fmt(r.num_idx[i], 1),
      d: fmt(r.den_idx[i], 1)
    }))
  }}
>
  {#snippet children(d)}
    {#if n && vals.length}
      {@const x = scaleLinear().domain([t[0] - 0.125, t[n - 1] + 0.125]).range([d.left, d.right])}
      {@const y = useLog ? scaleLog().domain(yDomain).range([d.bottom, d.top]).nice() : scaleLinear().domain(yDomain).range([d.bottom, d.top]).nice()}
      {@const ticks = useLog ? y.ticks(4).filter((v) => /^[125]0*$/.test(String(v))) : y.ticks(4)}
      <text class="ink2 unit" x={d.left} y={d.top - 10}>{mode === 'ratio' ? r.unit : `index, 100 = ${periodLabel(r.periods[r.num_idx.findIndex((v) => v !== null)] ?? r.periods[0])}${useLog ? ', logskala' : ''}`}</text>
      <Axis scale={y} dims={d} orient="left" tickValues={ticks} format={short} grid baseline={mode === 'sides' ? 100 : undefined} />
      <Axis scale={x} dims={d} tickValues={yearTicks(t[0], t[n - 1])} format={(v) => String(v)} />
      <Line data={a} x={(p) => x(p.t)} y={(p) => y(p.v ?? 1)} defined={(p) => p.v !== null && p.v > 0} endLabel={mode === 'sides' ? 'täljare' : undefined} />
      {#if mode === 'sides'}
        <Line data={b} x={(p) => x(p.t)} y={(p) => y(p.v ?? 1)} defined={(p) => p.v !== null && p.v > 0} color="var(--c-ink-2)" dashed endLabel="nämnare" />
      {:else}
        {@const last = [...a].reverse().find((p) => p.v !== null)}
        {#if last}<circle class="mark" cx={x(last.t)} cy={y(last.v ?? 1)} r="4.5" fill={dirColor} stroke="var(--c-surface)" stroke-width="2" />{/if}
      {/if}
    {:else}
      <text class="ink2" x={d.left} y={d.top + d.innerHeight / 2}>{mode === 'ratio' ? 'Ingen nivå i paketet' : 'Komponenterna saknas'}</text>
    {/if}
  {/snippet}
</ChartFrame>
