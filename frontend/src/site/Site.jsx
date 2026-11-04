import { useEffect } from 'react';
import { Logo } from '../components/ui.jsx';
import Features from './Features.jsx';

// Marketing site, ported from "A Instrument - Site.dc.html". All figures come from the
// view-model (`v`) for the sample desk-fan run and are labelled with v.sampleLabel.

const WRAP = 'max-w-[1240px] mx-auto';
const EYEBROW = 'font-mono text-[11.5px] font-medium leading-none tracking-[.16em]';
const H2 = 'text-[length:clamp(30px,4vw,44px)] tracking-[-.025em] font-semibold';
const ANCHOR = 'scroll-mt-[96px] desk:scroll-mt-[64px]';
const PRIMARY = 'inline-flex items-center bg-accent text-on-accent rounded-ctl font-semibold no-underline hover:no-underline whitespace-nowrap';
const APP = '/app';

function SectionHead({ eyebrow, title, color = 'text-signal' }) {
  return (
    <div>
      <span className={`${EYEBROW} ${color}`}>{eyebrow}</span>
      <h2 className={`mt-3 mb-0 ${H2}`}>{title}</h2>
    </div>
  );
}

function Header({ v }) {
  return (
    <header className="sticky top-0 z-30 border-b border-line bg-[color-mix(in_srgb,var(--bg)_86%,transparent)] backdrop-blur-[12px]">
      <div className={`${WRAP} flex flex-wrap items-center gap-x-3 gap-y-2.5 px-4 py-3 desk:flex-nowrap desk:gap-5 desk:px-6`}>
        <Logo href="#top" />
        <nav aria-label="Sections" className="order-last w-full flex flex-wrap gap-x-[18px] gap-y-1 font-mono text-[12px] font-medium leading-none tracking-[.06em] desk:order-none desk:w-auto desk:flex-1 desk:justify-center">
          <a href="#how" className="text-fg-2">HOW</a>
          <a href="#features" className="text-fg-2">FEATURES</a>
          <a href="#who" className="text-fg-2">WHO</a>
          <a href="#faq" className="text-fg-2">FAQ</a>
        </nav>
        <div className="ml-auto flex items-center gap-3 desk:ml-0 desk:gap-5">
          <button type="button" onClick={v.toggleTheme} aria-label="Toggle theme" className="size-[34px] border border-line-2 rounded-ctl bg-transparent text-fg-2">{v.themeIcon}</button>
          <a href={`${APP}#/dashboard`} className={`${PRIMARY} h-9 px-3.5 text-[13px]`}>Open workspace</a>
        </div>
      </div>
    </header>
  );
}

function Readout({ label, children, last = false }) {
  return (
    <div className={`px-4 py-3.5 ${last ? '' : 'border-r border-[#1c2321]'}`}>
      <div className="font-mono text-[10px] font-medium leading-none tracking-[.12em] text-[#75807c]">{label}</div>
      {children}
    </div>
  );
}

