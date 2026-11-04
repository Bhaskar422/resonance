import { useState } from 'react';
import { AutoGrid, EvidenceChip, Switch, TileGrid } from '../../components/ui.jsx';

// Run report (hero screen). Ported from the `RUN REPORT` section of the Instrument prototype.
// Everything dynamic comes from v.rep (reportVM in lib/core.js).

const LBL = 'font-mono text-[10.5px] font-medium leading-none tracking-[.12em] text-fg-3';
const HEAD = 'm-0 font-mono text-[11px] font-medium leading-none tracking-[.12em] text-fg-2';
const SUB = 'font-mono text-[11px] leading-none text-fg-3';
const CARD = 'card min-w-0';
const BTN = 'h-9 px-3.5 border border-line-2 bg-panel rounded-ctl text-[13px] transition-colors hover:bg-panel-2 hover:border-fg-3';
const PRIMARY = 'h-9 inline-flex items-center px-3.5 bg-accent text-on-accent rounded-ctl font-semibold text-[13px] no-underline hover:no-underline';

// Panel with the mono header row; `right` is the small caption on the right.
function Sec({ title, right, h = 'h2', className = '', children }) {
  const H = h;
  return (
    <section className={`${CARD} ${className}`}>
      <div className="panel-head flex flex-wrap justify-between gap-2 px-4 py-3 border-b border-line">
        <H className={HEAD}>{title}</H>
        {right != null && <span className={`${SUB} whitespace-nowrap`}>{right}</span>}
      </div>
      {children}
    </section>
  );
}

function Divider({ label, right }) {
  return (
    <div className="flex items-center gap-3 mt-2">
      <span className="font-mono text-[11px] font-semibold leading-none tracking-[.14em] text-signal">{label}</span>
      <span className="flex-1 h-px bg-line" />
      <span className={SUB}>{right}</span>
    </div>
  );
}

function Loading() {
  return (
    <div className="flex flex-col gap-3" aria-busy="true" aria-label="Loading run">
      <div className="h-[90px] bg-panel-2 rounded-card" />
      <div className="h-[140px] bg-panel-2 rounded-card" />
      <AutoGrid min={420} gap={12}>
        <div className="h-[300px] bg-panel-2 rounded-card" />
        <div className="h-[300px] bg-panel-2 rounded-card" />
      </AutoGrid>
    </div>
  );
}

function Failed({ r }) {
  return (
    <div role="alert" className="flex flex-col items-center gap-3 px-6 py-12 border border-sev-stop rounded-card text-center">
      <div className="font-mono text-[11px] font-semibold leading-none tracking-[.14em] text-sev-stop">RUN UNAVAILABLE</div>
      <p className="m-0 text-fg-2">{r.error}</p>
      <div className="flex gap-2.5">
        <button type="button" onClick={r.retry} className={BTN}>Retry</button>
        <a href="#/runs" className="h-9 inline-flex items-center px-3.5">All runs</a>
      </div>
    </div>
  );
}

function Warnings({ r }) {
  return (
    <div role="status" className="flex items-start gap-3 px-3.5 py-[11px] border border-[color-mix(in_oklch,var(--sev-monitor)_60%,transparent)] bg-[color-mix(in_oklch,var(--sev-monitor)_11%,var(--panel))] rounded-card">
      <span className="font-mono text-[10.5px] font-semibold leading-[1.6] tracking-[.08em] text-sev-monitor">WARN</span>
      <div className="flex flex-col gap-1 text-[13px] min-w-0">
        {r.warnings.map((w, i) => <span key={i}>{w.text}</span>)}
      </div>
    </div>
  );
}

function Header({ r }) {
  const pill = 'px-[9px] py-[5px] border border-line-2 bg-panel rounded-chip';
  return (
    <div className="flex flex-wrap justify-between items-end gap-4 pb-4 border-b border-line">
      <div className="min-w-0">
        <div className="font-mono text-[11px] font-medium leading-[1.4] tracking-[.08em] text-fg-3 [overflow-wrap:anywhere]">
          <a href="#/runs">RUNS</a> / {r.runId}
        </div>
        <h1 className="mt-2 mb-2.5 text-[30px] font-semibold tracking-[-.015em]">{r.machine}</h1>
        <div className="flex flex-wrap items-center gap-2 font-mono text-[12px] leading-none text-fg-2 tabular">
          <span className="inline-flex items-center gap-1.5 px-[9px] py-[5px] border rounded-chip font-semibold text-[11px] tracking-[.08em] uppercase"
            style={{ borderColor: `color-mix(in oklch, ${r.sevColor} 55%, transparent)`, color: r.sevColor, background: r.sevTint }}>
            <span className="size-1.5 rounded-full" style={{ background: r.sevColor }} />{r.sevLabel}
          </span>
          <span className={pill}>CONF {r.conf}</span>
          <span className={pill}>COST {r.cost}</span>
          <span>{r.date} · {r.time}</span>
          {r.hasTag && <span className="text-fg-3">{r.tag}</span>}
        </div>
      </div>
      <div data-noprint="" className="flex flex-wrap gap-2">
        <button type="button" onClick={r.print} className={BTN}>Export PDF</button>
        <button type="button" onClick={r.share} className={BTN}>Share link</button>
        <a href={r.rescanHref} className={PRIMARY}>Rescan</a>
      </div>
    </div>
  );
}

