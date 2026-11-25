// What the C4 holdout showed (opened once, 2026-11-24; never rerun). The numbers are copied from the committed
// result document, because regime.json carries only the live months. Source: docs/resultat/holdout_c3_c4.md,
// run log experiments/runs/20261124T082422Z_holdout_c3_c4.csv, spec docs/steg2/c4_spec.md (c4-v1, 735dc64),
// log docs/holdout_logg.md. Proposed lift (W10 report): export this block from Python into regime.json.
// Exact per-month probabilities are not in the document, so only the reported states (which are exact) are drawn.

export const HOLDOUT = {
  opened: '2026-11-24',
  spec: 'c4-v1',
  spec_commit: '735dc64',
  doc: 'docs/resultat/holdout_c3_c4.md',
  run_log: 'experiments/runs/20261124T082422Z_holdout_c3_c4.csv',
  first: '2025-07',
  last: '2026-10',
  n_days: 16,
  /** reported state per month end (two-months-in-a-row rule), real-time from 2012-01-31 */
  blocks: [
    {
      block: 'capex',
      label: 'capex och leverantörsled',
      slow_months: [] as string[],
      shifts_to_slow: 0,
      shifts_back: 0,
      reclassified: 0.0,
      smoothed_slow: 0,
      note: 'P(inbromsning) 0,45 i juli 2025, sedan 0,03–0,23 och från december 2025 högst 0,011. Hela holdouten rapporteras som expansion.'
    },
    {
      block: 'demand',
      label: 'efterfrågan',
      slow_months: ['2025-07', '2025-08', '2025-09', '2025-10', '2025-11'],
      shifts_to_slow: 0,
      shifts_back: 1,
      shift_back_month: '2025-12',
      reclassified: 0.25,
      smoothed_slow: 1,
      note:
        'P(inbromsning) 1,00 juli–oktober 2025, sedan högst 0,003. Modellen skattades om i november 2025 så att de senaste ' +
        'månaderna hamnade i den högre regimen. Med facit i hand (utjämnat på banan 2026-10-31) är bara en av månaderna inbromsning.'
    }
  ],
  bocpd: {
    series_days: 921,
    n_series: 60,
    per_100: 0.22,
    per_100_dev: 0.29,
    breaks: [
      { date: '2025-10-31', month: '2025-10', branch: 'G4', series: 'rpo_hyp4', latest_period: '2025Q3', p_recent: 0.98 },
      { date: '2026-04-30', month: '2026-04', branch: 'G4', series: 'rev_google_cloud', latest_period: '2026Q1', p_recent: 0.92 }
    ]
  },
  /** Spearman's rho between P(inbromsning) and the champions' absolute errors: information only, no test */
  rho: [
    { target: 'N1 (B1)', block: 'capex', n: 6, rho: -0.43 },
    { target: 'N1 (B1)', block: 'efterfrågan', n: 6, rho: -0.2 },
    { target: 'N2 (B3)', block: 'capex', n: 17, rho: 0.04 },
    { target: 'N2 (B3)', block: 'efterfrågan', n: 17, rho: 0.06 }
  ]
} as const;

/** "2025-07" .. "2026-10" inclusive. */
export function monthRange(from: string, to: string): string[] {
  const out: string[] = [];
  let [y, m] = from.split('-').map(Number);
  const [ty, tm] = to.split('-').map(Number);
  while (y < ty || (y === ty && m <= tm)) {
    out.push(`${y}-${String(m).padStart(2, '0')}`);
    m++;
    if (m > 12) {
      m = 1;
      y++;
    }
  }
  return out;
}
