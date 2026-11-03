// CH 04 · Capabilities: six rows of copy beside a product panel, fed by the sample desk-fan run.

const ROW = 'grid grid-cols-[repeat(auto-fit,minmax(min(100%,420px),1fr))] gap-8 items-center';
const PANEL = 'border border-line-2 rounded-[4px]';

function Copy({ tag, title, children, extra }) {
  return (
    <div className="flex flex-col gap-3">
      <span className="font-mono text-[12px] font-semibold leading-none text-signal">{tag}</span>
      <h3 className="m-0 text-[26px] font-semibold">{title}</h3>
      <p className="m-0 text-fg-2 leading-[1.6]">{children}</p>
      {extra}
    </div>
  );
}

function Row({ reveal, children }) {
  return <div ref={reveal} className={ROW}>{children}</div>;
}

function MaskPanel({ m }) {
  return (
    <div className={`relative aspect-[16/10] overflow-hidden ${PANEL}`} style={{ background: m.bg }}>
      {m.label && <span className="absolute left-3 top-3 font-mono text-[11px] leading-none text-fg-3">{m.label} · drop real frame</span>}
      {m.box && (
        <div className="absolute border-[1.5px] border-signal bg-[color-mix(in_oklch,var(--signal)_14%,transparent)]"
          style={{ left: m.box.left, top: m.box.top, width: m.box.width, height: m.box.height }}>
          <span className="absolute left-[-1.5px] top-[-22px] px-[7px] py-1 bg-signal text-on-accent font-mono text-[11px] font-semibold leading-none whitespace-nowrap">{m.prompt || 'fan'} · {m.conf}</span>
        </div>
      )}
      <span className="absolute right-3 bottom-3 font-mono text-[11px] leading-none text-fg-2">{m.area}&nbsp;measured</span>
    </div>
  );
}

function SpectrumPanel({ fan }) {
  const s = fan.spec;
  return (
    <div className={`p-4 bg-bg ${PANEL}`}>
      <div className="relative h-[220px] border-b border-line-2 [background-image:linear-gradient(var(--grid)_1px,transparent_1px),linear-gradient(90deg,var(--grid)_1px,transparent_1px)] [background-size:100%_20%,16.666%_100%]">
        {s.hasImg ? (
          <div className="absolute inset-0" style={{ background: s.imgBg }} role="img" aria-label="Vibration spectrum" />
        ) : (
          <svg viewBox="0 0 600 200" preserveAspectRatio="none" className="absolute inset-0 w-full h-full" aria-hidden="true">
            <path d={s.area} className="fill-signal-dim opacity-50" />
            <path d={s.line} className="fill-none stroke-signal stroke-[1.25] [vector-effect:non-scaling-stroke]" />
          </svg>
        )}
        {s.noImg && s.markers.map(k => (
          <span key={k.label} className="absolute translate-x-[6px] -translate-y-[4px] px-1 py-0.5 bg-panel border border-line-2 font-mono text-[10.5px] font-medium leading-none whitespace-nowrap"
            style={{ left: k.left, top: k.top }}>{k.label}</span>
        ))}
      </div>
      <div className="flex justify-between mt-1.5 font-mono text-[10px] leading-none text-fg-3"><span>0</span><span>40</span><span>80</span><span>120 Hz</span></div>
    </div>
  );
}

function DiagnosePanel({ fan }) {
  return (
    <div className={`flex flex-col gap-2.5 p-4 bg-bg ${PANEL}`}>
      {fan.faults.map(f => (
        <div key={f.name} className="grid grid-cols-[minmax(0,150px)_1fr_44px] gap-3 items-center text-[13.5px]">
          <span>{f.name}</span>
          <span className="h-1.5 bg-line rounded-[3px]"><span className="block h-full bg-signal rounded-[3px]" style={{ width: f.w }} /></span>
          <span className="font-mono text-[12.5px] font-medium leading-none text-right tabular">{f.pct}</span>
        </div>
      ))}
      <div className="h-px my-1 bg-line" />
      {fan.sel && fan.sel.sup.map(e => (
        <div key={e.detail} className="flex gap-2.5 items-start text-[13px] leading-[1.45]">
          <span className="shrink-0 px-1.5 py-[3px] border rounded-[2px] font-mono text-[10px] font-semibold leading-[1.1]" style={{ borderColor: e.srcColor, color: e.srcColor }}>{e.srcCode}</span>
          <span className="text-fg-2">{e.detail}</span>
        </div>
      ))}
      {fan.sel && fan.sel.con.map(c => (
        <div key={c.detail} className="flex gap-2.5 text-[13px]">
          <span className="shrink-0 px-1.5 py-[3px] border border-sev-act rounded-[2px] text-sev-act font-mono text-[10px] font-semibold leading-[1.1]">AGAINST</span>
          <span className="text-fg-2">{c.detail}</span>
        </div>
      ))}
    </div>
  );
}

