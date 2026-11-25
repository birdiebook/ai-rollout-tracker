<!-- Record status next to a heading (lesson 7): dashed = reconstructed or backtest, solid = live snapshot.
     `prominent` (R-W3): the size and weight of the heading's own kicker, in ink, for the start and month pages where a
     reconstructed month must not look as certain as a live one; `label` replaces the default words. -->
<script lang="ts">
  import type { RecordStatus } from './types';

  let { status, prominent = false, label }: { status: RecordStatus; prominent?: boolean; label?: string } = $props();
  const LABEL: Record<RecordStatus, string> = {
    recon: 'rekonstruerad historik',
    live: 'skarp ögonblicksbild',
    backtest: 'backtest, inte en skarp prognos'
  };
</script>

<span class="badge" class:live={status === 'live'} class:prominent data-status={status}>{label ?? LABEL[status]}</span>

<style>
  .badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 12px;
    color: var(--c-ink-2);
    border: 1px dashed var(--c-axis);
    border-radius: 999px;
    padding: 2px 9px;
    white-space: nowrap;
    font-weight: 400;
    vertical-align: middle;
  }
  .live {
    border-style: solid;
    border-color: var(--c-ink-2);
  }
  .prominent {
    font-size: var(--fs-small);
    font-weight: 620;
    color: var(--c-ink);
    border-width: 2px;
    border-color: var(--c-ink-2);
    padding: 3px 11px;
    white-space: normal;
  }
</style>
