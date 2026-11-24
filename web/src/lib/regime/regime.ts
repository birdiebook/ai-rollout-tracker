// Pure helpers for the regime page (track W10). P(inbromsning), the reported state, shifts and breaks come from
// regime.json (the pipeline); the rule thresholds are registered constants (rules.json), because regime.json does
// not carry them. Nothing here re-estimates or re-applies a rule.
import { dateLabel, fmt, periodLabel } from '$lib/design';
import rulesJson from './rules.json';
import { monthRange } from './holdout';
import type { RegimeLane } from './types';

export const RULES = {
  shiftAtLeast: rulesJson.shift_at_least,
  backAtMost: rulesJson.back_at_most,
  inARow: rulesJson.months_in_a_row,
  breakAtLeast: rulesJson.break_at_least,
  runLength: rulesJson.break_run_length_at_most,
  hazard: rulesJson.hazard,
  firstLive: rulesJson.first_live
} as const;

/** 0,83 -> "83 %" */
export const pctText = (p: number | null) => (p === null ? '–' : `${fmt(p * 100, 0)} %`);
export const pText = (p: number | null) => (p === null ? '–' : fmt(p, 2));

/** Which side of the registered thresholds a probability is on (descriptive: the rule needs two months in a row). */
export function zone(p: number | null): 'slow' | 'back' | 'between' | null {
  if (p === null) return null;
  if (p >= RULES.shiftAtLeast) return 'slow';
  if (p <= RULES.backAtMost) return 'back';
  return 'between';
}

/** The timeline's months: from the first live month for at least twelve months (the months to come stay empty). */
export function timelineMonths(months: string[], firstLiveDate: string, minMonths = 12): string[] {
  const first = months[0] ?? firstLiveDate.slice(0, 7);
  const lastData = months.at(-1) ?? first;
  const [y, m] = first.split('-').map(Number);
  const end = new Date(Date.UTC(y, m - 1 + minMonths - 1, 1)).toISOString().slice(0, 7);
  return monthRange(first, lastData > end ? lastData : end);
}

export const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);
const stateWord = (s: string | null) => (s === 'inbromsning' ? 'inbromsning' : s === 'expansion' ? 'expansion' : 'inget tillstånd');

export function laneSentence(l: RegimeLane): string {
  const x = l.latest;
  if (!x || x.p === null) return `${cap(l.label)}: ingen sannolikhet${x?.reason ? ` (${x.reason})` : ''}.`;
  const z = zone(x.p);
  const where =
    z === 'slow'
      ? `på eller över ${fmt(RULES.shiftAtLeast, 1)}`
      : z === 'back'
        ? `på eller under ${fmt(RULES.backAtMost, 1)}`
        : `mellan ${fmt(RULES.backAtMost, 1)} och ${fmt(RULES.shiftAtLeast, 1)}`;
  const shift = x.shift ? ` Tillståndet byttes till ${x.shift} denna månad.` : '';
  return `${cap(l.label)} ${periodLabel(x.month)}: P(inbromsning) ${pText(x.p)}, ${where}. Rapporterat tillstånd: ${stateWord(x.state)}.${shift}`;
}

export function headline(available: boolean, lanes: RegimeLane[], firstLive: string): string {
  if (!available || !lanes.length) return `Regimen följs skarpt från den första ögonblicksbilden ${dateLabel(firstLive)}. Ännu finns ingen skarp månad.`;
  return lanes.map((l) => `${cap(l.label)}: ${stateWord(l.latest?.state ?? null)} (P(inbromsning) ${pctText(l.latest?.p ?? null)})`).join('. ') + '.';
}

export function breaksSentence(n: number, nWithheld: number, months: number): string {
  if (!months) return 'Inga skarpa månader än, och därför inga rapporterade strukturbrott.';
  const total = n + nWithheld;
  if (!total) return `Inga strukturbrott rapporterade på ${months} skarpa ${months === 1 ? 'månad' : 'månader'}.`;
  const held = nWithheld ? `, varav ${nWithheld} på ${nWithheld === 1 ? 'en inhållen serie' : 'inhållna serier'} (räknas, visas utan namn och värde)` : '';
  return `${total} strukturbrott på ${months} skarpa ${months === 1 ? 'månad' : 'månader'}${held}.`;
}
