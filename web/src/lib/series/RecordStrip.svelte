<!-- The series' direction in the record at every month end (measure_history): one cell per month in the state
     colours (▲ ● ▼ in the cell when there is room), reconstructed months dashed/lighter and live ones solid (P9).
     These are the state engine's numbers as the record said them that month, never recomputed. -->
<script lang="ts">
  import { ChartFrame, DIRECTIONS, StripeCell, periodLabel, type RecordStatus } from '$lib/design';
  import { periodText } from './period';
  import { snum } from './text';
  import type { MeasureHistory } from './types';

  let { history, source, license }: { history: MeasureHistory; source?: string; license?: string } = $props();

  const n = $derived(history.months.length);
  const dirAt = (i: number) => (history.valid?.[i] === false ? null : (history.direction?.[i] ?? null));
  const status = (i: number): RecordStatus => (history.kind[i] === 'skarp' ? 'live' : 'recon');
  const nLive = $derived(history.kind.filter((k) => k === 'skarp').length);
  const counts = $derived(
    [1, 0, -1].map((d) => history.months.filter((_, i) => dirAt(i) === d).length)
  );
  const description = $derived(
    `${n} månadsslut från ${periodLabel(history.months[0] ?? '', true)}: ${counts[0]} gånger ökar takten, ${counts[1]} oförändrad, ${counts[2]} minskar takten` +
      (nLive ? `; ${nLive} skarpa ögonblicksbilder.` : '; allt är rekonstruerad historik.')
  );
  const word = (i: number) => {
    const d = dirAt(i);
    return d === null ? 'inget mått' : `${DIRECTIONS[d].glyph} ${DIRECTIONS[d].word}`;
  };
</script>

<ChartFrame
  id="record"
  title="Riktning i posten, månad för månad"
  {description}
  height={64}
  margin={{ top: 4, right: 4, bottom: 24, left: 4 }}
  status={nLive ? 'live' : 'recon'}
  {source}
  {license}
  table={{
    caption: 'Postens mått vid varje månadsslut, nyast först.',
    columns: [
      { key: 'm', label: 'Månad' },
      { key: 'p', label: 'Senaste period' },
      { key: 'pace', label: 'Takt' },
      { key: 'change', label: 'Förändring i takt' },
      { key: 'dir', label: 'Riktning', align: 'left' },
      { key: 'kind', label: 'Underlag', align: 'left' }
    ],
    rows: history.months
      .map((m, i) => ({
        m: periodLabel(m, true),
        p: history.latest_period?.[i] ? periodText(history.latest_period[i] ?? '') : '–',
        pace: snum(history.pace?.[i]),
        change: snum(history.change_in_pace?.[i]),
        dir: word(i),
        kind: history.kind[i] === 'skarp' ? 'skarp' : 'rekonstruerad'
      }))
      .reverse()
  }}
>
  {#snippet children(d)}
    {@const cw = d.innerWidth / Math.max(1, n)}
    {#each history.months as m, i (m)}
      {@const dd = dirAt(i)}
      <StripeCell
        x={d.left + i * cw}
        y={d.top}
        width={cw}
        height={d.innerHeight}
        value={dd === null ? null : (dd + 1) / 2}
        status={status(i)}
        tooltip={{
          title: periodLabel(m, true),
          rows: [
            ['Riktning', word(i)],
            ['Senaste period', history.latest_period?.[i] ? periodText(history.latest_period[i] ?? '') : '–'],
            ['Takt', snum(history.pace?.[i])],
            ['Förändring i takt', snum(history.change_in_pace?.[i])],
            ['Räknas i grenen', history.counted[i] ? 'ja' : 'nej']
          ],
          note: status(i) === 'live' ? 'skarp ögonblicksbild' : 'rekonstruerad historik'
        }}
      />
      {#if dd !== null && cw >= 16}
        <text class="cell-glyph" x={d.left + i * cw + cw / 2} y={d.top + d.innerHeight / 2 + 4} text-anchor="middle" aria-hidden="true">{DIRECTIONS[dd].glyph}</text>
      {/if}
      {#if m.endsWith('-01') || i === 0}
        <text x={d.left + i * cw} y={d.bottom + 16}>{i === 0 && !m.endsWith('-01') ? periodLabel(m) : m.slice(0, 4)}</text>
      {/if}
    {/each}
  {/snippet}
</ChartFrame>

<style>
  .cell-glyph {
    fill: var(--c-ink);
    font-size: 10px;
    pointer-events: none;
  }
</style>
