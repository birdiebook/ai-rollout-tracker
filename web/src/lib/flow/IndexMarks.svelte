<!-- Marks of the index-over-time chart (inside a ChartFrame, so the tooltip context is there): the stable zone between
     the registered thresholds, the thresholds themselves with direct labels, the index line (dashed where the month is
     reconstructed, solid where it is a live snapshot) and one dot per month in the state colour. Track W6. -->
<script lang="ts">
  import { scaleLinear, scalePoint } from 'd3-scale';
  import { Axis, Line, fmt, periodLabel, stateStyle, useTooltip, type ChartDims } from '$lib/design';

  type H = { month: string; kind: string; index: number | null; state: string | null; n_series?: number | null };
  let {
    d,
    history,
    lo = 0.33,
    hi = 0.67,
    labels = true
  }: { d: ChartDims; history: H[]; lo?: number; hi?: number; labels?: boolean } = $props();

  const tip = useTooltip();
  const x = $derived(scalePoint<string>().domain(history.map((h) => h.month)).range([d.left, d.right]).padding(0.5));
  const y = $derived(scaleLinear().domain([0, 1]).range([d.bottom, d.top]));
  const step = $derived(history.length > 1 ? (d.right - d.left) / history.length : 20);
  const r = $derived(Math.max(2, Math.min(4, step * 0.38)));
  const live = (h: H) => h.kind === 'skarp' || h.kind === 'live';
  // the reconstructed and the live part share the month where they meet, so the line is continuous
  const firstLive = $derived(history.findIndex(live));
  const reconPart = $derived(firstLive < 0 ? history : history.slice(0, firstLive + 1));
  const livePart = $derived(firstLive < 0 ? [] : history.slice(Math.max(0, firstLive - 1)));
  // January of every year; a short history without a January gets its first month
  const years = $derived.by(() => {
    const jan = history.filter((h) => h.month.endsWith('-01')).map((h) => h.month);
    return jan.length ? jan : history.slice(0, 1).map((h) => h.month);
  });
  const tickLabel = (m: string) => (m.endsWith('-01') ? m.slice(0, 4) : periodLabel(m));
  const xm = (m: string) => x(m) ?? 0;
</script>

<rect x={d.left} y={y(hi)} width={d.right - d.left} height={y(lo) - y(hi)} fill="var(--c-mid)" />
<Axis scale={y} dims={d} orient="left" tickValues={[0, 0.5, 1]} format={(v) => fmt(v, 1)} />
<line class="thr" x1={d.left} x2={d.right} y1={y(hi)} y2={y(hi)} />
<line class="thr" x1={d.left} x2={d.right} y1={y(lo)} y2={y(lo)} />
<text x={d.left - 6} y={y(hi) + 4} text-anchor="end">{fmt(hi, 2)}</text>
<text x={d.left - 6} y={y(lo) + 4} text-anchor="end">{fmt(lo, 2)}</text>
{#if labels}
  <text class="ink2" x={d.right + 6} y={(y(1) + y(hi)) / 2 + 4}>▲ accelererar</text>
  <text class="ink2" x={d.right + 6} y={(y(hi) + y(lo)) / 2 + 4}>● stabil</text>
  <text class="ink2" x={d.right + 6} y={(y(lo) + y(0)) / 2 + 4}>▼ bromsar in</text>
{/if}
<Axis scale={x} dims={d} tickValues={years} format={(v) => tickLabel(String(v))} />

<Line data={reconPart} x={(h) => xm(h.month)} y={(h) => y(h.index ?? 0)} defined={(h) => h.index !== null} dashed width={1.5} color="var(--c-ink-2)" />
{#if livePart.length > 1}
  <Line data={livePart} x={(h) => xm(h.month)} y={(h) => y(h.index ?? 0)} defined={(h) => h.index !== null} />
{/if}

{#each history as h (h.month)}
  {#if h.index !== null}
    {@const s = stateStyle(h.state)}
    <circle
      class="mark dot"
      class:live={live(h)}
      cx={xm(h.month)}
      cy={y(h.index)}
      {r}
      fill={s.key === 'none' ? 'var(--c-surface)' : s.color}
      stroke={s.key === 'none' ? 'var(--c-muted)' : live(h) ? 'var(--c-ink)' : 'var(--c-surface)'}
      stroke-width={live(h) ? 2 : 1}
      data-state={s.key}
      data-kind={h.kind}
      role="presentation"
      onpointerenter={(e) =>
        tip?.show(
          {
            title: periodLabel(h.month, true),
            rows: [
              ['Index', fmt(h.index, 2)],
              ['Tillstånd', `${s.glyph} ${s.word}`],
              ['Serier', h.n_series === null || h.n_series === undefined ? '–' : String(h.n_series)]
            ],
            note: live(h) ? 'skarp ögonblicksbild' : 'rekonstruerad historik'
          },
          e
        )}
      onpointerleave={() => tip?.hide()}
    />
  {/if}
{/each}

<style>
  .thr {
    stroke: var(--c-axis);
    stroke-width: 1;
    stroke-dasharray: 3 3;
  }
  .dot:hover {
    stroke: var(--c-ink);
    stroke-width: 2;
  }
</style>
