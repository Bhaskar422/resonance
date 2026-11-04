import { Eyebrow, Switch, tint } from '../../components/ui.jsx';

const H2 = 'm-0 text-[18px] font-semibold';
const FIELD_LABEL = 'font-mono text-[10.5px] font-medium leading-none tracking-[.1em] text-fg-3';
const INPUT = 'h-10 px-3 bg-bg border border-line-2 rounded-ctl text-fg min-w-0';
const PRIMARY = 'h-10 px-[18px] bg-accent text-on-accent border-0 rounded-ctl font-semibold disabled:opacity-45 disabled:cursor-not-allowed';
const SECONDARY = 'border border-line-2 bg-transparent rounded-ctl';
const GRID = min => ({ gridTemplateColumns: `repeat(auto-fit, minmax(min(100%, ${min}px), 1fr))` });

export default function Analyze({ v }) {
  const az = v.az;
  if (!az) return null;
  return (
    <div className="flex flex-col gap-[18px] max-w-[980px]">
      <div>
        <Eyebrow>CH 03 · ACQUIRE</Eyebrow>
        <h1 className="mt-2 mb-0 text-[26px] font-semibold">New analysis</h1>
      </div>

      {az.isRescan && (
        <div className="flex items-center gap-3.5 p-3 border border-signal rounded-card">
          <div className="w-24 aspect-[4/3] shrink-0 border border-line opacity-80" style={{ background: az.rescanBg }} />
          <div className="min-w-0">
            <div className="font-semibold">Rescan of {az.machine}</div>
            <div className="text-[13px] text-fg-2">Match the original framing: same spot, same distance, same fps. The result opens as a certificate of fix.</div>
          </div>
        </div>
      )}

      <ol className="list-none m-0 p-0 flex flex-wrap gap-1.5" aria-label="Steps">
        {az.steps.map(s => (
          <li key={s.n} className="flex-[1_1_120px]">
            <button type="button" onClick={s.go} aria-current={s.on ? 'step' : undefined}
              className="w-full flex items-center gap-2.5 px-3 py-2.5 border rounded-ctl text-left"
              style={{ borderColor: s.bd, background: s.bg, color: s.fg }}>
              <span className="font-mono text-[11px] font-semibold leading-none">{s.mark}</span>
              <span className="text-[13px] font-medium">{s.label}</span>
            </button>
          </li>
        ))}
      </ol>

      <section className="card p-[22px] flex flex-col gap-[18px] min-w-0">
        {az.s1 && <StepVideo az={az} />}
        {az.s2 && <StepDescribe az={az} />}
        {az.s3 && <StepEvidence az={az} />}
        {az.s4 && <StepOptions az={az} />}
        {az.s5 && <StepRun az={az} />}

        <div className="flex justify-between gap-2.5 pt-4 border-t border-line">
          {az.idle && <button type="button" onClick={az.back} className={`h-10 px-4 ${SECONDARY}`}>Back</button>}
          <span className="flex-1" />
          {(az.s1 || az.s2) && <button type="button" onClick={az.next} disabled={az.nextDisabled} className={PRIMARY}>Continue</button>}
          {az.s3 && <button type="button" onClick={az.next} className={PRIMARY}>Continue</button>}
          {az.s4 && <button type="button" onClick={az.start} className={PRIMARY}>Run analysis · {az.est}</button>}
        </div>
      </section>
    </div>
  );
}

