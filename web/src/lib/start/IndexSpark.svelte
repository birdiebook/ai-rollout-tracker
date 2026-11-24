<!-- A branch's diffusion index over the last 24 months: the stable zone (0.33–0.67) as a band with the thresholds
     dashed, the line in neutral ink (colour is the state of the end dot only). Reconstructed months are drawn lighter
     and thinner than live ones (P9). Hover shows the month (pointer only; the stripes table has every number). -->
<script lang="ts">
  import { fmt, periodLabel, stateStyle, useTooltip } from '$lib/design';
  import type { SparkView } from './model';

  let {
    spark,
    code,
    low = 0.33,
    high = 0.67,
    width = 104,
    height = 38
  }: { spark: SparkView; code: string; low?: number; high?: number; width?: number; height?: number } = $props();

  let measured = $state(0);
  const w = $derived(measured > 0 ? Math.round(measured) : width);
  const tip = useTooltip();
  const pad = 4;
  const n = $derived(spark.index.length);
  const x = (i: number) => pad + (i * (w - 2 * pad)) / Math.max(1, n - 1);
  const y = (v: number) => height - 3 - v * (height - 6);

  function path(keep: (i: number) => boolean) {
    let d = '';
    let pen = false;
    spark.index.forEach((v, i) => {
      if (v === null || !keep(i)) {
        pen = false;
        return;
      }
      d += `${pen ? 'L' : 'M'}${x(i).toFixed(1)},${y(v).toFixed(1)}`;
      pen = true;
    });
    return d;
  }
  const live = (i: number) => spark.kind[i] === 'skarp';
  // a live segment also joins the last reconstructed month, so the line has no gap
  const recon = $derived(path((i) => !live(i)));
  const liveD = $derived(path((i) => live(i) || (i + 1 < n && live(i + 1))));
  const lastI = $derived(spark.index.findLastIndex((v) => v !== null));
  const endState = $derived(stateStyle(lastI >= 0 ? spark.state[lastI] : null));
  const first = $derived(spark.index.find((v) => v !== null) ?? null);
  const last = $derived(lastI >= 0 ? spark.index[lastI] : null);
  const label = $derived(
    last === null
      ? `${code}: inget diffusionsindex de senaste ${n} månaderna`
      : `${code}, diffusionsindex ${periodLabel(spark.months[0])}–${periodLabel(spark.months.at(-1) ?? '')}: från ${fmt(first, 2)} till ${fmt(last, 2)}`
  );

  function onMove(e: PointerEvent) {
    const svg = e.currentTarget as SVGSVGElement;
    const r = svg.getBoundingClientRect();
    const px = ((e.clientX - r.left) / Math.max(1, r.width)) * w;
    const i = Math.max(0, Math.min(n - 1, Math.round(((px - pad) / Math.max(1, w - 2 * pad)) * (n - 1))));
    const v = spark.index[i];
    const st = stateStyle(spark.state[i]);
    tip?.show(
      {
        title: `${code} ${periodLabel(spark.months[i], true)}`,
        rows: [
          ['Index', v === null ? 'inget index' : fmt(v, 2)],
          ['Tillstånd', `${st.glyph} ${st.word}`]
        ],
        note: spark.kind[i] === 'skarp' ? 'skarp ögonblicksbild' : 'rekonstruerad historik'
      },
      e
    );
  }
</script>

<div class="spark" bind:clientWidth={measured}>
  <svg viewBox="0 0 {w} {height}" width="100%" {height} role="img" aria-label={label} onpointermove={onMove} onpointerleave={() => tip?.hide()}>
    <rect x="0" y={y(high)} width={w} height={y(low) - y(high)} fill="var(--c-mid)" rx="2" />
    <line class="thr" x1="0" x2={w} y1={y(high)} y2={y(high)} />
    <line class="thr" x1="0" x2={w} y1={y(low)} y2={y(low)} />
    {#if recon}<path class="mark" d={recon} fill="none" stroke="var(--c-ink-2)" stroke-width="1.5" stroke-linejoin="round" opacity="0.75" />{/if}
    {#if liveD}<path class="mark" d={liveD} fill="none" stroke="var(--c-ink)" stroke-width="2.25" stroke-linejoin="round" />{/if}
    {#if last !== null}
      <circle
        class="mark"
        cx={x(lastI)}
        cy={y(last)}
        r="4"
        fill={endState.key === 'none' ? 'var(--c-surface)' : endState.color}
        stroke={endState.key === 'none' ? 'var(--c-muted)' : 'var(--c-surface)'}
        stroke-width="1.5"
      />
    {/if}
  </svg>
</div>

<style>
  .spark {
    min-width: 0;
  }
  svg {
    display: block;
    overflow: visible;
  }
  .thr {
    stroke: var(--c-axis);
    stroke-width: 1;
    stroke-dasharray: 2 3;
  }
</style>
