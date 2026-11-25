// The W2 chart primitives. Pages import from '$lib/design' (see docs/steg3/webb.md).
export { default as ChartFrame } from './ChartFrame.svelte';
export { default as Axis } from './Axis.svelte';
export { default as Line } from './Line.svelte';
export { default as Band } from './Band.svelte';
export { default as QuantileDots } from './QuantileDots.svelte';
export { default as StripeCell } from './StripeCell.svelte';
export { default as Stripes } from './Stripes.svelte';
export { default as Glyph } from './Glyph.svelte';
export { default as Tooltip } from './Tooltip.svelte';
export { default as Legend } from './Legend.svelte';
export { default as TableToggle } from './TableToggle.svelte';
export { default as DataTable } from './DataTable.svelte';
export { default as StatusBadge } from './StatusBadge.svelte';
export { default as Deferred } from './Deferred.svelte';
export * from './types';
export { PRERENDER_CELLS, chartData, dataUrl, setChartData } from './chartData';
export * from './quantiles';
export { provideTooltip, useTooltip, TooltipState, type TooltipContent } from './tooltip.svelte';
