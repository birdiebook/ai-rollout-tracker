<!-- The live regime record as one timeline: a lane per block with P(inbromsning) (area and dots, neutral ink) and
     the registered thresholds 0,8 and 0,2, shifts as vertical markers, and a lane with the BOCPD structural breaks
     as markers (a withheld series' break is a hollow, nameless marker: counted, no name, no value). The axis runs
     at least twelve months from the first live month, so the months to come are visibly empty. Track W10. -->
<script lang="ts">
  import { ChartFrame, fmt, periodLabel, type RecordStatus } from '$lib/design';
  import { RULES, breaksSentence, cap, headline, pText } from './regime';
  import type { BreakView, RegimeLane } from './types';

  let {
    months,
    liveMonths,
    lanes,
    breaks,
    nWithheld,
    firstLive,
    status
  }: {
    months: string[];
    liveMonths: string[];
    lanes: RegimeLane[];
    breaks: BreakView[];
    nWithheld: number;
    firstLive: string;
    status?: RecordStatus;
  } = $props();

  const LANE = 80;
  const GAP = 34;
  const BRK = 54;
  const laneList = $derived(lanes.length ? lanes : [{ block: '-', label: 'P(inbromsning)', history: [], latest: null } as RegimeLane]);
  const liveLanes = $derived(lanes.filter((l) => l.history.length));
  const height = $derived(14 + laneList.length * (LANE + GAP) + BRK + 34);
  const lastLive = $derived(liveMonths.at(-1) ?? null);
  const breaksBy = $derived.by(() => {
    const m = new Map<string, BreakView[]>();
    for (const b of breaks) m.set(b.month, [...(m.get(b.month) ?? []), b]);
    return m;
  });
  const sentence = $derived(
    `${headline(liveMonths.length > 0, liveLanes, firstLive)} ${breaksSentence(breaks.length, nWithheld, liveMonths.length)}`
  );
  const tableRows = $derived(
    [...liveMonths].reverse().map((m) => {
      const row: Record<string, string> = { m: periodLabel(m) };
      for (const l of liveLanes) {
        const h = l.history.find((x) => x.month === m);
        row[`p-${l.block}`] = pText(h?.p ?? null);
        row[`s-${l.block}`] = (h?.state ?? '–') + (h?.shift ? ' (skifte)' : '');
      }
      row.b = (breaksBy.get(m) ?? []).map((b) => `${b.series} (${b.branch ?? ''}, P ${pText(b.p_recent)})`).join(', ') || '–';
      return row;
    })
  );
  const monthTick = (m: string) => (m.endsWith('-01') || m === months[0] ? periodLabel(m) : periodLabel(m).split(' ')[0]);
</script>

<ChartFrame
  id="regime-timeline"
  title="Regimsannolikhet och strukturbrott, skarpa månader"
  description={sentence}
  {height}
  width={760}
  {status}
  headingLevel={2}
  margin={{ top: 14, right: 40, bottom: 26, left: 12 }}
  table={{
    caption: 'Skarpa månader: P(inbromsning), rapporterat tillstånd och strukturbrott',
    columns: [
      { key: 'm', label: 'Månad' },
      ...liveLanes.flatMap((l) => [
        { key: `p-${l.block}`, label: `P(inbromsning), ${l.label}` },
        { key: `s-${l.block}`, label: `Tillstånd, ${l.label}`, align: 'left' as const }
      ]),
      { key: 'b', label: 'Strukturbrott', align: 'left' }
    ],
    rows: tableRows.length ? tableRows : [{ m: 'Inga skarpa månader än' }]
  }}
>
  {#snippet children(d)}
    {@const n = months.length}
    {@const w = d.innerWidth / Math.max(1, n)}
    {@const cx = (m: string) => d.left + (months.indexOf(m) + 0.5) * w}
    {@const futureFrom = lastLive ? months.indexOf(lastLive) + 1 : 0}
    {#if futureFrom < n}
      <rect x={d.left + futureFrom * w} y={d.top} width={(n - futureFrom) * w} height={d.innerHeight} class="future" />
      <text class="ink2 small" x={d.left + futureFrom * w + 6} y={d.top + 30 + LANE / 2 + 4}>{lastLive ? 'kommande månader' : `skarpt från ${periodLabel(firstLive.slice(0, 7))}`}</text>
    {/if}
    {#each laneList as l, li (l.block)}
      {@const top = d.top + li * (LANE + GAP) + 30}
      {@const y = (p: number) => top + (1 - p) * LANE}
      {@const pts = l.history.filter((h) => h.p !== null && months.includes(h.month))}
      <text class="lane" x={d.left} y={top - 12}>{cap(l.label)}</text>
      <line class="frame" x1={d.left} x2={d.right} y1={y(0)} y2={y(0)} />
      <line class="frame" x1={d.left} x2={d.right} y1={y(1)} y2={y(1)} />
      <line class="thr" x1={d.left} x2={d.right} y1={y(RULES.shiftAtLeast)} y2={y(RULES.shiftAtLeast)} />
      <line class="thr" x1={d.left} x2={d.right} y1={y(RULES.backAtMost)} y2={y(RULES.backAtMost)} />
      <text class="ink2 small" x={d.right + 4} y={y(RULES.shiftAtLeast) + 4}>{fmt(RULES.shiftAtLeast, 1)}</text>
      <text class="ink2 small" x={d.right + 4} y={y(RULES.backAtMost) + 4}>{fmt(RULES.backAtMost, 1)}</text>
      <text class="ink2 small" x={d.right + 4} y={y(1) + 4}>1</text>
      <text class="ink2 small" x={d.right + 4} y={y(0) + 4}>0</text>
      {#if pts.length > 1}
        <path
          class="area"
          d={`M${cx(pts[0].month)},${y(0)}` + pts.map((h) => `L${cx(h.month)},${y(h.p ?? 0)}`).join('') + `L${cx(pts[pts.length - 1].month)},${y(0)}Z`}
        />
        <path class="pline" d={pts.map((h, i) => `${i ? 'L' : 'M'}${cx(h.month)},${y(h.p ?? 0)}`).join('')} />
      {/if}
      {#each pts as h (h.month)}
        <circle class="mark" cx={cx(h.month)} cy={y(h.p ?? 0)} r="4.5" fill="var(--c-ink)" stroke="var(--c-surface)" stroke-width="2" />
        <text class="val" x={cx(h.month)} y={y(h.p ?? 0) + ((h.p ?? 0) > 0.6 ? 18 : -9)} text-anchor="middle">{pText(h.p)}</text>
      {/each}
      {#each l.history.filter((h) => h.shift && months.includes(h.month)) as h (h.month)}
        <line class="shift" x1={cx(h.month) - w / 2} x2={cx(h.month) - w / 2} y1={top - 2} y2={y(0)} />
        <!-- the label goes where the dots are not: a shift to slowdown has p >= 0.8 (top), a shift back p <= 0.2 -->
        <text class="small ink2" x={cx(h.month) - w / 2 + 4} y={h.shift === 'inbromsning' ? y(0) - 5 : y(1) + 13}>skifte: {h.shift}</text>
      {/each}
    {/each}
    {@const btop = d.top + laneList.length * (LANE + GAP) + 12}
    <text class="lane" x={d.left} y={btop + 6}>Strukturbrott (BOCPD, P(körlängd ≤ {RULES.runLength}) ≥ {fmt(RULES.breakAtLeast, 1)})</text>
    <line class="frame" x1={d.left} x2={d.right} y1={btop + BRK - 10} y2={btop + BRK - 10} />
    {#each [...breaksBy] as [m, bs] (m)}
      {#each bs as b, j (b.series)}
        {@const bx = cx(m)}
        {@const by = btop + BRK - 22 - j * 14}
        <path class="mark" d={`M${bx},${by - 6}L${bx + 6},${by}L${bx},${by + 6}L${bx - 6},${by}Z`} fill="var(--c-ink)" stroke="var(--c-surface)" stroke-width="1.5" />
        <text class="small" x={bx > d.right - 110 ? bx - 9 : bx + 9} y={by + 4} text-anchor={bx > d.right - 110 ? 'end' : 'start'}>{b.series}</text>
      {/each}
    {/each}
    {#if nWithheld && lastLive}
      {@const bx = cx(lastLive)}
      {@const by = btop + BRK - 22 - (breaksBy.get(lastLive)?.length ?? 0) * 14}
      <path d={`M${bx},${by - 6}L${bx + 6},${by}L${bx},${by + 6}L${bx - 6},${by}Z`} fill="var(--c-surface)" stroke="var(--c-ink-2)" stroke-dasharray="2 2" stroke-width="1.5" />
      <text class="small ink2" x={bx > d.right - 110 ? bx - 9 : bx + 9} y={by + 4} text-anchor={bx > d.right - 110 ? 'end' : 'start'}>{nWithheld} i inhållen serie</text>
    {/if}
    {@const every = Math.max(1, Math.ceil((n * 54) / Math.max(1, d.innerWidth)))}
    {#each months as m, i (m)}
      {#if i % every === 0}
        <text class="ink2 small" x={cx(m)} y={d.bottom + 16} text-anchor="middle">{monthTick(m)}</text>
      {/if}
    {/each}
    <line class="frame" x1={d.left} x2={d.right} y1={d.bottom + 0.5} y2={d.bottom + 0.5} />
  {/snippet}
  {#snippet legend()}
    <ul class="keys" aria-label="Teckenförklaring">
      <li><span class="sw dot" aria-hidden="true"></span>P(inbromsning) vid månadsslut</li>
      <li><span class="sw thr" aria-hidden="true"></span>registrerade trösklar {fmt(RULES.backAtMost, 1)} och {fmt(RULES.shiftAtLeast, 1)}, två månader i rad</li>
      <li><span class="sw dia" aria-hidden="true"></span>strukturbrott i en kärnserie</li>
      {#if nWithheld}<li><span class="sw dia held" aria-hidden="true"></span>brott i en inhållen serie (räknas, utan namn)</li>{/if}
    </ul>
  {/snippet}
</ChartFrame>

<style>
  .future {
    fill: var(--c-page);
    stroke: var(--c-grid);
    stroke-dasharray: 3 3;
  }
  .lane {
    font-size: 12px;
    font-weight: 620;
    fill: var(--c-ink);
  }
  .small {
    font-size: 11px;
  }
  .val {
    font-size: 11px;
    font-weight: 600;
    fill: var(--c-ink);
    font-variant-numeric: tabular-nums;
  }
  .frame {
    stroke: var(--c-axis);
  }
  .thr {
    stroke: var(--c-ink-2);
    stroke-dasharray: 5 4;
  }
  .area {
    fill: var(--c-ink);
    opacity: 0.1;
  }
  .pline {
    fill: none;
    stroke: var(--c-ink);
    stroke-width: 2;
    stroke-linejoin: round;
  }
  .shift {
    stroke: var(--c-ink);
    stroke-width: 1.5;
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
    box-sizing: border-box;
  }
  .sw.dot {
    border-radius: 50%;
    background: var(--c-ink);
  }
  .sw.thr {
    height: 0;
    border-top: 2px dashed var(--c-ink-2);
    vertical-align: 3px;
  }
  .sw.dia {
    width: 9px;
    height: 9px;
    transform: rotate(45deg);
    background: var(--c-ink);
    margin-left: 2px;
  }
  .sw.dia.held {
    background: var(--c-surface);
    border: 1.5px dashed var(--c-ink-2);
  }
</style>
