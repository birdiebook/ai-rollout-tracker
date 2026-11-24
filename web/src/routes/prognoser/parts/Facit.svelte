<!-- Facit: the error of every live forecast with an outcome, main model against the naive baseline and guidance
     where the nowcast has one. Zero is a perfect forecast; the sign follows the pipeline (error_unit). Shapes carry
     the identity too (circle, square, diamond), so colour is not the only channel. -->
<script lang="ts">
  import { scaleLinear, scalePoint } from 'd3-scale';
  import { Axis, ChartFrame, signed, useTooltip } from '$lib/design';
  import { errOf, extent, periodShort, periodTick, type LiveRow, type Roles } from './model';

  let { id, rows, roles, errorUnit }: { id: string; rows: LiveRow[]; roles: Roles; errorUnit: string } = $props();

  const scored = $derived(rows.filter((r) => r.scored));
  const models = $derived(
    [
      { id: roles.champion, key: 'champion', shape: 'circle', fill: 'var(--c-model)', label: `huvudmodell ${roles.champion}` },
      roles.baseline && { id: roles.baseline, key: roles.baseline, shape: 'square', fill: 'var(--c-base)', label: `naiv baslinje ${roles.baseline}` },
      roles.guidance && { id: roles.guidance, key: roles.guidance, shape: 'diamond', fill: 'var(--c-ink-2)', label: `guidance ${roles.guidance}` }
    ].filter(Boolean) as { id: string; key: string; shape: string; fill: string; label: string }[]
  );
  const err = (r: LiveRow, key: string) => errOf(r.score, key);
  const mae = (key: string) => {
    const e = scored.map((r) => err(r, key)).filter((x): x is number => x !== null);
    return e.length ? { v: e.reduce((a, b) => a + Math.abs(b), 0) / e.length, n: e.length } : null;
  };
  const description = $derived(
    scored.length === 0
      ? 'Inget facit ännu.'
      : `${scored.length} skarp${scored.length === 1 ? '' : 'a'} prognos${scored.length === 1 ? '' : 'er'} med utfall. Medelabsolutfel: ` +
          models
            .map((m) => {
              const a = mae(m.key);
              return `${m.label} ${a ? signed(a.v, 1).replace('+', '') : '–'}`;
            })
            .join(', ') +
          ` (${errorUnit}).${scored.length < 12 ? ' För få utfall för att skilja modellerna åt.' : ''}`
  );
  const tip = useTooltip();
  const dx = (i: number, n: number) => (i - (n - 1) / 2) * 9;
</script>

<ChartFrame
  {id}
  title="Fel per skarp prognos"
  {description}
  height={220}
  margin={{ top: 14, right: 14, bottom: 26, left: 52 }}
  table={{
    caption: `Fel per prognos (${errorUnit})`,
    columns: [{ key: 'p', label: 'Period', align: 'left' }, ...models.map((m) => ({ key: m.key, label: m.label, align: 'right' as const }))],
    rows: scored.map((r) => ({ p: periodShort(r.period), ...Object.fromEntries(models.map((m) => [m.key, signed(err(r, m.key), 1)])) }))
  }}
>
  {#snippet children(d)}
    {@const x = scalePoint<string>().domain(scored.map((r) => r.period)).range([d.left, d.right]).padding(0.5)}
    {@const ext = extent(scored.flatMap((r) => models.map((m) => err(r, m.key))).concat([0]), 0.12)}
    {@const m = Math.max(Math.abs(ext[0]), Math.abs(ext[1]))}
    {@const y = scaleLinear().domain([-m, m]).range([d.bottom, d.top]).nice()}
    <Axis scale={y} dims={d} orient="left" ticks={4} grid baseline={0} format={(v) => signed(v, 0)} />
    <Axis scale={x} dims={d} tickValues={scored.length > 12 ? scored.filter((_, i) => i % 3 === 0).map((r) => r.period) : scored.map((r) => r.period)} format={(v) => periodTick(v)} />
    {#each scored as r (r.slug)}
      {#each models as mo, i (mo.key)}
        {@const e = err(r, mo.key)}
        {#if e !== null}
          {@const cx = (x(r.period) ?? 0) + dx(i, models.length)}
          {@const cy = y(e)}
          <g
            role="presentation"
            onpointerenter={(ev) => tip?.show({ title: `${periodShort(r.period, true)} · ${mo.label}`, rows: [['Fel', `${signed(e, 1)} (${errorUnit})`]] }, ev)}
            onpointerleave={() => tip?.hide()}
          >
            {#if mo.shape === 'circle'}
              <circle class="mark" {cx} {cy} r="5" fill={mo.fill} stroke="var(--c-surface)" stroke-width="1.5" />
            {:else if mo.shape === 'square'}
              <rect class="mark" x={cx - 4.5} y={cy - 4.5} width="9" height="9" fill={mo.fill} stroke="var(--c-surface)" stroke-width="1.5" />
            {:else}
              <rect class="mark" x={cx - 4} y={cy - 4} width="8" height="8" fill={mo.fill} stroke="var(--c-surface)" stroke-width="1.5" transform="rotate(45 {cx} {cy})" />
            {/if}
          </g>
        {/if}
      {/each}
    {/each}
    <text class="ink2" x={d.left + 4} y={d.top + 10}>prognosen för hög ↑</text>
    <text class="ink2" x={d.left + 4} y={d.bottom - 6}>prognosen för låg ↓</text>
  {/snippet}
  {#snippet legend()}
    <ul class="keys">
      {#each models as m (m.key)}
        <li>
          <svg width="12" height="12" viewBox="0 0 12 12" aria-hidden="true">
            {#if m.shape === 'circle'}<circle cx="6" cy="6" r="5" fill={m.fill} />{:else if m.shape === 'square'}<rect x="1.5" y="1.5" width="9" height="9" fill={m.fill} />{:else}<rect x="2.5" y="2.5" width="7" height="7" fill={m.fill} transform="rotate(45 6 6)" />{/if}
          </svg>{m.label}
        </li>
      {/each}
    </ul>
  {/snippet}
</ChartFrame>

<style>
  .keys {
    display: flex;
    flex-wrap: wrap;
    gap: 4px 14px;
    margin: 0;
    padding: 0;
    list-style: none;
    font-size: 12px;
    color: var(--c-ink-2);
  }
  .keys li {
    display: inline-flex;
    align-items: center;
    gap: 6px;
  }
</style>