function Hero({ v }) {
  const { fan } = v;
  return (
    <section id="top" className={`${WRAP} px-6 pt-16 pb-10 flex flex-col gap-9`}>
      <div className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,460px),1fr))] gap-8 items-end">
        <div className="flex flex-col gap-5">
          <span className={`${EYEBROW} text-signal`}>CH 01 · VIBRATION ANALYSIS FROM A PHONE CAMERA</span>
          <h1 className="m-0 text-[length:clamp(40px,6.4vw,76px)] leading-[1.02] tracking-[-.035em] font-semibold text-balance">A vibration analyzer in your pocket.</h1>
        </div>
        <div className="flex flex-col gap-[22px]">
          <p className="m-0 text-[18px] leading-[1.55] text-fg-2 text-pretty">Film a fan, pump, motor or compressor in slow motion for 10 seconds. Resonance measures the vibration, magnifies it 20×, and tells you what’s wrong, with the evidence to prove it.</p>
          <div className="flex flex-wrap gap-2.5">
            <a href={`${APP}#/analyze`} className={`${PRIMARY} h-[46px] px-5`}>Analyze a machine</a>
            <a href={`${APP}#/runs`} className="inline-flex items-center h-[46px] px-5 border border-line-2 rounded-ctl text-fg no-underline hover:no-underline">See a sample report</a>
          </div>
        </div>
      </div>

      {/* Scope module: always dark, whatever the theme. */}
      <div className="border border-line-2 rounded-card bg-[#050706] overflow-hidden text-[#e6ece9] [--signal:#5ef0a0] [--signal-dim:rgba(94,240,160,.26)] [--grid:rgba(94,240,160,.07)] [--line-2:#26302d] [--fg-2:#8c9894]">
        <div className="flex flex-wrap justify-between gap-x-5 gap-y-2 px-4 py-2.5 border-b border-[#1c2321] font-mono text-[11px] font-medium leading-[1.4] tracking-[.08em] text-[#75807c]">
          <span><span className="text-[#5ef0a0]">●</span> LIVE · DESK FAN · CH 1</span>
          <span>HOVER THE TRACE TO MAGNIFY ×20</span>
          <span>{v.sampleLabel}</span>
        </div>
        <div className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,420px),1fr))]">
          <div className="relative h-[clamp(220px,28vw,340px)] border-r border-[#1c2321]">
            <canvas ref={v.refs.wave} aria-label="Animated vibration waveform. Hover to magnify." role="img" className="absolute inset-0 w-full h-full block cursor-crosshair" />
          </div>
          <div className="relative h-[clamp(220px,28vw,340px)]">
            <canvas ref={v.refs.motionSide} aria-label="Looping original and magnified motion of the fan" role="img" className="absolute inset-0 w-full h-full block" />
          </div>
        </div>
        <div className="grid grid-cols-[repeat(auto-fit,minmax(150px,1fr))] border-t border-[#1c2321]">
          <Readout label="FREQ"><div className="mt-2 font-mono text-[24px] font-medium leading-none text-[#5ef0a0] tabular">{fan.hz} <span className="text-[12px] text-[#75807c]">Hz</span></div></Readout>
          <Readout label="SPEED"><div className="mt-2 font-mono text-[24px] font-medium leading-none tabular">{fan.cpm} <span className="text-[12px] text-[#75807c]">CPM</span></div></Readout>
          <Readout label="AMPLITUDE"><div className="mt-2 font-mono text-[24px] font-medium leading-none tabular">{fan.px} <span className="text-[12px] text-[#75807c]">px</span></div></Readout>
          <Readout label="DIAGNOSIS" last><div className="mt-2 font-mono text-[15px] font-medium leading-[1.3] text-[#f59b4c] uppercase">{fan.primary || 'Imbalance'} · {fan.sevLabel || 'Act soon'}</div></Readout>
        </div>
      </div>
    </section>
  );
}

function Proof() {
  const stat = 'font-mono text-[52px] font-medium leading-none tracking-[-.03em] tabular';
  const body = 'mt-3 mb-0 text-fg-2 leading-[1.5]';
  return (
    <section aria-label="Proof" className="border-y border-line bg-panel">
      <div className={`${WRAP} grid grid-cols-[repeat(auto-fit,minmax(min(100%,280px),1fr))]`}>
        <div className="px-6 py-8 border-r border-line">
          <div className={`${stat} text-signal`}>16.42 Hz</div>
          <p className={body}>measured from the pixels of a real desk fan: the same peak a phone accelerometer on the machine recorded.</p>
        </div>
        <div className="px-6 py-8 border-r border-line">
          <div className={`${stat} text-info`}>−97.5%</div>
          <p className={body}>vibration at the fault frequency after the recommended fix, proven by a rescan from the same spot.</p>
        </div>
        <div className="px-6 py-8">
          <div className={`${stat} text-violet`}>≈$0.14</div>
          <p className={body}>per full diagnosis with the manual, in model calls. Measurement and magnification run locally for free.</p>
        </div>
      </div>
    </section>
  );
}

function How({ v }) {
  return (
    <section id="how" className={`${ANCHOR} ${WRAP} px-6 pt-[88px] pb-10 flex flex-col gap-8`}>
      <div className="flex flex-wrap justify-between items-end gap-4">
        <SectionHead eyebrow="CH 02 · PIPELINE" title="How it works, in six stages" />
        <span className="font-mono text-[13px] font-medium leading-none text-fg-2" aria-live="polite">NOW: {v.pipeNow}</span>
      </div>
      <div className="relative h-0.5 bg-line">
        <div className="absolute left-0 top-0 bottom-0 bg-signal shadow-[0_0_12px_var(--signal)] transition-[width] duration-[.6s] ease-[ease]" style={{ width: v.pipeW }} />
      </div>
      <ol className="list-none m-0 p-0 grid grid-cols-[repeat(auto-fit,minmax(min(100%,180px),1fr))] gap-3">
        {v.pipe.map(s => (
          <li key={s.n}>
            <button type="button" onClick={s.onClick} aria-pressed={!!s.on}
              className="w-full h-full text-left flex flex-col gap-2.5 p-4 border rounded-card text-fg transition-[opacity,background-color] duration-[.4s]"
              style={{ borderColor: s.bd, background: s.bg, opacity: s.op }}>
              <span className="flex justify-between items-center">
                <span className="font-mono text-[12px] font-semibold leading-none text-signal">{s.n}</span>
                <span className="size-2 rounded-full" style={{ background: s.dot }} />
              </span>
              <span className="text-[18px] font-semibold">{s.title}</span>
              <span className="text-[13.5px] leading-[1.5] text-fg-2">{s.desc}</span>
              <span className="mt-auto font-mono text-[10.5px] font-medium leading-none tracking-[.08em] text-fg-3 uppercase">{s.model}</span>
            </button>
          </li>
        ))}
      </ol>
    </section>
  );
}

