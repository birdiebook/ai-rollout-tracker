// W8: the forecast overview (N1–N6 and D2). Data only through the site_bundle loaders; trimmed to what the cards show.
import { bundle } from '$lib/server/bundle';

export async function load() {
  const b = bundle();
  const [m, ov, d2] = await Promise.all([b.manifest(), b.overview(), b.horizons()]);
  const nowcasts = await Promise.all(
    ov.calendar
      .filter((c) => c.id !== 'd2')
      .map(async (c) => {
        const n = await b.nowcast(c.id);
        return {
          id: n.id,
          label: n.label,
          title: n.title,
          champion: n.champion,
          decimals: n.decimals ?? 0,
          unit: n.unit ?? '',
          next_origin: n.next_origin,
          next_period: n.next_period,
          history: n.history ?? null,
          forecasts: n.forecasts ?? [],
          scorecard: n.scorecard ?? [],
          origin_rule: n.origin_rule ?? null
        };
      })
  );
  const t = d2.targets.find((x) => x.fan) ?? d2.targets[0] ?? null;
  return {
    today: String(m.today ?? ov.record.date),
    calendar: ov.calendar,
    nowcasts,
    d2: {
      first_live: d2.first_live,
      origin: d2.origin,
      next_origin: d2.next_origin,
      next_period: d2.next_period,
      n_targets: d2.targets.length,
      history: t?.history ?? null,
      unit: t?.unit ?? '',
      label: t?.label ?? ''
    }
  };
}
