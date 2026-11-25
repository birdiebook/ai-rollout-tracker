<!-- Index v2 on a branch page (register 2026-11-24): one row per counted source family with its vote (0–1, the
     index's own diverging fill) and its counted series as unit boxes. A family that counts a withheld series is
     counted but not named and has no vote in the bundle (n_families_withheld): it is one hatched row, its withheld
     series hatched boxes without direction, never a value (data contract 1.4.0). -->
<script lang="ts">
  import { divergingFill, fmt } from '$lib/design';
  import UnitBoxes from './UnitBoxes.svelte';
  import type { Dir } from './types';

  type Unit = { key: string; label: string; direction: Dir };
  let {
    families,
    counted,
    nWithheldFamilies = 0,
    withheld = [],
    withheldAnon = 0,
    href,
    label = 'Källfamiljer som röstar'
  }: {
    families: { family: string; series: string[]; vote: number | null }[];
    counted: Unit[];
    nWithheldFamilies?: number;
    /** withheld counted series (names only) */
    withheld?: { key: string; label: string }[];
    withheldAnon?: number;
    href: (key: string) => string;
    label?: string;
  } = $props();

  const byKey = $derived(new Map(counted.map((c) => [c.key, c])));
  const named = $derived(new Set(families.flatMap((f) => f.series)));
  /** publishable counted series of a family that is not named (it also counts a withheld series) */
  const inHeld = $derived(counted.filter((c) => !named.has(c.key)));
  const n = (k: number, one: string, many: string) => `${k} ${k === 1 ? one : many}`;
</script>

<ul class="fams" aria-label={label}>
  {#each families as f (f.family)}
    {@const items = f.series.map((k) => byKey.get(k) ?? { key: k, label: k, direction: null })}
    <li class="fam" data-family={f.family}>
      <span class="vote" aria-hidden="true">
        <span class="bar"><span class="fill" style:width="{(f.vote ?? 0) * 100}%" style:background={divergingFill(f.vote)}></span></span>
      </span>
      <span class="head">
        <code class="id">{f.family}</code>
        <span class="v">röst <strong class="num">{fmt(f.vote, 2)}</strong> · {n(f.series.length, 'serie', 'serier')}</span>
      </span>
      <UnitBoxes label="Serier i källfamiljen {f.family}, röst {fmt(f.vote, 2)}" {items} {href} />
    </li>
  {/each}
  {#if nWithheldFamilies > 0}
    <li class="fam held" data-family="withheld">
      <span class="vote" aria-hidden="true"><span class="bar"></span></span>
      <span class="head">
        <span class="id">{n(nWithheldFamilies, 'källfamilj', 'källfamiljer')} med inhållna serier</span>
        <span class="v">räknas i indexet, men namn och röst visas inte</span>
      </span>
      <UnitBoxes
        label="Serier i källfamiljer med inhållna serier"
        items={inHeld}
        {withheld}
        {withheldAnon}
        {href}
      />
    </li>
  {/if}
</ul>

<style>
  .fams {
    list-style: none;
    margin: 0;
    padding: 0;
    display: grid;
    gap: 8px;
  }
  .fam {
    display: grid;
    grid-template-columns: 56px minmax(0, 1fr);
    grid-template-areas: 'vote head' 'vote units';
    gap: 4px 12px;
    align-items: center;
    padding: 8px 10px;
    border: 1px solid var(--c-grid);
    border-radius: var(--radius-md);
    background: var(--c-surface);
  }
  .fam.held {
    border-style: dashed;
    border-color: var(--c-ink-2);
  }
  .vote {
    grid-area: vote;
    align-self: stretch;
    display: flex;
    align-items: center;
  }
  .bar {
    display: block;
    width: 56px;
    height: 10px;
    border-radius: 5px;
    border: 1px solid var(--c-axis);
    overflow: hidden;
    background: var(--c-page);
  }
  .held .bar {
    background: repeating-linear-gradient(135deg, var(--c-grid) 0 2px, transparent 2px 5px);
  }
  .fill {
    display: block;
    height: 100%;
  }
  .head {
    grid-area: head;
    display: flex;
    flex-wrap: wrap;
    gap: 2px 10px;
    align-items: baseline;
    font-size: var(--fs-small);
  }
  .id {
    font-size: 13px;
    overflow-wrap: anywhere;
  }
  .v {
    color: var(--c-ink-2);
  }
  .fam :global(.units) {
    grid-area: units;
  }
  @media (forced-colors: active) {
    .fill {
      forced-color-adjust: none;
    }
  }
</style>