function Verdict({ r }) {
  return (
    <section aria-label="Verdict" className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,230px),1fr))] card overflow-hidden">
      <div className="col-span-full flex items-start gap-4 px-5 pt-5 pb-[18px] border-b border-line bg-[linear-gradient(100deg,color-mix(in_oklch,var(--signal)_9%,transparent),transparent_65%)]">
        <span className="shrink-0 mt-1 font-mono text-[10.5px] font-semibold leading-none tracking-[.14em] text-signal">VERDICT</span>
        <p className="m-0 text-[18px] leading-[1.5] [text-wrap:pretty] max-w-[78ch]">{r.summary}</p>
      </div>
      <div className="px-5 py-4 border-r border-line min-w-0">
        <div className={LBL}>PRIMARY FAULT</div>
        <div className="mt-2.5 text-[20px] font-semibold">{r.primary}</div>
        <div className="mt-2.5 h-1 bg-line rounded-chip" role="meter" aria-label="Confidence" aria-valuemin={0} aria-valuemax={100} aria-valuenow={parseInt(r.confW, 10) || 0}>
          <div className="h-full bg-signal rounded-chip" style={{ width: r.confW }} />
        </div>
        <div className="mt-1.5 font-mono text-[11px] leading-none text-fg-3">confidence {r.conf}</div>
      </div>
      <div className="px-5 py-4 border-r border-line min-w-0">
        <div className={LBL}>FREQUENCY</div>
        <div className="mt-2.5 font-mono text-[26px] font-medium leading-none tabular">{r.hz} <span className="text-[13px] text-fg-3">Hz</span></div>
        <div className="mt-2 font-mono text-[12px] leading-none text-fg-2">{r.cpm}{' '}CPM{r.freqRel ? ` · ${r.freqRel}` : ''}</div>
      </div>
      <div className="px-5 py-4 min-w-0">
        <div className={LBL}>NEXT STEP</div>
        <div className="mt-2.5 text-[14px] leading-[1.5]">{r.nextStep}</div>
      </div>
    </section>
  );
}

function VideoPanel({ r }) {
  const vd = r.video;
  const [ready, setReady] = useState('');  // the url that has started playing
  const loading = vd.has && ready !== vd.url;
  return (
    <section className="bg-[#050706] border border-line rounded-card overflow-hidden">
      <div data-noprint="" className="flex flex-wrap justify-between items-center gap-2.5 px-3 py-2.5 border-b border-line bg-panel panel-head">
        <h2 className={HEAD}>VIDEO · side_by_side.mp4</h2>
        <div role="group" aria-label="Video view" className="flex gap-1">
          {vd.tabs.map(t => (
            <button key={t.label} type="button" onClick={t.onClick} aria-pressed={!!t.on}
              className="h-[30px] px-3 border rounded-ctl font-mono text-[11.5px] font-medium leading-none"
              style={{ borderColor: t.bd, background: t.bg, color: t.fg }}>{t.label}</button>
          ))}
        </div>
      </div>
      <div className="scope relative h-[clamp(220px,30vw,360px)] overflow-hidden">
        {vd.has ? (
          <>
            <video key={vd.url} src={vd.url} poster={vd.poster || undefined} autoPlay muted loop playsInline preload="auto" aria-label="Original and magnified motion"
              onPlaying={() => setReady(vd.url)} className="block h-full max-w-none object-cover" style={{ width: vd.w, transform: vd.x }} />
            {loading && (
              <div role="status" className="absolute inset-0 flex items-center justify-center bg-[rgba(5,7,6,.45)]">
                <span className="inline-flex items-center gap-2.5 px-3.5 py-2 rounded-chip bg-[rgba(5,7,6,.85)] border border-line font-mono text-[12px] text-[#cfd8d4]">
                  <span className="size-3.5 rounded-full border-2 border-[#3a4541] border-t-[var(--accent)] animate-spin" />Loading video…
                </span>
              </div>
            )}
          </>
        ) : (
          <>
            <canvas ref={r.motionRef} role="img" aria-label="Simulated original vs magnified motion" className="absolute inset-0 block w-full h-full" />
            <span className="absolute left-3 bottom-2.5 font-mono text-[10.5px] leading-none text-[#6f7b77]">Simulated preview · the real side_by_side.mp4 plays here on live runs</span>
          </>
        )}
      </div>
    </section>
  );
}

