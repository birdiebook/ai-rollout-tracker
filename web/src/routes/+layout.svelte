<!-- Site shell (W4): tokens, header with navigation and theme toggle, testdata banner, footer. Pages own their main.
     W12: navigation, search (⌘K), share tags and the citation line are components in $lib/nav. -->
<script lang="ts">
  import '$lib/design/base.css';
  import { tokensCss } from '$lib/design/tokens';
  import { resolve } from '$app/paths';
  import ThemeToggle from '$lib/components/ThemeToggle.svelte';
  import TimeTravel from '$lib/timetravel/TimeTravel.svelte';
  import MainNav from '$lib/nav/MainNav.svelte';
  import PageMeta from '$lib/nav/PageMeta.svelte';
  import SearchButton from '$lib/nav/SearchButton.svelte';
  import ShareCite from '$lib/nav/ShareCite.svelte';
  import { tt } from '$lib/timetravel/store.svelte';
  import { dateLabel } from '$lib/design';

  let { data, children } = $props();
  const css = `<style>${tokensCss()}</style>`;

  // R-W2: the hash carries view state (as_of, fonster, avsnitt …). A plain "#main" would replace it, so with JS the
  // skip link moves focus itself and leaves the URL alone (without JS the href works as usual).
  function skip(e: MouseEvent) {
    const main = document.getElementById('main');
    if (!main) return;
    e.preventDefault();
    main.scrollIntoView({ block: 'start' });
    main.focus({ preventScroll: true });
  }
</script>

<svelte:head>
  <!-- eslint-disable-next-line svelte/no-at-html-tags -- generated from tokens.ts at build time, no user input -->
  {@html css}
</svelte:head>
<PageMeta meta={data.meta} />

<a class="skip" href="#main" onclick={skip}>Hoppa till innehållet</a>
<header class="top wrap">
  <a class="brand" href={resolve('/')}>AI-utrullningen</a>
  <MainNav />
  <div class="tools">
    <SearchButton />
    <ThemeToggle />
  </div>
</header>

{#if data.site.testdata}
  <div class="wrap">
    <p class="testdata" role="note"><strong>Testdata.</strong> {data.site.note}</p>
  </div>
{/if}

<main id="main" class="wrap" tabindex="-1">
  <TimeTravel>{@render children()}</TimeTravel>
  <ShareCite cite={data.meta.cite} url={data.meta.url} />
</main>

<footer class="wrap">
  <p>
    Byggd från site_bundle (schema {data.site.schemaVersion}){#if data.site.build.sha}, commit
      <code>{data.site.build.sha.slice(0, 7)}</code>{/if}. Underlag:
    <!-- R-W1: under time travel the footer must not name today's record (hidden before paint, replaced after) -->
    {#if tt.active}<span data-tt="footer">tidsresa, posten som var känd den {dateLabel(tt.effective)}</span>{:else}<span class="tt-hide">{data.site.record.label}</span>{/if}.
    Ny sida under uppbyggnad; den nuvarande finns kvar tills paritet är kontrollerad.
  </p>
</footer>

<style>
  :global(html[data-tt]) .tt-hide {
    visibility: hidden;
  }
  .skip {
    position: absolute;
    left: -9999px;
  }
  main:focus {
    outline: none;
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
  header.top :global(.main-nav) {
    order: 3;
    width: 100%;
    font-size: var(--fs-small);
  }
  .tools {
    display: flex;
    align-items: center;
    gap: 8px;
  }
  @media (min-width: 641px) {
    header.top :global(.main-nav) {
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
