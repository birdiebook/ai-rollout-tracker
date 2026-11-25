<!-- The time slider (vision P5, section 5): "Vad visste vi den …?" with day resolution, ±1 month, play and today.
     Collapsed to one button until time travel starts. Every change goes to the URL (as_of) and from there to the
     views; playback steps one month end at a time and stops at the bundle's day. -->
<script lang="ts">
  import { onDestroy, tick } from 'svelte';
  import { dateLabel } from '$lib/design';
  import { MIN_DAY, tt } from './store.svelte';
  import { dayToMs, msToDay, stepMonth } from './url';

  const DAY_MS = 86_400_000;
  const span = $derived(Math.round((dayToMs(tt.max) - dayToMs(MIN_DAY)) / DAY_MS));
  const pos = $derived(Math.round((dayToMs(tt.effective) - dayToMs(MIN_DAY)) / DAY_MS));
  let timer: ReturnType<typeof setInterval> | null = null;

  function stop() {
    if (timer) clearInterval(timer);
    timer = null;
    tt.playing = false;
  }
  function play() {
    if (tt.playing) return stop();
    if (tt.effective >= tt.max) tt.set(stepMonth(tt.max, -36));
    tt.playing = true;
    timer = setInterval(() => {
      if (!tt.active || tt.effective >= tt.max) return stop();
      tt.set(stepMonth(tt.effective, 1));
    }, 700);
  }
  // R-W2: the bar swaps its markup when time travel starts or ends, which would drop keyboard focus on <body>;
  // focus goes to the slider (start) or back to the start button (I dag)
  let slider: HTMLInputElement | undefined = $state();
  let opener: HTMLButtonElement | undefined = $state();
  let barH = $state(0);
  const start = async () => {
    tt.set(stepMonth(tt.max, -12));
    await tick();
    slider?.focus();
  };
  const today = async () => {
    stop();
    tt.set(null);
    await tick();
    opener?.focus();
  };
  // R-W2 (WCAG 2.4.11): the bar is sticky on wide screens, so the page scrolls focused elements clear of it
  $effect(() => {
    const root = document.documentElement;
    const wide = matchMedia('(min-width: 861px)');
    const apply = () => (root.style.scrollPaddingTop = tt.active && wide.matches && barH ? `${barH + 18}px` : '');
    apply();
    wide.addEventListener('change', apply);
    return () => {
      wide.removeEventListener('change', apply);
      root.style.scrollPaddingTop = '';
    };
  });
  const step = (k: number) => {
    stop();
    tt.set(stepMonth(tt.effective, k));
  };
  $effect(() => {
    if (!tt.active && timer) stop();
  });
  onDestroy(stop);
</script>

{#if tt.active}
  <section class="bar on" aria-label="Tidsresa" bind:offsetHeight={barH}>
    <div class="row">
      <p class="when">
        <span class="k">Vad visste vi den</span>
        <strong aria-live={tt.playing ? 'off' : 'polite'}>{dateLabel(tt.effective)}</strong>
      </p>
      <input
        bind:this={slider}
        class="slider"
        type="range"
        min="0"
        max={span}
        step="1"
        value={pos}
        aria-label="Datum för tidsresan"
        aria-valuetext={dateLabel(tt.effective)}
        oninput={(e) => {
          stop();
          tt.set(msToDay(dayToMs(MIN_DAY) + Number((e.currentTarget as HTMLInputElement).value) * DAY_MS));
        }}
      />
      <div class="btns">
        <button type="button" class="chip" onclick={() => step(-1)} disabled={tt.effective <= MIN_DAY}>−1 månad</button>
        <!-- R-W2: the name says what a press does (Spela/Paus), so no aria-pressed; the glyph is not read out -->
        <button type="button" class="chip" onclick={play}><span aria-hidden="true">{tt.playing ? '❚❚' : '▶'}</span> {tt.playing ? 'Paus' : 'Spela'}</button>
        <button type="button" class="chip" onclick={() => step(1)} disabled={tt.effective >= tt.max}>+1 månad</button>
        <label class="date">
          <span class="visually-hidden">Datum</span>
          <input
            type="date"
            value={tt.effective}
            min={MIN_DAY}
            max={tt.max}
            onchange={(e) => {
              const v = (e.currentTarget as HTMLInputElement).value;
              if (/^\d{4}-\d{2}-\d{2}$/.test(v)) {
                stop();
                tt.set(v);
              }
            }}
          />
        </label>
        <button type="button" class="chip" onclick={today}>I dag</button>
      </div>
    </div>
    <p class="rule note">Allt nedan bygger bara på värden som var kända den dagen. Senare kunskap syns bara där det står ”i dag”.</p>
  </section>
{:else}
  <div class="bar off">
    <button bind:this={opener} type="button" class="chip" onclick={start}>Tidsresa: vad visste vi den …?</button>
  </div>
{/if}

<style>
  .bar {
    margin: 12px 0 0;
  }
  .off {
    display: flex;
    justify-content: flex-end;
  }
  .on {
    background: var(--c-surface);
    border: 1px solid var(--c-ink-2);
    border-radius: var(--radius-lg);
    padding: 10px 14px 8px;
  }
  @media (min-width: 861px) {
    .on {
      position: sticky;
      top: 6px;
      z-index: 20;
    }
  }
  .row {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 6px 14px;
  }
  .when {
    margin: 0;
    display: grid;
    line-height: 1.2;
    min-width: 9.5em;
  }
  .when .k {
    font-size: 12px;
    color: var(--c-ink-2);
  }
  .when strong {
    font-size: 19px;
    font-weight: 680;
    font-variant-numeric: tabular-nums;
  }
  .slider {
    flex: 1 1 220px;
    min-width: 0;
    accent-color: var(--c-ink);
    min-height: var(--hit);
  }
  .btns {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }
  .chip:disabled {
    opacity: 0.5;
    cursor: default;
  }
  .date input {
    font: inherit;
    font-size: var(--fs-small);
    min-height: var(--hit);
    border: 1px solid var(--c-ring);
    border-radius: var(--radius-md);
    background: var(--c-surface);
    color: var(--c-ink);
    padding: 2px 8px;
  }
  .rule {
    margin: 4px 0 0;
  }
</style>