function Tile({ label, value, unit, signal, edge = 'var(--info)' }) {
  return (
    <div className="edge bg-panel p-4 min-w-0" style={{ '--edge': signal ? 'var(--signal)' : edge }}>
      <div className={LBL}>{label}</div>
      <div className={`mt-3 font-mono text-[30px] font-medium leading-none tabular ${signal ? 'text-signal' : ''}`}>{value}</div>
      <div className="mt-1.5 font-mono text-[11px] leading-none text-fg-3">{unit}</div>
    </div>
  );
}

function Measurements({ r }) {
  return (
    <TileGrid min={150}>
      <Tile label="FREQUENCY" value={r.hz} unit={`Hz · ±${r.res}`} signal />
      <Tile label="SPEED" value={r.cpm} unit="CPM" />
      <Tile label="AMPLITUDE" value={r.px} unit="px peak" edge="var(--violet)" />
      <Tile label="SNR" value={r.snr} unit="signal / noise" edge="var(--c3)" />
      <div className="edge bg-panel px-4 py-3.5 flex items-center gap-3.5 min-w-0" style={{ '--edge': 'var(--c5)' }}>
        <div role="img" aria-label={`Vibration direction ${r.dirDeg}`}
          className="relative size-[76px] shrink-0 border border-line-2 rounded-full [background-image:linear-gradient(var(--line)_1px,transparent_1px),linear-gradient(90deg,var(--line)_1px,transparent_1px)] [background-size:100%_50%,50%_100%] [background-position:0_-.5px,-.5px_0]">
          <div className="absolute left-2 right-2 top-1/2 h-0.5 -mt-px bg-signal shadow-[0_0_8px_var(--signal-dim)]" style={{ transform: r.dirRot }} />
          <div className="absolute left-1/2 top-1/2 size-1.5 -m-[3px] rounded-full bg-fg" />
        </div>
        <div className="min-w-0">
          <div className={LBL}>DIRECTION</div>
          <div className="mt-2 font-mono text-[22px] font-medium leading-none">{r.dirDeg}</div>
          <div className="mt-1.5 text-[12px] text-fg-2">{r.dirLabel}</div>
        </div>
      </div>
    </TileGrid>
  );
}

function Spectrum({ r }) {
  const s = r.spec;
  const ticks = [];
  for (let f = 0; f <= s.fmax; f += 20) ticks.push(f);
  return (
    <Sec title="SPECTRUM · LOG AMPLITUDE" right={`0–${s.fmax} Hz`}>
      <div className="p-4">
        {s.hasImg ? (
          <div role="img" aria-label="Vibration spectrum" className="block w-full rounded-chip aspect-[3/1]" style={{ background: s.imgBg }} />
        ) : (
          <>
            <div role="img" aria-label={`Vibration spectrum, peaks: ${s.markers.map(k => k.label).join(', ') || 'none'}`}
              className="relative h-[220px] border-b border-line-2 [overflow-x:clip] [background-image:linear-gradient(var(--grid)_1px,transparent_1px),linear-gradient(90deg,var(--grid)_1px,transparent_1px)] [background-size:100%_20%,16.666%_100%]">
              <svg viewBox="0 0 600 200" preserveAspectRatio="none" aria-hidden="true" className="absolute inset-0 w-full h-full">
                <path d={s.area} style={{ fill: 'var(--signal-dim)', opacity: 0.5 }} />
                <path d={s.line} vectorEffect="non-scaling-stroke" style={{ fill: 'none', stroke: 'var(--signal)', strokeWidth: 1.25 }} />
              </svg>
              {s.markers.map(k => (
                <span key={k.label} className="absolute translate-x-1.5 -translate-y-1 font-mono text-[10.5px] font-medium leading-none text-fg bg-panel px-1 py-0.5 border border-line-2 whitespace-nowrap"
                  style={{ left: k.left, top: k.top }}>{k.label}</span>
              ))}
            </div>
            <div className="flex justify-between mt-1.5 font-mono text-[10px] leading-none text-fg-3" aria-hidden="true">
              {ticks.map((f, i) => <span key={f}>{i === ticks.length - 1 ? `${f} Hz` : f}</span>)}
            </div>
          </>
        )}
      </div>
    </Sec>
  );
}

