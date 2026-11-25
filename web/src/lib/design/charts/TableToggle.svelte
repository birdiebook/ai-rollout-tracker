<!-- Accessible chart/table switch: a button that controls which view is shown. R-W2: the label says what a press does
     ("Visa tabell" / "Visa diagram"), so it carries no aria-pressed: a toggle button must keep its name (WAI-ARIA APG),
     otherwise a screen reader hears "Visa diagram, pressed" while the table is shown. -->
<script lang="ts">
  let { pressed = $bindable(false), controls }: { pressed?: boolean; controls: string } = $props();
</script>

<button type="button" class="chip" aria-controls={controls} onclick={() => (pressed = !pressed)}>
  {pressed ? 'Visa diagram' : 'Visa tabell'}
</button>
