<!-- What the holdout showed (2025-07 – 2026-10, opened once): the reported state per month end for each block, as
     computed in real time, and the two BOCPD breaks as markers. Exact states only: the result document gives the
     per-month probabilities only approximately, so they are told in words, not drawn. Track W10. -->
<script lang="ts">
  import { resolve } from '$app/paths';
  import { ChartFrame, fmt, periodLabel } from '$lib/design';
  import { HOLDOUT, monthRange } from './holdout';
  import { cap } from './regime';

  let { links = {} }: { links?: Record<string, boolean> } = $props();
  const months = monthRange(HOLDOUT.first, HOLDOUT.last);
  const CELL_H = 26;
  const LANE = 48;
  const height = 16 + HOLDOUT.blocks.length * LANE + 52 + 24;
  const slow = (b: (typeof HOLDOUT.blocks)[number], m: string) => (b.slow_months as readonly string[]).includes(m);
  const sentence =
    `Holdouten ${periodLabel(HOLDOUT.first)}–${periodLabel(HOLDOUT.last)}, ${HOLDOUT.n_days} månadsslut i realtid: ` +
    HOLDOUT.blocks
      .map((b) => `${b.label} ${b.slow_months.length ? `inbromsning ${b.slow_months.length} månader, sedan expansion` : 'expansion alla månader'}`)
      .join('; ') +
    `. ${HOLDOUT.bocpd.breaks.length} strukturbrott: ` +
    HOLDOUT.bocpd.breaks.map((x) => `${x.series} ${periodLabel(x.month)}`).join(' och ') +
    '.';
</script>

<ChartFrame
  id="holdout-strip"
  title="Holdouten: rapporterat tillstånd per månadsslut"
  description={sentence}
  {height}
  width={760}
  headingLevel={3}
  margin={{ top: 16, right: 12, bottom: 24, left: 12 }}
  table={{
    caption: 'Holdouten: rapporterat tillstånd per block och strukturbrott per månadsslut',
    columns: [
      { key: 'm', label: 'Månad' },
      ...HOLDOUT.blocks.map((b) => ({ key: b.block, label: b.label, align: 'left' as const })),
      { key: 'b', label: 'Strukturbrott', align: 'left' }
    ],
    rows: months.map((m) => ({
      m: periodLabel(m),
      ...Object.fromEntries(HOLDOUT.blocks.map((b) => [b.block, slow(b, m) ? 'inbromsning' : 'expansion'])),
      b: HOLDOUT.bocpd.breaks.filter((x) => x.month === m).map((x) => `${x.series} (${x.branch}, P ${fmt(x.p_recent, 2)})`).join(', ') || '–'
    }))
  }}
>
  {#snippet children(d)}
    {@const w = d.innerWidth / months.length}
    {@const cx = (m: string) => d.left + (months.indexOf(m) + 0.5) * w}
    {#each HOLDOUT.blocks as b, bi (b.block)}
      {@const top = d.top + bi * LANE + 14}
      <text class="lane" x={d.left} y={top - 4}>{cap(b.label)}</text>
      {#each months as m, i (m)}
        <rect
          class="mark"
          x={d.left + i * w + 1}
          y={top}
          width={Math.max(1, w - 2)}
          height={CELL_H}
          rx="2"
          fill={slow(b, m) ? 'var(--c-ink-2)' : 'var(--c-surface)'}
          stroke="var(--c-ink-2)"
          stroke-width="1"
        />
      {/each}
      {#if 'shift_back_month' in b}
        {@const sx = cx(b.shift_back_month) - w / 2}
        <line x1={sx} x2={sx} y1={top - 14} y2={top + CELL_H + 4} stroke="var(--c-ink)" stroke-width="2" />
        <text class="small" x={sx + 4} y={top - 4}>→ tillbaka till expansion</text>
      {/if}
    {/each}
    {@const btop = d.top + HOLDOUT.blocks.length * LANE + 10}
    <text class="lane" x={d.left} y={btop + 4}>Strukturbrott</text>
    <line x1={d.left} x2={d.right} y1={btop + 36} y2={btop + 36} stroke="var(--c-axis)" />
    {#each HOLDOUT.bocpd.breaks as x (x.series)}
      {@const bx = cx(x.month)}
      {@const by = btop + 24}
      {@const right = bx > d.left + d.innerWidth * 0.6}
      <path class="mark" d={`M${bx},${by - 6}L${bx + 6},${by}L${bx},${by + 6}L${bx - 6},${by}Z`} fill="var(--c-ink)" stroke="var(--c-surface)" stroke-width="1.5" />
      <text class="small" x={right ? bx - 9 : bx + 9} y={by + 4} text-anchor={right ? 'end' : 'start'}>{x.series} · {fmt(x.p_recent, 2)}</text>
    {/each}
    {#each months as m, i (m)}
      {#if i % 3 === 0}
        <text class="ink2 small" x={cx(m)} y={d.bottom + 16} text-anchor="middle">{m.endsWith('-01') || i === 0 ? periodLabel(m) : periodLabel(m).split(' ')[0]}</text>
      {/if}
    {/each}
  {/snippet}
  {#snippet legend()}
    <ul class="keys" aria-label="Teckenförklaring">
      <li><span class="sw" aria-hidden="true"></span>expansion</li>
      <li><span class="sw slow" aria-hidden="true"></span>inbromsning (lägre takt, inte nödvändigtvis fallande)</li>
      <li><span class="sw dia" aria-hidden="true"></span>strukturbrott</li>
    </ul>
  {/snippet}
</ChartFrame>
<p class="links">
  Serierna med brott:
  {#each HOLDOUT.bocpd.breaks as x, i (x.series)}{#if i}{', '}{/if}{#if links[x.series]}<a href={resolve('/serie/[key]', { key: x.series })}>{x.series}</a>{:else}<code>{x.series}</code>{/if} ({x.latest_period}, beräknat {x.date}){/each}.
</p>

<style>
  .lane {
    font-size: 12px;
    font-weight: 620;
    fill: var(--c-ink);
  }
  .small {
    font-size: 11px;
    fill: var(--c-ink);
  }
  .ink2.small {
    fill: var(--c-ink-2);
  }
  .keys {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-wrap: wrap;
    gap: 4px 14px;
    font-size: 12px;
    color: var(--c-ink-2);
  }
  .sw {
    display: inline-block;
    width: 12px;
    height: 12px;
    margin-right: 5px;
    vertical-align: -1px;
    border: 1px solid var(--c-ink-2);
    border-radius: 2px;
    box-sizing: border-box;
    background: var(--c-surface);
  }
  .sw.slow {
    background: var(--c-ink-2);
  }
  .sw.dia {
    width: 9px;
    height: 9px;
    transform: rotate(45deg);
    background: var(--c-ink);
    border: 0;
    border-radius: 0;
    margin-left: 2px;
  }
  .links {
    font-size: var(--fs-small);
    color: var(--c-ink-2);
    margin: 6px 0 0;
  }
</style>
