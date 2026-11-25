// W13: hrefs of the story's links. Time-travel-capable views (start, branch, series) open at the month's known day
// (as_of in the hash, the global key of $lib/timetravel); the forecast, regime and method pages have no time travel
// and open as today.
import { resolve } from '$app/paths';
import type { CardView } from './model';

export function cardHref(t: CardView['target']): string {
  let path: string;
  switch (t.route) {
    case '/gren/[id]':
      path = resolve('/gren/[id]', { id: t.params.id });
      break;
    case '/serie/[key]':
      path = resolve('/serie/[key]', { key: t.params.key });
      break;
    case '/prognoser/[id]/[[slug]]':
      path = t.params.slug ? resolve('/prognoser/[id]/[[slug]]', { id: t.params.id, slug: t.params.slug }) : resolve('/prognoser/[id]/[[slug]]', { id: t.params.id });
      break;
    case '/regim':
      path = resolve('/regim');
      break;
    case '/metod':
      path = resolve('/metod');
      break;
    default:
      path = resolve('/');
  }
  return t.asOf ? `${path}#as_of=${t.asOf}` : path;
}

export const monthHref = (month: string) => resolve('/manad/[manad]', { manad: month });
