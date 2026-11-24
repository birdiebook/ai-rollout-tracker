<!-- One nowcast on the overview (W8): role, the target's recent levels as a sparkline with live forecasts as interval
     bars, the next forecast day and the live count. The whole card is one link. -->
<script lang="ts">
  import { scaleLinear, scalePoint } from 'd3-scale';
  import { Band, Line, dateLabel } from '$lib/design';
  import { count, daysUntil, extent, periodShort, type LiveRow } from './model';
  import OutcomeMark from './OutcomeMark.svelte';
  import RoleTag from './RoleTag.svelte';
  import KindTag from './KindTag.svelte';

  let {
    href,
    label,
    title,
    champion,
    shadow = false,
    history,
    rows,
    nextOrigin,
    nextPeriod,
    today,
    unit,
    note
  }: {
    href: string;
    label: string;
    title: string;
    champion: string | null;
    shadow?: boolean;
    history: { periods: string[]; values: (number | null)[] } | null | undefined;
    rows: LiveRow[];
    nextOrigin: string | null;
    nextPeriod: string | null;
    today: string;
    unit: string;
    note?: string;
  } = $props();

  const W = 300;
  const H = 64;
  const hist = $derived(
    ((history?.periods ?? []).map((p, i) => ({ p, v: history?.values[i] ?? null })).filter((h) => h.v !== null) as { p: string; v: number }[]).slice(-24)
  );
  const periods = $derived([...new Set([...hist.map((h) => h.p), ...rows.map((r) => r.period)])].sort());
  const x = $derived(scalePoint<string>().domain(periods).range([4, W - 8]).padding(0.3));
  const y = $derived(
    scaleLinear()
      .domain(extent([...hist.map((h) => h.v), ...rows.flatMap((r) => [r.intervals['95']?.[0], r.intervals['95']?.[1], r.outcome])], 0.1))
      .range([H - 4, 4])
  );
  const scored = $derived(rows.filter((r) => r.scored).length);
  const days = $derived(daysUntil(today, nextOrigin));
  const aria = $derived(
    `${label}: ${hist.length ? `målserien de senaste ${hist.length} perioderna` : 'inga publicerade nivåer'}` +
      `${rows.length ? `, ${rows.length} skarpa prognoser med intervall` : ''}.`
  );
</script>

<a class="card panel" {href}>
  <span class="top">
    <span class="lab">{label}</span>
    {#if shadow}<RoleTag role="shadow" />{:else if champion}<RoleTag role="champion" id={champion} />{/if}
  </span>
  <span class="title">{title}</span>
  {#if periods.length > 1}
    <svg viewBox="0 0 {W} {H}" width="100%" role="img" aria-label={aria}>
      <Line data={hist} x={(h) => x(h.p) ?? 0} y={(h) => y(h.v)} color="var(--c-ink-2)" width={1.5} />
      <Band
        variant="bars"
        barWidth={6}
        data={rows.filter((r) => r.value !== null)}
        x={(r) => x(r.period) ?? 0}
        center={(r) => y(r.value ?? 0)}
        levels={(['95', '80', '50'] as const).map((l) => ({
          level: l,
          lo: (r: LiveRow) => y(r.intervals[l]?.[0] ?? r.value ?? 0),
          hi: (r: LiveRow) => y(r.intervals[l]?.[1] ?? r.value ?? 0)
        }))}
      />
      {#each rows.filter((r) => r.scored && r.outcome !== null) as r (r.slug)}
        <OutcomeMark cx={x(r.period) ?? 0} cy={y(r.outcome ?? 0)} inside={r.inside['80'] ?? false} r={3} />
      {/each}
    </svg>
  {:else}
    <span class="nohist">{note ?? 'Inga publicerade nivåer i paketet ännu.'}</span>
  {/if}
  <span class="meta">
    {#if rows.length}
      <KindTag kind="skarp" />
      <span>{rows.length} skarp{rows.length === 1 ? '' : 'a'}, {count(scored, 'ett', 'inget')} utfall</span>
    {:else}
      <KindTag kind={shadow ? 'skugga' : 'väntar'} />
    {/if}
  </span>
  <span class="next">
    <span>
    {#if nextOrigin}
      Nästa: <b>{dateLabel(nextOrigin)}</b>{#if days !== null && days >= 0}&nbsp;(om {days} d){/if} → {periodShort(nextPeriod)}
    {:else}
      Ingen planerad prognosdag.
    {/if}
    </span>
    <span class="unit">{unit}</span>
  </span>
</a>

<style>
  .card {
    display: flex;
    flex-direction: column;
    gap: 6px;
    text-decoration: none;
    color: inherit;
    min-width: 0;
    transition: border-color var(--motion-fast);
  }
  .card:hover {
    border-color: var(--c-ink-2);
  }
  .top {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
  }
  .lab {
    font-weight: 680;
    font-size: var(--fs-section);
    letter-spacing: -0.01em;
  }
  .title {
    font-weight: 560;
    min-height: 3em;
  }
  svg {
    display: block;
    overflow: visible;
  }
  .nohist {
    display: flex;
    align-items: center;
    height: 64px;
    font-size: var(--fs-small);
    color: var(--c-muted);
    border: 1px dashed var(--c-axis);
    border-radius: var(--radius-md);
    padding: 0 10px;
  }
  .meta {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 6px 10px;
    font-size: var(--fs-small);
    color: var(--c-ink-2);
  }
  .next {
    display: flex;
    flex-wrap: wrap;
    justify-content: space-between;
    gap: 2px 10px;
    font-size: var(--fs-small);
    color: var(--c-ink-2);
  }
  .unit {
    color: var(--c-muted);
  }
  @media (prefers-reduced-motion: reduce) {
    .card {
      transition: none;
    }
  }
</style>
