<!-- Revision view with the versions loaded at run time (datakontrakt section 8): one thin line per version (older
     lighter), the version on the chosen day thick, today's dashed (section 4.1). The chosen day is time travel in
     miniature: exactly what was known that day (asOf), never a version before its known_from. W9 builds the global
     time slider on the same functions (versions.ts) and the same `as_of` in the URL. -->
<script lang="ts">
  import { Axis, ChartFrame, Legend, dateLabel, fmt } from '$lib/design';
  import HoverLayer from './HoverLayer.svelte';
  import { logTicks, timeScale, timeTicks, valueScale } from './chart';
  import { periodText, periodTime } from './period';
  import { logTickNum, num, snum, tickNum } from './text';
  import { asOf, backfillUntil, emptyOn, knownRows, reconstructedOn, sampleDates, snapshots, versionOn } from './versions';
  import type { Versions } from './types';

  let {
    versions,
    day = $bindable(),
    unit,
    log = false,
    from = -Infinity,
    backfill,
    source,
    license
  }: {
    versions: Versions;
    /** chosen day "YYYY-MM-DD" */
    day: string;
    unit: string;
    /** log value scale (follows the level chart's choice) */
    log?: boolean;
    from?: number;
    /** the series' rows block: backfill_last_known and backfill_fetched (datakontrakt 5.6) */
    backfill?: { backfill_last_known?: string | null; backfill_fetched?: string | null } | null;
    source?: string;
    license?: string;
  } = $props();

  const v = $derived(versions);
  const backfillTo = $derived(backfillUntil(backfill));
  const dates = $derived(v.dates);
  const idx = $derived(Math.max(0, knownRows(v, day) === 0 ? 0 : dates.indexOf(versionOn(v, day) ?? dates[0])));
  const then = $derived(asOf(v, day));
  const today = $derived(asOf(v, v.last_known));
  const lines = $derived.by(() => {
    const ds = sampleDates(v, 18);
    const snaps = snapshots(v, ds);
    return ds.map((d, i) => ({ date: d, pts: toPts(snaps[i]) })).filter((l) => l.pts.length > 1);
  });
  const thenPts = $derived(toPts(then));
  const todayPts = $derived(toPts(today));
  const allVals = $derived([...todayPts, ...lines.flatMap((l) => l.pts)].map((q) => q.v));
  const scaleRef = $derived(Math.max(...allVals.map(Math.abs), 0));
  const lm = $derived(Math.min(72, 14 + 6.6 * Math.max(3, num(scaleRef, scaleRef).length)));
  const nThen = $derived(then.size);
  const latestThen = $derived(thenPts.at(-1)?.p ?? null);
  const nChanged = $derived([...then].filter(([p, x]) => today.get(p) !== x).length);
  const empty = $derived(emptyOn(v, day));

  function toPts(s: Map<string, number>) {
    return [...s]
      .map(([p, x]) => ({ p, t: periodTime(p), v: x }))
      .filter((q) => q.t >= from)
      .sort((a, b) => a.t - b.t);
  }
  const step = (k: number) => {
    const i = Math.min(dates.length - 1, Math.max(0, idx + k));
    day = dates[i];
  };
  const sentence = $derived(
    empty
      ? `Inget var känt om serien den ${dateLabel(day)}. Första version: ${dateLabel(v.first_known)}.`
      : `Den ${dateLabel(day)} var ${fmt(nThen)} perioder kända, den senaste ${periodText(latestThen ?? '')}. ${fmt(nChanged)} av dem har ändrats sedan dess.`
  );
  const opacity = (i: number, n: number) => 0.12 + 0.4 * (i / Math.max(1, n - 1));
  const table = $derived({
    caption: `Värden kända den ${dateLabel(day)} mot i dag, nyast först.`,
    columns: [
      { key: 'p', label: 'Period' },
      { key: 'then', label: `Den ${day}` },
      { key: 'now', label: 'I dag' },
      { key: 'diff', label: 'Skillnad' }
    ],
    rows: [...thenPts].reverse().map((q) => {
      const now = today.get(q.p) ?? null;
      return { p: periodText(q.p), then: num(q.v, scaleRef), now: num(now, scaleRef), diff: now === null ? '–' : snum(now - q.v, scaleRef) };
    })
  });
</script>

<div class="controls" role="group" aria-label="Välj dag för versionen">
  <label class="slider">
    <span>Vad visste vi den <strong>{dateLabel(day)}</strong>?</span>
    <input
      type="range"
      min="0"
      max={dates.length - 1}
      step="1"
      value={idx}
      aria-valuetext="{dateLabel(dates[idx])}, version {idx + 1} av {dates.length}"
      oninput={(e) => (day = dates[Number((e.currentTarget as HTMLInputElement).value)])}
    />
  </label>
  <div class="btns">
    <button type="button" class="chip" onclick={() => step(-1)} disabled={idx === 0}>Föregående version</button>
    <button type="button" class="chip" onclick={() => step(empty ? 0 : 1)} disabled={idx === dates.length - 1}>Nästa version</button>
    <button type="button" class="chip" onclick={() => (day = v.last_known)} disabled={day === v.last_known}>I dag</button>
    <label class="date">
      <span class="visually-hidden">Dag</span>
      <input type="date" value={day} min="1990-01-01" max={v.last_known} onchange={(e) => {
        const val = (e.currentTarget as HTMLInputElement).value;
        if (/^\d{4}-\d{2}-\d{2}$/.test(val)) day = val;
      }} />
    </label>
  </div>
