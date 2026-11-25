<!-- Legend row: swatch + text (text in text tokens, never the data colour). -->
<script lang="ts">
  let { items }: { items: { label: string; fill?: string; border?: string; dashed?: boolean; line?: boolean }[] } = $props();
</script>

<ul class="legend">
  {#each items as it (it.label)}
    <li>
      <span
        class="sw"
        aria-hidden="true"
        style:background={it.fill ?? 'transparent'}
        style:border={it.border ? `1px ${it.dashed ? 'dashed' : 'solid'} ${it.border}` : undefined}
        style:height={it.line ? '2px' : undefined}
        style:vertical-align={it.line ? '3px' : undefined}
      ></span>{it.label}
    </li>
  {/each}
</ul>
