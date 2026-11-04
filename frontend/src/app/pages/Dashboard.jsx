import { PageHeader, Button, SeverityBadge, AutoGrid } from '../../components/ui.jsx';

const LABEL = 'font-mono text-[10.5px] font-medium leading-none tracking-[.12em] text-fg-3';
const TILE = 'edge flex flex-col gap-2.5 p-4 card min-w-0';
const edge = c => ({ '--edge': c });
const H2 = 'm-0 font-mono text-[11px] font-medium leading-none tracking-[.12em] text-fg-2';
const ROW_LINK = 'text-fg no-underline hover:no-underline';
// Graticule: 4 horizontal bands, 10 vertical divisions.
const CHART_GRID = '[background-image:linear-gradient(var(--grid)_1px,transparent_1px),linear-gradient(90deg,var(--grid)_1px,transparent_1px)] [background-size:100%_25%,10%_100%]';

function PanelHead({ title, children }) {
  return (
    <div className="panel-head flex flex-wrap items-center justify-between gap-2 px-4 py-3 border-b border-line">
      <h2 className={H2}>{title}</h2>
      {children}
    </div>
  );
}

function SevCount({ n, label, color }) {
  return (
    <div className="pt-2 border-t-2" style={{ borderColor: color }}>
      <div className="font-mono text-[28px] font-medium leading-none tabular" style={{ color }}>{n}</div>
      <div className="font-mono text-[10px] font-medium leading-[1.6] text-fg-3">{label}</div>
    </div>
  );
}

function AmplitudeChart({ chart }) {
  const series = chart.series || [];
  return (
    <div role="img" aria-label="Dominant vibration amplitude per machine over time"
      className={`relative h-[220px] mt-4 mr-4 mb-1.5 ml-11 border-l border-b border-line-2 ${CHART_GRID}`}>
      {(chart.ticks || []).map((t, i) => (
        <span key={i} className="absolute -left-10 w-[34px] -translate-y-1/2 text-right font-mono text-[10px] leading-none text-fg-3 tabular" style={{ top: t.top }}>{t.label}</span>
      ))}
      <svg viewBox="0 0 600 200" preserveAspectRatio="none" aria-hidden="true" className="absolute inset-0 w-full h-full overflow-visible">
        {series.map((s, i) => (
          <polyline key={i} points={s.points} fill="none" strokeWidth="1.75" vectorEffect="non-scaling-stroke" style={{ stroke: s.color }} />
        ))}
      </svg>
      {series.map((s, i) => s.dots.map((d, j) => (
        <span key={`${i}-${j}`} title={d.label}
          className="absolute size-[7px] -mt-[3.5px] -ml-[3.5px] rounded-full bg-panel border-[1.5px]"
          style={{ left: d.left, top: d.top, borderColor: d.color }} />
      )))}
    </div>
  );
}

