<!-- A state or direction: colour + glyph + word, always all three (P3). With word={false} the word is still there
     for screen readers. -->
<script lang="ts">
  import { DIRECTIONS, stateStyle, type Direction } from '../state';

  let {
    state,
    direction,
    word = true,
    size = '1em'
  }: { state?: string | null; direction?: Direction | null; word?: boolean; size?: string } = $props();
  const s = $derived(direction !== undefined && direction !== null ? DIRECTIONS[direction] : stateStyle(state));
</script>

<span class="glyph-wrap" data-state={s.key}>
  <span class="glyph" aria-hidden="true" style:color={s.color} style:font-size={size}>{s.glyph}</span>
  {#if word}<span class="word">{s.word}</span>{:else}<span class="visually-hidden">{s.word}</span>{/if}
</span>

<style>
  .glyph-wrap {
    display: inline-flex;
    align-items: baseline;
    gap: 0.3em;
    white-space: nowrap;
  }
  .glyph {
    line-height: 1;
  }
  @media (forced-colors: active) {
    .glyph {
      color: CanvasText !important;
    }
  }
</style>