function StepVideo({ az }) {
  return (
    <div className="flex flex-col gap-4">
      <div>
        <h2 className={H2}>Upload a slow-motion clip</h2>
        <p className="mt-1 mb-0 text-fg-2 text-[13.5px]">10 seconds at 240 fps, phone braced, machine filling a third of the frame. <a href="#/guide">Recording guide</a></p>
      </div>
      {az.noFile && (
        <>
          <div onDrop={az.onDrop} onDragOver={az.onDragOver} onDragLeave={az.onDragLeave}
            className="relative px-5 py-12 border-[1.5px] border-dashed rounded-card text-center flex flex-col gap-2 items-center"
            style={{ borderColor: az.dropBd, background: az.dropBg }}>
            <span className="font-mono text-[28px] font-medium leading-none text-signal" aria-hidden="true">⤒</span>
            <span className="font-semibold">Drop a video here, or click to browse</span>
            <span className="font-mono text-[12px] leading-none text-fg-3">.mov · .mp4 · up to 100 MB</span>
            <input type="file" accept="video/*" onChange={az.onFile} aria-label="Choose a video" className="absolute inset-0 w-full h-full opacity-0 cursor-pointer" />
          </div>
          {az.isSample && (
            <button type="button" onClick={az.useSample} className={`self-start h-9 px-3.5 text-[13px] ${SECONDARY}`}>Use the sample desk-fan clip</button>
          )}
          {az.hasExamples && (
            <div className="flex flex-col gap-2.5">
              <div className="font-mono text-[11px] font-medium leading-none tracking-[.12em] text-fg-2">NO FOOTAGE? TRY ONE OF OURS</div>
              <div className="grid gap-2.5" style={GRID(220)}>
                {az.examples.map(e => (
                  <button key={e.id} type="button" onClick={e.use} className="card text-left p-3.5 flex flex-col gap-1.5 hover:border-[var(--accent)] cursor-pointer">
                    {e.thumb && <img src={e.thumb} alt="" className="block w-full aspect-video object-cover rounded-chip border border-line mb-1" />}
                    <span className="font-semibold text-[14px]">{e.title}</span>
                    {e.note && <span className="text-fg-2 text-[12.5px] leading-[1.45]">{e.note}</span>}
                    <span className="font-mono text-[11px] text-fg-3">{e.size_mb} MB{e.accel ? ' · + phyphox' : ''}{e.manual ? ' · + manual' : ''}</span>
                  </button>
                ))}
              </div>
            </div>
          )}
        </>
      )}
      {az.hasFile && (
        <div className="grid gap-4 items-start" style={GRID(280)}>
          <div className="relative aspect-video stripe border border-line rounded-chip overflow-hidden">
            {az.hasPreview && (
              <video src={az.previewUrl} muted playsInline preload="metadata" onLoadedMetadata={az.onMeta}
                className="block w-full h-full object-cover" aria-label="First frame of the clip" />
            )}
            <span className="absolute left-2.5 bottom-2.5 font-mono text-[10.5px] font-medium leading-none bg-bg px-1.5 py-[3px]">FRAME 0001</span>
          </div>
          <div className="flex flex-col gap-2.5 font-mono text-[12.5px] leading-[1.4] min-w-0">
            {az.exampleTitle && <div className="font-mono text-[10.5px] font-medium tracking-[.12em] text-signal">EXAMPLE CLIP · {az.exampleTitle}</div>}
            <div className="font-sans font-semibold text-[15px] [overflow-wrap:anywhere]">{az.fileName}</div>
            <div className="text-fg-2">{az.fileSize} · {az.resolution}</div>
            <button type="button" onClick={az.clearFile} className={`self-start h-8 px-3 ${SECONDARY}`}>Replace video</button>
          </div>
        </div>
      )}
    </div>
  );
}

function StepDescribe({ az }) {
  const auto = !az.fps;
  return (
    <div className="flex flex-col gap-4">
      <h2 className={H2}>Describe the clip</h2>
      <div className="grid gap-3.5" style={GRID(260)}>
        <label className="flex flex-col gap-1.5">
          <span className={FIELD_LABEL}>WHAT TO SEGMENT *</span>
          <input value={az.prompt} onChange={az.onPrompt} placeholder="fan" required className={INPUT} />
          <span className="text-[12px] text-fg-3">One or two words SAM 3.1 can find: fan, pump, motor.</span>
        </label>
        <label className="flex flex-col gap-1.5">
          <span className={FIELD_LABEL}>MACHINE NAME / MODEL</span>
          <input value={az.machine} onChange={az.onMachine} placeholder="Desk fan, Vornado 630" className={INPUT} />
          <span className="text-[12px] text-fg-3">Groups runs and helps Muse Spark find the rated speed.</span>
        </label>
        <div className="flex flex-col gap-1.5" role="group" aria-labelledby="az-fps-label">
          <span id="az-fps-label" className={FIELD_LABEL}>CAPTURE FPS *</span>
          <div className="flex gap-1.5">
            {az.fpsOpts.map(o => (
              <button key={o.label} type="button" onClick={o.onClick} aria-pressed={!!o.on}
                className="flex-1 min-w-0 h-10 border rounded-ctl font-mono text-[12.5px] font-medium leading-none"
                style={{ borderColor: o.bd, background: o.bg, color: o.fg }}>{o.label}</button>
            ))}
          </div>
          <input type="number" min="1" value={auto ? '' : az.fps} placeholder="auto" onChange={az.onFps} aria-label="Custom fps"
            className="h-9 px-3 bg-bg border border-line-2 rounded-ctl text-fg font-mono min-w-0" />
        </div>
        <label className="flex flex-col gap-1.5">
          <span className={FIELD_LABEL}>DURATION · S *</span>
          <input type="number" min="1" step="0.1" value={az.duration} onChange={az.onDuration} required className={`${INPUT} font-mono`} />
          <span className="font-mono text-[12px] leading-[1.4] text-fg-3" aria-live="polite">Max measurable {az.nyquist} · resolution {az.resHz}</span>
        </label>
      </div>
    </div>
  );
}

