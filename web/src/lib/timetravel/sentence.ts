// The sentences of the start page on a past day, generated from the cut record exactly as Python writes them for
// the bundle (site_bundle.export.headline). The golden test compares them with Python's replay on each probe day.
import type { OverviewOn } from './gate';

const sv = (n: number) => (n === 0 ? 'ingen' : n === 1 ? 'en' : String(n));

export function headlineSentence(o: Pick<OverviewOn, 'counts'>): string {
  const c = o.counts;
  const acc = c['accelererar'] ?? 0;
  const stb = c['stabil'] ?? 0;
  const brk = c['bromsar in'] ?? 0;
  return `Av ${acc + stb + brk} grenar med tillstånd: ${sv(acc)} accelererar, ${sv(stb)} ${stb === 1 ? 'är stabil' : 'är stabila'} och ${sv(brk)} bromsar in.`;
}

export function changeSentence(o: Pick<OverviewOn, 'branches'>): string {
  const ch = o.branches.filter((b) => b.previous && b.state_changed);
  if (!ch.length) return 'Inget tillstånd har ändrats sedan förra månaden.';
  return 'Sedan förra månaden: ' + ch.map((b) => `${b.code} ${b.previous!.state} → ${b.state}`).join('; ') + '.';
}
