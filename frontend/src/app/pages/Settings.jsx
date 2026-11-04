import { PageHeader, Panel, Switch } from '../../components/ui.jsx';
import { AccountSettings, DeleteAccount } from '../Account.jsx';

const ROW = 'flex items-center gap-3.5 px-4 py-3 border-b border-line last:border-b-0';

// Two-option toggle group; {label, on, bg, fg, bd, onClick} come from the view-model.
function Options({ opts, label, h = 'h-[34px]' }) {
  return (
    <div role="group" aria-label={label} className="flex gap-1">
      {opts.map(o => (
        <button key={o.label} type="button" onClick={o.onClick} aria-pressed={!!o.on}
          className={`${h} px-3.5 border rounded-[3px] font-mono text-[12px] font-medium leading-none whitespace-nowrap`}
          style={{ background: o.bg, color: o.fg, borderColor: o.bd }}>{o.label}</button>
      ))}
    </div>
  );
}

export default function Settings({ v, a }) {
  const s = v.set;
  if (!s) return null;
  return (
    <div className="flex flex-col gap-4 max-w-[820px]">
      <PageHeader eyebrow="CH 08 · CONFIG" title="Settings" />

      {a && <AccountSettings a={a} />}

      <Panel label="API KEYS" bodyClass="">
        {s.keys.map(k => (
          <div key={k.name} className="flex flex-wrap items-center gap-x-4 gap-y-2 px-4 py-3 border-b border-line">
            <span className="flex-1 min-w-[160px]"><b className="font-semibold">{k.name}</b> <span className="text-[12px] text-fg-3">{k.use}</span></span>
            <span className="font-mono text-[12px] leading-none text-fg-3" aria-label="Key hidden">••••••••••••</span>
            <span className="inline-flex items-center gap-1.5 font-mono text-[11.5px] font-medium leading-none" style={{ color: k.color }}>
              <span className="size-[7px] rounded-full" style={{ background: k.color }} />{k.status}
            </span>
          </div>
        ))}
        <p className="m-0 px-4 py-3 text-[12.5px] text-fg-3">Keys live in the backend’s environment and are never sent to the browser.</p>
      </Panel>

      <Panel label="DATA SOURCE" bodyClass="flex flex-wrap items-center gap-3 px-4 py-3.5">
        <Options opts={s.modes} label="Data source" h="h-9" />
        <span className="font-mono text-[12px] leading-[1.4] text-fg-3 [overflow-wrap:anywhere]">API_BASE = {s.apiBase}</span>
      </Panel>

      <Panel label="DEFAULT ANALYSIS OPTIONS" bodyClass="">
        <div className={ROW}><span className="flex-1">Diagnose with Muse Spark</span><Switch sw={s.diag} label="Diagnose by default" /></div>
        <div className={ROW}><span className="flex-1">Show the fix with Muse Image</span><Switch sw={s.viz} label="Show the fix by default" /></div>
      </Panel>

      <Panel label="DISPLAY" bodyClass="">
        <div className={`${ROW} flex-wrap`}><span className="flex-1 min-w-[140px]">Theme</span><Options opts={s.themes} label="Theme" /></div>
        <div className={`${ROW} flex-wrap`}><span className="flex-1 min-w-[140px]">Frequency units</span><Options opts={s.units} label="Frequency units" /></div>
        <div className={ROW}><span className="flex-1">Amplitude units</span><span className="font-mono text-[12px] font-medium leading-none text-fg-2 text-right">px (pixels of displacement)</span></div>
      </Panel>

      {a && <DeleteAccount a={a} />}
    </div>
  );
}