</div>
<p class="note" aria-live="polite">
  {#if reconstructedOn(backfillTo, day)}Historiken före {dateLabel(backfillTo ?? '')} är bakåtfylld med dagens version (rekonstruerad){#if backfill?.backfill_fetched && backfill.backfill_fetched === backfillTo}: värdena hämtades {dateLabel(backfill.backfill_fetched)}, inte när perioderna först publicerades{/if}.{/if}
  {#if v.collapsed_before && day < v.collapsed_before}Versioner före {dateLabel(v.collapsed_before)} är hopslagna; serien visar inget före den dagen.{/if}
</p>

<ChartFrame
  id="rev-versions"
  title="Versioner"
  description={`${fmt(v.n_versions)} versioner på ${fmt(dates.length)} dagar. ${sentence}`}
  height={260}
  margin={{ top: 18, right: 14, bottom: 26, left: lm }}
  {source}
  {license}
  {table}
>
  {#snippet children(d)}
    {#if todayPts.length > 0}
      {@const x = timeScale(Math.min(todayPts[0].t, thenPts[0]?.t ?? Infinity), todayPts.at(-1)!.t, d)}
      {@const ys = valueScale(allVals, d, { log })}
      {@const y = ys.scale}
      {@const tt = timeTicks(x, d)}
      {@const path = (pts: { t: number; v: number }[]) => pts.map((q, i) => `${i ? 'L' : 'M'}${x(q.t).toFixed(1)},${y(q.v).toFixed(1)}`).join('')}
      <Axis
        scale={y}
        dims={d}
        orient="left"
        ticks={4}
        tickValues={ys.log ? logTicks(y.domain()[0], y.domain()[1]) : undefined}
        format={(val) => (ys.log ? logTickNum(val) : tickNum(val, scaleRef))}
        grid
        label={ys.log ? `${unit} (logaritmisk skala)` : unit}
      />
      <Axis scale={x} dims={d} tickValues={tt.values} format={tt.format} />
      {#each lines as l, i (l.date)}
        <path class="mark" d={path(l.pts)} fill="none" stroke="var(--c-ink-2)" stroke-width="1" opacity={opacity(i, lines.length)} />
      {/each}
      <path class="mark" d={path(todayPts)} fill="none" stroke="var(--c-ink)" stroke-width="1.5" stroke-dasharray="5 4" />
      {#if thenPts.length > 1}
        <path class="mark" d={path(thenPts)} fill="none" stroke="var(--c-ink)" stroke-width="3" stroke-linejoin="round" />
      {:else if thenPts.length === 1}
        <circle class="mark" cx={x(thenPts[0].t)} cy={y(thenPts[0].v)} r="5" fill="var(--c-ink)" />
      {/if}
      <HoverLayer
        dims={d}
        points={(thenPts.length ? thenPts : todayPts).map((q) => {
          const now = today.get(q.p) ?? null;
          const was = then.get(q.p) ?? null;
          return {
            x: x(q.t),
            y: y(q.v),
            tip: {
              title: periodText(q.p, true),
              rows: [
                [`Den ${day}`, num(was, scaleRef)],
                ['I dag', num(now, scaleRef)]
              ],
              note: unit
            }
          };
        })}
      />
    {/if}
  {/snippet}
  {#snippet legend()}
    <Legend
      items={[
        { label: `version ${dateLabel(day)}`, fill: 'var(--c-ink)', line: true },
        { label: 'i dag (streckad)', fill: 'var(--c-ink)', line: true },
        { label: 'tidigare versioner', fill: 'var(--c-ink-2)', line: true }
      ]}
    />
  {/snippet}
</ChartFrame>

<style>
  .controls {
    display: flex;
    flex-wrap: wrap;
    gap: 10px 16px;
    align-items: end;
    margin-bottom: 6px;
  }
  .slider {
    display: grid;
    gap: 4px;
    flex: 1 1 280px;
    font-size: var(--fs-small);
    color: var(--c-ink-2);
  }
  .slider input {
    width: 100%;
    accent-color: var(--c-ink);
    min-height: var(--hit);
  }
  .btns {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }
  .chip:disabled {
    opacity: 0.5;
    cursor: default;
  }
  .date input {
    font: inherit;
    font-size: var(--fs-small);
    min-height: var(--hit);
    border: 1px solid var(--c-ring);
    border-radius: var(--radius-md);
    background: var(--c-surface);
    color: var(--c-ink);
    padding: 2px 8px;
  }
</style>