function EvidenceCard({ code, color, title, desc, accept, chooseLabel, has, name, onChoose, onClear, onSample, isSample }) {
  return (
    <div className="relative p-[18px] border border-line-2 rounded-card flex flex-col gap-2 min-w-0">
      <span className="font-mono text-[10.5px] font-semibold leading-none tracking-[.1em]" style={{ color }}>{code}</span>
      <span className="font-semibold">{title}</span>
      <span className="text-[13px] text-fg-2">{desc}</span>
      {!has && (
        <div className="flex gap-2 flex-wrap">
          <label className="relative h-[34px] inline-flex items-center px-3 border border-line-2 rounded-ctl cursor-pointer text-[13px] focus-within:outline-2 focus-within:outline-focus focus-within:outline-offset-2">
            {chooseLabel}
            <input type="file" accept={accept} onChange={onChoose} aria-label={`${chooseLabel}: ${title}`} className="absolute inset-0 w-full h-full opacity-0 cursor-pointer" />
          </label>
          {isSample && <button type="button" onClick={onSample} className="h-[34px] px-3 border-0 bg-transparent text-accent text-[13px]">Use sample</button>}
        </div>
      )}
      {has && (
        <div className="flex gap-2 items-center font-mono text-[12.5px] leading-[1.3]">
          <span className="text-ok" aria-hidden="true">✓</span>
          <span className="flex-1 min-w-0 [overflow-wrap:anywhere]">{name}</span>
          <button type="button" onClick={onClear} className="border-0 bg-transparent text-fg-3" aria-label={`Remove ${name}`}>Remove</button>
        </div>
      )}
    </div>
  );
}

function StepEvidence({ az }) {
  return (
    <div className="flex flex-col gap-4">
      <div>
        <h2 className={H2}>Attach evidence <span className="font-normal text-fg-3 text-[14px]">optional</span></h2>
        <p className="mt-1 mb-0 text-fg-2 text-[13.5px]">More sources make the diagnosis more confident, and every one is cited.</p>
      </div>
      <div className="grid gap-3" style={GRID(280)}>
        <EvidenceCard code="ACC · ACCELEROMETER" color="var(--c3)" title="phyphox recording" desc="CSV or zip export, recorded with the phone on the machine."
          accept=".csv,.zip" chooseLabel="Choose file" has={az.hasAccel} name={az.accelName}
          onChoose={az.onAccel} onClear={az.clearAccel} onSample={az.sampleAccel} isSample={az.isSample} />
        <EvidenceCard code="MAN · MANUAL" color="var(--c4)" title="Machine manual (PDF)" desc="Quotes are checked against the PDF and badged verified."
          accept="application/pdf" chooseLabel="Choose PDF" has={az.hasManual} name={az.manualName}
          onChoose={az.onManual} onClear={az.clearManual} onSample={az.sampleManual} isSample={az.isSample} />
      </div>
    </div>
  );
}

