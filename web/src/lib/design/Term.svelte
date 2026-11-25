<!-- A technical word linked to its explanation in the glossary on /metod#ordlista (R-W3). -->
<script lang="ts">
  import type { Snippet } from 'svelte';
  import { resolve } from '$app/paths';
  import { GLOSSARY } from './glossary';

  let { id, children }: { id: string; children?: Snippet } = $props();
  const entry = GLOSSARY.find((g) => g.id === id);
</script>

<a class="term" href="{resolve('/metod')}#ord-{id}" title={entry?.text}>{#if children}{@render children()}{:else}{entry?.term.toLowerCase() ?? id}{/if}</a>

<style>
  .term {
    text-decoration-style: dotted;
    text-underline-offset: 2px;
  }
</style>
