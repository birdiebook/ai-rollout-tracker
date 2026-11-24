<!-- Q2: how well the champion's intervals held in the backtest, in one picture (always marked backtest). -->
<script lang="ts">
  import { ChartFrame, fmt } from '$lib/design';
  import CalibrationMarks from './CalibrationMarks.svelte';
  import { calibrationDescription, type CalibrationView } from './model';

  let { c }: { c: CalibrationView } = $props();
  const rowH = 20;
  const p = (v: number | null) => (v === null ? '–' : `${fmt(v * 100, 0)} %`);
  const table = $derived({
    caption: `Täckning i backtest, ${c.label} (${c.model}, n = ${c.n})`,
    columns: [
      { key: 'l', label: 'Nivå' },
      { key: 'c', label: 'Täckning' },
      { key: 'b', label: 'Slumpband' }
    ],
    rows: c.rows.map((r) => ({ l: `${r.level} %`, c: p(r.coverage), b: r.band ? `${p(r.band[0])}–${p(r.band[1])}` : '–' }))
  });
</script>

<ChartFrame
  id="calibration"
  title="Hur intervallen har hållit för {c.label}"
  description={calibrationDescription(c)}
  height={c.rows.length * rowH + 22}
  width={340}
  margin={{ top: 0, right: 44, bottom: 22, left: 40 }}
  {table}
  status="backtest"
>
  {#snippet children(d)}<CalibrationMarks {d} {c} {rowH} />{/snippet}
  {#snippet legend()}
    <p class="note k">streck: nominell nivå · grått: 90 % slumpband · prick: andel utfall inom intervallet</p>
  {/snippet}
</ChartFrame>

<style>
  .k {
    margin: 0;
  }
</style>
