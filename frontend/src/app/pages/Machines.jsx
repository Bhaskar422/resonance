import { PageHeader, Button, SeverityBadge, AutoGrid } from '../../components/ui.jsx';

const H2 = 'm-0 font-mono text-[11px] font-medium leading-none tracking-[.12em] text-fg-2';
const PANEL = 'card min-w-0';
const ROW_LINK = 'text-fg no-underline hover:no-underline';

function Badge({ s, tinted = true, className = '' }) {
  return (
    <span className={`border rounded-chip font-mono text-[10px] font-semibold leading-none uppercase whitespace-nowrap ${className}`}
      style={{ borderColor: s.sevColor, color: s.sevColor, background: tinted ? s.sevTint : undefined }}>{s.sevLabel}</span>
  );
}

export function Machines({ v }) {
  return (
    <div className="flex flex-col gap-5">
      <PageHeader eyebrow="CH 02 · ASSETS" title="Machines"
        sub={<span className="text-[13px]">Grouped from your runs by the machine Muse Spark identified.</span>}>
        <Button primary href="#/analyze">+ Scan a machine</Button>
      </PageHeader>

      {v.loading && (
        <div role="status" aria-label="Loading machines" className="animate-pulse">
          <AutoGrid min={280} gap={12} fill>
            {v.skel6.map(k => <div key={k} className="h-[168px] rounded-card bg-panel-2 border border-line" />)}
          </AutoGrid>
        </div>
      )}

      {v.empty && (
        <div className="p-12 text-center text-fg-2 border border-dashed border-line-2 rounded-card">
          No machines yet. <a href="#/analyze">Run your first analysis</a>.
        </div>
      )}

      {(v.machines || []).length > 0 && (
        <AutoGrid min={280} gap={12} fill>
          {v.machines.map(m => (
            <a key={m.id} href={m.href} className={`flex flex-col gap-3.5 p-4 ${PANEL} ${ROW_LINK}`}>
              <div className="flex items-start justify-between gap-2.5">
                <div className="min-w-0">
                  <div className="text-[15px] font-semibold">{m.name}</div>
                  <div className="font-mono text-[11px] leading-[1.6] text-fg-3">{m.count}{m.hasTag && ` · ${m.tag}`}</div>
                </div>
                <Badge s={m} className="shrink-0 px-2 py-1 tracking-[.08em]" />
              </div>
              <div className="flex flex-wrap items-baseline gap-x-2.5">
                <span className="font-mono text-[30px] font-medium leading-none tabular">{m.freq}</span>
                <span className="font-mono text-[12px] leading-none text-fg-3">{m.freqAlt}</span>
              </div>
              <div className="flex flex-wrap justify-between gap-2 pt-3 border-t border-line font-mono text-[12px] leading-[1.3] text-fg-2">
                <span className="tabular">{m.amp}</span>
                <span style={{ color: m.trendColor }}>{m.trend} {m.trendLabel}</span>
                <span className="text-fg-3">{m.ago}</span>
              </div>
            </a>
          ))}
        </AutoGrid>
      )}
    </div>
  );
}

function HistoryChart({ chart, fhz }) {
  const series = chart.series || [];
  return (
    <div role="img" aria-label={`Amplitude at ${fhz} across runs`}
      className="relative h-[240px] mt-[18px] mr-[18px] mb-[18px] ml-12 border-l border-b border-line-2 [background-image:linear-gradient(var(--grid)_1px,transparent_1px)] [background-size:100%_25%]">
      {(chart.ticks || []).map((t, i) => (
        <span key={i} className="absolute -left-11 w-[38px] -translate-y-1/2 text-right font-mono text-[10px] leading-none text-fg-3 tabular" style={{ top: t.top }}>{t.label}</span>
      ))}
      <svg viewBox="0 0 600 200" preserveAspectRatio="none" aria-hidden="true" className="absolute inset-0 w-full h-full overflow-visible">
        {series.map((s, i) => (
          <polyline key={i} points={s.points} fill="none" strokeWidth="2" vectorEffect="non-scaling-stroke" style={{ stroke: 'var(--signal)' }} />
        ))}
      </svg>
      {series.map((s, i) => s.dots.map((d, j) => (
        <span key={`${i}-${j}`}>
          <span title={d.label} className="absolute size-2.5 -mt-[5px] -ml-[5px] rounded-full border-2 border-panel"
            style={{ left: d.left, top: d.top, background: d.sevColor }} />
          <span aria-hidden="true" className="absolute -translate-x-1/2 -translate-y-[22px] font-mono text-[10.5px] font-medium leading-none text-fg-2 whitespace-nowrap"
            style={{ left: d.left, top: d.top }}>{d.label}</span>
        </span>
      )))}
    </div>
  );
}

