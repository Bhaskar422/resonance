import { Logo, Toast } from '../components/ui.jsx';

export default function Shell({ v, children }) {
  return (
    <div className="min-h-screen flex bg-bg text-fg font-sans text-[14px]">
      <aside data-noprint className="hidden desk:flex flex-col w-[232px] shrink-0 sticky top-0 h-screen border-r border-line bg-panel">
        <div className="p-[18px] border-b border-line"><Logo /></div>
        <nav aria-label="Workspace" className="flex flex-col gap-0.5 px-2.5 py-3 flex-1">
          <div className="px-2.5 pt-1.5 pb-2.5 font-mono text-[10px] font-medium leading-none tracking-[.14em] text-fg-3">CHANNELS</div>
          {v.nav.map(n => (
            <a key={n.key} href={n.href} aria-current={n.current} className="flex items-center gap-3 px-2.5 py-[9px] rounded-[3px] text-[13.5px] no-underline hover:no-underline hover:bg-panel-2"
              style={{ color: n.on ? n.fg : 'var(--fg-2)', background: n.on ? n.bg : undefined }}>
              <span className="font-mono text-[10.5px] font-medium leading-none opacity-70">{n.n}</span><span>{n.label}</span>
            </a>
          ))}
        </nav>
        <div className="flex flex-col gap-2.5 px-[18px] py-3.5 border-t border-line font-mono text-[11px] font-medium leading-[1.4] text-fg-3">
          <a href="#/kit" className="text-fg-2">Component kit →</a>
          <a href="/" className="text-fg-2">Marketing site →</a>
          <span>v1.0 · Apache-2.0</span>
        </div>
      </aside>

      <main className="flex-1 min-w-0 flex flex-col" style={{ paddingBottom: 'var(--tabpad)' }}>
        <header data-noprint className="sticky top-0 z-30 flex items-center gap-3 py-2.5 border-b border-line backdrop-blur-[10px]"
          style={{ paddingInline: 'var(--pad)', background: 'color-mix(in oklch, var(--bg) 90%, transparent)' }}>
          <div className="desk:hidden"><Logo /></div>
          <div className="hidden desk:block min-w-0 truncate font-mono text-[11px] font-medium leading-none tracking-[.1em] uppercase text-fg-3">WS / <span className="text-fg">{v.pageTitle}</span></div>
          <div className="flex-1" />
          <div className="relative w-[min(300px,42vw)]">
            <input type="search" value={v.search} onChange={v.onSearch} placeholder="Search machines, runs" aria-label="Search machines and runs"
              className="w-full h-[34px] px-3 bg-panel border border-line-2 rounded-[3px] text-fg text-[13px]" />
            {v.searching && (
              <div className="absolute top-10 right-0 z-40 w-[min(360px,86vw)] p-1.5 bg-panel border border-line-2 rounded-[4px] shadow-[0_18px_40px_rgba(0,0,0,.35)]">
                {v.results.map(s => (
                  <a key={s.href + s.label} href={s.href} onClick={v.clearSearch} className="block px-2.5 py-[9px] rounded-[3px] text-fg no-underline hover:no-underline hover:bg-panel-2">
                    <div className="text-[13px]">{s.label}</div><div className="font-mono text-[11px] leading-[1.4] text-fg-3">{s.sub}</div>
                  </a>
                ))}
                {v.noResults && <div className="p-2.5 text-fg-3 text-[13px]">No matches.</div>}
              </div>
            )}
          </div>
          <a href="#/settings" title="Data source" className="hidden sm:flex items-center gap-1.5 h-[34px] px-2.5 border border-line-2 rounded-[3px] font-mono text-[11px] font-medium leading-none text-fg-2 no-underline hover:no-underline whitespace-nowrap">
            <span className="size-1.5 rounded-full" style={{ background: v.live ? 'var(--signal)' : 'var(--sev-monitor)' }} />{v.modeLabel}
          </a>
          <button type="button" onClick={v.toggleTheme} aria-label="Toggle theme" className="size-[34px] shrink-0 border border-line-2 rounded-[3px] bg-transparent text-fg-2 text-[14px]">{v.themeIcon}</button>
        </header>

        <div className="w-full max-w-[1380px] mx-auto flex flex-col gap-5 pt-6 pb-14" style={{ paddingInline: 'var(--pad)' }}>
          {v.failed && (
            <div role="alert" className="flex flex-wrap items-center gap-3 px-3.5 py-3 border border-sev-stop rounded-[4px]" style={{ background: 'color-mix(in oklch, var(--sev-stop) 10%, transparent)' }}>
              <span className="font-mono text-[11px] font-semibold leading-none tracking-[.08em] text-sev-stop">ERR</span>
              <span className="flex-1 min-w-[200px]">Couldn’t load runs: {v.error}</span>
              <button type="button" onClick={v.retry} className="h-8 px-3 border border-line-2 bg-panel rounded-[3px]">Retry</button>
              <a href="#/settings" className="text-[13px]">Switch to sample data</a>
            </div>
          )}
          {children}
        </div>
      </main>

      <nav data-noprint aria-label="Primary" className="desk:hidden fixed inset-x-0 bottom-0 z-40 flex bg-panel border-t border-line px-1.5 pt-1.5" style={{ paddingBottom: 'calc(6px + env(safe-area-inset-bottom))' }}>
        {v.tabs.map(t => (
          <a key={t.key} href={t.href} aria-current={t.current} className="flex-1 flex flex-col items-center justify-center gap-1 min-h-14 rounded-[4px] no-underline hover:no-underline" style={{ color: t.fg, background: t.bg }}>
            <span className="font-mono text-[10px] font-semibold leading-none">{t.n}</span><span className="text-[11.5px]">{t.label}</span>
          </a>
        ))}
      </nav>

      <Toast v={v} />
    </div>
  );
}
