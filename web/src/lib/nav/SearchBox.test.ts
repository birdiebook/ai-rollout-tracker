import { cleanup, fireEvent, render } from '@testing-library/svelte';
import { tick } from 'svelte';
import { afterEach, describe, expect, it, vi } from 'vitest';
import SearchBox from './SearchBox.svelte';
import type { SearchItem } from './search';

const items: SearchItem[] = [
  { t: 'led', id: 'L6', l: 'L6 Halvledare och minne', h: '/l6/' },
  { t: 'gren', id: 'G6', l: 'G6 Utbud och halvledare', h: '/g6/' },
  { t: 'serie', id: 'a', l: 'Halvledare A', s: 'G6', h: '/a/' },
  { t: 'serie', id: 'b', l: 'Halvledare B', s: 'G6', h: '/b/' }
];

describe('SearchBox (ARIA combobox + listbox)', () => {
  afterEach(cleanup);
  it('has the combobox roles and states, and suggestions when empty', () => {
    const { getByRole, getAllByRole } = render(SearchBox, { items, onpick: () => {} });
    const input = getByRole('combobox');
    expect(input.getAttribute('aria-autocomplete')).toBe('list');
    expect(input.getAttribute('aria-controls')).toBe('sok-list');
    expect(input.getAttribute('aria-expanded')).toBe('true');
    // suggestions: no series
    expect(getAllByRole('option').map((o) => o.textContent)).toHaveLength(2);
    expect(input.getAttribute('aria-activedescendant')).toBe('sok-opt-0');
    expect(getByRole('listbox').getAttribute('aria-label')).toBe('Träffar');
  });

  it('arrow keys move the active option (wrapping), Enter picks it', async () => {
    const onpick = vi.fn();
    const { getByRole, getAllByRole } = render(SearchBox, { items, onpick });
    const input = getByRole('combobox') as HTMLInputElement;
    await fireEvent.input(input, { target: { value: 'halvledare' } });
    await tick();
    const opts = getAllByRole('option');
    expect(opts).toHaveLength(4);
    expect(opts[0].getAttribute('aria-selected')).toBe('true');
    await fireEvent.keyDown(input, { key: 'ArrowDown' });
    expect(input.getAttribute('aria-activedescendant')).toBe('sok-opt-1');
    expect(getAllByRole('option')[1].getAttribute('aria-selected')).toBe('true');
    await fireEvent.keyDown(input, { key: 'ArrowUp' });
    await fireEvent.keyDown(input, { key: 'ArrowUp' });
    expect(input.getAttribute('aria-activedescendant')).toBe('sok-opt-3');
    await fireEvent.keyDown(input, { key: 'Enter' });
    expect(onpick).toHaveBeenCalledTimes(1);
    expect(onpick.mock.calls[0][0].l).toBe(getAllByRole('option')[3].querySelector('.l')?.textContent);
    // label matches rank above subline matches: the two series first, then the lead and the branch
    expect(getAllByRole('option').map((o) => o.dataset.kind)).toEqual(['serie', 'serie', 'led', 'gren']);
  });

  it('no hits: collapsed list and a status message; Escape clears, then calls onescape', async () => {
    const onescape = vi.fn();
    const { getByRole, queryAllByRole } = render(SearchBox, { items, onpick: () => {}, onescape });
    const input = getByRole('combobox') as HTMLInputElement;
    await fireEvent.input(input, { target: { value: 'zzz' } });
    await tick();
    expect(queryAllByRole('option')).toHaveLength(0);
    expect(input.getAttribute('aria-expanded')).toBe('false');
    expect(input.hasAttribute('aria-activedescendant')).toBe(false);
    expect(getByRole('status').textContent).toContain('Inga träffar');
    await fireEvent.keyDown(input, { key: 'Escape' });
    await tick();
    expect(input.value).toBe('');
    expect(onescape).not.toHaveBeenCalled();
    await fireEvent.keyDown(input, { key: 'Escape' });
    expect(onescape).toHaveBeenCalledTimes(1);
  });

  it('a click on an option picks it', async () => {
    const onpick = vi.fn();
    const { getByRole, getAllByRole } = render(SearchBox, { items, onpick });
    await fireEvent.input(getByRole('combobox'), { target: { value: 'G6' } });
    await tick();
    await fireEvent.click(getAllByRole('option')[0]);
    expect(onpick.mock.calls[0][0].id).toBe('G6');
  });
});
