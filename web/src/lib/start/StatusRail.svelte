<!-- A rail above the stripes that marks which months are reconstructed (dashed) and which are live snapshots
     (solid), so the record status sits in the picture, not in a footnote (P9, lesson 7). The label column width
     mirrors the design system's Stripes (34 px under 500 px width, else 200 px). -->
<script lang="ts">
  import type { ChartDims } from '$lib/design';

  let { d, kind }: { d: ChartDims; kind: (string | null)[] } = $props();
  const labelW = $derived(d.width < 500 ? 34 : 200);
  const cw = $derived((d.width - labelW) / Math.max(1, kind.length));
  const runs = $derived.by(() => {
    const out: { live: boolean; from: number; to: number }[] = [];
    kind.forEach((k, i) => {
      const live = k === 'skarp' || k === 'live';
      const last = out.at(-1);
      if (last && last.live === live) last.to = i;
      else out.push({ live, from: i, to: i });
    });
    return out;
  });
</script>

{#each runs as r (r.from)}
  {@const x0 = labelW + r.from * cw + 1}
  {@const x1 = labelW + (r.to + 1) * cw - 1}
  {@const atEnd = r.to === kind.length - 1 && x1 - x0 < 140}
  <line
    class="mark"
    x1={x0}
    x2={x1}
    y1="14"
    y2="14"
    stroke={r.live ? 'var(--c-ink)' : 'var(--c-axis)'}
    stroke-width={r.live ? 3 : 2}
    stroke-dasharray={r.live ? undefined : '4 3'}
    data-status={r.live ? 'live' : 'recon'}
  />
  <text class={r.live ? 'ink' : 'ink2'} x={atEnd ? x1 : x0} y="8" text-anchor={atEnd ? 'end' : 'start'}>
    {r.live ? 'skarp ögonblicksbild' : 'rekonstruerad historik'}
  </text>
{/each}
