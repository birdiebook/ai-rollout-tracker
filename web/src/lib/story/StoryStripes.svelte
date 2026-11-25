<!-- W13: the state stripes up to the story month (cut by the gate), the month outlined. Design-system Stripes. -->
<script lang="ts">
  import { ChartFrame, Legend, Stripes, divergingFill, fmt, periodLabel, type RecordStatus } from '$lib/design';
  import type { StripesOn } from '$lib/timetravel/gate';

  let { id, stripes, highlight, status }: { id: string; stripes: StripesOn; highlight: string | null; status: RecordStatus } = $props();
  const n = $derived(stripes.months.length);
  const hi = $derived(highlight ? stripes.months.indexOf(highlight) : -1);
  const description = $derived(
    n
      ? `Diffusionsindex per gren och månad, ${periodLabel(stripes.months[0], true)}–${periodLabel(stripes.months[n - 1], true)}, som det var känt vid månadens slut. ` +
          `Blått: fler serier ökar takten, orange: fler minskar den, grått: balans.`
      : 'Ingen månad var känd ännu.'
  );
  const table = $derived({
    caption: 'Diffusionsindex per gren och månad',
    columns: [{ key: 'b', label: 'Gren', align: 'left' as const }, ...stripes.months.map((m) => ({ key: m, label: periodLabel(m) }))],
    rows: stripes.rows.map((r) => ({ b: `${r.code} ${r.name}`, ...Object.fromEntries(stripes.months.map((m, i) => [m, fmt(r.index[i], 2)])) }))
  });
  const rowH = 22;
</script>

<ChartFrame {id} title="Grenarnas index per månad" {description} height={stripes.rows.length * rowH + 26} margin={{ top: 0, right: 0, bottom: 24, left: 0 }} {status} {table}>
  {#snippet children(d)}
    <Stripes dims={d} months={stripes.months} kind={stripes.kind} rows={stripes.rows} rowHeight={rowH} />
    {#if hi >= 0}
      {@const labelW = d.width < 500 ? 34 : 200}
      {@const cw = (d.width - labelW) / Math.max(1, n)}
      <rect class="hl" x={labelW + hi * cw} y="0" width={cw} height={stripes.rows.length * rowH} />
    {/if}
  {/snippet}
  {#snippet legend()}
    <Legend
      items={[
        { label: '0 · alla minskar takten', fill: divergingFill(0) },
        { label: `${fmt(stripes.thresholds.braking_at_most, 2)}`, fill: divergingFill(stripes.thresholds.braking_at_most) },
        { label: '0,5 · balans', fill: divergingFill(0.5) },
        { label: `${fmt(stripes.thresholds.accelerating_at_least, 2)}`, fill: divergingFill(stripes.thresholds.accelerating_at_least) },
        { label: '1 · alla ökar takten', fill: divergingFill(1) },
        { label: 'ram: månaden', border: 'var(--c-ink)' }
      ]}
    />
  {/snippet}
</ChartFrame>

<style>
  .hl {
    fill: none;
    stroke: var(--c-ink);
    stroke-width: 2;
  }
</style>
