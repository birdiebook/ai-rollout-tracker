import { bundle } from '$lib/server/bundle';

export async function load() {
  const b = bundle();
  const ov = await b.overview();
  const nowcasts = await Promise.all(ov.calendar.filter((c) => c.id !== 'd2').map((c) => b.nowcast(c.id)));
  return { calendar: ov.calendar, nowcasts };
}