function Harmonics({ r }) {
  return (
    <Sec title="HARMONICS 1×–6×" right="relative to 1×">
      <div className="grid grid-cols-6 gap-2.5 p-4 items-end">
        {r.harm.map(h => (
          <div key={h.order} className="flex flex-col gap-1.5 items-stretch min-w-0">
            <span className="font-mono text-[11px] font-medium leading-none text-center text-fg-2">{h.rel}</span>
            <div className="h-[150px] flex items-end border-b border-line-2">
              <div className="w-full rounded-t-chip" style={{ height: h.h, background: h.color }} aria-hidden="true" />
            </div>
            <span className="font-mono text-[13px] font-semibold leading-none text-center">{h.order}</span>
            <span className="font-mono text-[10px] leading-[1.3] text-center text-fg-3">{h.hz}{' '}Hz</span>
            <span className="font-mono text-[10px] leading-[1.3] text-center text-fg-3">{h.status}</span>
          </div>
        ))}
      </div>
    </Sec>
  );
}

function Segmentation({ r }) {
  const m = r.mask;
  return (
    <Sec title={`SEGMENTATION · ${m.source}`} right={`prompt “${m.prompt}”`}>
      <div className="p-4 flex flex-col gap-3">
        <div role="img" aria-label={`Segmentation mask for “${m.prompt}”`} className="relative aspect-[16/10] border border-line rounded-chip overflow-hidden" style={{ background: m.bg }}>
          <span className="absolute left-2.5 top-2.5 font-mono text-[10.5px] leading-none text-fg-3">{m.label}</span>
          {m.box && (
            <div className="absolute border-[1.5px] border-signal bg-[color-mix(in_oklch,var(--signal)_14%,transparent)]"
              style={{ left: m.box.left, top: m.box.top, width: m.box.width, height: m.box.height }}>
              <span className="absolute left-[-1.5px] -top-5 px-1.5 py-[3px] bg-signal text-on-accent font-mono text-[10px] font-semibold leading-none whitespace-nowrap">{m.prompt} · {m.conf}</span>
            </div>
          )}
        </div>
        <div className="flex flex-wrap gap-x-[18px] gap-y-1.5 font-mono text-[12px] leading-[1.4] text-fg-2">
          <span>measured {m.area}</span><span>fast-motion excluded {m.excluded}</span>
        </div>
      </div>
    </Sec>
  );
}

function CrossChecks({ r }) {
  const a = r.acc, rot = r.rot;
  const box = 'p-3 border border-line-2 rounded-ctl min-w-0';
  return (
    <section className={`${CARD} flex flex-col`}>
      <div className="px-4 py-3 border-b border-line"><h2 className={HEAD}>CROSS-CHECKS</h2></div>
      <div className="p-4 flex flex-col gap-3.5">
        {r.hasAcc && a && (
          <div className="flex items-center gap-3.5 p-3.5 border rounded-ctl" style={{ borderColor: a.color, background: `color-mix(in oklch, ${a.color} 7%, transparent)` }}>
            <span className="font-mono text-[20px] font-semibold leading-none" style={{ color: a.color }} aria-hidden="true">{a.agrees ? '✓' : '✕'}</span>
            <div className="flex-1 min-w-0">
              <div className="font-semibold">{a.label}</div>
              <div className="font-mono text-[12px] leading-[1.5] text-fg-2">{a.source}{' '}peak {a.hz} · {a.delta}{' '}from camera</div>
            </div>
          </div>
        )}
        {r.noAcc && (
          <div className="p-3.5 border border-dashed border-line-2 rounded-ctl text-[13px] text-fg-2">No accelerometer recording attached. Add a phyphox CSV next time to cross-check the camera.</div>
        )}
        {rot && (
          <div className="flex flex-col gap-2.5">
            <div className={LBL}>ROTATION RELATION</div>
            <div className="grid grid-cols-[1fr_auto_1fr] gap-2.5 items-center">
              <div className={box}>
                <div className="font-mono text-[10.5px] leading-none text-fg-3">MEASURED</div>
                <div className="mt-1.5 font-mono text-[18px] font-medium leading-none tabular">{rot.measured}</div>
                <div className="mt-1 font-mono text-[11px] leading-none text-fg-3">{rot.measuredRpm}</div>
              </div>
              <span className="font-mono text-[14px] font-medium leading-none text-signal" aria-label="approximately equals">≈</span>
              <div className={box}>
                <div className="font-mono text-[10.5px] leading-none text-fg-3">RATED</div>
                <div className="mt-1.5 font-mono text-[18px] font-medium leading-none tabular">{rot.rated}</div>
                <div className="mt-1 font-mono text-[11px] leading-[1.2] text-fg-3">{rot.source}</div>
              </div>
            </div>
            <p className="m-0 text-[13px] text-fg-2 leading-[1.5]">{rot.relation}</p>
          </div>
        )}
      </div>
    </section>
  );
}

