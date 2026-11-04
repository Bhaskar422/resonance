import { PageHeader, Panel, AutoGrid, Skeleton } from '../../components/ui.jsx';

const ROW = 'border-b border-line last:border-b-0';

function Loading({ n }) {
  return Array.from({ length: n }, (_, i) => <div key={i} className={`px-4 py-3.5 ${ROW}`}><Skeleton h={12} w={`${60 + (i % 3) * 12}%`} /></div>);
}

export default function Usage({ v }) {
  const u = v.usage;
  if (!u) return null;
  return (
    <div className="flex flex-col gap-[18px]">
      <PageHeader eyebrow="CH 07 · METER" title="Usage & cost">
        {u.mock && (
          <span className="px-[9px] py-[5px] border border-dashed border-sev-monitor rounded-chip text-sev-monitor font-mono text-[11px] font-medium leading-[1.3]">
            Mock ledger · /api/costs not built yet
          </span>
        )}
      </PageHeader>

      <section className="flex flex-col gap-3.5 p-5 card min-w-0">
        <div className="flex flex-wrap items-baseline gap-x-4 gap-y-2">
          <span className="font-mono text-[44px] font-medium leading-none tabular">{u.total}</span>
          <span className="font-mono text-[14px] leading-none text-fg-3">of {u.budget}&nbsp;budget</span>
          <span className="ml-auto font-mono text-[12.5px] leading-[1.4] text-fg-2">{u.remaining}&nbsp;left · ≈ {u.left}&nbsp;more analyses at {u.avg}&nbsp;avg</span>
        </div>
        <div className="h-2.5 bg-line rounded-card overflow-hidden">
          <div className="h-full bg-signal" style={{ width: u.barW }} />
        </div>
        <div className="font-mono text-[11px] leading-none text-fg-3">{u.pct}&nbsp;used</div>
      </section>

      <AutoGrid min={380} gap={16}>
        <Panel label="BY MODEL" bodyClass="">
          {u.loading ? <Loading n={3} /> : u.byModel.map(b => (
            <div key={b.model} className={`flex flex-col gap-2 px-4 py-3.5 ${ROW}`}>
              <div className="flex justify-between gap-2.5">
                <span><b className="font-semibold">{b.model}</b> <span className="text-[12px] text-fg-3">{b.use}</span></span>
                <span className="font-mono text-[13px] font-medium leading-none tabular">{b.cost}</span>
              </div>
              <div className="h-1.5 bg-line rounded-ctl"><div className="h-full bg-signal rounded-ctl" style={{ width: b.w }} /></div>
              <span className="font-mono text-[11px] leading-none text-fg-3">{b.calls}</span>
            </div>
          ))}
        </Panel>

        <Panel label="BY RUN" bodyClass="">
          {u.loading ? <Loading n={5} /> : u.byRun.map(b => (
            <a key={b.run} href={b.href} className={`grid grid-cols-[minmax(0,1fr)_90px_60px] items-center gap-3 px-4 py-2.5 text-fg text-[13px] no-underline hover:no-underline hover:bg-panel-2 ${ROW}`}>
              <span className="truncate">{b.title} <span className="font-mono text-[11px] leading-none text-fg-3">{b.date}</span></span>
              <span className="h-[5px] bg-line rounded-ctl"><span className="block h-full bg-c2 rounded-ctl" style={{ width: b.w }} /></span>
              <span className="font-mono text-[12px] font-medium leading-none text-right tabular">{b.cost}</span>
            </a>
          ))}
        </Panel>
      </AutoGrid>

      <Panel label="RECENT CALLS" bodyClass="">
        {u.loading ? <Loading n={8} /> : u.calls.map((c, i) => (
          <div key={i} className={`flex flex-wrap gap-x-4 gap-y-1 px-4 py-2.5 font-mono text-[12px] leading-[1.4] ${ROW}`}>
            <span className="w-[150px] text-fg-3">{c.time}</span>
            <span className="w-24 text-fg">{c.model}</span>
            <span className="w-20 text-fg-2">{c.endpoint}</span>
            {c.hasRun
              ? <a href={c.href} className="flex-1 min-w-[180px] [overflow-wrap:anywhere]">{c.run}</a>
              : <span className="flex-1 min-w-[180px] [overflow-wrap:anywhere] text-fg-3">{c.run}</span>}
            <span className="font-medium tabular">{c.cost}</span>
          </div>
        ))}
      </Panel>
    </div>
  );
}
