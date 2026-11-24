<!-- Record status next to a heading (lesson 7): dashed = reconstructed or backtest, solid = live snapshot. -->
<script lang="ts">
  import type { RecordStatus } from './types';

  let { status }: { status: RecordStatus } = $props();
  const LABEL: Record<RecordStatus, string> = {
    recon: 'rekonstruerad historik',
    live: 'skarp ögonblicksbild',
    backtest: 'backtest, inte en skarp prognos'
  };
</script>

<span class="badge" class:live={status === 'live'} data-status={status}>{LABEL[status]}</span>

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
</style>
