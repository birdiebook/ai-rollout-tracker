<!-- Test-only harness: one ChartFrame with every primitive inside, so component tests can render a real chart. -->
<script lang="ts">
  import { scaleLinear, scalePoint } from 'd3-scale';
  import { Axis, Band, ChartFrame, Line, QuantileDots, StripeCell } from '../index';

  let {
    dots = [] as number[],
    outcome = undefined as number | undefined,
    nRows = 3,
    dataHref = undefined as string | undefined
  } = $props();
  const data = [
    { m: '2026-01', v: 1, lo: 0, hi: 2 },
    { m: '2026-02', v: 2, lo: 1, hi: 3 },
    { m: '2026-03', v: 3, lo: 2, hi: 4 }
  ];
</script>

<ChartFrame
  id="t"
  title="Test"
  description="Testmening."
  height={160}
  source="test"
  license="CC0"
  {dataHref}
  table={{ columns: [{ key: 'm', label: 'Månad' }, { key: 'v', label: 'Värde' }], rows: Array.from({ length: nRows }, (_, i) => ({ m: `r${i + 1}`, v: String(i + 1) })) }}
>
  {#snippet children(d)}
    {@const x = scalePoint<string>().domain(data.map((r) => r.m)).range([d.left, d.right])}
    {@const y = scaleLinear().domain([0, 4]).range([d.bottom, d.top])}
    {@const xv = scaleLinear().domain([0, 10]).range([d.left, d.right])}
    <Axis scale={y} dims={d} orient="left" tickValues={[0, 2, 4]} grid baseline={0} />
    <Axis scale={x} dims={d} />
    <Band data={data} x={(r) => x(r.m) ?? 0} levels={[{ level: '80', lo: (r) => y(r.lo), hi: (r) => y(r.hi) }, { level: '50', lo: (r) => y(r.lo + 0.5), hi: (r) => y(r.hi - 0.5) }]} center={(r) => y(r.v)} />
    <Line data={data} x={(r) => x(r.m) ?? 0} y={(r) => y(r.v)} endDot endLabel="3" />
    <QuantileDots values={dots} x={(v) => xv(v)} dims={d} {outcome} />
    <StripeCell x={0} y={0} width={10} height={10} value={0.9} tooltip={{ title: 'Cell' }} />
    <StripeCell x={10} y={0} width={10} height={10} value={null} />
  {/snippet}
</ChartFrame>
