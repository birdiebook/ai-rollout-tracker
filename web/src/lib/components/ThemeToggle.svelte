<!-- Light/dark toggle. The OS preference is the default; a choice is remembered (localStorage, best effort) and
     applied before paint by the inline script in app.html. -->
<script lang="ts">
  import { onMount } from 'svelte';

  let theme = $state<'light' | 'dark'>('light');
  onMount(() => {
    const set = document.documentElement.dataset.theme;
    theme = set === 'dark' || set === 'light' ? set : matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  });
  function toggle() {
    theme = theme === 'dark' ? 'light' : 'dark';
    document.documentElement.dataset.theme = theme;
    try {
      localStorage.setItem('theme', theme);
    } catch {
      /* private mode: the choice lasts for this page only */
    }
  }
</script>

<button type="button" class="theme-btn" onclick={toggle} aria-label={theme === 'dark' ? 'Byt till ljust läge' : 'Byt till mörkt läge'}>
  {theme === 'dark' ? 'Ljust' : 'Mörkt'}
</button>

<style>
  .theme-btn {
    border: 1px solid var(--c-ring);
    background: var(--c-surface);
    color: var(--c-ink-2);
    border-radius: var(--radius-md);
    font: inherit;
    font-size: var(--fs-small);
    padding: 4px 10px;
    min-height: var(--hit);
    cursor: pointer;
  }
</style>
