<!-- W13: the monthly story as scrollytelling. Without JavaScript it is a list of cards, each with its figure (the
     figure is sticky inside its card on wide screens, so the text scrolls past the picture). With JavaScript the
     card in the middle of the screen is marked in the rail and by its top rule, and j/k (or the rail and the
     links in each card) move between the cards, and the links open the time-travel views at the month's known day
     (as_of is set after mount: time travel needs JavaScript, and the prerendered link opens today's view). prefers-reduced-motion: no transitions, no smooth scrolling. -->
<script lang="ts">
  import { onMount } from 'svelte';
  import { DIRECTIONS, StatusBadge, dateLabel } from '$lib/design';
  import Figure from './Figure.svelte';
  import { cardHref, monthHref } from './links';
  import { typeGlyph, type MonthNav, type StoryPage } from './model';

  let { page, months = page.months }: { page: StoryPage; months?: MonthNav[] } = $props();
  const s = $derived(page.story);
  const cards = $derived(page.cards);
  const status = $derived(s.status === 'live' ? 'live' : 'recon');
  const i = $derived(months.findIndex((m) => m.month === s.month));
  const prev = $derived(i > 0 ? months[i - 1] : null);
  const next = $derived(i >= 0 && i < months.length - 1 ? months[i + 1] : null);
  const cap = (x: string) => x.charAt(0).toUpperCase() + x.slice(1);
  const typeNames: Record<string, string> = {
    K1: 'tillståndsskiften',
    K2: 'regimskiften',
    K3: 'nya skarpa utfall',
    K4: 'strukturbrott',
    K5: 'kärnserier i extrem percentil',
    K6: 'avstämningar i extrem percentil'
  };
  const typeName1: Record<string, string> = {
    K1: 'tillståndsskifte',
    K2: 'regimskifte',
    K3: 'nytt skarpt utfall',
    K4: 'strukturbrott',
    K5: 'kärnserie i extrem percentil',
    K6: 'avstämning i extrem percentil'
  };
  const counted = (t: string, n: number) => `${n} ${n === 1 ? typeName1[t] : typeNames[t]}`;
  const prevLabel = $derived(s.previous ? (months.find((m) => m.month === s.previous)?.month_sv ?? s.previous) : null);
  const omitted = $derived(Object.entries(s.omitted).filter(([, n]) => n > 0));
  const withheld = $derived(Object.entries(s.withheld).filter(([, n]) => n > 0));
  const dirColor = (d: -1 | 0 | 1 | null) => (d === null ? 'var(--c-model)' : DIRECTIONS[d].color);
  // A state change (K1) moves the branch's index, not its pace: "högre/lägre index" (R-W3).
  const dirWord = (t: string, d: -1 | 0 | 1 | null) =>
    d === null ? '' : t === 'K1' ? (d === 1 ? 'högre index' : 'lägre index') : d === 1 ? 'mer takt' : d === -1 ? 'mindre takt' : 'oförändrad takt';

  const clip = (x: string, n = 26) => (x.length > n ? x.slice(0, n - 1).trimEnd() + '…' : x);
  function railLabel(c: (typeof page.cards)[number]): string {
    const f = c.facts;
    if (c.type === 'K1') return `${f.branch} → ${f.to}`;
    if (c.type === 'K2') return `Regim: ${f.label}`;
    if (c.type === 'K3') return `Utfall ${f.label}`;
    if (c.type === 'K4' || c.type === 'K5' || c.type === 'K6') return clip(String(f.label).replace(/^\[syntetisk\]\s*/, ''));
    return c.type_label;
  }

  let active = $state(0);
  let enhanced = $state(false);
  let host: HTMLElement | undefined = $state();

  function go(k: number, reduced: boolean) {
    const el = host?.querySelector<HTMLElement>(`[data-step="${k}"]`);
    if (!el) return;
    el.scrollIntoView({ block: 'start', behavior: reduced ? 'auto' : 'smooth' });
    el.focus({ preventScroll: true });
    active = k;
  }

  onMount(() => {
    enhanced = true;
    const reduced = matchMedia('(prefers-reduced-motion: reduce)');
    const steps = [...(host?.querySelectorAll<HTMLElement>('[data-step]') ?? [])];
    const io = new IntersectionObserver(
      (entries) => {
        for (const e of entries) if (e.isIntersecting) active = Number((e.target as HTMLElement).dataset.step);
      },
      { rootMargin: '-45% 0px -45% 0px' }
    );
    steps.forEach((el) => io.observe(el));
    const onKey = (e: KeyboardEvent) => {
      if (e.altKey || e.ctrlKey || e.metaKey) return;
      const t = e.target as HTMLElement | null;
      if (t && (t.isContentEditable || /^(INPUT|TEXTAREA|SELECT|BUTTON)$/.test(t.tagName))) return;
      // R-W2 (WCAG 2.1.4): single-letter shortcuts only while focus is in the story, not anywhere on the page
      if (!t || !host?.contains(t)) return;
      if (e.key === 'j' || e.key === 'k') {
        // step from the focused card (the observer's card can be the next one once a card is scrolled to the top)
        const focused = (document.activeElement as HTMLElement | null)?.closest<HTMLElement>('[data-step]');
        const from = focused ? Number(focused.dataset.step) : active;
        const k = Math.max(0, Math.min(steps.length - 1, from + (e.key === 'j' ? 1 : -1)));
        e.preventDefault();
        go(k, reduced.matches);
      }
    };
    addEventListener('keydown', onKey);
    return () => {
      io.disconnect();
      removeEventListener('keydown', onKey);
    };
  });
</script>

<article class="story" data-month={s.month} data-status={s.status} data-known={s.known} bind:this={host}>
  <header class="head">
    <p class="kicker">Månadens berättelse <StatusBadge {status} /></p>
    <h1>{cap(s.month_sv)}</h1>
    <p class="lede">{s.headline}</p>
    <p class="note">
      Korten väljs mekaniskt med en regel som registrerades i förväg (måttregistret, {s.rule.entry.split(' – ')[0]}): tillståndsskiften,
      regimskiften, nya skarpa utfall, strukturbrott och serier som når percentil ≤ {s.rule.low} eller ≥ {s.rule.high}, i båda riktningarna,
      högst {s.rule.cap} kort. Allt är som det var känt {dateLabel(s.known)}.
    </p>
    <nav class="monthnav" aria-label="Föregående och nästa månad">
      {#if prev}<a href={monthHref(prev.month)} rel="prev">← {prev.month_sv}</a>{:else}<span></span>{/if}
      {#if next}<a href={monthHref(next.month)} rel="next">{next.month_sv} →</a>{/if}
    </nav>
  </header>

  <div class="scrolly" class:enhanced>
    <nav class="rail" aria-label={`Korten i ${s.month_sv}`}>
      <ol>
        {#each cards as c, k (c.id)}
          <li>
            <a href={`#kort-${c.id}`} aria-current={enhanced && active === k ? 'step' : undefined}>
              <span class="g" aria-hidden="true" style:color={dirColor(c.direction)}>{typeGlyph[c.type] ?? '·'}</span>
              <span class="rl">{railLabel(c)}</span>
            </a>
          </li>
        {/each}
      </ol>
      {#if enhanced}<p class="note keys">När fokus är i berättelsen går tangenterna j och k till nästa och föregående kort.</p>{/if}
    </nav>

    <ol class="steps">
      {#each cards as c, k (c.id)}
        <li>
          <article
            class="step"
            class:on={enhanced && active === k}
            id={`kort-${c.id}`}
            data-step={k}
            data-type={c.type}
            data-card={c.id}
            tabindex="-1"
            aria-labelledby={`t-${c.id}`}
          >
            <p class="kicker kick">
              <span class="tag" style:border-color={dirColor(c.direction)}>
                <span aria-hidden="true" style:color={dirColor(c.direction)}>{typeGlyph[c.type] ?? '·'}</span>
                <span>{c.type_label}{#if dirWord(c.type, c.direction)}, {dirWord(c.type, c.direction)}{/if}</span>
              </span>
              <span class="count">Kort {k + 1} av {cards.length}</span>
            </p>
            <div class="txt">
              <h2 id={`t-${c.id}`}>{c.title}</h2>
              <p class="body">{c.text}</p>
              <p class="go"><a href={cardHref(enhanced ? c.target : { ...c.target, asOf: null })} data-link={c.link.kind} data-tt-own={enhanced && c.target.asOf ? '' : undefined}>{c.link.label} →</a>
                {#if enhanced && c.target.asOf}<span class="note"> (som det var känt {dateLabel(c.target.asOf)})</span>{/if}</p>
              <p class="stepnav note">
                {#if k > 0}<a href={`#kort-${cards[k - 1].id}`}>↑ Föregående kort</a>{/if}
                {#if k < cards.length - 1}<a href={`#kort-${cards[k + 1].id}`}>Nästa kort ↓</a>{:else}<a href="#om-urvalet">Om urvalet ↓</a>{/if}
              </p>
            </div>
            <div class="fig"><Figure card={c} /></div>
          </article>
        </li>
      {/each}
    </ol>
  </div>

  <section class="about panel" id="om-urvalet" aria-labelledby="om-h">
    <h2 id="om-h">Om urvalet</h2>
    <p>
      Regeln prövar sex villkor i den här ordningen: tillståndsskifte, regimskifte, nytt skarpt utfall, strukturbrott, kärnserie i extrem
      percentil och avstämning i extrem percentil. Läget visas alltid först, och en månad utan utslag får ett kort som säger det.
      Taket är {s.rule.cap} kort (strukturbrott högst {s.rule.type_caps.K4}, kärnserier högst {s.rule.type_caps.K5}, avstämningar högst {s.rule.type_caps.K6}).
    </p>
    <ul class="facts">
      <li>{omitted.length ? `Uppfyllde villkoren men visas inte på grund av taket: ${omitted.map(([t, n]) => counted(t, n)).join(', ')}.` : 'Inget kort ströks på grund av taket.'}</li>
      <li>{withheld.length ? `Serier som inte visas av licensskäl men uppfyllde villkoren (räknas, namnges inte): ${withheld.map(([t, n]) => counted(t, n)).join(', ')}.` : 'Inga serier som hålls inne av licensskäl uppfyllde villkoren.'}</li>
      <li>{prevLabel ? `Jämförelsemånad: ${prevLabel}.` : 'Ingen jämförelsemånad: tillståndsskiften och extrema percentiler kunde inte prövas.'}</li>
    </ul>
    <details class="all">
      <summary>Alla månader ({months.length})</summary>
      <ol class="mlist">
        {#each [...months].reverse() as m (m.month)}
          <li>
            <a href={monthHref(m.month)} aria-current={m.month === s.month ? 'page' : undefined}>{m.month_sv}</a>
            <span class="note">{m.n_events === 0 ? 'inga utslag' : `${m.n_events} kort`}{m.kind === 'rekonstruerad' ? ', rekonstruerad' : ', skarp'}</span>
          </li>
        {/each}
      </ol>
    </details>
  </section>
</article>

<style>
  .head {
    margin: 20px 0 18px;
  }
  .head .kicker {
    display: flex;
    gap: 10px;
    align-items: center;
    margin: 0;
  }
  .head .note {
    max-width: 78ch;
    margin: 10px 0 0;
  }
  .monthnav {
    display: flex;
    justify-content: space-between;
    gap: 12px;
    margin-top: 14px;
    font-size: var(--fs-small);
  }
  .monthnav a,
  .rail a,
  .stepnav a,
  .go a,
  .mlist a {
    display: inline-flex;
    align-items: center;
    min-height: var(--hit, 44px);
  }
  .rail {
    display: none;
  }
  .rail ol,
  .steps,
  .mlist {
    list-style: none;
    margin: 0;
    padding: 0;
  }
  .steps > li + li {
    margin-top: 18px;
  }
  .step {
    display: flex;
    flex-direction: column;
    gap: 12px;
    border-top: 1px solid var(--c-grid);
    padding-top: 16px;
    outline-offset: 6px;
    transition: border-color var(--motion-base, 300ms) var(--easing, ease);
  }
  .kick {
    margin: 0;
  }
  .step .fig {
    min-width: 0; /* mobile: the picture before the text (vision 3.4), after the card's label */
  }
  .txt {
    order: 1;
  }
  .txt {
    min-width: 0;
  }
  .txt h2 {
    margin: 6px 0 8px;
  }
  .body {
    margin: 0 0 10px;
    max-width: 62ch;
  }
  .kicker .tag {
    display: inline-flex;
    gap: 6px;
    align-items: center;
    border: 1px solid;
    border-radius: 999px;
    padding: 1px 9px;
    color: var(--c-ink-2);
  }
  .count {
    margin-left: 8px;
    white-space: nowrap;
  }
  .go,
  .stepnav {
    margin: 0;
  }
  .stepnav {
    display: flex;
    gap: 18px;
  }
  .about {
    margin: 34px 0 10px;
  }
  .about p,
  .facts {
    max-width: 78ch;
  }
  .facts {
    padding-left: 18px;
  }
  .mlist {
    columns: 2 220px;
    margin-top: 8px;
  }
  .mlist li {
    break-inside: avoid;
    display: flex;
    gap: 8px;
    align-items: center;
  }
  .mlist a[aria-current='page'] {
    font-weight: 650;
  }
  @media (min-width: 900px) {
    .scrolly {
      display: grid;
      grid-template-columns: 170px minmax(0, 1fr);
      gap: 24px;
      align-items: start;
    }
    .rail {
      display: block;
      position: sticky;
      top: 16px;
      font-size: var(--fs-small);
    }
    .rail a {
      gap: 8px;
      color: var(--c-ink-2);
      text-decoration: none;
      min-height: 32px;
      padding: 0 8px;
      border-left: 2px solid transparent;
    }
    .rail a:hover {
      color: var(--c-ink);
    }
    .rail a[aria-current='step'] {
      color: var(--c-ink);
      border-left-color: var(--c-ink);
      font-weight: 600;
    }
    .keys {
      margin-top: 10px;
      padding-left: 8px;
    }
    .step {
      display: grid;
      grid-template-columns: minmax(0, 5fr) minmax(0, 7fr);
      grid-template-areas: 'kick fig' 'txt fig';
      grid-template-rows: auto 1fr;
      gap: 6px 24px;
      align-items: start;
      min-height: 50vh;
    }
    .kick {
      grid-area: kick;
    }
    .txt {
      grid-area: txt;
    }
    .step .fig {
      grid-area: fig;
      position: sticky;
      top: 16px;
    }
    .steps > li + li {
      margin-top: 28px;
    }
  }
  .step.on {
    border-top-color: var(--c-ink);
  }
  .step.on .fig :global(.figure) {
    border-color: var(--c-axis);
  }
  @media (prefers-reduced-motion: reduce) {
    .step {
      transition: none;
    }
  }
</style>
