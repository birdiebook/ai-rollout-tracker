import { fireEvent, render, screen } from '@testing-library/svelte';
import { describe, expect, it } from 'vitest';
import ChartHarness from '../test/ChartHarness.svelte';
import Glyph from './Glyph.svelte';
import StatusBadge from './StatusBadge.svelte';
import DataTable from './DataTable.svelte';

describe('Glyph', () => {
  it('shows colour + glyph + word; glyph is hidden from screen readers', () => {
    const { container } = render(Glyph, { state: 'accelererar' });
    expect(container.textContent).toContain('▲');
    expect(container.textContent).toContain('accelererar');
    expect(container.querySelector('.glyph')?.getAttribute('aria-hidden')).toBe('true');
    expect((container.querySelector('.glyph') as HTMLElement).style.color).toContain('--c-acc');
  });
  it('keeps the word for screen readers when hidden visually', () => {
    const { container } = render(Glyph, { direction: -1, word: false });
    expect(container.querySelector('.visually-hidden')?.textContent).toBe('minskar takten');
  });
  it('falls back to "för få serier" for unknown states', () => {
    const { container } = render(Glyph, { state: 'okänt' });
    expect(container.textContent).toContain('○');
  });
});

describe('StatusBadge', () => {
  it('labels reconstructed history dashed and live snapshots solid', () => {
    const r = render(StatusBadge, { status: 'recon' });
    expect(r.container.textContent).toContain('rekonstruerad');
    expect(r.container.querySelector('.live')).toBeNull();
    r.unmount();
    const l = render(StatusBadge, { status: 'live' });
    expect(l.container.querySelector('.live')).not.toBeNull();
  });
});

describe('DataTable', () => {
  it('renders a header row and row headers', () => {
    render(DataTable, { table: { columns: [{ key: 'a', label: 'A' }, { key: 'b', label: 'B' }], rows: [{ a: 'x', b: '1' }] } });
    expect(screen.getAllByRole('columnheader')).toHaveLength(2);
    expect(screen.getByRole('rowheader').textContent).toBe('x');
  });
});

describe('ChartFrame with primitives', () => {
  it('names the SVG by title and sentence; a small table is prerendered in a native <details> (R-W2 B1)', () => {
    const { container } = render(ChartHarness, { dots: [] });
    const svg = container.querySelector('svg[role="img"]')!;
    expect(svg.getAttribute('aria-labelledby')).toBe('t-title t-desc');
    expect(container.querySelector('#t-desc')?.textContent).toBe('Testmening.');
    const details = container.querySelector('details.tbl') as HTMLDetailsElement;
    expect(details.open).toBe(false);
    expect(details.querySelector('summary')?.textContent?.replace(/\s+/g, ' ').trim()).toBe('Tabell (3 rader)');
    // prerendered: the rows are in the DOM before the <details> is opened, so they open without JavaScript
    expect(container.querySelectorAll('#t-table tbody tr')).toHaveLength(3);
    expect(container.querySelector('#t-table')?.hasAttribute('data-pre')).toBe(true);
    expect(container.querySelector('#t-chart')?.hasAttribute('hidden')).toBe(false);
    expect(container.textContent).toContain('Källa: test');
  });
  it('draws a large table only when it is opened, and links the data (R-W2 P1)', async () => {
    const { container } = render(ChartHarness, { dots: [], nRows: 40, dataHref: '/x/data/series/a.json' });
    const details = container.querySelector('details.tbl') as HTMLDetailsElement;
    expect(container.querySelector('#t-table')?.hasAttribute('data-pre')).toBe(false);
    expect(container.querySelectorAll('#t-table tr')).toHaveLength(0);
    expect(container.querySelector('#t-table .nojs')?.textContent).toContain('40 rader');
    expect(container.querySelector('#t-table a')?.getAttribute('href')).toBe('/x/data/series/a.json');
    details.open = true;
    await fireEvent(details, new Event('toggle'));
    expect(container.querySelectorAll('#t-table tbody tr')).toHaveLength(40);
    details.open = false;
    await fireEvent(details, new Event('toggle'));
    expect(container.querySelectorAll('#t-table tbody tr')).toHaveLength(40); // kept once drawn
  });
  it('draws axis ticks, band levels widest first, a line with end dot and label', () => {
    const { container } = render(ChartHarness, { dots: [] });
    expect(container.querySelectorAll('.axis-left text')).toHaveLength(3);
    expect(container.querySelectorAll('.axis-bottom text')).toHaveLength(3);
    const levels = [...container.querySelectorAll('.band path[data-level]')].map((p) => p.getAttribute('data-level'));
    expect(levels).toEqual(['80', '50']);
    expect(container.querySelector('path.line')?.getAttribute('d')).toMatch(/^M/);
    expect([...container.querySelectorAll('text')].some((t) => t.textContent === '3')).toBe(true);
  });
  it('draws one dot per quantile and counts dots under the outcome', () => {
    const dots = Array.from({ length: 20 }, (_, i) => i / 2);
    const { container } = render(ChartHarness, { dots, outcome: 5.2 });
    expect(container.querySelectorAll('.qdots circle')).toHaveLength(20);
    expect(container.querySelector('.qdots text')?.textContent).toContain('11 av 20 under');
  });
  it('fills stripe cells from the diverging scale and leaves missing ones empty', () => {
    const { container } = render(ChartHarness, { dots: [] });
    const cells = container.querySelectorAll('rect.cell');
    expect((cells[0] as SVGElement).style.fill).toContain('color-mix');
    expect(cells[1].getAttribute('stroke')).toBe('var(--c-grid)');
  });
  it('shows a text tooltip on pointer enter', async () => {
    const { container } = render(ChartHarness, { dots: [] });
    await fireEvent.pointerEnter(container.querySelector('rect.cell')!, { clientX: 5, clientY: 5 });
    expect(container.querySelector('.tip')?.textContent).toContain('Cell');
  });
});
