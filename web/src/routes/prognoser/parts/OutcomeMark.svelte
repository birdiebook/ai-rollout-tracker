<!-- An outcome: filled ink dot inside the 80 % interval, a ring outside (section 4.1). -->
<script lang="ts">
  let { cx, cy, inside, r = 4 }: { cx: number; cy: number; inside: boolean; r?: number } = $props();
</script>

<circle class="mark" {cx} {cy} {r} fill={inside ? 'var(--c-ink)' : 'var(--c-surface)'} stroke="var(--c-ink)" stroke-width="1.6" data-inside={inside} />
