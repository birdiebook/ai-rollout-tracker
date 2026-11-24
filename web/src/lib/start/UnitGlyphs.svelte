<!-- Unit chart: one mark per counted series of a branch, grouped ▲ (more pace), ● (unchanged), ▼ (less pace).
     Withheld series are counted in the branch's aggregate without a direction of their own (datakontrakt 4), so
     they are part of the counts and named only as a number below. -->
<script lang="ts">
  let {
    up,
    neutral,
    down,
    withheld = 0,
    perRow = 7,
    cell = 11,
    gap = 3
  }: { up: number; neutral: number; down: number; withheld?: number; perRow?: number; cell?: number; gap?: number } = $props();

  const kinds = $derived([...Array(up).fill('acc'), ...Array(neutral).fill('stb'), ...Array(down).fill('brk')] as ('acc' | 'stb' | 'brk')[]);
  const n = $derived(kinds.length);
  const rows = $derived(Math.max(1, Math.ceil(n / perRow)));
  const w = $derived(perRow * (cell + gap) - gap);
  const h = $derived(rows * (cell + gap) - gap);
  const label = $derived(
    n === 0
      ? 'inga räknade serier'
      : `${n} räknade serier: ${up} ökar takten, ${neutral} oförändrad takt, ${down} minskar takten` +
          (withheld ? `, varav ${withheld} inhållna av licensskäl` : '')
  );
</script>

<span class="units">
  {#if n === 0}
    <span class="none">inga räknade serier</span>
  {:else}
    <svg viewBox="0 0 {w} {h}" width={w} height={h} role="img" aria-label={label}>
      {#each kinds as k, i (i)}
        {@const x = (i % perRow) * (cell + gap)}
        {@const y = Math.floor(i / perRow) * (cell + gap)}
        {#if k === 'stb'}
          <circle class="mark" cx={x + cell / 2} cy={y + cell / 2} r={cell / 2 - 1.5} fill="var(--c-stb)" />
        {:else if k === 'acc'}
          <path class="mark" d="M{x + cell / 2},{y + 0.5} L{x + cell},{y + cell - 1} L{x},{y + cell - 1}Z" fill="var(--c-acc)" />
        {:else}
          <path class="mark" d="M{x},{y + 1} L{x + cell},{y + 1} L{x + cell / 2},{y + cell - 0.5}Z" fill="var(--c-brk)" />
        {/if}
      {/each}
    </svg>
    {#if withheld}<span class="wh">varav {withheld} inhållna</span>{/if}
  {/if}
</span>

<style>
  .units {
    display: flex;
    flex-direction: column;
    gap: 2px;
    min-width: 0;
  }
  svg {
    display: block;
    max-width: 100%;
    height: auto;
  }
  .none,
  .wh {
    font-size: 11px;
    color: var(--c-muted);
    line-height: 1.2;
  }
</style>
