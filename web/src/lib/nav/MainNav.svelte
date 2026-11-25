<!-- W12: the main menu. Flödet is current on lead, branch and series pages too (they are the chain's depth). -->
<script lang="ts">
  import { page } from '$app/state';
  import { resolve } from '$app/paths';

  const nav = [
    { href: resolve('/'), label: 'Läget', match: (p: string) => p === resolve('/') },
    {
      href: resolve('/flode'),
      label: 'Flödet',
      match: (p: string) => [resolve('/flode'), resolve('/gren'), resolve('/serie')].some((x) => p.startsWith(x))
    },
    { href: resolve('/prognoser'), label: 'Prognoser', match: (p: string) => p.startsWith(resolve('/prognoser')) },
    { href: resolve('/avstamningar'), label: 'Avstämningar', match: (p: string) => p.startsWith(resolve('/avstamningar')) },
    { href: resolve('/regim'), label: 'Regim', match: (p: string) => p.startsWith(resolve('/regim')) },
    { href: resolve('/metod'), label: 'Metod', match: (p: string) => p.startsWith(resolve('/metod')) }
  ];
  const path = $derived(page.url.pathname.replace(/\/?$/, '/'));
</script>

<nav aria-label="Huvudmeny" class="main-nav">
  <ul>
    {#each nav as n (n.href)}
      <li><a href={n.href} aria-current={n.match(path) ? 'page' : undefined}>{n.label}</a></li>
    {/each}
  </ul>
</nav>

<style>
  .main-nav ul {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-wrap: wrap;
    gap: 0 2px;
  }
  a {
    text-decoration: none;
    display: inline-flex;
    align-items: center;
    min-height: var(--hit);
    padding: 0 7px;
    border-radius: var(--radius-md);
    color: var(--c-ink-2);
  }
  a:hover {
    color: var(--c-ink);
    background: var(--c-mid);
  }
  a[aria-current='page'] {
    color: var(--c-ink);
    font-weight: 620;
    text-decoration: underline;
    text-decoration-thickness: 2px;
    text-underline-offset: 6px;
  }
  li:first-child a {
    margin-left: -7px;
  }
  @media (min-width: 641px) {
    li:first-child a {
      margin-left: 0;
    }
  }
</style>
