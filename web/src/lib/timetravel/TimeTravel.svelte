<!-- Global time travel (W9), mounted once around the page in +layout.svelte. Reads `as_of` from the URL; with it set,
     the page's own content (built from today's bundle) is replaced by the time-travel view of the route, which gets
     its data only through gate.ts (known_from <= as_of). Routes without a time-travel view say so instead of
     showing today's data under a past date. Internal links carry `as_of` along (pointerdown/keydown/click, capture
     phase, before SvelteKit's router reads the href). -->
<script lang="ts">
  import { onMount, type Component, type Snippet } from 'svelte';
  import { afterNavigate } from '$app/navigation';
  import { page } from '$app/state';
  import { resolve } from '$app/paths';
  import { dateLabel } from '$lib/design';
  import TimeBar from './TimeBar.svelte';
  import { tt } from './store.svelte';
  import { PREPAINT_SCRIPT } from './prepaint';
  import { carryHref, readAsOf } from './url';

  let { children }: { children: Snippet } = $props();

  // before first paint: a URL with as_of hides today's content until the time-travel view replaces it, so later
  // knowledge never flashes under a past date (without JS nothing runs and the prerendered page shows as usual)
  // (R-W1: the same parser as readAsOf, prepaint.ts; the old regex missed e.g. "#as%5Fof=" and hid invalid days)
  const pre = PREPAINT_SCRIPT;

  type ViewKind = 'start' | 'branch' | 'series';
  const ROUTES: Record<string, ViewKind> = { '/': 'start', '/gren/[id]': 'branch', '/serie/[key]': 'series' };
  const LOADERS: Record<ViewKind, () => Promise<{ default: Component<any> }>> = {
    start: () => import('./views/StartOn.svelte'),
    branch: () => import('./views/BranchOn.svelte'),
    series: () => import('./views/SeriesOn.svelte')
  };
  const kind = $derived<ViewKind | null>(ROUTES[page.route.id ?? ''] ?? null);
  const site = $derived((page.data as { site?: { build?: { built?: string | null } } }).site);
  const base = resolve('/').replace(/\/$/, '');

  let mounted = $state(false);
  let View = $state<Component<any> | null>(null);
  let viewKind = $state<ViewKind | null>(null);
  let viewError = $state<string | null>(null);

  $effect(() => {
    if (!mounted || !tt.active || !kind || viewKind === kind) return;
    const k = kind;
    LOADERS[k]()
      .then((m) => {
        View = m.default;
        viewKind = k;
      })
      .catch((e) => (viewError = String(e)));
  });

  function carry(e: Event) {
    if (e instanceof KeyboardEvent && e.key !== 'Enter') return;
    if (e instanceof MouseEvent && e.type !== 'click' && e.button > 1) return;
    const a = (e.target as Element | null)?.closest?.('a[href]') as HTMLAnchorElement | null;
    if (!a || a.hasAttribute('download')) return;
    const cur = a.getAttribute('href') ?? '';
    const raw = a.dataset.ttSet === cur ? (a.dataset.ttHref ?? cur) : cur;
    const day = readAsOf(location.hash);
    if (raw.startsWith('#')) {
      // an in-page anchor would replace the hash and drop as_of: scroll to it ourselves while travelling
      if (day && e.type === 'click' && raw.length > 1) {
        const el = document.getElementById(decodeURIComponent(raw.slice(1)));
        if (el) {
          e.preventDefault();
          el.scrollIntoView({ block: 'start' });
          if (!el.hasAttribute('tabindex')) el.setAttribute('tabindex', '-1');
          el.focus({ preventScroll: true });
        }
      }
      return;
    }
    const next = carryHref(raw, location.href, base, day);
    if (next === null || next === a.href) return;
    a.dataset.ttHref = raw;
    a.href = next;
    a.dataset.ttSet = a.getAttribute('href') ?? '';
  }

  onMount(() => {
    const built = site?.build?.built;
    if (built && /^\d{4}-\d{2}-\d{2}/.test(built)) tt.max = built.slice(0, 10);
    tt.read();
    mounted = true;
    document.documentElement.removeAttribute('data-tt');
    const onHash = () => tt.read();
    addEventListener('hashchange', onHash);
    for (const t of ['pointerdown', 'keydown', 'click']) addEventListener(t, carry, true);
    return () => {
      removeEventListener('hashchange', onHash);
      for (const t of ['pointerdown', 'keydown', 'click']) removeEventListener(t, carry, true);
    };
  });
  afterNavigate(() => {
    if (mounted) tt.read();
  });
</script>

<svelte:head>
  <!-- eslint-disable-next-line svelte/no-at-html-tags -- a constant, no user input -->
  {@html pre}
</svelte:head>

<TimeBar />

{#if mounted && tt.active}
  <div class="tt-view" data-tt="view" data-tt-day={tt.effective}>
    {#if !kind}
      <section class="tt-none">
        <h1>Den här sidan har ingen tidsresa ännu</h1>
        <p class="lede">
          Den visar bara dagens kunskap, och därför visas den inte under datumet {dateLabel(tt.effective)}. Tidsresan finns för
          <a href={resolve('/')}>läget</a>, grensidorna och seriesidorna.
        </p>
        <p><button type="button" class="chip" onclick={() => tt.set(null)}>Visa sidan som i dag</button></p>
      </section>
    {:else if viewError}
      <p class="note" role="alert">Kunde inte ladda tidsresan: {viewError}</p>
    {:else if View && viewKind === kind}
      {#key `${kind}:${JSON.stringify(page.params)}`}
        <View day={tt.effective} params={page.params} />
      {/key}
    {:else}
      <p class="note" role="status">Laddar tidsresan …</p>
    {/if}
  </div>
{:else}
  <div class="tt-today">{@render children()}</div>
{/if}

<style>
  .tt-today {
    display: contents;
  }
  :global(html[data-tt]) .tt-today {
    visibility: hidden;
  }
  .tt-none {
    margin-top: 28px;
  }
</style>
