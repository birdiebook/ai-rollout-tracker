<!-- Accessible chart/table switch: a toggle button (aria-pressed) that controls which view is shown. -->
<script lang="ts">
  let { pressed = $bindable(false), controls }: { pressed?: boolean; controls: string } = $props();
</script>

<button type="button" class="chip" aria-pressed={pressed} aria-controls={controls} onclick={() => (pressed = !pressed)}>
  {pressed ? 'Visa diagram' : 'Visa tabell'}
</button>