const VERSUS = [
  ['Thousands of dollars of hardware', 'The phone you already carry'],
  ['A trained vibration analyst', 'Plain-language diagnosis with evidence'],
  ['Sensors mounted per measurement point', '10 seconds of slow-motion video'],
  ['A spectrum you have to interpret', 'Repair steps, the fix drawn on your frame, and proof it worked'],
];

function Problem({ v }) {
  const head = 'px-4 py-3.5 border-b border-line font-mono text-[10.5px] font-medium leading-none tracking-[.12em]';
  return (
    <section className={`${WRAP} px-6 py-[72px] grid grid-cols-[repeat(auto-fit,minmax(min(100%,440px),1fr))] gap-10 items-start`}>
      <div ref={v.refs.reveal} className="flex flex-col gap-4">
        <span className={`${EYEBROW} text-sev-act`}>CH 03 · THE PROBLEM</span>
        <h2 className={`m-0 ${H2} text-balance`}>Machines tell you they’re failing. Most people can’t hear it.</h2>
        <p className="m-0 text-[17px] leading-[1.6] text-fg-2">Imbalance, misalignment and looseness show up as vibration weeks before a bearing seizes or a mount cracks. Catching it takes an analyzer that costs thousands of dollars and an analyst trained to read it. So small sites wait for the breakdown, and pay for the downtime.</p>
      </div>
      <div ref={v.refs.reveal} role="table" aria-label="Pro analyzer compared with Resonance" className="grid grid-cols-2 border border-line-2 rounded-card overflow-hidden">
        <div role="row" className="contents">
          <div role="columnheader" className={`${head} bg-panel text-fg-3`}>PRO ANALYZER</div>
          <div role="columnheader" className={`${head} border-l bg-[color-mix(in_oklch,var(--signal)_9%,var(--panel))] text-signal`}>RESONANCE</div>
        </div>
        {VERSUS.map(([a, b], i) => {
          const bb = i < VERSUS.length - 1 ? 'border-b border-line' : '';
          return (
            <div role="row" key={a} className="contents">
              <div role="cell" className={`p-4 ${bb}`}>{a}</div>
              <div role="cell" className={`p-4 border-l border-line ${bb}`}>{b}</div>
            </div>
          );
        })}
      </div>
    </section>
  );
}

const WHO = [
  ['A', 'Maintenance technicians', 'A second opinion on the spot. Film, read the evidence, follow the repair steps, rescan before you leave.'],
  ['B', 'Facility managers', 'See every machine’s trend in one place, prioritise by severity, and keep a certificate for every fix.'],
  ['C', 'Makers & small shops', 'Lathes, grinders, CNC spindles and shop fans. Diagnose them without buying an analyzer.'],
];

