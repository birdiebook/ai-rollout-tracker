<!-- The state stripes as known on the day (W9): the design system's Stripes over the known months only, at the
     width they have in the full calendar, and the months after the day left empty. Click a column to travel. -->
<script lang="ts">
  import { ChartFrame, Stripes, dateLabel, fmt, periodLabel, stateStyle, type RecordStatus } from '$lib/design';
  import { monthEnd, type StripesOn } from '../gate';

  let {
    stripes,
    months,
    day,
    status,
    onpick
  }: { stripes: StripesOn; months: string[]; day: string; status: RecordStatus; onpick?: (day: string) => void } = $props();

  const ROW = 24;
  const n = $derived(stripes.months.length);
  const sentence = $derived(
    n
      ? `Grenarnas tillstånd per månadsslut från ${periodLabel(stripes.months[0], true)} till ${periodLabel(stripes.months[n - 1], true)}, som de var kända den ${dateLabel(day)}.`
      : `Den ${dateLabel(day)} fanns ännu inga månadsslut i historiken.`
  );
  const table = $derived({
    caption: `Index per gren och månad, kända den ${day}`,
    columns: [{ key: 'm', label: 'Månad' }, ...stripes.rows.map((r) => ({ key: r.code, label: r.code }))],
    rows: [...stripes.months.keys()].reverse().map((i) => ({
      m: periodLabel(stripes.months[i]),
      ...Object.fromEntries(stripes.rows.map((r) => [r.code, r.index[i] === null ? '–' : `${stateStyle(r.state[i]).glyph} ${fmt(r.index[i], 2)}`]))
    }))
  });
  function pick(e: MouseEvent, width: number, labelW: number, cw: number) {
    if (!onpick) return;
    const svg = (e.currentTarget as SVGElement).ownerSVGElement;
    const box = svg?.getBoundingClientRect();
    if (!box) return;
    const px = ((e.clientX - box.left) / box.width) * width;
    const i = Math.floor((px - labelW) / cw);
    if (i >= 0 && i < months.length) onpick(monthEnd(months[i]));
  }
</script>

<ChartFrame id="tt-stripes" title="Hur tillstånden hade skiftat" description={sentence} height={ROW * stripes.rows.length + 26} margin={{ top: 0, right: 0, bottom: 0, left: 0 }} {status} {table} headingLevel={2}>
  {#snippet children(d)}
    {@const labelW = d.width < 500 ? 34 : 200}
    {@const cw = (d.width - labelW) / Math.max(1, months.length)}
    {@const knownW = labelW + cw * n}
    <!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -- pointer shortcut; the slider is the keyboard path -->
    <g class="pick" onclick={(e) => pick(e, d.width, labelW, cw)} data-known={stripes.known.at(-1) ?? ''}>
      {#if n}
        <Stripes dims={{ ...d, width: knownW, right: knownW, innerWidth: knownW }} months={stripes.months} kind={stripes.kind} rows={stripes.rows} rowHeight={ROW} />
      {:else}
        {#each stripes.rows as r, j (r.code)}
          <text class="ink2" x="0" y={j * ROW + ROW / 2 + 4}>{d.width < 500 ? r.code : `${r.code} ${r.name}`}</text>
        {/each}
      {/if}
      {#if months.length > n}
        <rect class="later" x={knownW + 1} y="1" width={Math.max(0, d.width - knownW - 1)} height={ROW * stripes.rows.length - 2} rx="2" />
        {#if d.width - knownW > 90}<text class="ink2" x={(knownW + d.width) / 2} y={(ROW * stripes.rows.length) / 2 + 4} text-anchor="middle">ännu inte känt</text>{/if}
        {#each months.slice(n) as m, k (m)}
          {#if m.endsWith('-01')}<text x={knownW + k * cw} y={ROW * stripes.rows.length + 18}>{m.slice(0, 4)}</text>{/if}
        {/each}
      {/if}
    </g>
  {/snippet}
</ChartFrame>

<style>
  .later {
    fill: var(--c-grid);
    opacity: 0.55;
  }
  .pick {
    cursor: pointer;
  }
</style>
