// Server-side (prerender) loading of the monthly story (W13): the typed loaders only, then the pure model, which
// cuts every figure through the time-travel boundary.
import { bundle } from '$lib/server/bundle';
import type { Branch } from '$lib/data';
import { storyPage } from './model';

export async function storyMonths(): Promise<string[]> {
  const idx = await bundle().storyIndex();
  return idx.months.map((m) => m.month);
}

export async function loadStory(month: string) {
  const b = bundle();
  const [story, index, overview, regime] = await Promise.all([b.story(month), b.storyIndex(), b.overview(), b.regime()]);
  const codes = [...new Set(story.cards.filter((c) => c.type === 'K1').map((c) => String(c.facts.branch)))];
  const branches: Record<string, Branch> = {};
  for (const code of codes) branches[code] = await b.branch(code);
  return storyPage({ story, index, overview, regime, branches });
}
