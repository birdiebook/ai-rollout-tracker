<!-- A branch's diffusion index over time in a ChartFrame: stable zone and thresholds, state per month, reconstructed
     months dashed (P9), table view with the same numbers. Track W6. -->
<script lang="ts">
  import { ChartFrame, Legend, fmt, periodLabel, stateStyle, type RecordStatus } from '$lib/design';
  import IndexMarks from './IndexMarks.svelte';
  import { indexSentence } from './prepare';

  type H = { month: string; kind: string; index: number | null; state: string | null; n_series?: number | null };
  let {
    id,
    title = 'Diffusionsindex över tid',
    history,
    status,
    lo = 0.33,
    hi = 0.67,
    height = 220,
    headingLevel = 2,
    showLegend = true
  }: {
    id: string;
    title?: string;
    history: H[];
    status: RecordStatus;
    lo?: number;
    hi?: number;
    height?: number;
    headingLevel?: 2 | 3 | 4;
    showLegend?: boolean;
  } = $props();
</script>

<ChartFrame
  {id}
  {title}
  description={indexSentence(history)}
  {height}
  {status}
  {headingLevel}
  legend={showLegend ? legendRow : undefined}
  margin={{ top: 12, right: 84, bottom: 24, left: 40 }}
  table={{
    caption: `${title}: index och tillstånd per månadsslut`,
    columns: [
      { key: 'm', label: 'Månad' },
      { key: 'i', label: 'Index' },
      { key: 's', label: 'Tillstånd', align: 'left' },
      { key: 'n', label: 'Serier' },
      { key: 'k', label: 'Underlag', align: 'left' }
    ],
    rows: [...history].reverse().map((h) => ({
      m: periodLabel(h.month),
      i: fmt(h.index, 2),
      s: `${stateStyle(h.state).glyph} ${stateStyle(h.state).word}`,
      n: h.n_series ?? null,
      k: h.kind
    }))
  }}
>
  {#snippet children(d)}
    <IndexMarks {d} {history} {lo} {hi} />
  {/snippet}
</ChartFrame>

{#snippet legendRow()}
  <Legend
    items={[
      { label: 'stabil zon mellan gränserna', fill: 'var(--c-mid)', border: 'var(--c-axis)' },
      { label: 'streckad linje: rekonstruerad historik', line: true, fill: 'var(--c-ink-2)' },
      { label: 'ring: skarp ögonblicksbild', fill: 'var(--c-surface)', border: 'var(--c-ink)' }
    ]}
  />
{/snippet}
