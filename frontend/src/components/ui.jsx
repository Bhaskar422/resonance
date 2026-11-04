// Shared building blocks for the Instrument design. Colours come from view-model values
// (CSS variables) passed in as inline styles; everything static is Tailwind.

export const tint = (c, p = 15) => `color-mix(in oklch, ${c} ${p}%, transparent)`;

export function Eyebrow({ children, className = '', color = 'var(--signal)' }) {
  return <div className={`font-mono text-[11px] font-medium leading-none tracking-[.14em] uppercase ${className}`} style={{ color }}>{children}</div>;
}

export function PageHeader({ eyebrow, title, sub, children }) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-4">
      <div className="min-w-0">
        {eyebrow && <Eyebrow>{eyebrow}</Eyebrow>}
        <h1 className="mt-2 mb-0 text-[26px] font-semibold tracking-[-0.01em]">{title}</h1>
        {sub && <p className="mt-1.5 mb-0 text-fg-2">{sub}</p>}
      </div>
      {children}
    </div>
  );
}

// Panel with the mono uppercase header label used everywhere.
export function Panel({ label, right, children, className = '', bodyClass = 'p-4', dark = false, as: Tag = 'section', ...rest }) {
  return (
    <Tag className={`${dark ? 'scope border border-line rounded-card shadow-card' : 'card'} min-w-0 ${className}`} {...rest}>
      {label != null && (
        <div className={`flex flex-wrap items-center justify-between gap-2 px-4 py-3 border-b border-line ${dark ? '' : 'panel-head'}`}>
          <h2 className="m-0 font-mono text-[11px] font-medium leading-none tracking-[.12em] uppercase text-fg-2">{label}</h2>
          {right}
        </div>
      )}
      <div className={bodyClass}>{children}</div>
    </Tag>
  );
}

export function SeverityBadge({ s, dot = true, className = '' }) {
  return (
    <span className={`inline-flex items-center gap-1.5 px-2 py-1 border rounded-chip font-mono text-[10.5px] font-semibold leading-none tracking-[.08em] uppercase whitespace-nowrap ${className}`}
      style={{ borderColor: tint(s.sevColor, 55), color: s.sevColor, background: s.sevTint }}>
      {dot && <span className="size-1.5 rounded-full" style={{ background: s.sevColor }} />}
      {s.sevLabel}
    </span>
  );
}

export function EvidenceChip({ e, wide = false }) {
  return (
    <span className={`inline-flex items-center gap-1.5 px-[7px] py-1 border rounded-chip font-mono text-[10px] font-semibold leading-[1.1] ${wide ? 'min-w-[112px]' : ''}`}
      style={{ borderColor: tint(e.srcColor, 50), color: e.srcColor, background: e.srcTint }}>
      {e.srcCode} <span className="font-normal">{e.srcLabel}</span>
    </span>
  );
}

export function Tag({ children, color = 'var(--fg-3)' }) {
  return <span className="inline-flex items-center px-1.5 py-[3px] border border-dashed rounded-chip font-mono text-[10px] leading-none whitespace-nowrap" style={{ borderColor: color, color }}>{children}</span>;
}

// Bordered pill used in the report header (CONF 78%, COST $0.035).
export function Pill({ children }) {
  return <span className="inline-flex items-center gap-1.5 h-[26px] px-2 border border-line-2 bg-panel-2 rounded-chip font-mono text-[11px] text-fg-2 tabular whitespace-nowrap">{children}</span>;
}

export function MetricTile({ label, value, unit, color, edge, children, big = 30 }) {
  return (
    <div className="edge bg-panel p-4 min-w-0" style={{ '--edge': edge || color || 'var(--info)' }}>
      <div className="font-mono text-[10.5px] font-medium leading-none tracking-[.12em] uppercase text-fg-3">{label}</div>
      <div className="mt-3 font-mono font-medium leading-none tabular" style={{ fontSize: big, color }}>{value}</div>
      {unit && <div className="mt-1.5 font-mono text-[11px] leading-[1.3] text-fg-3">{unit}</div>}
      {children}
    </div>
  );
}

