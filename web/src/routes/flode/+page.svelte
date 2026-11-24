<!-- PLACEHOLDER (W4). Owner in wave 1: W6 (leads L1–L9 and branch pages: minimap, index over time, small multiples). -->
<script lang="ts">
  import { resolve } from '$app/paths';
  import { Glyph } from '$lib/design';

  let { data } = $props();
  const byCode = $derived(new Map(data.branches.map((b) => [b.code, b])));
</script>

<svelte:head><title>Flödet L1–L9 – AI-utrullningen</title></svelte:head>

<h1>Flödet från användning till el</h1>
<p class="lede">Kedjan L1→L9. Varje led visar grenarnas tillstånd.</p>
<ol class="chain">
  {#each data.leads as l (l.code)}
    <li class="panel">
      <h2>{l.code} {l.name}</h2>
      <ul>
        {#each l.branches as code (code)}
          <li>
            <a href={resolve('/gren/[id]', { id: code })}>{code} {byCode.get(code)?.name ?? ''}</a>
            <Glyph state={byCode.get(code)?.state} />
          </li>
        {/each}
      </ul>
    </li>
  {/each}
</ol>

<style>
  .chain {
    list-style: none;
    padding: 0;
    display: grid;
    gap: 10px;
    grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  }
  .chain h2 {
    font-size: 16px;
  }
  .chain ul {
    list-style: none;
    padding: 0;
    margin: 6px 0 0;
    font-size: 14px;
    display: grid;
    gap: 4px;
  }
  .chain li li {
    display: flex;
    justify-content: space-between;
    gap: 8px;
  }
</style>