function NoDiagnosis({ dx }) {
  return (
    <div className="flex flex-col items-center gap-2.5 px-6 py-11 border border-dashed border-line-2 rounded-card text-center">
      <div className="font-mono text-[11px] font-medium leading-none tracking-[.14em] text-fg-3">NO DIAGNOSIS</div>
      <h2 className="m-0 text-[19px] font-semibold">This run was measured but not diagnosed</h2>
      <p className="m-0 text-fg-2 max-w-[520px]">The spectrum and harmonics above are complete. Diagnose this run to get a ranked fault list with evidence, repair steps and, optionally, the fix drawn on your frame. The measurement is reused; nothing is uploaded again.</p>

      {dx.running ? (
        <div role="status" aria-live="polite" className="w-full max-w-[520px] mt-2 border border-line rounded-card text-left">
          {dx.stages.map(g => (
            <div key={g.key} className="flex items-center gap-3 px-3.5 py-[11px] border-b border-line last:border-b-0" style={{ opacity: g.st === 'pending' ? 0.5 : 1 }}>
              <span className={`size-2.5 rounded-full shrink-0 ${g.st === 'running' ? 'animate-pulse' : ''}`} style={{ background: g.color }} />
              <span className="flex-1 text-[13.5px]">{g.desc}</span>
              <span className="font-mono text-[10px] font-semibold uppercase" style={{ color: g.color }}>{{ pending: 'Waiting', running: 'Running', done: 'Done', error: 'Failed' }[g.st]}</span>
            </div>
          ))}
          <div className="px-3.5 py-2 font-mono text-[11px] text-fg-3 tabular">{dx.elapsed} · usually 30–90 s</div>
        </div>
      ) : (
        <>
          <div className="flex flex-wrap items-center justify-center gap-x-6 gap-y-3 mt-2">
            <label className="flex items-center gap-2.5 text-[13px] text-fg-2">
              <Switch sw={dx.visualize} label="Also show the fix with Muse Image" />
              Also show the fix (Muse Image)
            </label>
            <span className="flex items-center gap-2 text-[13px] text-fg-2">
              {dx.hasManual ? (
                <>
                  <span className="font-mono text-[11.5px] text-c4">MAN · {dx.manualName}</span>
                  <button type="button" onClick={dx.clearManual} className="border-0 bg-transparent text-fg-3 text-[12px] underline">Remove</button>
                </>
              ) : (
                <label className="relative cursor-pointer underline">
                  Attach the manual (PDF, optional)
                  <input type="file" accept="application/pdf,.pdf" onChange={dx.onManual} className="absolute inset-0 opacity-0 cursor-pointer" aria-label="Attach the machine's manual as a PDF" />
                </label>
              )}
            </span>
          </div>
          {dx.hasError && <p role="alert" className="m-0 max-w-[520px] text-[13px] text-sev-stop">{dx.error}</p>}
          <button type="button" onClick={dx.start} className={`${PRIMARY} border-0 mt-1`}>
            {dx.hasError ? 'Try again' : 'Diagnose this run'} · {dx.cost}
          </button>
          {!dx.live && <p className="m-0 text-[12px] text-fg-3">Sample mode: switch to Live API in Settings to diagnose your own runs.</p>}
        </>
      )}
    </div>
  );
}

