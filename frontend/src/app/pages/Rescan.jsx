import { Eyebrow, Switch } from '../../components/ui.jsx';

const FIELD_LABEL = 'font-mono text-[10.5px] font-medium leading-none tracking-[.1em] text-fg-3';
const SELECT = 'h-10 px-2.5 bg-bg border border-line-2 rounded-ctl text-fg min-w-0 w-full';
const SECTION_LABEL = 'font-mono text-[10.5px] font-medium leading-none tracking-[.12em] text-fg-3';

export default function Rescan({ v }) {
  const rs = v.rs;
  if (!rs) return null;
  return (
    <div className="flex flex-col gap-[18px]">
      <div>
        <Eyebrow>CH 05 · VERIFY</Eyebrow>
        <h1 className="mt-2 mb-0 text-[26px] font-semibold">Rescan &amp; compare</h1>
        <p className="mt-1.5 mb-0 text-fg-2 text-[13.5px]">Pick a before and an after run of the same machine. The result is a shareable certificate of fix.</p>
      </div>

      {rs.none && (
        <div className="p-10 border border-dashed border-line-2 rounded-card text-center text-fg-2">
          You need two runs of the same machine to compare. <a href="#/analyze">Scan a machine</a>
        </div>
      )}

      {rs.can && (
        <section data-noprint="" aria-label="Choose runs to compare"
          className="grid gap-3 items-end p-4 card"
          style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 200px), 1fr))' }}>
          <label className="flex flex-col gap-1.5 min-w-0">
            <span className={FIELD_LABEL}>MACHINE</span>
            <select value={rs.machine} onChange={rs.onMachine} className={SELECT}>
              {rs.machineOpts.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          </label>
          <label className="flex flex-col gap-1.5 min-w-0">
            <span className={FIELD_LABEL}>BEFORE</span>
            <select value={rs.before} onChange={rs.onBefore} className={`${SELECT} font-mono text-[12px]`}>
              {rs.beforeOpts.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          </label>
          <label className="flex flex-col gap-1.5 min-w-0">
            <span className={FIELD_LABEL}>AFTER</span>
            <select value={rs.after} onChange={rs.onAfter} className={`${SELECT} font-mono text-[12px]`}>
              {rs.afterOpts.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          </label>
          <div className="flex gap-2.5 items-center h-10">
            <Switch sw={rs.spark} label="Ask Muse Spark" />
            <span className="text-[13px]">Muse Spark verdict</span>
          </div>
          <button type="button" onClick={rs.run} className="h-10 px-[18px] bg-accent text-on-accent border-0 rounded-ctl font-semibold">Compare runs</button>
        </section>
      )}

      {rs.same && <div role="alert" className="text-[13px] text-sev-monitor">Before and after are the same run. Pick two different runs.</div>}

      {rs.loading && (
        <div className="flex flex-col gap-3" role="status" aria-live="polite">
          <span className="flex items-center gap-2.5 font-mono text-[12px] leading-none text-fg-3"><span className="size-3.5 rounded-full border-2 border-line-2 border-t-[var(--accent)] animate-spin" />Comparing spectra and asking Muse Spark…</span>
          <div className="h-[200px] rounded-card bg-panel-2 animate-pulse" />
          <div className="h-[160px] rounded-card bg-panel-2 animate-pulse" />
        </div>
      )}

      {rs.failed && (
        <div role="alert" className="flex flex-wrap gap-3 items-center p-3.5 border border-sev-stop rounded-card">
          <span className="flex-1 min-w-[200px] [overflow-wrap:anywhere]">Comparison failed: {rs.error}</span>
          <button type="button" onClick={rs.run} className="h-[34px] px-3 border border-line-2 bg-panel rounded-ctl">Retry</button>
        </div>
      )}

      {rs.idle && (
        <div className="p-9 border border-dashed border-line-2 rounded-card text-center text-fg-2">Choose two runs and press Compare.</div>
      )}

      {rs.hasResult && rs.res && <Certificate v={v} rs={rs} res={rs.res} />}
    </div>
  );
}

