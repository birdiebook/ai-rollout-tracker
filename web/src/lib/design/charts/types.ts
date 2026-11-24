// Shared types for the chart primitives.

/** The drawing area a ChartFrame hands its children (pixels, SVG user units). */
export interface ChartDims {
  width: number;
  height: number;
  margin: Margin;
  /** inner plot area */
  left: number;
  right: number;
  top: number;
  bottom: number;
  innerWidth: number;
  innerHeight: number;
}

export interface Margin {
  top: number;
  right: number;
  bottom: number;
  left: number;
}

/** The part of a d3 scale the primitives use (continuous or band). */
export interface AnyScale<D = any> {
  (v: D): number | undefined;
  domain(): D[];
  range(): number[];
  ticks?: (count?: number) => D[];
  bandwidth?: () => number;
}

export interface TableColumn {
  key: string;
  label: string;
  /** numbers are right-aligned (default for numeric values) */
  align?: 'left' | 'right';
}

export interface TableSpec {
  caption?: string;
  columns: TableColumn[];
  /** already formatted strings (use format.ts), so that the table shows what the chart shows */
  rows: Record<string, string | number | null>[];
}

export type RecordStatus = 'recon' | 'live' | 'backtest';

export function dims(width: number, height: number, margin: Margin): ChartDims {
  return {
    width,
    height,
    margin,
    left: margin.left,
    right: width - margin.right,
    top: margin.top,
    bottom: height - margin.bottom,
    innerWidth: Math.max(0, width - margin.left - margin.right),
    innerHeight: Math.max(0, height - margin.top - margin.bottom)
  };
}
