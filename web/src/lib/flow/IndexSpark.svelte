<!-- A tiny index line for the chain overview (aria-hidden: the number and state are in the text next to it):
     stable zone between the thresholds, the index over the last months, the last value as a tick. Track W6. -->
<script lang="ts">
  let {
    values,
    lo = 0.33,
    hi = 0.67,
    color = 'var(--c-ink)'
  }: { values: (number | null)[]; lo?: number; hi?: number; color?: string } = $props();
  const W = 120;
  const H = 28;
  const x = (i: number) => (values.length > 1 ? (i / (values.length - 1)) * W : W / 2);
  const y = (v: number) => H - 2 - v * (H - 4);
  const path = $derived.by(() => {
    let d = '';
    values.forEach((v, i) => {
      if (v === null) return;
      d += `${i === 0 || values[i - 1] === null ? 'M' : 'L'}${x(i).toFixed(1)},${y(v).toFixed(1)} `;
    });
    return d.trim();
  });
</script>

<svg viewBox="0 0 {W} {H}" preserveAspectRatio="none" aria-hidden="true" focusable="false">
  <rect x="0" y={y(hi)} width={W} height={y(lo) - y(hi)} fill="var(--c-mid)" />
  {#if path}
    <path d={path} fill="none" stroke={color} stroke-width="1.6" vector-effect="non-scaling-stroke" stroke-linejoin="round" />
  {/if}
</svg>

<style>
  svg {
    display: block;
    width: 100%;
    height: 28px;
  }
</style>