function FixPanel({ fan }) {
  const s = fan.slider, w = fan.where;
  return (
    <div className={`relative aspect-[16/10] overflow-hidden select-none ${PANEL}`}>
      <div className="absolute inset-0" style={{ background: s.after }}>
        {s.afterLabel && <span className="absolute right-3 top-3 font-mono text-[11px] leading-none text-fg-3">fixed_state.png</span>}
      </div>
      <div className="absolute inset-0" style={{ background: `${s.before}, var(--panel-2)`, clipPath: s.clip }}>
        {s.beforeLabel && <span className="absolute left-3 top-3 font-mono text-[11px] leading-none text-fg-3">key_frame.png</span>}
        <div className="absolute size-11 -m-[22px] border-2 border-sev-act rounded-full" style={{ left: w.x, top: w.y }} aria-hidden="true" />
      </div>
      <div className="absolute top-0 bottom-0 w-0.5 -ml-px bg-signal pointer-events-none" style={{ left: s.left }}>
        <span className="absolute top-1/2 left-1/2 grid place-items-center size-[30px] -m-[15px] rounded-full bg-signal text-on-accent font-mono text-[12px] font-semibold leading-none">⇔</span>
      </div>
      <input type="range" min="0" max="100" value={s.pos} onChange={s.onInput} aria-label="Compare now and after the fix"
        className="absolute inset-0 w-full h-full m-0 opacity-0 cursor-ew-resize" />
    </div>
  );
}

function CertPanel({ cmp }) {
  return (
    <div className="flex flex-col gap-3 p-5 bg-bg border border-sev-normal rounded-[4px]">
      <div className="flex justify-between gap-3 font-mono text-[10.5px] font-medium leading-none tracking-[.12em] text-fg-3"><span>CERTIFICATE OF FIX</span><span>{cmp.cert}</span></div>
      <div className="flex flex-wrap items-baseline gap-3.5">
        <span className="font-mono text-[56px] font-medium leading-none tracking-[-.03em] tabular">{cmp.big}</span>
        <span className="text-[22px] font-semibold" style={{ color: cmp.color }}>{cmp.label}</span>
      </div>
      {cmp.rows.map(w => (
        <div key={w.label} className="flex flex-wrap justify-between gap-1.5 font-mono text-[12.5px] leading-[1.3] tabular">
          <span>{w.label} · {w.hz}</span>
          <span>{w.before} → {w.after}&nbsp;px</span>
          <span style={{ color: w.color }}>{w.pct} · {w.db}</span>
        </div>
      ))}
      {cmp.spark && <div className="text-[13px] text-fg-2">{cmp.spark.matches ? '✓' : '!'} {cmp.spark.label}</div>}
    </div>
  );
}

export default function Features({ v }) {
  const { fan, cmp } = v, reveal = v.refs.reveal;
  return (
    <section id="features" className="scroll-mt-[96px] desk:scroll-mt-[64px] border-t border-line bg-panel">
      <div className="max-w-[1240px] mx-auto px-6 py-[88px] flex flex-col gap-14">
        <div>
          <span className="font-mono text-[11.5px] font-medium leading-none tracking-[.16em] text-signal">CH 04 · CAPABILITIES</span>
          <h2 className="mt-3 mb-0 text-[length:clamp(30px,4vw,44px)] tracking-[-.025em] font-semibold">Every number has a source.</h2>
        </div>

        <Row reveal={reveal}>
          <Copy tag="01 · SEGMENT · SAM 3.1" title="Only the machine is measured.">Type “fan” and SAM 3.1 finds it. Background pixels become the camera reference, so hand shake is measured and subtracted instead of mistaken for vibration.</Copy>
          <MaskPanel m={fan.mask} />
        </Row>

        <Row reveal={reveal}>
          <Copy tag="02 · MEASURE" title="A real spectrum, not a guess."
            extra={
              <div className="flex flex-wrap gap-2 font-mono text-[12px] font-medium leading-none tabular">
                <span className="px-[9px] py-1.5 border border-line-2 rounded-[2px]">{fan.hz}&nbsp;Hz</span>
                <span className="px-[9px] py-1.5 border border-line-2 rounded-[2px]">SNR {fan.snr}</span>
                {fan.acc && <span className="px-[9px] py-1.5 border rounded-[2px]" style={{ borderColor: fan.acc.color, color: fan.acc.color }}>{fan.acc.agrees ? '✓' : '!'} {fan.acc.label}</span>}
              </div>
            }>
            Frequency in Hz and CPM, amplitude in pixels, harmonics 1×–6× with signal-to-noise. Attach a phyphox accelerometer recording and the two are cross-checked.
          </Copy>
          <SpectrumPanel fan={fan} />
        </Row>

        <Row reveal={reveal}>
          <Copy tag="03 · MAGNIFY" title="See half a pixel of motion.">The fan moves 0.5 px. Invisible to the eye. Magnified about 20×, the rocking is obvious, and you can show it to anyone.</Copy>
          <div className={`scope relative h-[260px] overflow-hidden ${PANEL}`}>
            <canvas ref={fan.motionRef} aria-label="Original and magnified motion side by side" role="img" className="absolute inset-0 w-full h-full" />
          </div>
        </Row>

        <Row reveal={reveal}>
          <Copy tag="04 · DIAGNOSE · MUSE SPARK" title="Evidence for, and against.">A ranked list of faults with likelihoods. Each one shows supporting and contradicting evidence, tagged by where it came from. Uncertainties are stated, not hidden.</Copy>
          <DiagnosePanel fan={fan} />
        </Row>

        <Row reveal={reveal}>
          <Copy tag="05 · VISUALIZE · MUSE IMAGE" title="The fix, on your own frame.">Where to act, marked on the real machine. Drag to see what it should look like after the repair. Manual quotes are checked against the PDF and badged verified.</Copy>
          <FixPanel fan={fan} />
        </Row>

        <Row reveal={reveal}>
          <Copy tag="06 · RESCAN" title="Proof the repair worked.">Film again from the same spot. Resonance compares the two runs harmonic by harmonic and Muse Spark checks the result against its own prediction.</Copy>
          {cmp && <CertPanel cmp={cmp} />}
        </Row>
      </div>
    </section>
  );
}
