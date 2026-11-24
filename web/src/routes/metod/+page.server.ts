// Explorable method page (track W11). The server load reads method.json, the nine branch documents, one nowcast's
// backtest calibration and one revised series, and hands the page only the compact inputs its figures need.
import { BRANCH_CODES, type Nowcast } from '$lib/data';
import { bundle } from '$lib/server/bundle';
import type { SeriesDoc } from '$lib/series/types';
import { defaultBranch, exploreBranchOf, leakageRows, mostRevisedPeriod, pickRevised, revisedCandidates, rulesOf, slicePeriods, sourceView, type BranchInput } from '$lib/method/prepare';
import { roles } from '../prognoser/parts/model';

/** The as_of figure shows the periods from this many years before the series' last known day. */
const ASOF_YEARS = 5;

export async function load() {
  const b = bundle();
  const [method, idx, manifest] = await Promise.all([b.method(), b.seriesIndex(), b.manifest()]);
  const m = method as Record<string, unknown> & {
    record: { status: string; label: string; date: string; month: string; recon_label?: string };
    register: { file: string; sha256: string | null };
    sources: Parameters<typeof sourceView>[0][];
    nowcasts: { id: string; title: string; variants: { id: string; text: string }[] }[];
    n_series: number;
    n_published: number;
    n_withheld: number;
    interval_levels: string[];
  };
  const branches = await Promise.all(BRANCH_CODES.map(async (c) => exploreBranchOf((await b.branch(c)) as unknown as BranchInput)));

  // The calibration example: N2 (the monthly target with the longest backtest), else the first with a backtest.
  const ids = ['n2', 'n1', 'n3', 'n4', 'n5', 'n6'];
  let calib: { id: string; title: string; label: string; cal: Nowcast['backtest_calibration']; roles: ReturnType<typeof roles> } | null = null;
  for (const id of ids) {
    let nc: Nowcast;
    try {
      nc = await b.nowcast(id);
    } catch {
      continue;
    }
    if (nc.backtest_calibration?.available && (nc.backtest_calibration.rows ?? []).length) {
      calib = { id, title: nc.title ?? id, label: nc.label ?? id.toUpperCase(), cal: nc.backtest_calibration, roles: roles(nc) };
      break;
    }
  }

  // The as_of example: a revised monthly series with a stable base, its last five years of periods.
  const cands = await Promise.all(revisedCandidates(idx.series).map(async (k) => (await b.series(k)) as unknown as SeriesDoc));
  const doc = pickRevised(cands);
  let asof = null;
  if (doc?.versions) {
    const y = Number(doc.versions.last_known.slice(0, 4)) - ASOF_YEARS;
    const v = slicePeriods(doc.versions, `${y}-01`);
    asof = {
      key: doc.key,
      label: doc.label,
      unit: doc.unit ?? '',
      lag_days: doc.lag_days ?? null,
      license: doc.license?.short ?? '',
      source: doc.source ?? '',
      versions: v,
      period: mostRevisedPeriod(v),
      leakage: leakageRows(doc.measure_history, doc.measure_path),
      pace_unit: doc.measure?.pace_unit ?? ''
    };
  }

  const man = manifest as unknown as { repo?: string; git_sha?: string };
  const repo = typeof man.repo === 'string' && /^https:\/\/github\.com\/[\w.-]+\/[\w.-]+$/.test(man.repo) ? man.repo : null;
  const ref = man.git_sha && /^[0-9a-f]{7,40}$/.test(man.git_sha) ? man.git_sha : 'main';
  return {
    registerHref: repo ? `${repo}/blob/${ref}/${m.register.file}` : null,
    linkable: idx.series.map((s) => s.key).filter((k) => branches.some((x) => x.series.some((s) => s.key === k))),
    record: { status: m.record.status, label: m.record.label, date: m.record.date, month: m.record.month },
    register: m.register,
    rules: rulesOf(m),
    branches,
    initial: defaultBranch(branches),
    calib,
    asof,
    nowcasts: m.nowcasts.map((n) => ({ id: n.id, title: n.title })),
    sources: m.sources.map(sourceView),
    counts: { n_series: m.n_series, n_published: m.n_published, n_withheld: m.n_withheld }
  };
}
