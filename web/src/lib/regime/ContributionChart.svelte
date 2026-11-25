<!-- The ratio's pace (pipeline, log ×100 per year) split into what the numerator and the denominator contributed:
     pace = 100·Δ4 log N − 100·Δ4 log D. Bars stack by sign around the zero line; the numerator is solid, the
     denominator (with its sign flipped) is an outline, and a rest that does not add up is hatched. Neutral ink:
     colour is reserved for direction (the end dot). Track W10. -->
<script lang="ts">
  import { scaleLinear } from 'd3-scale';
  import { Axis, ChartFrame, DIRECTIONS, Line, periodLabel, signed } from '$lib/design';
  import { periodTime } from '$lib/flow';
  import { REST_TOLERANCE, contributionSentence, yearTicks } from './recon';
  import type { ReconView } from './types';

  let { r, height = 200 }: { r: ReconView; height?: number } = $props();

  const n = $derived(r.periods.length);
  const t = $derived(r.periods.map(periodTime));
  const showRest = $derived(r.max_rest !== null && r.max_rest >= REST_TOLERANCE);
  type Seg = { i: number; y0: number; y1: number; kind: 'num' | 'den' | 'rest' };
  const segs = $derived.by(() => {
    const out: Seg[] = [];
    r.periods.forEach((_, i) => {
      let up = 0;
      let down = 0;
      const parts: [number | null, Seg['kind']][] = [
        [r.num_c[i] ?? null, 'num'],
        [r.den_c[i] ?? null, 'den'],
        [showRest ? (r.rest[i] ?? null) : null, 'rest']
      ];
      for (const [v, kind] of parts) {
        if (v === null || v === 0) continue;
        if (v > 0) {
          out.push({ i, y0: up, y1: up + v, kind });
          up += v;
        } else {
          out.push({ i, y0: down, y1: down + v, kind });
          down += v;
        }
      }
    });
    return out;
  });
  const yDomain = $derived.by((): [number, number] => {
    const vals = [0, ...segs.flatMap((s) => [s.y0, s.y1]), ...r.pace_path.filter((v): v is number => v !== null)];
    return [Math.min(...vals), Math.max(...vals)];
  });
  const pts = $derived(r.periods.map((p, i) => ({ t: t[i], v: r.pace_path[i] })));
  const last = $derived([...pts].reverse().find((p) => p.v !== null));
  const dirColor = $derived(r.direction === null ? 'var(--c-muted)' : DIRECTIONS[r.direction].color);
  const pid = $derived(`hatch-${r.key}`);
</script>

<ChartFrame
  id="c-{r.key}-bidrag"
  title="Takten och vad komponenterna bidrog med"
  description={contributionSentence(r)}
  {height}
  width={380}
  margin={{ top: 22, right: 10, bottom: 22, left: 40 }}
  prerenderTable={false}
  table={{
    caption: `${r.short}: takt och bidrag per kvartal (log ×100 per år)`,
    columns: [
      { key: 'p', label: 'Kvartal' },
      { key: 't', label: 'Takt' },
      { key: 'n', label: 'Täljaren' },
      { key: 'd', label: 'Nämnaren' },
      ...(showRest ? [{ key: 'r', label: 'Rest' }] : [])
    ],
    rows: [...r.periods.keys()].reverse().map((i) => ({
      p: periodLabel(r.periods[i]),
      t: signed(r.pace_path[i], 1),
      n: signed(r.num_c[i], 1),
      d: signed(r.den_c[i], 1),
      r: signed(r.rest[i], 1)
    }))
  }}
>
  {#snippet children(d)}
    {#if n}
      {@const x = scaleLinear().domain([t[0] - 0.125, t[n - 1] + 0.125]).range([d.left, d.right])}
      {@const y = scaleLinear().domain(yDomain).range([d.bottom, d.top]).nice()}
      {@const bw = Math.max(1.5, Math.min(14, (d.innerWidth / n) * 0.72))}
      <defs>
        <pattern id={pid} width="5" height="5" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
          <line x1="0" y1="0" x2="0" y2="5" stroke="var(--c-ink-2)" stroke-width="1.5" />
        </pattern>
      </defs>
      <text class="ink2 unit" x={d.left} y={d.top - 10}>log ×100 per år</text>
      <Axis scale={y} dims={d} orient="left" ticks={4} format={(v) => signed(v, 0).replace('±', '')} grid baseline={0} />
      <Axis scale={x} dims={d} tickValues={yearTicks(t[0], t[n - 1])} format={(v) => String(v)} />
      <!-- one path per kind (bars as subpaths): the same picture with a few elements, so the page with ten ratios
           stays inside the DOM budget (WV2) -->
      {#each ['num', 'den', 'rest'] as const as kind (kind)}
        {@const dPath = segs
          .filter((s) => s.kind === kind)
          .map((s) => {
            const top = y(Math.max(s.y0, s.y1));
            const h = Math.max(0.5, Math.abs(y(s.y0) - y(s.y1)));
            return `M${(x(t[s.i]) - bw / 2).toFixed(1)},${top.toFixed(1)}h${bw.toFixed(1)}v${h.toFixed(1)}h${(-bw).toFixed(1)}Z`;
          })
          .join('')}
        {#if dPath}
          <path
            class="mark bars"
            data-kind={kind}
            d={dPath}
            fill={kind === 'num' ? 'var(--c-ink-2)' : kind === 'den' ? 'var(--c-surface)' : `url(#${pid})`}
            stroke={kind === 'num' ? 'none' : 'var(--c-ink-2)'}
            stroke-width="1.2"
          />
        {/if}
      {/each}
      <Line data={pts} x={(p) => x(p.t)} y={(p) => y(p.v ?? 0)} defined={(p) => p.v !== null} color="var(--c-surface)" width={5} />
      <Line data={pts} x={(p) => x(p.t)} y={(p) => y(p.v ?? 0)} defined={(p) => p.v !== null} />
      {#if last}
        <circle class="mark" cx={x(last.t)} cy={y(last.v ?? 0)} r="4.5" fill={dirColor} stroke="var(--c-surface)" stroke-width="2" />
      {/if}
    {:else}
      <text class="ink2" x={d.left} y={d.top + d.innerHeight / 2}>Ingen takt i posten</text>
    {/if}
  {/snippet}
  {#snippet legend()}
    <ul class="keys" aria-label="Teckenförklaring">
      <li><span class="sw line" aria-hidden="true"></span>takt (pipelinen)</li>
      <li><span class="sw numsw" aria-hidden="true"></span>täljaren</li>
      <li><span class="sw densw" aria-hidden="true"></span>nämnaren (med omvänt tecken)</li>
      {#if showRest}<li><span class="sw restsw" aria-hidden="true"></span>rest, går inte ihop</li>{/if}
    </ul>
  {/snippet}
</ChartFrame>

<style>
  .keys {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-wrap: wrap;
    gap: 4px 12px;
    font-size: 12px;
    color: var(--c-ink-2);
  }
  .sw {
    display: inline-block;
    width: 11px;
    height: 11px;
    margin-right: 5px;
    vertical-align: -1px;
    box-sizing: border-box;
  }
  .line {
    height: 2px;
    vertical-align: 3px;
    background: var(--c-ink);
  }
  .numsw {
    background: var(--c-ink-2);
  }
  .densw {
    border: 1.2px solid var(--c-ink-2);
    background: var(--c-surface);
  }
  .restsw {
    border: 1.2px solid var(--c-ink-2);
    background: repeating-linear-gradient(45deg, var(--c-ink-2) 0 1.5px, transparent 1.5px 4px);
  }
</style>