export default function Dashboard({ v }) {
  const dash = v.dash || {};
  const chart = dash.chart || { series: [], ticks: [], legend: [] };
  return (
    <div className="flex flex-col gap-5">
      <PageHeader eyebrow="CH 01 · OVERVIEW" title="Fleet health">
        <Button primary href="#/analyze">+ New analysis</Button>
      </PageHeader>

      {v.loading && (
        <div role="status" aria-label="Loading runs" className="grid gap-3 grid-cols-[repeat(auto-fit,minmax(min(100%,200px),1fr))]">
          {v.skel.map(k => (
            <div key={k} className="h-[118px] rounded-card border border-line bg-[linear-gradient(90deg,var(--panel)_0%,var(--panel-2)_50%,var(--panel)_100%)]" />
          ))}
        </div>
      )}

      {v.empty && (
        <div className="flex flex-col items-center gap-3 px-6 py-14 text-center border border-dashed border-line-2 rounded-card">
          <div className="font-mono text-[11px] font-medium leading-none tracking-[.14em] text-fg-3">NO SIGNAL</div>
          <h2 className="m-0 text-[20px] font-semibold">No runs yet</h2>
          <p className="m-0 max-w-[420px] text-fg-2">Film a machine in slow motion for 10 seconds and Resonance will measure, magnify and diagnose it.</p>
          <Button primary href="#/analyze">Analyze your first machine</Button>
        </div>
      )}

      {v.hasRuns && (
        <>
          <AutoGrid min={210} gap={12}>
            <div className={TILE} style={edge('var(--info)')}>
              <div className={LABEL}>MACHINES ANALYSED</div>
              <div className="font-mono text-[36px] font-medium leading-none tabular">{dash.machines}</div>
              <div className="text-[12.5px] text-fg-2">{dash.openN}&nbsp;with open issues</div>
            </div>
            <div className={TILE} style={edge('var(--sev-act)')}>
              <div className={LABEL}>OPEN ISSUES</div>
              <div className="grid grid-cols-3 gap-2">
                <SevCount n={dash.stop} label="STOP NOW" color="var(--sev-stop)" />
                <SevCount n={dash.act} label="ACT SOON" color="var(--sev-act)" />
                <SevCount n={dash.mon} label="MONITOR" color="var(--sev-monitor)" />
              </div>
            </div>
            <div className={TILE} style={edge('var(--sev-normal)')}>
              <div className={LABEL}>FIXES VERIFIED</div>
              <div className="font-mono text-[36px] font-medium leading-none tabular text-sev-normal">{dash.fixes}</div>
              <div className="text-[12.5px] text-fg-2">Proven by rescan, not by checklist</div>
            </div>
            <a href="#/usage" className={`${TILE} text-fg no-underline hover:no-underline`} style={edge('var(--violet)')}>
              <div className={LABEL}>API SPEND</div>
              <div className="font-mono text-[36px] font-medium leading-none tabular">{dash.spend}</div>
              <div className="h-1 bg-line rounded-chip overflow-hidden" role="progressbar" aria-label="Budget used"
                aria-valuemin={0} aria-valuemax={100} aria-valuenow={parseFloat(dash.budgetPct) || 0}>
                <div className="h-full bg-signal" style={{ width: v.usage ? v.usage.barW : '0%' }} />
              </div>
              <div className="font-mono text-[11.5px] leading-none text-fg-3">of {dash.budget}&nbsp;budget · {dash.budgetPct}</div>
            </a>
          </AutoGrid>

          <AutoGrid min={440} gap={16}>
            <section className="card min-w-0">
              <PanelHead title="NEEDS ATTENTION"><span className="font-mono text-[11px] leading-none text-fg-3">by severity</span></PanelHead>
              {dash.allClear && <div className="px-4 py-8 text-center text-fg-2">All machines are within normal limits.</div>}
              {(dash.attention || []).map(m => (
                <a key={m.id} href={m.href} className={`flex flex-wrap items-center gap-x-3.5 gap-y-2.5 px-4 py-[13px] border-b border-line ${ROW_LINK}`}>
                  <span className="size-2 rounded-full shrink-0" style={{ background: m.sevColor, boxShadow: `0 0 0 3px ${m.sevTint}` }} />
                  <div className="flex-1 min-w-[160px]">
                    <div className="font-medium">{m.name}</div>
                    <div className="font-mono text-[12px] leading-[1.5] text-fg-3">{m.fault} · {m.freq} · {m.ago}</div>
                  </div>
                  <span className="font-mono text-[13px] font-medium leading-none" style={{ color: m.trendColor }} title={m.trendLabel}>{m.trend} {m.trendLabel}</span>
                  <SeverityBadge s={m} dot={false} />
                </a>
              ))}
            </section>

            <section className="flex flex-col card min-w-0">
              <PanelHead title="AMPLITUDE @ 1× · PX"><span className="font-mono text-[11px] leading-none text-fg-3">{chart.from} → today</span></PanelHead>
              <AmplitudeChart chart={chart} />
              <div className="flex flex-wrap gap-x-4 gap-y-2 px-4 pt-2.5 pb-3.5">
                {(chart.legend || []).map((l, i) => (
                  <span key={i} className="inline-flex items-center gap-1.5 font-mono text-[11.5px] leading-none text-fg-2">
                    <span className="w-3 h-0.5" style={{ background: l.color }} />{l.name}
                  </span>
                ))}
              </div>
            </section>
          </AutoGrid>

          <section className="card min-w-0">
            <PanelHead title="RECENT RUNS"><a href="#/runs" className="font-mono text-[11px] font-medium leading-none">All runs →</a></PanelHead>
            <div className="relative py-2 pr-4 pl-[34px]">
              <div className="absolute left-[21px] top-[18px] bottom-[18px] w-px bg-line-2" />
              {(dash.recent || []).map(r => (
                <a key={r.run} href={r.href} className="relative flex flex-wrap items-center gap-x-4 gap-y-1.5 py-[11px] border-b border-line text-fg no-underline hover:no-underline">
                  <span className="absolute -left-[17px] top-1/2 size-[9px] -mt-[4.5px] rounded-full bg-bg border-2" style={{ borderColor: r.sevColor }} />
                  <span className="w-24 font-mono text-[12px] leading-none text-fg-3">{r.ago}</span>
                  <span className="flex-1 min-w-[140px] font-medium">
                    {r.title}
                    {r.hasTag && <span className="ml-1.5 font-mono text-[11px] font-normal leading-none text-fg-3">{r.tag}</span>}
                  </span>
                  <span className="w-24 font-mono text-[13px] font-medium leading-none tabular">{r.freq}</span>
                  <span className="w-[92px] font-mono text-[12px] leading-none text-fg-2 tabular">{r.amp}</span>
                  <span className="px-2 py-1 border rounded-chip font-mono text-[10px] font-semibold leading-none tracking-[.08em] uppercase whitespace-nowrap"
                    style={{ borderColor: `color-mix(in oklch, ${r.sevColor} 55%, transparent)`, color: r.sevColor, background: `color-mix(in oklch, ${r.sevColor} 14%, transparent)` }}>{r.sevLabel}</span>
                </a>
              ))}
            </div>
          </section>
        </>
      )}
    </div>
  );
}
