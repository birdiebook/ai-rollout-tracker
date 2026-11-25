// R-W2 P1: the DOM budget of scripts/budget.mjs counts elements in the prerendered HTML.
import { describe, expect, it } from 'vitest';
import { countElements } from '../../../scripts/count-elements.mjs';

describe('countElements (budget.mjs)', () => {
  it('counts start tags, not scripts, styles or comments', () => {
    const html = '<!doctype html><html><head><style>a<b{}</style><script>if (a<b) x("<div>")</script></head><body><!-- <p> --><div><svg><rect/></svg><p>x</p></div></body></html>';
    expect(countElements(html)).toBe(9); // html head style script body div svg rect p
  });
});
