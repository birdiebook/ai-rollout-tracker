<!-- as_of and known_from (track W11): why only what was known is used. One revised series: W7's revision view (all
     versions, the chosen day thick), the story of its most revised period (each version from its known_from day), and
     the measure as the record stated it each month against today's version of the same period (both pipeline numbers:
     measure_history and measure_path). The day is shared by all three. -->
<script lang="ts">
  import { scaleLinear, scaleUtc } from 'd3-scale';
  import { Axis, ChartFrame, Legend, dateLabel, fmt, periodLabel, signed, type RecordStatus } from '$lib/design';
  import RevisionExplorer from '$lib/series/RevisionExplorer.svelte';
  import { timeTicks } from '$lib/series/chart';
  import { asOf, periodVersions } from '$lib/series/versions';
  import type { Versions } from '$lib/series/types';

  type Leak = { month: string; kind: string; period: string; known_from: string | null; then: number; now: number | null };
  let {
    data,
    status
  }: {
    data: {
      key: string;
      label: string;
      unit: string;
      lag_days: number | null;
      license: string;
      source: string;
      versions: Versions;
      period: string | null;
      leakage: Leak[];
      pace_unit: string;
    };
    status: RecordStatus;
  } = $props();

  const v = $derived(data.versions);
  const periodsWithRevisions = $derived(v.periods.filter((p) => periodVersions(v, p).length >= 2));
  // svelte-ignore state_referenced_locally
  let period = $state(data.period ?? data.versions.periods.at(-1) ?? '');
  const story = $derived(periodVersions(v, period));
  // svelte-ignore state_referenced_locally
  let day = $state(periodVersions(data.versions, data.period ?? '')[1]?.date ?? data.versions.last_known);

  const known = $derived(asOf(v, day).get(period) ?? null);
  const knownIdx = $derived(story.filter((s) => s.date <= day).length);
  const today = $derived(story.at(-1) ?? null);
  const t = (d: string) => Date.parse(d + 'T00:00:00Z');

  const storySentence = $derived(
    story.length === 0
      ? ''
      : knownIdx === 0
        ? `Den ${dateLabel(day)} var ${periodLabel(period, true)} ännu inte publicerad. Första version kom ${dateLabel(story[0].date)}.`
        : `Den ${dateLabel(day)} var värdet för ${periodLabel(period, true)} känt som ${fmt(known, 1)} (version ${knownIdx} av ${story.length}). I dag är det ${fmt(today?.value, 1)}.`
  );

  const leak = $derived(data.leakage.filter((r) => r.now !== null));
  const nDiff = $derived(leak.filter((r) => Math.abs((r.now as number) - r.then) >= 0.05).length);
  const medGap = $derived.by(() => {
    const g = leak.map((r) => Math.abs((r.now as number) - r.then)).sort((a, b) => a - b);
    return g.length ? g[Math.floor((g.length - 1) / 2)] : null;
  });
  const flips = $derived(leak.filter((r) => Math.sign(r.then) !== Math.sign(r.now as number) && Math.abs(r.then) > 0.05).length);
</script>

<RevisionExplorer versions={v} bind:day unit={data.unit} source={data.source} license={data.license} />

