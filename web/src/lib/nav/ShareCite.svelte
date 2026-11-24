<!-- W12: "Dela och citera" at the end of every page: the citation line (copyable), the page's permalink with its
     view state, and links to each section of the page.
     Sections: every visible <h2> in <main> is an anchor. Its id is the page's own (h2 or its section), else a
     slug of the heading without dates. The section lives in the hash as `avsnitt=<id>` next to the view state
     ($lib/nav/hash, W7's permalink convention: other keys are kept). Opening such a link scrolls to the section
     after hydration. The page's headings are not changed beyond a missing id (their text and tests stay the
     page owner's); the list here is the way to a section link. -->
<script lang="ts">
  import { afterNavigate } from '$app/navigation';
  import { onMount } from 'svelte';
  import { asOfOf, sectionOf, slugify, withSection } from './hash';
  import type { Citation } from './meta';

  let { cite, url }: { cite: Citation; url: string } = $props();

  interface Sec {
    id: string;
    text: string;
  }
  let sections: Sec[] = $state([]);
  let href = $state('');
  let copied = $state('');
  let root: HTMLElement | undefined = $state();

  const live = $derived(href || url);
  const hash = $derived(live.includes('#') ? live.slice(live.indexOf('#')) : '');
  const asOf = $derived(asOfOf(hash));
  const text = $derived(`AI-utrullningen, ${cite.what}, version per ${asOf ?? cite.date}${cite.commit ? ` (commit ${cite.commit})` : ''}, ${live}`);
  const sectionHref = (id: string) => withSection(hash, id) || '#';

  const reduce = () => matchMedia('(prefers-reduced-motion: reduce)').matches;

  function headingText(h: HTMLElement): string {
    const c = h.cloneNode(true) as HTMLElement;
    c.querySelectorAll('.visually-hidden, [aria-hidden="true"]').forEach((n) => n.remove());
    return (c.textContent ?? '').replace(/\s+/g, ' ').trim();
  }

  function collect() {
    const main = document.getElementById('main');
    if (!main) return;
    const used = new Set<string>();
    const out: Sec[] = [];
    for (const h of main.querySelectorAll<HTMLElement>('h2')) {
      if (root?.contains(h) || h.closest('dialog, [hidden]') || h.classList.contains('visually-hidden')) continue;
      const t = headingText(h);
      if (!t) continue;
      let id = h.id || h.closest('section')?.id || '';
      if (!id) {
        const base = slugify(t) || 'avsnitt';
        id = base;
        for (let k = 2; used.has(id) || (document.getElementById(id) && document.getElementById(id) !== h); k++) id = `${base}-${k}`;
        h.id = id;
      }
      if (used.has(id)) continue;
      used.add(id);
      out.push({ id, text: t });
    }
    sections = out;
  }

  function scrollToSection(behavior: ScrollBehavior) {
    const id = sectionOf(location.hash);
    if (!id) return;
    const el = document.getElementById(id);
    if (!el || id === 'main' || root?.contains(el)) return;
    el.scrollIntoView({ block: 'start', behavior: reduce() ? 'auto' : behavior });
    const h = el.matches('h2, h3') ? el : el.querySelector<HTMLElement>('h2, h3');
    if (h) {
      if (!h.hasAttribute('tabindex')) h.setAttribute('tabindex', '-1');
      h.focus({ preventScroll: true });
    }
  }

  const sync = () => (href = location.href);

  onMount(() => {
    const onhash = () => {
      sync();
      scrollToSection('smooth');
    };
    addEventListener('hashchange', onhash);
    // other components change the hash with history.replaceState (no event): keep the shown link current
    const t = setInterval(() => location.href !== href && sync(), 1000);
    return () => {
      removeEventListener('hashchange', onhash);
      clearInterval(t);
    };
  });

  afterNavigate(() => {
    sync();
    collect();
    // after the page's own hash handling and the charts' first redraw
    requestAnimationFrame(() => requestAnimationFrame(() => scrollToSection('auto')));
  });

  async function copy(kind: 'cite' | 'link') {
    const value = kind === 'cite' ? text : location.href;
    try {
      await navigator.clipboard.writeText(value);
      copied = kind === 'cite' ? 'Citeringen är kopierad.' : 'Länken är kopierad.';
    } catch {
      copied = `Kopiera för hand: ${value}`;
    }
  }
</script>

<section class="share" aria-labelledby="dela-h" bind:this={root}>
  <h2 id="dela-h">Dela och citera</h2>
  <div class="cite">
    <p class="cite-text" id="cite-text"><span class="visually-hidden">Citering: </span>{text}</p>
    <div class="btns">
      <button type="button" class="chip" aria-describedby="cite-text" onclick={() => copy('cite')}>Kopiera citeringen</button>
      <button type="button" class="chip" onclick={() => copy('link')}>Kopiera länken</button>
    </div>
    <p class="note copied" role="status">{copied}</p>
  </div>
  {#if sections.length > 1}
    <nav aria-labelledby="avsnitt-h" class="secs">
      <h3 id="avsnitt-h">Avsnitt på sidan</h3>
      <ul>
        {#each sections as s (s.id)}
          <li><a href={sectionHref(s.id)}>{s.text}</a></li>
        {/each}
      </ul>
    </nav>
  {/if}
</section>

<style>
  .share {
    margin: 40px 0 0;
    padding: 16px 18px;
    border: 1px solid var(--c-ring);
    border-radius: var(--radius-lg);
    background: var(--c-surface);
    display: grid;
    gap: 14px 32px;
  }
  @media (min-width: 861px) {
    .share {
      grid-template-columns: minmax(0, 3fr) minmax(0, 2fr);
    }
    .share h2 {
      grid-column: 1 / -1;
    }
  }
  h2 {
    font-size: var(--fs-subsection);
    margin: 0;
  }
  h3 {
    font-size: var(--fs-small);
    color: var(--c-ink-2);
    font-weight: 620;
    margin: 0 0 4px;
  }
  .cite-text {
    margin: 0 0 8px;
    font-size: var(--fs-small);
    color: var(--c-ink);
    overflow-wrap: anywhere;
    font-variant-numeric: tabular-nums;
    padding: 8px 10px;
    background: var(--c-page);
    border-radius: var(--radius-md);
    border: 1px solid var(--c-grid);
  }
  .btns {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }
  .copied {
    margin: 6px 0 0;
    min-height: 1.5em;
    overflow-wrap: anywhere;
  }
  .secs ul {
    list-style: none;
    margin: 0;
    padding: 0;
    columns: 2 180px;
    column-gap: 16px;
    font-size: var(--fs-small);
  }
  .secs li {
    break-inside: avoid;
  }
  .secs a {
    display: inline-flex;
    align-items: center;
    min-height: 28px;
    color: var(--c-ink-2);
  }
  .secs a:hover {
    color: var(--c-ink);
  }
  :global(main h2[id], main section[id], main figure[id]) {
    scroll-margin-top: 12px;
  }
  :global(main h2[tabindex='-1']:focus) {
    outline: none;
  }
</style>
