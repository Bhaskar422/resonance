import { PageHeader, Button } from '../../components/ui.jsx';

export default function Runs({ v }) {
  const runs = v.runs || [];
  return (
    <div className="flex flex-col gap-5">
      <PageHeader eyebrow="CH 04 · LOG" title="Runs">
        <Button primary href="#/analyze">+ New analysis</Button>
      </PageHeader>

      <section className="card min-w-0">
        {/* Column header; hidden on narrow screens where the rows wrap and columns no longer line up. */}
        <div className="hidden sm:flex gap-4 px-4 py-2.5 border-b border-line font-mono text-[10.5px] font-medium leading-none tracking-[.1em] text-fg-3" aria-hidden="true">
          <span className="flex-1">MACHINE · RUN</span><span className="w-[110px]">FREQ</span><span className="w-24">AMP</span><span className="w-24">STATUS</span>
        </div>

        {v.loading && (
          <div role="status" aria-label="Loading runs">
            {v.skel6.map(k => <div key={k} className="h-[58px] border-b border-line bg-[linear-gradient(90deg,transparent,var(--panel-2),transparent)]" />)}
          </div>
        )}
        {v.empty && <div className="p-10 text-center text-fg-2">No runs yet.</div>}

        {runs.map(r => (
          <a key={r.run} href={r.href} className="flex flex-wrap items-center gap-x-4 gap-y-1.5 px-4 py-3 border-b border-line text-fg no-underline hover:no-underline">
            <div className="flex-1 min-w-[200px]">
              <div className="font-medium">
                {r.title}
                {r.hasTag && <span className="ml-1.5 font-mono text-[11px] font-normal leading-none text-fg-3">{r.tag}</span>}
              </div>
              <div className="font-mono text-[11.5px] leading-[1.5] text-fg-3 [overflow-wrap:anywhere]">{r.run} · {r.date} {r.time}</div>
            </div>
            <span className="w-[110px] font-mono text-[13px] font-medium leading-none tabular">{r.freq}</span>
            <span className="w-24 font-mono text-[12.5px] leading-none text-fg-2 tabular">{r.amp}</span>
            <span className="w-24">
              <span className="px-[7px] py-1 border rounded-chip font-mono text-[10px] font-semibold leading-none tracking-[.06em] uppercase whitespace-nowrap"
                style={{ borderColor: r.sevColor, color: r.sevColor }}>{r.sevLabel}</span>
            </span>
          </a>
        ))}
      </section>
    </div>
  );
}