// gap:1px on a --line background draws hairline dividers between tiles.
export function TileGrid({ min = 150, children, className = '' }) {
  return <div className={`grid gap-px bg-line border border-line rounded-card overflow-hidden ${className}`} style={{ gridTemplateColumns: `repeat(auto-fit, minmax(min(100%, ${min}px), 1fr))` }}>{children}</div>;
}

export function AutoGrid({ min = 300, gap = 16, children, className = '', fill = false }) {
  return <div className={`grid ${className}`} style={{ gap, gridTemplateColumns: `repeat(${fill ? 'auto-fill' : 'auto-fit'}, minmax(min(100%, ${min}px), 1fr))` }}>{children}</div>;
}

export function Button({ primary = false, small = false, className = '', children, href, ...rest }) {
  const cls = `inline-flex items-center justify-center gap-2 ${small ? 'h-8 px-3 text-[12.5px]' : 'h-[38px] px-4 text-[13px]'} rounded-ctl font-semibold whitespace-nowrap no-underline hover:no-underline disabled:opacity-45 disabled:cursor-not-allowed transition-[background-color,border-color,filter] duration-150 ${primary ? 'bg-accent text-on-accent border border-accent shadow-[inset_0_1px_0_rgba(255,255,255,.2),0_3px_10px_-6px_var(--accent)] hover:brightness-110' : 'bg-panel text-fg border border-line-2 shadow-[0_1px_2px_rgba(0,0,0,.06)] hover:bg-panel-2 hover:border-fg-3'} ${className}`;
  return href ? <a href={href} className={cls} {...rest}>{children}</a> : <button type="button" className={cls} {...rest}>{children}</button>;
}

// Segmented control; options come from the view-model with {label, bg, fg, bd, on, onClick}.
export function Segmented({ options, label, size = 'md' }) {
  return (
    <div role="group" aria-label={label} className="inline-flex flex-wrap gap-1.5">
      {options.map(o => (
        <button key={o.label} type="button" onClick={o.onClick} aria-pressed={!!o.on}
          className={`${size === 'sm' ? 'h-[30px] px-2.5 text-[11.5px]' : 'h-9 px-3 text-[12px]'} border rounded-ctl font-mono font-medium whitespace-nowrap`}
          style={{ background: o.bg, color: o.fg, borderColor: o.bd }}>{o.label}</button>
      ))}
    </div>
  );
}

// {on, toggle, track, knob} from the view-model.
export function Switch({ sw, label, disabled = false }) {
  return (
    <button type="button" role="switch" aria-checked={!!sw.on} aria-label={label} onClick={sw.toggle} disabled={disabled}
      className="shrink-0 w-11 h-6 p-0.5 rounded-xl border-0 disabled:cursor-not-allowed" style={{ background: sw.track }}>
      <span className="block size-5 rounded-full bg-bg transition-transform duration-150" style={{ transform: sw.knob }} />
    </button>
  );
}

export function EmptyState({ eyebrow = 'NO SIGNAL', title, children, cta, ctaHref, onCta, className = '' }) {
  return (
    <div className={`flex flex-col items-center gap-2 px-4 py-10 text-center border border-dashed border-line-2 rounded-card ${className}`}>
      <span className="font-mono text-[10.5px] font-medium leading-none tracking-[.14em] text-fg-3">{eyebrow}</span>
      <span className="text-[19px] font-semibold">{title}</span>
      {children && <span className="max-w-[56ch] text-[13.5px] text-fg-2">{children}</span>}
      {cta && <Button primary href={ctaHref} onClick={onCta} className="mt-2">{cta}</Button>}
    </div>
  );
}

export function Skeleton({ h = 12, w = '100%', className = '' }) {
  return <div className={`bg-panel-2 rounded-chip animate-pulse ${className}`} style={{ height: h, width: w }} />;
}