function Certificate({ v, rs, res }) {
  return (
    <article aria-label={`Certificate of fix ${res.cert}`} className="border rounded-card bg-panel overflow-hidden min-w-0" style={{ borderColor: res.color }}>
      <div className="flex flex-wrap justify-between gap-2.5 px-5 py-3 border-b border-line font-mono text-[11px] font-medium leading-[1.4] tracking-[.1em] text-fg-3">
        <span>CERTIFICATE OF FIX · {res.cert}</span>
        <span>ISSUED {res.issued}{res.tag ? ` · ${res.tag}` : ''}</span>
      </div>

      <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 340px), 1fr))' }}>
        <div className="px-6 py-7 flex flex-col gap-3.5 border-r border-line min-w-0">
          <div className="text-[15px] text-fg-2">{res.machine}</div>
          <div className="flex items-center gap-3">
            <span className="size-3.5 rounded-full shrink-0" style={{ background: res.color, boxShadow: `0 0 0 6px ${res.tintc}` }} />
            <span className="font-sans text-[40px] font-semibold leading-none tracking-[-.02em]" style={{ color: res.color }}>{res.label}</span>
          </div>
          <div className="font-mono text-[64px] font-medium leading-none tracking-[-.03em] tabular">{res.big}</div>
          <div className="font-mono text-[13px] leading-[1.4] text-fg-2 tabular">vibration at {res.hz} · {res.bigDb}</div>
          <div className="scope relative h-[150px] mt-1.5 border border-line rounded-ctl overflow-hidden">
            <canvas ref={v.refs.motionCompare} role="img" aria-label="Before and after magnified motion" className="absolute inset-0 block w-full h-full" />
          </div>
        </div>

        <div className="px-6 py-5 flex flex-col gap-3 min-w-0">
          <div className={SECTION_LABEL}>BEFORE → AFTER · PX</div>
          {res.rows.map(w => (
            <div key={w.label} className="flex flex-col gap-1.5 pb-2.5 border-b border-line">
              <div className="flex flex-wrap justify-between gap-1.5 font-mono text-[12.5px] leading-[1.2] tabular">
                <span className="text-fg">{w.label} <span className="text-fg-3">{w.hz}</span></span>
                <span>{w.before} → {w.after}</span>
                <span className="font-semibold" style={{ color: w.color }}>{w.pct} · {w.db}</span>
              </div>
              <div className="relative h-1.5 bg-line-2 rounded-ctl">
                <div className="absolute left-0 top-0 bottom-0 rounded-ctl" style={{ width: w.wA, background: w.color }} />
              </div>
            </div>
          ))}
          <div className="flex flex-wrap justify-between gap-1.5 font-mono text-[13px] font-medium leading-[1.2] px-3 py-2.5 border border-line-2 rounded-ctl tabular">
            <span>RMS displacement</span>
            <span>{res.rms.before} → {res.rms.after}</span>
            <span style={{ color: res.rms.color }}>{res.rms.pct}</span>
          </div>
          <div className={`${SECTION_LABEL} mt-1.5`}>OVERLAID SPECTRUM</div>
          {res.hasPlot && (
            <div role="img" aria-label="Overlaid before and after spectrum" className="w-full block aspect-[3/1]" style={{ background: res.plotBg }} />
          )}
          {res.noPlot && (
            <>
              <div className="relative h-[140px] border-b border-line-2"
                style={{ backgroundImage: 'linear-gradient(var(--grid) 1px, transparent 1px)', backgroundSize: '100% 25%' }}>
                <svg viewBox="0 0 600 200" preserveAspectRatio="none" className="absolute inset-0 w-full h-full" role="img" aria-label={`Overlaid before and after spectrum, 0 to ${res.ov.fmax} Hz`}>
                  <path d={res.ov.b} fill="none" stroke="var(--sev-act)" strokeWidth="1.25" vectorEffect="non-scaling-stroke" opacity=".85" />
                  <path d={res.ov.a} fill="none" stroke="var(--signal)" strokeWidth="1.25" vectorEffect="non-scaling-stroke" />
                </svg>
              </div>
              <div className="flex gap-4 font-mono text-[11px] leading-none text-fg-2">
                <span className="inline-flex gap-1.5 items-center"><span className="w-3 h-0.5 bg-sev-act" />before</span>
                <span className="inline-flex gap-1.5 items-center"><span className="w-3 h-0.5 bg-signal" />after</span>
                <span className="ml-auto">0–{res.ov.fmax} Hz</span>
              </div>
            </>
          )}
        </div>
      </div>

      {res.hasSpark && res.spark && (
        <div className="flex flex-wrap gap-x-6 gap-y-3.5 px-6 py-[18px] border-t border-line bg-panel-2">
          <div className="min-w-[200px]">
            <div className={SECTION_LABEL}>MUSE SPARK</div>
            <div className="mt-2 inline-flex gap-2 items-center font-semibold" style={{ color: res.spark.color }}>✓ {res.spark.label}</div>
          </div>
          <p className="flex-1 min-w-[240px] m-0 text-[14px] leading-[1.55]">{res.spark.explanation}</p>
          <div className="flex-1 min-w-[200px]">
            <div className={SECTION_LABEL}>NEXT STEP</div>
            <div className="mt-1.5 text-[13.5px] leading-[1.5]">{res.spark.next}</div>
          </div>
        </div>
      )}
      {res.noSpark && (
        <div className="px-6 py-3.5 border-t border-line text-[13px] text-fg-3">Muse Spark verdict not requested for this comparison.</div>
      )}

      <div data-noprint="" className="flex flex-wrap gap-2 justify-between items-center px-5 py-3 border-t border-line font-mono text-[11.5px] leading-[1.4]">
        <span className="text-fg-3 [overflow-wrap:anywhere]">
          <a href={res.before.href}>{res.before.date}&nbsp;before</a> → <a href={res.after.href}>{res.after.date}&nbsp;after</a>
        </span>
        <span className="flex gap-2">
          <button type="button" onClick={rs.print} className="h-8 px-3 border border-line-2 bg-transparent rounded-ctl">Export PDF</button>
          <button type="button" onClick={rs.share} className="h-8 px-3 bg-accent text-on-accent border-0 rounded-ctl font-semibold">Share certificate</button>
        </span>
      </div>
    </article>
  );
}
