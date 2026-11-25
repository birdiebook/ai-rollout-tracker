// Monthly story (W13): the view model. The cards and their texts come from story/<YYYY-MM>.json, selected in Python
// by the rule pre-registered in docs/mattregister.md (2026-11-25). This file only attaches one figure per card and
// the links. Every figure is cut to the month's known day through the time-travel boundary ($lib/timetravel/gate),
// and the assembled page is checked with leaks() before it is returned: nothing known after the month's snapshot.
import type { Branch, Overview, Regime, Story, StoryCard, StoryIndex, StoryLink, StoryTrack } from '$lib/data';
import type { LiveRow } from '../../routes/prognoser/parts/model';
import type { RegimeLane } from '$lib/regime/types';
import { LeakError, branchOn, cutHistory, cutStripes, leaks, monthKnown, type HistoryRow, type StripesOn } from '$lib/timetravel/gate';

/** Months of history drawn in the stripes and index figures. */
export const FIGURE_MONTHS = 24;

export type Figure =
  | { kind: 'stripes'; stripes: StripesOn; highlight: string | null }
  | { kind: 'index'; code: string; name: string; history: (HistoryRow & { known: string })[] }
  | { kind: 'meter'; lane: RegimeLane }
  | { kind: 'forecast'; row: LiveRow; unit: string; decimals: number }
  | { kind: 'track'; track: StoryTrack; month: string; direction: -1 | 0 | 1 | null; unit: string | null }
  | { kind: 'none'; why: string };

export interface CardView extends StoryCard {
  figure: Figure;
  /** the link target as a route and its as_of (time-travel views get the month's known day) */
  target: { route: string; params: Record<string, string>; asOf: string | null };
}

export interface MonthNav {
  month: string;
  month_sv: string;
  kind: string;
  known: string;
  n_events: number;
}

export interface StoryPage {
  day: string;
  story: Story;
  cards: CardView[];
  months: MonthNav[];
  prev: MonthNav | null;
  next: MonthNav | null;
}

const tail = <T>(xs: T[], n: number) => xs.slice(Math.max(0, xs.length - n));

export function target(link: StoryLink, day: string): CardView['target'] {
  switch (link.kind) {
    case 'branch':
      return { route: '/gren/[id]', params: { id: link.id ?? '' }, asOf: day };
    case 'series':
      return { route: '/serie/[key]', params: { key: link.id ?? '' }, asOf: day };
    case 'nowcast':
      return { route: '/prognoser/[id]/[[slug]]', params: { id: link.id ?? '', ...(link.slug ? { slug: link.slug } : {}) }, asOf: null };
    case 'regime':
      return { route: '/regim', params: {}, asOf: null };
    case 'method':
      return { route: '/metod', params: {}, asOf: null };
    default:
      return { route: '/', params: {}, asOf: day };
  }
}

function forecastRow(f: Record<string, any>): LiveRow {
  const iv = (f.intervals ?? {}) as LiveRow['intervals'];
  const inside: LiveRow['inside'] = {};
  for (const l of ['50', '80', '95'] as const) {
    const p = iv[l];
    if (p && p[0] !== null && p[1] !== null && f.outcome !== null) inside[l] = f.outcome >= Math.min(p[0], p[1]) && f.outcome <= Math.max(p[0], p[1]);
  }
  return {
    slug: f.slug ?? '',
    period: f.period,
    origin: f.origin ?? null,
    file: f.file ?? '',
    value: f.forecast ?? null,
    intervals: iv,
    variants: {},
    champion: f.champion,
    score: null,
    scored: true,
    status: 'utfall',
    outcome: f.outcome ?? null,
    outcomeKnown: f.known_from ?? null,
    err: f.err_champion ?? null,
    inside,
    pit: null,
    crps: null,
    // the story card links the forecast's own page, which shows its commit (RW1-X 4a)
    commit: null,
    verified: false
  };
}