export function StageRow({ g, showDesc = true }) {
  return (
    <div className="flex flex-wrap items-center gap-3 px-3 py-2.5 border-b border-line last:border-b-0" style={{ opacity: g.op }}>
      <span className={`size-2.5 rounded-full shrink-0 ${g.isRun ? 'animate-pulse' : ''}`} style={{ background: g.color }} />
      <span className="font-mono text-[11px] text-fg-3">{g.n}</span>
      <span className="flex-1 min-w-[160px]">
        <span className="text-[13.5px]">{g.label}</span>
        {showDesc && g.desc && <span className="block text-[12px] text-fg-3">{g.desc}</span>}
      </span>
      {g.cost && <span className="font-mono text-[11px] text-fg-3">{g.cost}</span>}
      <span className="w-[52px] text-right font-mono text-[11px] font-medium tabular">{g.elapsed}</span>
      <span className="w-[58px] text-right font-mono text-[10px] font-semibold uppercase" style={{ color: g.color }}>{g.stLabel}</span>
    </div>
  );
}

// After image is the base layer; the before layer is clipped on top.
export function BeforeAfterSlider({ s, className = 'aspect-video', label = 'Compare now and after the fix' }) {
  return (
    <div className={`relative overflow-hidden border border-line rounded-card bg-panel-2 ${className}`}>
      <div className="absolute inset-0" style={{ background: s.after }} />
      {s.afterLabel && <span className="absolute right-2 bottom-2 font-mono text-[10.5px] text-fg-3">{s.afterLabel}</span>}
      <div className="absolute inset-0 bg-panel-2" style={{ background: s.before, clipPath: s.clip }}>
        {s.beforeLabel && <span className="absolute left-2 bottom-2 font-mono text-[10.5px] text-fg-3">{s.beforeLabel}</span>}
      </div>
      <span className="absolute top-2 left-2 px-1.5 py-1 bg-black/60 text-white font-mono text-[10px] font-semibold tracking-[.1em] rounded-chip">NOW</span>
      <span className="absolute top-2 right-2 px-1.5 py-1 bg-black/60 text-white font-mono text-[10px] font-semibold tracking-[.1em] rounded-chip">AFTER FIX</span>
      <div className="absolute top-0 bottom-0 w-0.5 bg-signal pointer-events-none" style={{ left: s.left }}>
        <span className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 grid place-items-center size-[30px] rounded-full bg-signal text-on-accent font-mono text-[14px]">⇔</span>
      </div>
      <input type="range" min="0" max="100" value={s.pos} onChange={s.onInput} aria-label={label}
        className="absolute inset-0 w-full h-full m-0 opacity-0 cursor-ew-resize" />
    </div>
  );
}

export function Toast({ v }) {
  if (!v.hasToast) return null;
  return (
    <div role="status" className="fixed right-5 z-[60] flex items-center gap-3 max-w-[min(420px,calc(100vw-40px))] px-3.5 py-3 bg-panel border rounded-card shadow-pop"
      style={{ borderColor: v.toastColor, backgroundImage: `linear-gradient(${tint(v.toastColor, 10)}, ${tint(v.toastColor, 10)})`, bottom: 'calc(20px + var(--tabpad))' }}>
      <span className="size-2 rounded-full" style={{ background: v.toastColor }} />
      <span className="flex-1 text-[13.5px]">{v.toast.msg}</span>
      <button type="button" onClick={v.dismissToast} aria-label="Dismiss" className="border-0 bg-transparent text-fg-3">✕</button>
    </div>
  );
}

// Canvas driven by one of the core's stable callback refs (refs.wave, refs.motion, …).
export function Scope({ canvasRef, className = '', label }) {
  return <canvas ref={canvasRef} className={`block w-full h-full ${className}`} role="img" aria-label={label} />;
}

export function Logo({ href = '#/dashboard' }) {
  return (
    <a href={href} className="flex items-center gap-2.5 text-fg no-underline hover:no-underline">
      <span className="grid place-items-center size-[22px] rounded-full border-[1.5px] border-signal"><span className="size-1.5 rounded-full bg-signal" /></span>
      <span className="font-mono text-[13px] font-semibold leading-none tracking-[.2em]">RESONANCE</span>
    </a>
  );
}
