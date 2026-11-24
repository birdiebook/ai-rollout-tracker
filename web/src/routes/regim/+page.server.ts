// Regime and structural breaks (track W10): C4 from regime.json, which holds only the committed live snapshots
// (never reconstructed). The thresholds are registered constants ($lib/regime/rules.json), not in the bundle.
import { regime } from '$lib/regime/load.server';
import { RULES } from '$lib/regime/regime';

export async function load() {
  const r = await regime();
  const firstLive = r.record.first_live_date ?? RULES.firstLive;
  return { ...r, firstLive, isLive: r.available && r.record.status === 'live' };
}
