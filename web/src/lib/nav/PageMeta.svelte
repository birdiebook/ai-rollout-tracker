<!-- W12: head tags for sharing, generated from data per page ($lib/nav/describe.server): description (only where
     the page does not write its own), Open Graph and Twitter card with the page's share image (og/<page>.png,
     1200x630, drawn at build time). The page keeps its own <title>. No <link rel=canonical>: nothing is loaded
     from absolute URLs (scripts/check-external-hosts.mjs), og:url says the same. -->
<script lang="ts">
  import type { PageMeta } from './meta';

  let { meta }: { meta: PageMeta & { url: string; image: string } } = $props();
</script>

<svelte:head>
  {#if !meta.ownDescription}<meta name="description" content={meta.description} />{/if}
  <meta property="og:type" content="website" />
  <meta property="og:site_name" content="AI-utrullningen" />
  <meta property="og:locale" content="sv_SE" />
  <meta property="og:title" content={meta.title} />
  <meta property="og:description" content={meta.description} />
  <meta property="og:url" content={meta.url} />
  <meta property="og:image" content={meta.image} />
  <meta property="og:image:type" content="image/png" />
  <meta property="og:image:width" content="1200" />
  <meta property="og:image:height" content="630" />
  <meta property="og:image:alt" content={meta.imageAlt} />
  <meta name="twitter:card" content="summary_large_image" />
  <meta name="twitter:title" content={meta.title} />
  <meta name="twitter:description" content={meta.description} />
  <meta name="twitter:image" content={meta.image} />
  <meta name="twitter:image:alt" content={meta.imageAlt} />
</svelte:head>
