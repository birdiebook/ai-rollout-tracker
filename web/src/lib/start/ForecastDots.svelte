<!-- Q2: the latest live forecast as 20 equally likely outcomes (quantile dots, P4), from its central value and its
     50/80/95 intervals. Before the first live forecast the card says when it comes instead. -->
<script lang="ts">
  import { scaleLinear } from 'd3-scale';
  import { Axis, ChartFrame, QuantileDots, dateLabel, dotValues, fmt, periodLabel } from '$lib/design';
  import { forecastQuantiles, type ForecastView } from './model';

  let { forecast }: { forecast: ForecastView } = $props();
  const values = $derived(dotValues(forecastQuantiles(forecast), 20));
  const lo = $derived(forecast.intervals['95'][0]);
  const hi = $derived(forecast.intervals['95'][1]);
  const pad = $derived((hi - lo) * 0.12);
  const f = (v: number) => fmt(v, forecast.decimals);
  const description = $derived(
    `Senaste skarpa prognosen: ${forecast.label} för ${periodLabel(forecast.period)}, lämnad ${dateLabel(forecast.origin)} med ${forecast.champion}: ` +
      `${f(forecast.value)} ${forecast.unit}, 80 % intervall ${f(forecast.intervals['80'][0])}–${f(forecast.intervals['80'][1])}. Varje prick är ett av 20 lika sannolika utfall.`
  );
  const table = $derived({
    caption: `${forecast.label} ${forecast.title}, ${periodLabel(forecast.period)}`,
    columns: [
      { key: 'k', label: 'Nivå' },
      { key: 'lo', label: 'Nedre' },
      { key: 'hi', label: 'Övre' }
    ],
    rows: [
      { k: 'Prognos', lo: f(forecast.value), hi: '' },
      ...(['50', '80', '95'] as const).map((l) => ({ k: `${l} %`, lo: f(forecast.intervals[l][0]), hi: f(forecast.intervals[l][1]) }))
    ]
  });
</script>

<ChartFrame id="forecast" title="{forecast.label} {forecast.title}" {description} height={96} width={340} margin={{ top: 6, right: 12, bottom: 24, left: 12 }} {table} status="live">
  {#snippet children(d)}
    {@const x = scaleLinear().domain([lo - pad, hi + pad]).range([d.left, d.right]).nice()}
    <Axis scale={x} dims={d} ticks={3} format={(v: number) => f(v)} />
    <QuantileDots {values} x={(v) => x(v)} dims={d} format={f} />
  {/snippet}
</ChartFrame>
