<!-- Q1 "Var står vi nu?": each branch's diffusion index on 0–1 this month (dot, state colour) and last month (ring),
     joined by a line: position and change in one picture (lesson 4). The stable zone between the registered
     thresholds is the grey band. Clicking a row opens the branch (pointer shortcut; the chain above has the links). -->
<script lang="ts">
  import { ChartFrame, fmt, periodLabel, stateStyle } from '$lib/design';
  import NowMarks from './NowMarks.svelte';
  import { nowDescription, type StartData } from './model';

  let { start }: { start: StartData } = $props();
  const rowH = 24;
  const month = $derived(periodLabel(start.record.month, true));
  const prev = $derived(start.headline.prevMonth ? periodLabel(start.headline.prevMonth, true) : null);
  const description = $derived(nowDescription(start.branches, month, prev));
  // v1 beside v2: a tick where v1's index differs from the official one
  const v1 = $derived(start.branches.some((b) => b.rule_version === 'v2' && b.index_v1 !== null && b.index !== null && Math.abs(b.index_v1 - b.index) > 0.005));
  const table = $derived({
    caption: `Diffusionsindex per gren, ${month}${prev ? ` och ${prev}` : ''}`,
    columns: [
      { key: 'g', label: 'Gren' },
      { key: 'i', label: 'Index' },
      { key: 'p', label: 'Förra månaden' },
      { key: 's', label: 'Tillstånd' },
      { key: 'f', label: 'Källfamiljer' },
      { key: 'n', label: 'Serier ▲ ● ▼' },
      { key: 'v', label: 'Regel v1' }
    ],
    rows: start.branches.map((b) => ({
      g: `${b.code} ${b.name}`,
      i: fmt(b.index, 2),
      p: fmt(b.prev?.index ?? null, 2),
      s: `${stateStyle(b.state).glyph} ${b.state}`,
      f: b.n_families === null ? '–' : String(b.n_families),
      n: `${b.n_up} · ${b.n_neutral} · ${b.n_down}`,
      v: b.rule_version === 'v2' && b.index_v1 !== null ? `${fmt(b.index_v1, 2)} ${b.state_v1 ?? ''}`.trim() : '–'
    }))
  });
</script>

<ChartFrame
  id="now"
  title="Diffusionsindex per gren"
  {description}
  height={start.branches.length * rowH + 40}
  width={340}
  margin={{ top: 2, right: 10, bottom: 38, left: 34 }}
  {table}
  status={start.record.status === 'live' ? 'live' : 'recon'}
>
  {#snippet children(d)}<NowMarks {d} {start} {rowH} />{/snippet}
  {#snippet legend()}
    <p class="note k">
      <span><svg width="14" height="14" aria-hidden="true"><circle cx="7" cy="7" r="5.5" fill="var(--c-stb)" /></svg> nu, i tillståndets färg</span>
      <span><svg width="14" height="14" aria-hidden="true"><circle cx="7" cy="7" r="3.5" fill="none" stroke="var(--c-ink-2)" stroke-width="1.5" /></svg> förra månaden</span>
      <span><svg width="14" height="14" aria-hidden="true"><circle cx="7" cy="7" r="5.5" fill="none" stroke="var(--c-muted)" stroke-width="1.5" stroke-dasharray="3 2" /></svg> för få källor för ett tillstånd</span>
      {#if v1}<span><svg width="14" height="14" aria-hidden="true"><line x1="7" x2="7" y1="1" y2="13" stroke="var(--c-ink-2)" stroke-width="2" /></svg> regel v1, en röst per serie</span>{/if}
    </p>
  {/snippet}
</ChartFrame>

<style>
  .k {
    display: flex;
    flex-wrap: wrap;
    gap: 2px 12px;
    margin: 0;
  }
  .k span {
    display: inline-flex;
    align-items: center;
    gap: 4px;
  }
</style>