function OptionRow({ title, meta, desc, sw, label, op, dashed = false, small = false, disabled = false }) {
  return (
    <div className={`flex gap-3.5 items-center p-3.5 border ${dashed ? 'border-dashed' : ''} border-line-2 rounded-card`} style={op ? { opacity: op } : undefined}>
      <div className="flex-1 min-w-0">
        <div className={`font-semibold ${small ? 'text-[13.5px]' : ''}`}>
          {title}
          {meta && <span className="font-mono text-[11px] font-normal leading-none text-fg-3 ml-1.5">{meta}</span>}
        </div>
        <div className={small ? 'text-[12.5px] text-fg-3' : 'text-[13px] text-fg-2'}>{desc}</div>
      </div>
      <Switch sw={sw} label={label} disabled={disabled} />
    </div>
  );
}

function StepOptions({ az }) {
  return (
    <div className="flex flex-col gap-3.5">
      <h2 className={H2}>Options</h2>
      <OptionRow title="Diagnose" meta="Muse Spark · ≈ $0.021" desc="Ranked faults, evidence, repair steps and manual citations." sw={az.diagnose} label="Diagnose" />
      <OptionRow title="Show the fix" meta="Muse Image · ≈ $0.012" desc="Where to act on your frame, and the machine after the repair. Needs Diagnose."
        sw={az.visualize} label="Show the fix" op={az.visualize.op} disabled={az.visualize.disabled} />
      {az.isSample && (
        <OptionRow dashed small title="Demo: simulate a failure at Magnify" desc="Shows the recoverable error state. Sample mode only." sw={az.simFail} label="Simulate failure" />
      )}
      <div className="flex flex-wrap gap-x-5 gap-y-1.5 pt-1.5 font-mono text-[12.5px] leading-[1.4] text-fg-2 tabular">
        <span>{az.nStages}&nbsp;stages</span>
        <span>expected cost {az.estRange}</span>
        <span className="[overflow-wrap:anywhere]">{az.fileName}</span>
      </div>
    </div>
  );
}

function StepRun({ az }) {
  return (
    <div className="flex flex-col gap-4" aria-live="polite">
      <div className="flex flex-wrap justify-between gap-2.5 items-baseline">
        <h2 className={H2}>{az.current}</h2>
        <span className="font-mono text-[13px] font-medium leading-none text-fg-2 tabular">{az.pct} · {az.elapsed}</span>
      </div>
      <div className="h-1 bg-line rounded-chip overflow-hidden" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={az.pctN} aria-label="Analysis progress">
        <div className="h-full bg-signal transition-[width] duration-300" style={{ width: az.pct }} />
      </div>
      {az.hasError && (
        <div role="alert" className="flex flex-wrap gap-3 items-center p-3.5 border border-sev-stop rounded-card" style={{ background: tint('var(--sev-stop)', 9) }}>
          <div className="flex-1 min-w-[220px]">
            <div className="font-semibold">{az.errStage}&nbsp;failed</div>
            <div className="text-[13px] text-fg-2">{az.error}</div>
          </div>
          <button type="button" onClick={az.retry} className="h-9 px-3.5 bg-accent text-on-accent border-0 rounded-ctl font-semibold">Retry from {az.errStage}</button>
          <button type="button" onClick={az.reset} className={`h-9 px-3.5 ${SECONDARY}`}>Start over</button>
        </div>
      )}
      <div className="border border-line rounded-card">
        {az.stages.map(g => (
          <div key={g.key} className="flex flex-wrap items-center gap-x-3.5 gap-y-1.5 px-3.5 py-[11px] border-b border-line last:border-b-0" style={{ opacity: g.op }}>
            <span className={`size-2.5 rounded-full shrink-0 ${g.isRun ? 'animate-pulse' : ''}`} style={{ background: g.color }} />
            <span className="font-mono text-[11px] font-medium leading-none text-fg-3 w-[22px]">{g.n}</span>
            <div className="flex-1 min-w-[180px]">
              <div className="font-medium text-[13.5px]">{g.label}</div>
              <div className="text-[12.5px] text-fg-2">{g.desc}</div>
            </div>
            <span className="font-mono text-[11.5px] leading-none text-fg-3 w-[92px]">{g.cost}</span>
            <span className="font-mono text-[12px] font-medium leading-none w-14 text-right tabular">{g.elapsed}</span>
            <span className="font-mono text-[10px] font-semibold leading-none tracking-[.08em] uppercase w-[62px] text-right" style={{ color: g.color }}>{g.stLabel}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
