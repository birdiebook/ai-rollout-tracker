<!-- One of the three question cards: a number, the question as the heading, a short generated answer, then pictures. -->
<script lang="ts">
  import type { Snippet } from 'svelte';

  let { n, id, question, answer, children }: { n: number; id: string; question: string; answer?: Snippet; children: Snippet } = $props();
</script>

<article class="panel q" aria-labelledby="{id}-h" data-question={n}>
  <span class="qn">Fråga {n}</span>
  <h2 id="{id}-h">{question}</h2>
  {#if answer}<div class="answer">{@render answer()}</div>{/if}
  <div class="pics">{@render children()}</div>
</article>

<style>
  .q {
    display: flex;
    flex-direction: column;
    gap: 8px;
    min-width: 0;
  }
  .qn {
    font-size: 12px;
    color: var(--c-muted);
    letter-spacing: 0.06em;
    text-transform: uppercase;
  }
  h2 {
    font-size: 19px;
  }
  .answer {
    font-size: 15px;
    color: var(--c-ink-2);
  }
  .pics {
    display: grid;
    gap: 18px;
    min-width: 0;
  }
</style>