function Diagnosis({ r }) {
  const sel = r.sel;
  return (
    <>
      <Divider label="§ DIAGNOSIS" right="Muse Spark" />
      <section aria-label="Diagnosis" className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,340px),1fr))] card overflow-hidden">
        <div className="border-r border-line p-2 min-w-0">
          <div className={`px-2 pt-2 pb-2.5 ${LBL}`}>RANKED FAULTS</div>
          {r.faults.map(f => (
            <button key={f.rank} type="button" onClick={f.onClick} aria-pressed={!!f.on}
              className="flex flex-col gap-2 w-full text-left p-3 mb-1.5 border rounded-ctl text-fg"
              style={{ borderColor: f.bd, background: f.bg }}>
              <span className="flex justify-between items-baseline gap-2.5">
                <span className="font-semibold"><span className="mr-2 font-mono text-[11px] font-medium leading-none text-fg-3">{f.rank}</span>{f.name}</span>
                <span className="font-mono text-[15px] font-semibold leading-none tabular">{f.pct}</span>
              </span>
              <span className="block h-1 bg-line rounded-chip"><span className="block h-full bg-signal rounded-chip" style={{ width: f.w }} /></span>
              <span className="font-mono text-[11px] leading-none text-fg-3">{f.freq} · {f.rel} · {f.nSup}{' '}for / {f.nCon}{' '}against</span>
            </button>
          ))}
        </div>
        {sel && (
          <div className="px-[18px] py-4 flex flex-col gap-3.5 min-w-0" aria-live="polite">
            <div className="flex flex-wrap justify-between items-baseline gap-2">
              <h3 className="m-0 text-[17px] font-semibold">Evidence · {sel.name}</h3>
              <span className="font-mono text-[12px] leading-none text-fg-3">{sel.freq} · {sel.rel}</span>
            </div>
            <div className="font-mono text-[10.5px] font-medium leading-none tracking-[.12em] text-sev-normal">SUPPORTING</div>
            {sel.sup.map((e, i) => (
              <div key={i} className="flex items-start gap-3 pb-2.5 border-b border-line">
                <span title={e.srcLabel} className="shrink-0 tracking-[.04em]"><EvidenceChip e={e} wide /></span>
                <span className="text-[13.5px] leading-[1.5] min-w-0">{e.detail}</span>
              </div>
            ))}
            <div className="mt-1 font-mono text-[10.5px] font-medium leading-none tracking-[.12em] text-sev-act">CONTRADICTING</div>
            {sel.con.map((c, i) => (
              <div key={i} className="flex gap-2.5 text-[13.5px] leading-[1.5]">
                <span className="font-mono text-[12px] font-semibold leading-[1.5] text-sev-act" aria-label="against">−</span>
                <span className="min-w-0">{c.detail}</span>
              </div>
            ))}
            {sel.noCon && <div className="text-[13px] text-fg-3">Nothing contradicts this fault.</div>}
          </div>
        )}
      </section>
      {r.hasUnc && (
        <section className="flex flex-col gap-2 px-4 py-3.5 border border-dashed border-line-2 rounded-card">
          <h3 className="m-0 font-mono text-[10.5px] font-medium leading-none tracking-[.12em] text-fg-3">WHAT WE’RE UNSURE ABOUT</h3>
          {r.unc.map((u, i) => (
            <div key={i} className="flex gap-2.5 text-[13.5px] text-fg-2 leading-[1.5]">
              <span className="font-mono text-fg-3" aria-hidden="true">?</span>{u.text}
            </div>
          ))}
        </section>
      )}
    </>
  );
}

function FixSlider({ r }) {
  const s = r.slider;
  const tagCls = 'absolute bottom-2.5 px-1.5 py-[3px] font-mono text-[10px] font-semibold leading-none';
  return (
    <Sec title="NOW ↔ AFTER THE FIX" right="drag" h="h3">
      <div className="p-4">
        <div className="relative aspect-[4/3] border border-line rounded-chip overflow-hidden select-none">
          <div className="absolute inset-0" style={{ background: s.after }}>
            <span className="absolute right-2.5 top-2.5 font-mono text-[10.5px] leading-none text-fg-3">{s.afterLabel}</span>
          </div>
          <div className="absolute inset-0 bg-panel-2" style={{ clipPath: s.clip }}>
            <div className="absolute inset-0" style={{ background: s.before }} />
            <span className="absolute left-2.5 top-2.5 font-mono text-[10.5px] leading-none text-fg-3">{s.beforeLabel}</span>
          </div>
          <div className="absolute top-0 bottom-0 w-0.5 -ml-px bg-signal pointer-events-none" style={{ left: s.left }}>
            <span className="absolute top-1/2 left-1/2 size-[30px] -m-[15px] rounded-full bg-signal text-on-accent grid place-items-center font-mono text-[12px] font-semibold leading-none" aria-hidden="true">⇔</span>
          </div>
          <span className={`${tagCls} left-2.5 bg-bg`}>NOW</span>
          <span className={`${tagCls} right-2.5 bg-signal text-on-accent`}>AFTER FIX</span>
          <input type="range" min="0" max="100" value={s.pos} onChange={s.onInput} aria-label="Compare now and after the fix"
            className="absolute inset-0 w-full h-full m-0 opacity-0 cursor-ew-resize" />
        </div>
        <p className="mt-3 mb-0 text-[13px] text-fg-2 leading-[1.5]">{r.fixedDesc}</p>
      </div>
    </Sec>
  );
}

