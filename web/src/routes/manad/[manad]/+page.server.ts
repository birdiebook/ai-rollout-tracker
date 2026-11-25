// /manad/[manad] (W13): the monthly story. One page per month of the record, prerendered from story/<YYYY-MM>.json;
// every figure is cut to the month's known day by the time-travel boundary ($lib/story/model.ts).
import { error } from '@sveltejs/kit';
import { loadStory, storyMonths } from '$lib/story/load.server';

export async function entries() {
  return (await storyMonths()).map((manad) => ({ manad }));
}

export async function load({ params }) {
  if (!(await storyMonths()).includes(params.manad)) error(404, `Ingen berättelse för ${params.manad}`);
  return { page: await loadStory(params.manad) };
}
