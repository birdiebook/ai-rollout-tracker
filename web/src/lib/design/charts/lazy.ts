// R-W2 P1: deferred drawing of chart bodies. On the server ChartFrame renders the chart's SVG body to a string, and
// on the client the initial hydration only claims that markup ({@html}) instead of walking every mark. Each chart
// is then drawn live in its own task, visible charts first, so the blocking time after the first paint is split into
// short tasks instead of one long hydration task. The prerendered markup is what the live drawing would produce at
// the default width, so nothing is missing before a chart is live; only hover tips and the redraw at the measured
// width wait. A chart is drawn at once when its sentence or table changes (a slider, a view in the URL) or the pointer
// enters it, and the first key press draws every remaining chart before the browser moves focus. Pointer and focus
// events do not: replacing the markup under a pressed link would swallow the click.
import { flushSync } from 'svelte';

let initial = typeof window !== 'undefined';
type Job = { el: Element; run: () => void; after?: () => void; visible: boolean; done: boolean };
const queue: Job[] = [];
let io: IntersectionObserver | null = null;
let pumping = false;
let listening = false;

/** True while the page's first hydration runs (only then is there server markup to claim). */
export function claimingServerMarkup(): boolean {
  return initial;
}

/** Called once by the root layout after the first hydration: from now on charts are drawn directly. */
export function hydrationDone(): void {
  initial = false;
  if (!listening) {
    listening = true;
    addEventListener('keydown', drainAll, { capture: true, passive: true });
  }
  pump();
}

function run(j: Job) {
  if (j.done) return;
  j.done = true;
  io?.unobserve(j.el);
  flushSync(j.run);
  j.after?.();
}

function drainAll() {
  while (queue.length) run(queue.shift()!);
}

function pump() {
  if (pumping || initial) return;
  pumping = true;
  const step = () => {
    const i = queue.findIndex((j) => j.visible);
    const j = queue.splice(i >= 0 ? i : 0, 1)[0];
    if (j) run(j);
    if (queue.length) setTimeout(step, 0);
    else pumping = false;
  };
  setTimeout(step, 0);
}

/** Queue a chart to be drawn live. `now()` draws it at once with a synchronous flush (event handlers only), and
 *  `cancel()` takes it off the queue when the caller sets its state itself (inside an effect, where a flush is not
 *  allowed). `after` runs once the live DOM is in place. */
export function enqueue(el: Element, draw: () => void, after?: () => void): { now: () => void; cancel: () => void } {
  const job: Job = { el, run: draw, after, visible: false, done: false };
  queue.push(job);
  if (typeof IntersectionObserver !== 'undefined') {
    io ??= new IntersectionObserver(
      (entries) => {
        for (const e of entries) {
          const j = queue.find((q) => q.el === e.target);
          if (j) j.visible = e.isIntersecting;
        }
      },
      { rootMargin: '200px 0px' }
    );
    io.observe(el);
  }
  pump();
  const remove = () => {
    const k = queue.indexOf(job);
    if (k >= 0) queue.splice(k, 1);
  };
  return {
    now: () => {
      remove();
      run(job);
    },
    cancel: () => {
      remove();
      job.done = true;
      io?.unobserve(el);
    }
  };
}

/** Server markup of a chart body for {@html}: hydration comments removed (the markup is never hydrated, and an empty
 *  comment would end the {@html} block early). */
export const staticMarkup = (html: string): string => html.replace(/<!--[\s\S]*?-->/g, '');

/** Draw a deferred block now, outside the queue (Deferred.svelte in static mode). */
export function drawOnce(draw: () => void, after?: () => void): void {
  flushSync(draw);
  after?.();
}
