<!-- Server only (ChartFrame): renders a chart body snippet on its own, so its markup can be prerendered as a string. -->
<script lang="ts">
  import type { Snippet } from 'svelte';
  let { snippet, args }: { snippet: Snippet<[never]>; args: never } = $props();
</script>

{@render snippet(args)}