export function MachineDetail({ v }) {
  const m = v.machine || {};
  return (
    <div className="flex flex-col gap-5">
      {m.missing && (
        <div className="p-12 text-center border border-dashed border-line-2 rounded-card">
          Machine not found. <a href="#/machines">Back to machines</a>
        </div>
      )}
      {!m.found && !m.missing && v.loading && (
        <div role="status" aria-label="Loading machine" className="animate-pulse flex flex-col gap-3">
          <div className="h-[90px] rounded-card bg-panel-2" />
          <div className="h-[300px] rounded-card bg-panel-2" />
        </div>
      )}

      {m.found && (
        <>
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div className="min-w-0">
              <a href="#/machines" className="font-mono text-[11px] font-medium leading-none tracking-[.12em]">← MACHINES</a>
              <h1 className="mt-2.5 mb-2 text-[28px] font-semibold">{m.name}</h1>
              <div className="flex flex-wrap items-center gap-2 font-mono text-[12px] leading-none text-fg-2">
                <SeverityBadge s={m} dot={false} />
                <span>{m.fault}</span><span aria-hidden="true">·</span><span>{m.freq}</span><span aria-hidden="true">·</span><span>{m.count}</span>
                {m.hasTag && <span className="text-fg-3">{m.tag}</span>}
              </div>
            </div>
            <Button primary href={m.rescanHref}>Rescan this machine</Button>
          </div>

          <section className={PANEL}>
            <div className="flex justify-between px-4 py-3 border-b border-line">
              <h2 className={H2}>AMPLITUDE AT FAULT FREQUENCY ({m.fhz}) ACROSS RUNS</h2>
            </div>
            <HistoryChart chart={m.chart || {}} fhz={m.fhz} />
          </section>

          <AutoGrid min={420} gap={16}>
            <section className={PANEL}>
              <div className="px-4 py-3 border-b border-line"><h2 className={H2}>EVERY RUN</h2></div>
              {(m.runs || []).map(r => (
                <a key={r.run} href={r.href} className={`flex flex-wrap items-center gap-x-3.5 gap-y-1.5 px-4 py-3 border-b border-line ${ROW_LINK}`}>
                  <span className="flex-1 min-w-[150px] font-mono text-[12px] leading-[1.4] text-fg-2">{r.date} · {r.time}</span>
                  <span className="font-mono text-[12.5px] font-medium leading-none tabular">{r.amp}</span>
                  <Badge s={r} tinted={false} className="px-[7px] py-[3px] tracking-[.06em]" />
                </a>
              ))}
            </section>

            <section className={PANEL}>
              <div className="px-4 py-3 border-b border-line"><h2 className={H2}>BEFORE / AFTER FIX PAIRS</h2></div>
              {m.noPairs && (
                <div className="px-4 py-7 text-[13px] text-fg-2">No verified fixes yet. After a repair, rescan from the same spot to prove the result.</div>
              )}
              {(m.pairs || []).map(c => (
                <a key={c.before.run + c.after.run}
                  href={`#/rescan?before=${encodeURIComponent(c.before.run)}&after=${encodeURIComponent(c.after.run)}`}
                  className={`flex flex-wrap items-center gap-x-4 gap-y-2.5 px-4 py-3.5 border-b border-line ${ROW_LINK}`}>
                  <span className="font-mono text-[26px] font-semibold leading-none tabular" style={{ color: c.color }}>{c.big}</span>
                  <div className="flex-1 min-w-[150px]">
                    <div className="font-semibold">{c.label}&nbsp;at {c.hz}</div>
                    <div className="font-mono text-[11.5px] leading-[1.5] text-fg-3">{c.before.date} → {c.after.date} · {c.cert}</div>
                  </div>
                  <span className="font-mono text-[11px] font-medium leading-none">Certificate →</span>
                </a>
              ))}
            </section>
          </AutoGrid>
        </>
      )}
    </div>
  );
}
