// The pre-paint check (W9, tightened by R-W1): before the first paint, a URL whose hash will make the store travel
// hides today's content. It must use the SAME parser as readAsOf (URLSearchParams + a real calendar day), or a hash
// like "#as%5Fof=2024-06-30" travels after hydration but paints today's content first. The function is the test
// oracle; PREPAINT_SCRIPT is the same logic as an inline script string (no imports run before hydration).
/** True when the inline head script hides today's content for this hash (must equal readAsOf(hash) !== null). */
export function hidesBeforePaint(hash: string): boolean {
  // the exact code that runs in <head>, run against a stub location/document
  return new Function('location', 'document', PREPAINT_BODY)({ hash }, { documentElement: { setAttribute() {} } }) === true;
}

/** Body of the inline script: returns true when it set html[data-tt]. Kept in sync with url.ts readAsOf/isDay. */
const PREPAINT_BODY =
  "try{var v=new URLSearchParams(location.hash.replace(/^#/,'')).get('as_of');" +
  "if(v&&/^\\d{4}-\\d{2}-\\d{2}$/.test(v)&&new Date(v+'T00:00:00Z').toISOString().slice(0,10)===v)" +
  "{document.documentElement.setAttribute('data-tt','');return true}}catch(e){}return false";

export const PREPAINT_SCRIPT = `<script>(function(){${PREPAINT_BODY}})()<\/script>`;
