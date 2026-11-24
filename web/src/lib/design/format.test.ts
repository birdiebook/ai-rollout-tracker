import { describe, expect, it } from 'vitest';
import { MINUS, dateLabel, fmt, pct, periodLabel, signed, monthOrdinal, ordinalMonth } from './format';

describe('Swedish formatting', () => {
  it('uses space thousands, comma decimals and a real minus', () => {
    expect(fmt(1234567.891, 1).replace(/\s/g, ' ')).toBe('1 234 567,9');
    expect(fmt(-4.44, 1)).toBe(`${MINUS}4,4`);
    expect(fmt(-0.01, 1)).toBe('0,0');
    expect(fmt(null)).toBe('–');
    expect(fmt(Number.NaN)).toBe('–');
  });
  it('signs', () => {
    expect(signed(4.8)).toBe('+4,8');
    expect(signed(-4.4)).toBe(`${MINUS}4,4`);
    expect(signed(0.01)).toBe('±0,0');
  });
  it('percent', () => expect(pct(0.43)).toBe('43 %'));
  it('periods and dates', () => {
    expect(periodLabel('2026-11')).toBe('nov 2026');
    expect(periodLabel('2026-11', true)).toBe('november 2026');
    expect(periodLabel('2026Q3')).toBe('kv. 3 2026');
    expect(dateLabel('2026-12-05')).toBe('5 dec 2026');
    expect(ordinalMonth(monthOrdinal('2023-06'))).toBe('2023-06');
  });
});
