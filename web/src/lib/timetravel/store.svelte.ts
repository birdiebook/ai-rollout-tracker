// The global time-travel state. The URL hash (`as_of=`) is the only source of truth: the store reads it on mount,
// on hashchange and after every navigation, and writes it with SvelteKit's replaceState (no history entry per
// slider step). `max` is the bundle's build day: travelling later than that shows today's knowledge, so it is
// clamped.
import { replaceState } from '$app/navigation';
import { clampDay, readAsOf, withAsOf } from './url';

/** Earliest day of the slider (series histories reach back to the 2010s; the state history starts later). */
export const MIN_DAY = '2015-01-01';

class TimeTravel {
  /** as_of from the URL, or null (today) */
  day = $state<string | null>(null);
  max = $state(new Date().toISOString().slice(0, 10));
  playing = $state(false);
  get active() {
    return this.day !== null;
  }
  /** the day every view is cut at */
  get effective(): string {
    return clampDay(this.day ?? this.max, MIN_DAY, this.max);
  }
  read() {
    this.day = typeof location === 'undefined' ? null : readAsOf(location.hash);
  }
  set(day: string | null) {
    const d = day === null ? null : clampDay(day, MIN_DAY, this.max);
    const h = withAsOf(location.hash, d);
    if (h !== location.hash && !(h === '' && location.hash === '')) {
      try {
        replaceState(location.pathname + location.search + h, {});
      } catch {
        history.replaceState(history.state, '', location.pathname + location.search + h);
      }
    }
    this.day = d;
    if (d === null) this.playing = false;
  }
}

export const tt = new TimeTravel();