<div class="story">
  <label class="pick">
    <span>Följ en period:</span>
    <select bind:value={period}>
      {#each [...periodsWithRevisions].reverse() as p (p)}<option value={p}>{periodLabel(p, true)} ({periodVersions(v, p).length} versioner)</option>{/each}
    </select>
  </label>

  <ChartFrame
    id="asof-period"
    title="{periodLabel(period, true)}: varje version från sitt known_from"
    description={storySentence}
    height={210}
    margin={{ top: 16, right: 16, bottom: 26, left: 56 }}
    source={data.source}
    license={data.license}
    table={{
      caption: `${data.label}, ${periodLabel(period, true)}: alla versioner`,
      columns: [
        { key: 'd', label: 'known_from', align: 'left' },
        { key: 'v', label: 'Värde' },
        { key: 'k', label: `Känd den ${day}`, align: 'left' }
      ],
      rows: story.map((s, i) => ({ d: dateLabel(s.date), v: fmt(s.value, 2), k: i === knownIdx - 1 ? 'ja, den som gällde' : s.date <= day ? 'ja, ersatt' : 'nej, kom senare' }))
    }}
    legend={storyLegend}
  >
    {#snippet children(d)}
      {#if story.length}
        {@const span0 = t(story[0].date)}
        {@const span1 = Math.max(t((story.at(-1) as { date: string }).date), t(day))}
        {@const padT = Math.max(30 * 864e5, (span1 - span0) * 0.08)}
        {@const t0 = span0 - padT}
        {@const t1 = span1 + padT}
        {@const x = scaleUtc().domain([t0, t1]).range([d.left, d.right])}
        {@const vals = story.map((s) => s.value)}
        {@const pad = (Math.max(...vals) - Math.min(...vals)) * 0.15 || Math.abs(vals[0]) * 0.05 || 1}
        {@const y = scaleLinear().domain([Math.min(...vals) - pad, Math.max(...vals) + pad]).range([d.bottom, d.top]).nice()}
        {@const dig = Math.abs(y.domain()[1] - y.domain()[0]) >= 20 ? 0 : 1}
        <Axis scale={y} dims={d} orient="left" ticks={4} format={(q) => fmt(q, dig)} grid />
        {@const tt = timeTicks(x, d)}
        <Axis scale={x} dims={d} tickValues={tt.values} format={tt.format} />
        {#each story as s, i (i)}
          {@const xe = i < story.length - 1 ? x(t(story[i + 1].date)) : x(t1)}
          {@const cur = i === knownIdx - 1}
          {@const future = s.date > day}
          <line class="mark vline" class:cur class:future x1={x(t(s.date))} x2={xe} y1={y(s.value)} y2={y(s.value)} />
          {#if i > 0}<line class="riser" class:future x1={x(t(s.date))} x2={x(t(s.date))} y1={y(story[i - 1].value)} y2={y(s.value)} />{/if}
          <circle class="mark vdot" class:cur class:future cx={x(t(s.date))} cy={y(s.value)} r={cur ? 5.5 : 3.5} />
        {/each}
        {@const xd = Math.min(d.right, Math.max(d.left, x(t(day))))}
        <line class="day" x1={xd} x2={xd} y1={d.top - 6} y2={d.bottom} />
        <text class="ink" x={xd > d.right - 100 ? xd - 4 : xd + 4} y={d.top + 2} text-anchor={xd > d.right - 100 ? 'end' : 'start'}>{dateLabel(day)}</text>
      {/if}
    {/snippet}
  </ChartFrame>
</div>

{#if leak.length}
  <ChartFrame
    id="asof-leak"
    title="Takten som posten angav, mot dagens version"
    description={`Varje månadsslut beräknades takten för den senaste kända perioden med det som var känt då. I ${nDiff} av ${leak.length} månader ger dagens version en annan takt för samma period, i median ${fmt(medGap, 1)} enheter${flips ? `, och ${flips} gånger med motsatt tecken` : ''}. Att räkna om historiken med dagens data vore läckage.`}
    height={230}
    margin={{ top: 12, right: 16, bottom: 26, left: 44 }}
    {status}
    source={data.source}
    license={data.license}
    table={{
      caption: `${data.label}: takt (${data.pace_unit}) enligt posten vid varje månadsslut och enligt dagens version`,
      columns: [
        { key: 'm', label: 'Postens månad', align: 'left' },
        { key: 'p', label: 'Period' },
        { key: 'k', label: 'known_from' },
        { key: 't', label: 'Takt då' },
        { key: 'n', label: 'Takt i dag' },
        { key: 'd', label: 'Skillnad' }
      ],
      rows: [...leak].reverse().map((r) => ({
        m: `${periodLabel(r.month)} (${r.kind})`,
        p: periodLabel(r.period),
        k: r.known_from ? dateLabel(r.known_from) : '–',
        t: fmt(r.then, 1),
        n: fmt(r.now, 1),
        d: signed((r.now as number) - r.then, 1)
      }))
    }}
    legend={leakLegend}
  >
    {#snippet children(d)}
      {@const ps = [...new Set(leak.map((r) => r.period))].sort()}
      {@const x = scaleLinear().domain([0, Math.max(1, ps.length - 1)]).range([d.left + 4, d.right - 4])}
      {@const all = leak.flatMap((r) => [r.then, r.now as number])}
      {@const y = scaleLinear().domain([Math.min(0, ...all), Math.max(0, ...all)]).range([d.bottom, d.top]).nice()}
      {@const xi = (p: string) => x(ps.indexOf(p))}
      <Axis scale={y} dims={d} orient="left" ticks={4} format={(q) => fmt(q)} baseline={0} grid />
      {#each ps.filter((p, i) => i % Math.max(1, Math.ceil(ps.length / Math.max(2, Math.floor(d.innerWidth / 70)))) === 0) as p (p)}
        <text x={xi(p)} y={d.bottom + 16} text-anchor="middle">{periodLabel(p)}</text>
      {/each}
      <path class="mark nowline" d={leak.map((r, i) => `${i ? 'L' : 'M'}${xi(r.period).toFixed(1)},${y(r.now as number).toFixed(1)}`).join('')} />
      {#each leak as r (r.month)}
        <line class="gap" x1={xi(r.period)} x2={xi(r.period)} y1={y(r.then)} y2={y(r.now as number)} />
        <circle class="mark then" class:recon={r.kind !== 'skarp'} cx={xi(r.period)} cy={y(r.then)} r="3.5" />
      {/each}
    {/snippet}
  </ChartFrame>
{/if}

{#snippet storyLegend()}
  <Legend
    items={[
      { label: 'tjock: versionen som gällde den valda dagen', fill: 'var(--c-ink)' },
      { label: 'ljus: kom senare', fill: 'var(--c-axis)' }
    ]}
  />
{/snippet}

{#snippet leakLegend()}
  <Legend
    items={[
      { label: 'prick: takten i posten (känd då), skarp', fill: 'var(--c-ink)' },
      { label: 'ring: rekonstruerad månad', fill: 'var(--c-surface)', border: 'var(--c-ink)' },
      { label: 'linje: samma periods takt enligt dagens version', line: true, fill: 'var(--c-ink-2)' }
    ]}
  />
{/snippet}

<style>
  .story {
    margin-top: 18px;
  }
  .pick {
    display: flex;
    flex-wrap: wrap;
    gap: 6px 10px;
    align-items: center;
    font-size: var(--fs-small);
    margin-bottom: 8px;
  }
  select {
    font: inherit;
    min-height: var(--hit);
    background: var(--c-surface);
    color: var(--c-ink);
    border: 1px solid var(--c-ring);
    border-radius: var(--radius-sm);
    padding: 2px 6px;
  }
  .vline {
    stroke: var(--c-ink-2);
    stroke-width: 2;
  }
  .vline.cur {
    stroke: var(--c-ink);
    stroke-width: 4;
  }
  .vline.future,
  .riser.future {
    stroke: var(--c-axis);
  }
  .riser {
    stroke: var(--c-ink-2);
    stroke-dasharray: 2 2;
  }
  .vdot {
    fill: var(--c-ink-2);
  }
  .vdot.cur {
    fill: var(--c-ink);
  }
  .vdot.future {
    fill: var(--c-axis);
  }
  .day {
    stroke: var(--c-ink);
    stroke-dasharray: 4 3;
  }
  .nowline {
    fill: none;
    stroke: var(--c-ink-2);
    stroke-width: 1.5;
    stroke-dasharray: 5 3;
  }
  .gap {
    stroke: var(--c-axis);
  }
  .then {
    fill: var(--c-ink);
  }
  .then.recon {
    fill: var(--c-surface);
    stroke: var(--c-ink);
    stroke-width: 1.5;
  }
</style>
