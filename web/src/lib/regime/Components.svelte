<!-- The component series of one reconciliation, grouped into numerator and denominator. A published component has
     its level (as known on the record date), its own pace and direction from the pipeline, and a link to the series
     instrument. A withheld one (publish=False) is a dashed box with its name only: no values, no direction.
     Track W10. -->
<script lang="ts">
  import { resolve } from '$app/paths';
  import { scaleLinear } from 'd3-scale';
  import { Glyph, fmt, periodLabel, signed } from '$lib/design';
  import type { ComponentView } from './types';

  let { items }: { items: ComponentView[] } = $props();
  const groups = $derived([
    { side: 'num', title: 'Täljare', items: items.filter((c) => c.side === 'num') },
    { side: 'den', title: 'Nämnare', items: items.filter((c) => c.side === 'den') }
  ]);
  const W = 120;
  const H = 30;
  function spark(c: ComponentView): string {
    const v = c.levels?.values ?? [];
    const ok = v.map((x, i) => [i, x] as const).filter((p): p is readonly [number, number] => p[1] !== null);
    if (ok.length < 2) return '';
    const lo = Math.min(...ok.map((p) => p[1]));
    const hi = Math.max(...ok.map((p) => p[1]));
    const x = scaleLinear().domain([0, v.length - 1]).range([1, W - 4]);
    const y = scaleLinear().domain(lo === hi ? [lo - 1, hi + 1] : [lo, hi]).range([H - 3, 3]);
    return ok.map(([i, val], k) => `${k ? 'L' : 'M'}${x(i).toFixed(1)},${y(val).toFixed(1)}`).join('');
  }
</script>

<div class="comps">
  {#each groups as g (g.side)}
    <div class="grp">
      <h4 class="gh">{g.title}{g.items.length > 1 ? ' (summa)' : ''}</h4>
      <ul>
        {#each g.items as c (c.key)}
          <li class="c" class:held={!c.linkable}>
            {#if c.linkable}
              <a class="name" href={resolve('/serie/[key]', { key: c.key })}>{c.label}</a>
              <span class="key">{c.key}{c.window === 4 ? ' · summa av 4 kvartal' : ''}</span>
              <span class="row">
                <svg class="spark" width={W} height={H} viewBox="0 0 {W} {H}" aria-hidden="true">
                  <path d={spark(c)} fill="none" stroke="var(--c-ink)" stroke-width="1.5" stroke-linejoin="round" />
                </svg>
                <span class="stats">
                  {#if c.pace !== null}
                    <span class="num">takt {signed(c.pace, 1)}{c.pace_percentile !== null ? ` · ${fmt(c.pace_percentile, 0)}:e percentilen` : ''}{#if c.pace_percentile !== null}<span class="visually-hidden"> av seriens egen historik</span>{/if}</span>
                  {/if}
                  {#if c.direction !== null}<Glyph direction={c.direction} />{:else}<span class="muted">ingen riktning</span>{/if}
                  {#if c.latest_period}<span class="muted">{periodLabel(c.latest_period)}</span>{/if}
                </span>
              </span>
            {:else}
              <span class="name">{c.label}</span>
              <span class="key">{c.key}</span>
              <span class="muted">inhållen serie: visas bara med namn, inga värden</span>
            {/if}
          </li>
        {/each}
      </ul>
    </div>
  {/each}
</div>

<style>
  .comps {
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    gap: 10px 18px;
  }
  @media (min-width: 720px) {
    .comps {
      grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
    }
  }
  .gh {
    margin: 0 0 6px;
    font-size: 12px;
    font-weight: 620;
    color: var(--c-ink-2);
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }
  ul {
    list-style: none;
    margin: 0;
    padding: 0;
    display: grid;
    gap: 6px;
  }
  .c {
    display: flex;
    flex-direction: column;
    gap: 2px;
    padding: 8px 10px;
    border: 1px solid var(--c-ring);
    border-radius: var(--radius-md);
    background: var(--c-page);
    min-width: 0;
  }
  .c.held {
    border: 1px dashed var(--c-axis);
    background: transparent;
  }
  .name {
    font-size: 14px;
    font-weight: 560;
  }
  .key {
    font-family: var(--mono);
    font-size: 11px;
    color: var(--c-muted);
    overflow-wrap: anywhere;
  }
  .row {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 4px 12px;
    margin-top: 2px;
  }
  .stats {
    display: flex;
    flex-wrap: wrap;
    gap: 2px 10px;
    font-size: 12px;
    color: var(--c-ink-2);
  }
  .muted {
    font-size: 12px;
    color: var(--c-muted);
  }
  .spark {
    flex: none;
  }
</style>
