<!-- Site shell (W4): tokens, header with navigation and theme toggle, testdata banner, footer. Pages own their main. -->
<script lang="ts">
  import '$lib/design/base.css';
  import { tokensCss } from '$lib/design/tokens';
  import { page } from '$app/state';
  import { resolve } from '$app/paths';
  import ThemeToggle from '$lib/components/ThemeToggle.svelte';

  let { data, children } = $props();
  const css = `<style>${tokensCss()}</style>`;
  const nav = [
    { href: resolve('/'), label: 'Läget', match: (p: string) => p === resolve('/') },
    { href: resolve('/flode'), label: 'Flödet', match: (p: string) => p.startsWith(resolve('/flode')) || p.startsWith(resolve('/gren')) },
    { href: resolve('/prognoser'), label: 'Prognoser', match: (p: string) => p.startsWith(resolve('/prognoser')) },
    { href: resolve('/metod'), label: 'Metod', match: (p: string) => p.startsWith(resolve('/metod')) }
  ];
  const path = $derived(page.url.pathname.replace(/\/?$/, '/'));
</script>

<svelte:head>
  <!-- eslint-disable-next-line svelte/no-at-html-tags -- generated from tokens.ts at build time, no user input -->
  {@html css}
</svelte:head>

<a class="skip" href="#main">Hoppa till innehållet</a>
<header class="top wrap">
  <a class="brand" href={resolve('/')}>AI-utrullningen</a>
  <nav aria-label="Huvudmeny">
    {#each nav as n (n.href)}
      <a href={n.href} aria-current={n.match(path) ? 'page' : undefined}>{n.label}</a>
    {/each}
  </nav>
  <ThemeToggle />
</header>

{#if data.site.testdata}
  <div class="wrap">
    <p class="testdata" role="note"><strong>Testdata.</strong> {data.site.note}</p>
  </div>
{/if}

<main id="main" class="wrap">
  {@render children()}
</main>

<footer class="wrap">
  <p>
    Byggd från site_bundle (schema {data.site.schemaVersion}){#if data.site.build.sha}, commit
      <code>{data.site.build.sha.slice(0, 7)}</code>{/if}. Underlag: {data.site.record.label}.
    Ny sida under uppbyggnad; den nuvarande finns kvar tills paritet är kontrollerad.
  </p>
</footer>

<style>
  .skip {
    position: absolute;
    left: -9999px;
  }
  .skip:focus {
    left: 16px;
    top: 8px;
    z-index: 50;
    background: var(--c-surface);
    padding: 6px 10px;
    border-radius: 8px;
  }
  header.top {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 6px 12px;
    padding-top: 14px;
    padding-bottom: 14px;
    border-bottom: 1px solid var(--c-grid);
  }
  .brand {
    font-weight: 650;
    letter-spacing: -0.01em;
    text-decoration: none;
  }
  nav {
    order: 3;
    width: 100%;
    display: flex;
    gap: 4px 14px;
    flex-wrap: wrap;
    font-size: var(--fs-small);
    color: var(--c-ink-2);
  }
  nav a {
    text-decoration: none;
    display: inline-flex;
    align-items: center;
    min-height: var(--hit);
  }
  nav a[aria-current='page'] {
    color: var(--c-ink);
    font-weight: 600;
    text-decoration: underline;
  }
  @media (min-width: 561px) {
    nav {
      order: 0;
      width: auto;
      font-size: 14px;
      margin-left: auto;
    }
  }
  .testdata {
    margin: 12px 0 0;
    padding: 8px 12px;
    border: 1px dashed var(--c-axis);
    border-radius: var(--radius-md);
    font-size: var(--fs-small);
    color: var(--c-ink-2);
  }
  footer {
    margin-top: 40px;
    margin-bottom: 30px;
    font-size: 12px;
    color: var(--c-muted);
    border-top: 1px solid var(--c-grid);
    padding-top: 12px;
  }
</style>
