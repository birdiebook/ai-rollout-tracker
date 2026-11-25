<!-- Forecast kind (W8): a committed live forecast (solid), a backtest, a shadow run or a file whose commit the build
     could not find ("overifierad", RW1-X 4a: never shown as live) (dashed). Complements the
     design system's StatusBadge, which names record status; this one names what kind of forecast a number is. -->
<script lang="ts">
  let { kind }: { kind: 'skarp' | 'backtest' | 'skugga' | 'väntar' | 'overifierad' } = $props();
  const WORD = {
    skarp: 'skarp prognos, committad',
    backtest: 'backtest, inte en skarp prognos',
    skugga: 'skuggprognos, inte huvudmodell',
    väntar: 'ingen skarp prognos ännu',
    overifierad: 'väntar på verifiering: ingen commit i bygget'
  };
</script>

<span class="kind" data-kind={kind}>{WORD[kind]}</span>

<style>
  .kind {
    display: inline-flex;
    align-items: center;
    font-size: 12px;
    color: var(--c-ink-2);
    border: 1px dashed var(--c-axis);
    border-radius: 999px;
    padding: 2px 9px;
    white-space: nowrap;
  }
  [data-kind='skarp'] {
    border-style: solid;
    border-color: var(--c-ink-2);
  }
</style>
