import { render, within } from '@testing-library/svelte';
import { describe, expect, it } from 'vitest';
import UnitBoxes from './UnitBoxes.svelte';
import WithheldBoxes from './WithheldBoxes.svelte';
import DeadbandGauge from './DeadbandGauge.svelte';
import Minimap from './Minimap.svelte';

describe('UnitBoxes', () => {
  it('one box per series with glyph and word; withheld boxes have no direction', () => {
    const { container } = render(UnitBoxes, {
      label: 'test',
      items: [
        { key: 'a', label: 'A', direction: 1 },
        { key: 'b', label: 'B', direction: -1 },
        { key: 'c', label: 'C', direction: null },
        { key: 'd', label: 'D', direction: 1, counted: false }
      ],
      withheld: [{ key: 'w', label: 'W' }],
      withheldAnon: 1,
      href: (k: string) => `#s-${k}`
    });
    const w = within(container);
    expect(w.getByRole('link', { name: 'A: ökar takten' }).getAttribute('href')).toBe('#s-a');
    expect(w.getByRole('link', { name: 'B: minskar takten' })).toBeTruthy();
    // not counted: no direction colour or glyph even if the pipeline describes one
    expect(w.getByRole('link', { name: 'D: räknas inte' }).classList.contains('nodir')).toBe(true);
    const held = container.querySelectorAll('.held');
    expect(held).toHaveLength(2);
    for (const h of held) {
      expect(h.textContent?.trim()).toBe('');
      expect(h.getAttribute('aria-label')).toContain('riktningen visas inte');
      expect(h.getAttribute('aria-label')).not.toMatch(/ökar|minskar|oförändrad/);
    }
  });
});

describe('WithheldBoxes', () => {
  it('shows name, source, reason and counted flag, never a number', () => {
    const { container } = render(WithheldBoxes, {
      items: [{ key: 'x', label: 'Serie X', source: 'Källa', license: 'inte kontrollerad', why: 'licensen är inte kontrollerad', counted: true }]
    });
    expect(container.textContent).toContain('Serie X');
    expect(container.textContent).toContain('räknas i grenens index');
    expect(container.textContent).not.toMatch(/\d/);
  });
});

describe('DeadbandGauge', () => {
  it('places the dot right of zero for more pace, and flips doubling times', () => {
    const a = render(DeadbandGauge, { change: 4, deadband: 2, direction: 1 });
    expect(parseFloat((a.container.querySelector('.dot') as HTMLElement).style.left)).toBeGreaterThan(50);
    a.unmount();
    const b = render(DeadbandGauge, { change: 4, deadband: 2, direction: -1, inverted: true });
    expect(parseFloat((b.container.querySelector('.dot') as HTMLElement).style.left)).toBeLessThan(50);
  });
});

describe('Minimap', () => {
  it('nine boxes in fixed order, the current lead marked', () => {
    const leads = Array.from({ length: 9 }, (_, i) => ({
      code: `L${i + 1}`,
      name: `Led ${i + 1}`,
      short: [`Led ${i + 1}`],
      branches: [{ code: `G${i + 1}`, name: 'g', state: 'stabil' as const, index: 0.5 }]
    }));
    const { container } = render(Minimap, { leads, current: ['L6'] });
    const links = within(container).getAllByRole('link');
    expect(links).toHaveLength(9);
    expect(links[5].getAttribute('aria-current')).toBe('page');
    expect(links.filter((l) => l.hasAttribute('aria-current'))).toHaveLength(1);
  });
});
