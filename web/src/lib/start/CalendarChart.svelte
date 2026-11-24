<!-- Q2: the calendar of live forecasts as a timeline (lesson 4: a picture, not a list). -->
<script lang="ts">
  import { ChartFrame, dateLabel, periodLabel } from '$lib/design';
  import CalendarMarks from './CalendarMarks.svelte';
  import { calendarDescription, upcoming, type StartData } from './model';

  let { start }: { start: StartData } = $props();
  const groups = $derived(upcoming(start.calendar));
  const stack = $derived(Math.max(1, ...groups.map((g) => g.items.length)));
  const description = $derived(calendarDescription(start.calendar, dateLabel, (p) => periodLabel(p)));
  const table = $derived({
    caption: 'Kalender för skarpa prognoser',
    columns: [
      { key: 'n', label: 'Prognos' },
      { key: 'p', label: 'Avser' },
      { key: 'o', label: 'Lämnas' },
      { key: 'k', label: 'Skarpa hittills' }
    ],
    rows: start.calendar
      .filter((c) => c.id !== 'd2')
      .map((c) => ({
        n: `${c.label} ${c.title}`,
        p: c.next_period ? periodLabel(c.next_period) : '–',
        o: c.next_origin ? dateLabel(c.next_origin) : 'inte planerad',
        k: String(c.n_live)
      }))
  });
</script>

<ChartFrame id="calendar" title="Kalendern" {description} height={44 + stack * 13} width={340} margin={{ top: 0, right: 14, bottom: 0, left: 14 }} {table}>
  {#snippet children(d)}<CalendarMarks {d} calendar={start.calendar} today={start.today} forecast={start.forecast} />{/snippet}
</ChartFrame>
