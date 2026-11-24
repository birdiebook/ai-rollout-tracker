<!-- Placeholder for a quantile dot plot before the first live forecast: 20 dashed rings in the shape the forecast will
     take. Illustrative only, no values (aria-hidden; the text next to it says what will be shown). -->
<script lang="ts">
  import { binDots, dotValues } from '$lib/design';
  const W = 320;
  const r = 7;
  // a symmetric, slightly heavy-tailed shape on [0, 1]
  const vals = dotValues([[0.025, 0.06], [0.1, 0.22], [0.25, 0.37], [0.5, 0.5], [0.75, 0.63], [0.9, 0.78], [0.975, 0.94]], 20);
  const dots = binDots(vals, (v) => 10 + v * (W - 20), 10, r);
  const H = Math.max(...dots.map((d) => d.k)) * r * 2.1 + r * 2 + 12;
</script>

<svg class="ghost" viewBox="0 0 {W} {H}" width="100%" aria-hidden="true">
  {#each dots as d, i (i)}
    <circle cx={d.cx} cy={H - 8 - r - d.k * r * 2.1} {r} fill="none" stroke="var(--c-axis)" stroke-width="1.5" stroke-dasharray="3 2.5" />
  {/each}
  <line x1="10" x2={W - 10} y1={H - 4} y2={H - 4} stroke="var(--c-axis)" />
</svg>

<style>
  .ghost {
    display: block;
    max-width: 360px;
    margin: 0 auto;
  }
</style>