function FixPlan({ r }) {
  const w = r.where;
  return (
    <>
      <Divider label="§ FIX PLAN" right="Muse Image" />
      <AutoGrid min={420}>
        <section className={CARD}>
          <div className="px-4 py-3 border-b border-line"><h3 className={HEAD}>REPAIR STEPS</h3></div>
          <ol className="m-0 p-0 list-none">
            {r.actions.map(a => (
              <li key={a.n} className="flex gap-3.5 px-4 py-3.5 border-b border-line">
                <span className="font-mono text-[20px] font-semibold leading-none text-signal" aria-hidden="true">{a.n}</span>
                <div className="flex flex-col gap-2 min-w-0">
                  <span className="text-[14px] leading-[1.5]">{a.step}</span>
                  <span className="flex flex-wrap gap-1.5 font-mono text-[11px] leading-none">
                    <span className="px-[7px] py-1 border border-line-2 rounded-chip text-fg-2">AT {a.where}</span>
                    <span className="px-[7px] py-1 border border-c4 text-c4 rounded-chip">{a.page}</span>
                  </span>
                </div>
              </li>
            ))}
          </ol>
          <div className="px-4 py-3.5 flex flex-col gap-1.5">
            <span className={LBL}>WHAT THE RESCAN SHOULD SHOW</span>
            <span className="text-[13.5px] leading-[1.5]">{r.expect}</span>
          </div>
        </section>
        <Sec title="WHERE TO ACT" right="where_to_act.png" h="h3">
          <div className="p-4">
            <div role="img" aria-label={w.hasPt ? `Where to act: ${w.pt}` : 'Where to act'} className="relative aspect-[4/3] border border-line rounded-chip overflow-hidden" style={{ background: w.bg }}>
              <span className="absolute left-2.5 top-2.5 font-mono text-[10.5px] leading-none text-fg-3">{w.label}</span>
              {w.hasPt && (
                <>
                  <div className="absolute size-11 -m-[22px] border-2 border-sev-act rounded-full shadow-[0_0_0_6px_color-mix(in_oklch,var(--sev-act)_22%,transparent)]" style={{ left: w.x, top: w.y }} />
                  <span className="absolute translate-x-[30px] -translate-y-1/2 px-2 py-1 bg-sev-act text-[#120800] font-mono text-[11px] font-semibold leading-[1.2] whitespace-nowrap" style={{ left: w.x, top: w.y }}>{w.pt}</span>
                </>
              )}
            </div>
          </div>
        </Sec>
      </AutoGrid>
      {r.noViz && (
        <div className="p-[22px] border border-dashed border-line-2 rounded-card text-fg-2 text-[13.5px]">No fix visualization for this run. Turn on “Show the fix” in Analyze to see the repair drawn on your frame with Muse Image.</div>
      )}
      <AutoGrid min={420}>
        {r.viz && <FixSlider r={r} />}
        <section className={CARD}>
          <div className="px-4 py-3 border-b border-line"><h3 className={HEAD}>MANUAL CITATIONS</h3></div>
          {r.noCites && <div className="px-4 py-5 text-fg-2 text-[13px]">No manual attached. Add the PDF to get quotes checked against the source.</div>}
          {r.cites.map((c, i) => (
            <div key={i} className="px-4 py-3.5 border-b border-line flex flex-col gap-2">
              <div className="flex flex-wrap items-center gap-1.5 font-mono text-[10.5px] font-medium leading-none">
                <span className="px-[7px] py-1 border rounded-chip font-semibold tracking-[.06em] uppercase" style={{ borderColor: c.color, color: c.color, background: c.tintc }}>{c.badge}</span>
                <span className="text-fg-2">{c.page}</span>
                <span className="text-fg-3">{c.found} · {c.score}</span>
              </div>
              <blockquote className="m-0 text-[14px] leading-[1.55] pl-3 border-l-2 border-line-2">“{c.quote}”</blockquote>
              <span className="text-[12px] text-fg-3">{c.relevance}</span>
            </div>
          ))}
        </section>
      </AutoGrid>
    </>
  );
}

