<!-- Unit chart (section 4.1, diffusion index): one box per series, ▲ ● ▼ in the direction colour for publishable
     series, a hatched box without glyph for a withheld series (publish=False: counted, but its own direction is never
     shown, section 4 of the data contract). Each box links to the series' card. Track W6. -->
<script lang="ts">
  import { DIRECTIONS } from '$lib/design';
  import type { Dir } from './types';

  let {
    items,
    withheld = [],
    withheldAnon = 0,
    href,
    withheldHref,
    label
  }: {
    /** counted=false: registered but not counted this month, drawn without a direction */
    items: { key: string; label: string; direction: Dir; counted?: boolean }[];
    withheld?: { key: string; label: string }[];
    /** withheld series that count but cannot be named here */
    withheldAnon?: number;
    href: (key: string) => string;
    withheldHref?: string;
    label: string;
  } = $props();
  const word = (d: Dir) => (d === null ? 'ingen riktning' : DIRECTIONS[d].word);
</script>

<ul class="units" aria-label={label}>
  {#each items as s (s.key)}
    {@const st = s.direction === null || s.counted === false ? null : DIRECTIONS[s.direction]}
    {@const w = s.counted === false ? 'räknas inte' : word(s.direction)}
    <li>
      <a
        class="unit"
        href={href(s.key)}
        style:background={st ? st.color : 'transparent'}
        class:nodir={!st}
        aria-label="{s.label}: {w}"
        title="{s.label}: {w}"
      >
        <span aria-hidden="true">{st ? st.glyph : '–'}</span>
      </a>
    </li>
  {/each}
  {#each withheld as w (w.key)}
    <li>
      <a class="unit held" href={withheldHref ?? '#inhallna'} aria-label="{w.label}: inhållen, riktningen visas inte" title="{w.label}: inhållen">
        <span aria-hidden="true"></span>
      </a>
    </li>
  {/each}
  {#each Array.from({ length: withheldAnon }, (_, i) => i) as i (i)}
    <li>
      <a class="unit held" href={withheldHref ?? '#inhallna'} aria-label="inhållen serie, riktningen visas inte" title="inhållen serie">
        <span aria-hidden="true"></span>
      </a>
    </li>
  {/each}
</ul>

<style>
  .units {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
  }
  .unit {
    display: grid;
    place-items: center;
    width: 32px;
    height: 32px;
    border-radius: var(--radius-sm);
    text-decoration: none;
    color: var(--c-page);
    font-size: 19px;
    font-weight: 700;
    line-height: 1;
  }
  .unit:hover {
    outline: 2px solid var(--c-ink);
    outline-offset: 1px;
  }
  .nodir {
    border: 1px solid var(--c-axis);
    color: var(--c-ink-2);
  }
  .held {
    border: 1px dashed var(--c-ink-2);
    background: repeating-linear-gradient(135deg, var(--c-grid) 0 3px, transparent 3px 7px);
  }
  @media (forced-colors: active) {
    .unit {
      forced-color-adjust: none;
      border: 1px solid CanvasText;
    }
  }
</style>