export interface Docs {
  story: Story;
  index: StoryIndex;
  overview: Overview;
  regime: Regime;
  branches: Record<string, Branch>;
}

/** The page of one month: cards with figures, cut to the month's known day by the gate. Throws LeakError when
 *  anything on the page was known later. */
export function storyPage(d: Docs): StoryPage {
  const { story, index, overview, regime } = d;
  const day = monthKnown(story.month, overview.record);
  if (story.known > day) throw new LeakError([`story ${story.month}: known ${story.known} > ${day}`]);
  const stripes = cutStripes(overview.stripes, day, overview.record);
  const short: StripesOn = {
    ...stripes,
    months: tail(stripes.months, FIGURE_MONTHS),
    known: tail(stripes.known, FIGURE_MONTHS),
    kind: tail(stripes.kind, FIGURE_MONTHS),
    rows: stripes.rows.map((r) => ({ ...r, index: tail(r.index, FIGURE_MONTHS), state: tail(r.state, FIGURE_MONTHS), n_series: tail(r.n_series, FIGURE_MONTHS) }))
  };
  const cards: CardView[] = story.cards.map((c) => {
    let figure: Figure;
    const f = c.facts;
    if (c.type === 'K0' || c.type === 'K9') figure = { kind: 'stripes', stripes: short, highlight: story.month };
    else if (c.type === 'K1') {
      const doc = d.branches[f.branch];
      const history = doc ? tail(branchOn(doc as Branch & { history?: HistoryRow[] }, day).history, FIGURE_MONTHS) : [];
      figure = history.length ? { kind: 'index', code: f.branch, name: f.name, history } : { kind: 'none', why: 'Grenens historik saknas i paketet.' };
    } else if (c.type === 'K2') {
      const block = regime.blocks.find((b) => b.block === f.block);
      const hist = block ? cutHistory(block.history, day, regime.record) : [];
      const last = hist.at(-1);
      figure = last
        ? {
            kind: 'meter',
            lane: {
              block: f.block,
              label: f.label,
              history: hist.map((h) => ({ month: h.month, p: h.p_slow ?? null, state: h.state, shift: h.shift, reason: h.reason ?? '' })),
              latest: { month: last.month, p: last.p_slow ?? null, state: last.state, shift: last.shift, n_months: last.n_months ?? null, reason: last.reason ?? '' }
            }
          }
        : { kind: 'none', why: 'C4-sektionen saknas för månaden.' };
    } else if (c.type === 'K3') figure = { kind: 'forecast', row: forecastRow(f), unit: f.unit ?? '', decimals: f.decimals ?? 0 };
    else if (c.track && c.track.months.length) figure = { kind: 'track', track: c.track, month: story.month, direction: c.type === 'K6' ? null : c.direction, unit: f.pace_unit ?? null }; // K6: no direction in an index (R-W3), drawn in ink
    else figure = { kind: 'none', why: 'Ingen historik i posten för serien.' };
    return { ...c, figure, target: target(c.link, day) };
  });
  const months: MonthNav[] = index.months.map((m) => ({ month: m.month, month_sv: m.month_sv, kind: m.kind, known: m.known, n_events: m.n_events }));
  const i = months.findIndex((m) => m.month === story.month);
  const page: StoryPage = { day, story, cards, months, prev: i > 0 ? months[i - 1] : null, next: i >= 0 && i < months.length - 1 ? months[i + 1] : null };
  // the month navigation may name later months (it is navigation, not knowledge); everything else must be known
  const bad = leaks({ ...page, months: [], next: null }, day);
  if (bad.length) throw new LeakError(bad);
  return page;
}

/** Time travel on day D: the months whose story was known on D (the index, cut by the gate's monthKnown). */
export function monthsKnownOn(months: MonthNav[], day: string): MonthNav[] {
  return months.filter((m) => m.known <= day);
}

export const typeGlyph: Record<string, string> = { K0: '◆', K1: '⇄', K2: '◐', K3: '◎', K4: '┆', K5: '◉', K6: '⚖', K9: '○' };