function Who({ v }) {
  return (
    <section id="who" className={`${ANCHOR} ${WRAP} px-6 pt-[88px] pb-12 flex flex-col gap-7`}>
      <SectionHead eyebrow="CH 05 · OPERATORS" title="Who it’s for" />
      <div ref={v.refs.reveal} className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,300px),1fr))] gap-px bg-line border border-line rounded-card overflow-hidden">
        {WHO.map(([k, t, d]) => (
          <div key={k} className="p-6 bg-panel flex flex-col gap-2.5">
            <span className="font-mono text-[12px] font-semibold leading-none text-signal">{k}</span>
            <h3 className="m-0 text-[20px] font-semibold">{t}</h3>
            <p className="m-0 text-fg-2 leading-[1.55]">{d}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

const TRUST = [
  ['SPEC · HARM · MAG', 'text-c1', 'Evidence-backed AI', 'Every claim is tied to a source chip, and every fault lists what argues against it.'],
  ['MAN · p.6 · VERIFIED', 'text-c4', 'Verified citations', 'Manual quotes are searched in your PDF. Found on the page: verified. Not found: flagged.'],
  ['ACC · Δ 0.02 Hz', 'text-c3', 'Accelerometer cross-check', 'Record phyphox at the same time and the camera’s frequency is checked against a physical sensor.'],
  ['APACHE-2.0', 'text-fg-2', 'Open source', 'Read the code, run the backend yourself, bring your own model keys.'],
];

function Trust({ v }) {
  return (
    <section className={`${WRAP} px-6 py-12 flex flex-col gap-7`}>
      <SectionHead eyebrow="CH 06 · TRUST" title="Built to be checked." />
      <div ref={v.refs.reveal} className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,250px),1fr))] gap-3">
        {TRUST.map(([code, color, t, d]) => (
          <div key={t} className="p-5 border border-line-2 rounded-card flex flex-col gap-2">
            <span className={`font-mono text-[10.5px] font-semibold leading-none tracking-[.1em] ${color}`}>{code}</span>
            <h3 className="m-0 text-[17px] font-bold">{t}</h3>
            <p className="m-0 text-[14px] text-fg-2 leading-[1.55]">{d}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

function Faq({ v }) {
  return (
    <section id="faq" className={`${ANCHOR} max-w-[900px] mx-auto px-6 py-[72px] flex flex-col gap-5`}>
      <h2 className="m-0 text-[length:clamp(28px,3.6vw,40px)] tracking-[-.025em] font-semibold">Questions</h2>
      <div className="border-t border-line">
        {v.faq.map(f => (
          <div key={f.n} className="border-b border-line">
            <h3 className="m-0">
              <button type="button" onClick={f.toggle} aria-expanded={!!f.open} aria-controls={`faq-${f.n}`}
                className="w-full flex gap-4 items-center py-[18px] px-0 border-0 bg-transparent text-left text-fg">
                <span className="font-mono text-[12px] font-medium leading-none text-fg-3">{f.n}</span>
                <span className="flex-1 text-[17px] font-medium">{f.q}</span>
                <span className="font-mono text-[20px] font-medium leading-none text-signal" aria-hidden="true">{f.sign}</span>
              </button>
            </h3>
            {f.open && <p id={`faq-${f.n}`} className="mt-0 mb-5 ml-10 text-fg-2 leading-[1.65] max-w-[68ch]">{f.a}</p>}
          </div>
        ))}
      </div>
    </section>
  );
}

function Closing() {
  return (
    <section className="border-t border-line bg-panel">
      <div className={`${WRAP} px-6 py-16 flex flex-wrap justify-between items-center gap-6`}>
        <h2 className="m-0 text-[length:clamp(28px,3.6vw,40px)] tracking-[-.025em] font-semibold max-w-[640px]">A phone and 10 seconds of video.</h2>
        <a href={`${APP}#/analyze`} className={`${PRIMARY} h-12 px-[22px]`}>Analyze a machine</a>
      </div>
    </section>
  );
}

export function Footer() {
  return (
    <footer className="border-t border-line">
      <div className={`${WRAP} px-6 py-7 flex flex-wrap gap-x-8 gap-y-4 justify-between font-mono text-[12px] leading-[1.6] text-fg-3`}>
        <span>RESONANCE · Apache-2.0</span>
        <span className="flex flex-wrap gap-[18px]">
          <a href={`${APP}#/guide`} className="text-fg-2">Recording guide</a>
          <a href={`${APP}#/dashboard`} className="text-fg-2">Workspace</a>
          <a href="/#faq" className="text-fg-2">FAQ</a>
          <a href="/privacy" className="text-fg-2">Privacy</a>
          <a href="/terms" className="text-fg-2">Terms</a>
        </span>
        <span>Models: SAM 3.1 · Muse Spark · Muse Image</span>
      </div>
    </footer>
  );
}

export default function Site({ v }) {
  // In-page anchors (HOW / FEATURES / WHO / FAQ) scroll smoothly, as in the prototype.
  useEffect(() => {
    const el = document.documentElement, prev = el.style.scrollBehavior;
    el.style.scrollBehavior = 'smooth';
    return () => { el.style.scrollBehavior = prev; };
  }, []);

  if (!v || !v.fan) return null;
  return (
    <div className="bg-bg wash text-fg font-sans leading-[normal] overflow-x-clip">
      <Header v={v} />
      <main>
        <Hero v={v} />
        <Proof />
        <How v={v} />
        <Problem v={v} />
        <Features v={v} />
        <Who v={v} />
        <Trust v={v} />
        <Faq v={v} />
        <Closing />
      </main>
      <Footer />
    </div>
  );
}