// Muse Spark found nothing wrong: no repair steps to draw, nothing to prove with a rescan.
function NoFixNeeded({ r }) {
  return (
    <>
      <Divider label="§ RESULT" right="Muse Spark" />
      <AutoGrid min={420}>
        <section className={CARD}>
          <div className="flex items-start gap-3.5 px-4 py-4 border-b border-line">
            <span className="grid place-items-center size-8 shrink-0 rounded-full border-2 border-sev-normal text-sev-normal font-semibold" aria-hidden="true">✓</span>
            <div className="flex flex-col gap-1">
              <h3 className="m-0 text-[17px] font-semibold text-sev-normal">No fix needed</h3>
              <span className="text-[13.5px] text-fg-2 leading-[1.5]">No fault found ({r.conf} confident).{r.vizSkipped ? ' The fix images were skipped, so nothing was spent on them.' : ''}</span>
            </div>
          </div>
          {r.actions.length > 0 && (
            <>
              <div className="px-4 pt-3.5"><h4 className={HEAD}>RECOMMENDED</h4></div>
              <ol className="m-0 p-0 list-none">
                {r.actions.map(a => (
                  <li key={a.n} className="flex gap-3.5 px-4 py-3 border-b border-line last:border-b-0">
                    <span className="font-mono text-[16px] font-semibold leading-none text-fg-3" aria-hidden="true">{a.n}</span>
                    <span className="text-[14px] leading-[1.5]">{a.step}</span>
                  </li>
                ))}
              </ol>
            </>
          )}
          {r.expect && (
            <div className="px-4 py-3.5 flex flex-col gap-1.5 border-t border-line">
              <span className={LBL}>WHAT A FUTURE SCAN SHOULD SHOW</span>
              <span className="text-[13.5px] leading-[1.5]">{r.expect}</span>
            </div>
          )}
        </section>
        {r.hasCites && (
          <section className={CARD}>
            <div className="px-4 py-3 border-b border-line"><h3 className={HEAD}>MANUAL CITATIONS</h3></div>
            {r.cites.map((c, i) => (
              <div key={i} className="px-4 py-3.5 border-b border-line flex flex-col gap-2">
                <span className="font-mono text-[10.5px] text-fg-2">{c.badge} · {c.page} · {c.found}</span>
                <blockquote className="m-0 text-[14px] leading-[1.55] pl-3 border-l-2 border-line-2">“{c.quote}”</blockquote>
              </div>
            ))}
          </section>
        )}
      </AutoGrid>
    </>
  );
}

function RescanCta({ r }) {
  if (r.noFault) {
    return (
      <section data-noprint="" className="flex flex-wrap items-center justify-between gap-4 p-[22px] border border-line rounded-card bg-panel">
        <div>
          <div className="text-[17px] font-semibold">Healthy today. Scan again later to track it.</div>
          <div className="mt-1 text-fg-2 text-[13.5px]">A later scan from the same spot shows whether the vibration starts to grow.</div>
        </div>
        <a href={r.rescanHref} className="h-10 inline-flex items-center px-4 border border-line-2 rounded-ctl text-fg text-[13px] no-underline hover:no-underline">Scan again</a>
      </section>
    );
  }
  return (
    <section data-noprint="" className="flex flex-wrap items-center justify-between gap-4 p-[22px] border border-signal rounded-card bg-[color-mix(in_oklch,var(--signal)_7%,var(--panel))]">
      <div>
        <div className="text-[19px] font-semibold">Fixed it? Rescan from the same spot.</div>
        <div className="mt-1 text-fg-2 text-[13.5px]">Same angle, same distance. Resonance compares both runs and issues a certificate of fix.</div>
      </div>
      <div className="flex flex-wrap gap-2">
        {r.hasCompare && (
          <a href={r.compareHref} className="h-10 inline-flex items-center px-4 border border-line-2 rounded-ctl text-fg text-[13px] no-underline hover:no-underline">View certificate</a>
        )}
        <a href={r.rescanHref} className="h-10 inline-flex items-center px-[18px] bg-accent text-on-accent rounded-ctl font-semibold no-underline hover:no-underline">Start rescan</a>
      </div>
    </section>
  );
}

export default function Report({ v }) {
  const r = v.rep;
  if (!r) return null;
  return (
    <div className="flex flex-col gap-4">
      {r.loading && <Loading />}
      {r.failed && <Failed r={r} />}
      {r.ok && (
        <div className="flex flex-col gap-4">
          {r.hasWarnings && <Warnings r={r} />}
          <Header r={r} />
          {r.diag && <Verdict r={r} />}
          <VideoPanel r={r} />
          <Measurements r={r} />
          <AutoGrid min={440}>
            <Spectrum r={r} />
            <Harmonics r={r} />
            <Segmentation r={r} />
            <CrossChecks r={r} />
          </AutoGrid>
          {r.noDiag && <NoDiagnosis dx={r.dx} />}
          {r.diag && (
            <div className="flex flex-col gap-4">
              <Diagnosis r={r} />
              {r.noFault ? <NoFixNeeded r={r} /> : <FixPlan r={r} />}
            </div>
          )}
          <RescanCta r={r} />
        </div>
      )}
    </div>
  );
}
