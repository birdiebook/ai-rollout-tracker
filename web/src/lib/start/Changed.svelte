<!-- Q3 "Har något fundamentalt ändrats?": the regime probability per block (C4) against its registered threshold,
     when the live snapshots have it, and the reconciliations between the leads as "where is the pace in its own
     history" (percentile, direction as colour + glyph). Rows are HTML so every reconciliation can link to its series. -->
<script lang="ts">
  import { resolve } from '$app/paths';
  import { DIRECTIONS, StatusBadge, dateLabel, fmt, periodLabel, signed } from '$lib/design';
  import { REGIME_HIGH, REGIME_LOW, reconDescription, type StartData } from './model';

  let { start }: { start: StartData } = $props();
  const reg = $derived(start.regime);
  const W = 120;
  const px = (p: number) => 4 + p * (W - 8);
</script>

<figure class="block" aria-labelledby="regime-h">
  <figcaption class="head">
    <h3 id="regime-h">Regimsannolikhet per block</h3>
    {#if reg.available}<StatusBadge status="live" />{/if}
  </figcaption>
  {#if reg.available && reg.blocks.length}
    <p class="desc">
      Sannolikheten för inbromsning enligt regimmodellen, {periodLabel(reg.blocks[0].month ?? start.record.month, true)}.
      Ett skifte till inbromsning registreras när två månader i rad ligger på minst {fmt(REGIME_HIGH, 1)}, och ett skifte
      till expansion när två månader i rad ligger på högst {fmt(REGIME_LOW, 1)}.
    </p>
    <ul class="rows">
      {#each reg.blocks as b (b.block)}
        <li class="row">
          <span class="lbl">{b.label}{#if b.shift}<span class="shift"> · skifte: {b.shift}</span>{/if}</span>
          <svg viewBox="0 0 {W} 22" width={W} height="22" role="img" aria-label="{b.label}: sannolikhet för inbromsning {b.p_slow === null ? 'saknas' : fmt(b.p_slow * 100, 0) + ' %'}, tröskel {fmt(REGIME_HIGH * 100, 0)} %">
            <rect x="4" y="6" width={W - 8} height="10" rx="3" fill="var(--c-grid)" />
            {#if b.p_slow !== null}<rect class="mark" x="4" y="6" width={Math.max(1, px(b.p_slow) - 4)} height="10" rx="3" fill="var(--c-model)" />{/if}
            <line x1={px(REGIME_HIGH)} x2={px(REGIME_HIGH)} y1="2" y2="20" stroke="var(--c-ink)" stroke-width="1.5" />
          </svg>
          <span class="val num">{b.p_slow === null ? '–' : `${fmt(b.p_slow * 100, 0)} %`}</span>
        </li>
      {/each}
    </ul>
    <p class="note k">stapel: sannolikhet 0–100 % · streck: registrerad tröskel {fmt(REGIME_HIGH, 1)}</p>
  {:else}
    <p class="desc">
      Regimsannolikheten räknas bara på skarpa ögonblicksbilder.
      {#if start.record.first_live_date}Den första committas {dateLabel(start.record.first_live_date)}, och då visas
        sannolikheten här per block.{/if}
    </p>
  {/if}
</figure>

<figure class="block" aria-labelledby="recon-h">
  <figcaption class="head">
    <h3 id="recon-h">Avstämningar mellan leden</h3>
    <StatusBadge status={start.record.status === 'live' ? 'live' : 'recon'} />
  </figcaption>
  <p class="desc">{reconDescription(start.reconciliations)}</p>
  <ul class="rows">
    {#each start.reconciliations as r (r.key)}
      {@const dir = r.direction === null ? null : DIRECTIONS[r.direction]}
      <li class="row" data-recon={r.key}>
        <span class="lbl">
          {#if r.linkable}<a href={resolve('/serie/[key]', { key: r.key })}>{r.short}</a>{:else}{r.short}{/if}
          <span class="lead">{r.lead}</span>
        </span>
        <svg
          viewBox="0 0 {W} 22"
          width={W}
          height="22"
          role="img"
          aria-label="{r.short}: takten på percentil {fmt(r.pace_percentile, 0)} av sin historik, {dir?.word ?? 'ingen riktning'}, takt {signed(r.pace)} {r.pace_unit} ({r.latest_period ?? '–'})"
        >
          <line x1="4" x2={W - 4} y1="11" y2="11" class="axisline" />
          {#each [0, 50, 100] as t (t)}<line x1={px(t / 100)} x2={px(t / 100)} y1="7" y2="15" class="axisline" />{/each}
          {#if r.pace_percentile !== null}
            <circle class="mark" cx={px(r.pace_percentile / 100)} cy="11" r="5.5" fill={dir?.color ?? 'var(--c-stb)'} stroke="var(--c-surface)" stroke-width="2" />
          {/if}
        </svg>
        <span class="val num"><span aria-hidden="true" style:color={dir?.color}>{dir?.glyph ?? ''}</span> {fmt(r.pace_percentile, 0)}</span>
      </li>
    {/each}
  </ul>
  <p class="note k">prick: takten som percentil 0–100 av sin egen historik · färg och glyf: förändring i takt</p>
</figure>

<style>
  .block {
    margin: 0;
  }
  .block + .block {
    margin-top: 18px;
  }
  .head {
    display: flex;
    flex-wrap: wrap;
    gap: 6px 10px;
    align-items: center;
  }
  h3 {
    font-size: var(--fs-subsection);
  }
  .desc {
    margin: 2px 0 8px;
    font-size: var(--fs-small);
    color: var(--c-ink-2);
  }
  .rows {
    list-style: none;
    margin: 0;
    padding: 0;
    display: grid;
    gap: 4px;
  }
  .row {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 120px 44px;
    gap: 8px;
    align-items: center;
    font-size: var(--fs-small);
  }
  .lbl {
    line-height: 1.25;
    color: var(--c-ink);
  }
  .lbl a {
    display: inline-flex;
    align-items: center;
    min-height: 24px;
  }
  .lead,
  .shift {
    color: var(--c-muted);
    font-size: 12px;
    margin-left: 4px;
  }
  .val {
    text-align: right;
    white-space: nowrap;
  }
  svg {
    display: block;
  }
  .k {
    margin: 6px 0 0;
  }
  @media (forced-colors: active) {
    .val span {
      color: CanvasText !important;
    }
  }
</style>
