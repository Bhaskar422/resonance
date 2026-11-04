import { PageHeader, AutoGrid } from '../../components/ui.jsx';

// 20px graticule behind the illustrations (the shared `graticule` utility is 28px).
const GRID20 = '[background-image:linear-gradient(var(--grid)_1px,transparent_1px),linear-gradient(90deg,var(--grid)_1px,transparent_1px)] [background-size:20px_20px]';
const ART = 'h-[120px] border-b border-line';
const DASH = 'border-dashed border-line-2';

function Fps() {
  return (
    <div className={`${ART} grid place-items-center ${GRID20}`}>
      <span className="font-mono text-[46px] font-medium leading-none text-signal">240<span className="text-[16px] text-fg-3"> fps</span></span>
    </div>
  );
}

function Tripod() {
  return (
    <div className={`${ART} relative ${GRID20}`}>
      <div className="absolute left-1/2 top-[18px] w-[34px] h-14 -ml-[17px] border-2 border-signal rounded-card" />
      <div className="absolute left-1/2 top-[74px] w-0.5 h-[34px] bg-fg-2" />
      <div className="absolute left-1/2 top-[76px] w-0.5 h-9 bg-fg-2 origin-top rotate-[28deg]" />
      <div className="absolute left-1/2 top-[76px] w-0.5 h-9 bg-fg-2 origin-top -rotate-[28deg]" />
    </div>
  );
}

function TenSeconds() {
  return (
    <div className={`${ART} flex items-center justify-center gap-1 px-6`}>
      {Array.from({ length: 10 }, (_, i) => <span key={i} className="flex-1 h-[26px] bg-signal opacity-90" />)}
      <span className="ml-2 font-mono text-[13px] font-medium leading-none">10 s</span>
    </div>
  );
}

function Light() {
  return (
    <div className={`${ART} grid place-items-center`}>
      <div className="size-14 rounded-full bg-sev-monitor [box-shadow:0_0_0_12px_color-mix(in_oklch,var(--sev-monitor)_18%,transparent),0_0_0_24px_color-mix(in_oklch,var(--sev-monitor)_8%,transparent)]" />
    </div>
  );
}

function Thirds() {
  // Cell borders for the 3×3 rule-of-thirds frame; the centre cell is the machine.
  const cells = ['border-r border-b', 'border-r border-b', 'border-b', 'border-r border-b', 'centre', 'border-b', 'border-r', 'border-r', ''];
  return (
    <div className={`${ART} grid place-items-center`}>
      <div className="w-[150px] h-[88px] border-[1.5px] border-fg-2 grid grid-cols-3 grid-rows-3">
        {cells.map((c, i) => c === 'centre'
          ? <span key={i} className="bg-[color-mix(in_oklch,var(--signal)_40%,transparent)] outline-[1.5px] outline-solid outline-signal" />
          : <span key={i} className={c ? `${c} ${DASH}` : ''} />)}
      </div>
    </div>
  );
}

function NoZoom() {
  return (
    <div className={`${ART} flex items-center justify-center gap-[22px]`}>
      <span className="grid place-items-center size-14 rounded-full border-2 border-signal font-mono text-[16px] font-semibold leading-none text-signal">1×</span>
      <span className="relative grid place-items-center size-14 rounded-full border-2 border-line-2 font-mono text-[16px] font-semibold leading-none text-fg-3">
        3×<span className="absolute -left-1 -right-1 top-1/2 h-0.5 bg-sev-stop -rotate-40" />
      </span>
    </div>
  );
}

const CARDS = [
  [Fps, 'Slow motion, 240 fps', 'Measures up to 120 Hz (7,200 RPM). 120 fps works for slower machines.'],
  [Tripod, 'Tripod or braced', 'Hand shake looks like vibration. Brace the phone on something that isn’t the machine.'],
  [TenSeconds, '10 seconds, steady state', 'Let the machine reach speed first. 10 s gives 0.1 Hz resolution.'],
  [Light, 'Good, even light', 'Slow motion needs light. Avoid flickering LEDs; daylight or a work lamp is best.'],
  [Thirds, 'Machine fills a third of the frame', 'Close enough for detail, with some still background as the camera reference.'],
  [NoZoom, 'No zoom', 'Digital zoom amplifies sensor noise. Move the phone closer instead.'],
];

const SECTION = 'card p-[18px] min-w-0';
const H2 = 'mt-0 mb-3 font-mono text-[11px] font-semibold leading-none tracking-[.12em]';
const LIST = 'm-0 pl-[18px] flex flex-col gap-2 text-[13.5px] leading-[1.5] text-fg-2';
const B = ({ children }) => <b className="text-fg">{children}</b>;

export default function Guide() {
  return (
    <div className="flex flex-col gap-5 max-w-[1100px]">
      <PageHeader eyebrow="PROCEDURE" title="Recording a good clip" sub="Six checks. Get these right and the measurement is as good as the physics allows." />

      <AutoGrid min={300} gap={12} fill>
        {CARDS.map(([Art, title, body], i) => (
          <div key={title} className="card overflow-hidden min-w-0">
            <Art />
            <div className="px-4 py-3.5">
              <div className="font-mono text-[11px] font-semibold leading-none text-fg-3">{String(i + 1).padStart(2, '0')}</div>
              <h3 className="mt-1.5 mb-1 text-[15px] font-bold">{title}</h3>
              <p className="m-0 text-[13px] leading-[1.5] text-fg-2">{body}</p>
            </div>
          </div>
        ))}
      </AutoGrid>

      <AutoGrid min={320} gap={12}>
        <section className={SECTION}>
          <h2 className={`${H2} text-c3`}>ACC · RECORD PHYPHOX AT THE SAME TIME</h2>
          <ol className={`${LIST} list-decimal`}>
            <li>Install phyphox on a second phone and open <B>Acceleration (without g)</B>.</li>
            <li>Place it flat on the machine housing, away from moving parts.</li>
            <li>Press play, then start the slow-motion video within a second.</li>
            <li>Stop both after 10 s. Export as CSV or zip and attach it in step 3.</li>
          </ol>
        </section>
        <section className={SECTION}>
          <h2 className={`${H2} text-fg-2`}>IPHONE</h2>
          <ul className={`${LIST} list-disc`}>
            <li>Settings → Camera → Record Slo-mo → <B>1080p at 240 fps</B>.</li>
            <li>Use Slo-mo mode, not Video. Tap to lock exposure (AE/AF lock).</li>
            <li>Export the original file; don’t trim the slow-motion section.</li>
          </ul>
        </section>
        <section className={SECTION}>
          <h2 className={`${H2} text-fg-2`}>ANDROID</h2>
          <ul className={`${LIST} list-disc`}>
            <li>Camera → More → <B>Slow motion</B>; pick 240 fps if offered.</li>
            <li>Turn off “super slow-mo” auto-detect, which only captures a short burst.</li>
            <li>Check the capture fps in the file details and enter it in step 2.</li>
          </ul>
        </section>
      </AutoGrid>
    </div>
  );
}
