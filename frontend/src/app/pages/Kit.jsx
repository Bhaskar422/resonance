import { PageHeader, AutoGrid, SeverityBadge, EvidenceChip, MetricTile, TileGrid, StageRow, BeforeAfterSlider, EmptyState, Button, Skeleton } from '../../components/ui.jsx';

function Card({ title, children }) {
  return (
    <section className="flex flex-col gap-3 p-4 bg-panel border border-line rounded-[4px] min-w-0">
      <h2 className="m-0 font-mono text-[11px] font-medium leading-none tracking-[.12em] text-fg-3">{title}</h2>
      {children}
    </section>
  );
}

export default function Kit({ v }) {
  const k = v.kit;
  if (!k) return null;
  const rep = v.rep && v.rep.ok ? v.rep : null;
  const res = v.rs && v.rs.res;
  return (
    <div className="flex flex-col gap-[18px]">
      <PageHeader eyebrow="SYS · COMPONENTS" title="Component kit" sub="Shared across all three directions; only the visual language changes." />

      <AutoGrid min={380} gap={16}>
        <Card title="SEVERITY BADGE">
          <div className="flex flex-wrap gap-2">{k.sevs.map(s => <SeverityBadge key={s.sevLabel} s={s} />)}</div>
        </Card>

        <Card title="EVIDENCE CHIP">
          <div className="flex flex-wrap gap-1.5">{k.chips.map(e => <EvidenceChip key={e.srcCode} e={e} />)}</div>
        </Card>

        <Card title="METRIC TILE">
          {rep ? (
            <TileGrid min={120}>
              <MetricTile label="FREQUENCY" value={rep.hz} unit="Hz" color="var(--signal)" big={26} />
              <MetricTile label="SNR" value={rep.snr} unit="ratio" big={26} />
            </TileGrid>
          ) : <Skeleton h={88} />}
        </Card>

        <Card title="STAGE PROGRESS">
          <div className="border border-line">{k.stages.map(g => <StageRow key={g.label} g={g} showDesc={false} />)}</div>
        </Card>

        <Card title="BEFORE / AFTER SLIDER">
          {rep ? <BeforeAfterSlider s={rep.slider} label="Slider demo" /> : <Skeleton className="aspect-video" h="auto" />}
        </Card>

        <Card title="VERDICT CARD">
          {res ? (
            <div className="flex items-center gap-4 p-4 border rounded-[4px]" style={{ borderColor: res.color }}>
              <span className="font-mono text-[36px] font-medium leading-none tabular">{res.big}</span>
              <div className="min-w-0">
                <div className="font-semibold" style={{ color: res.color }}>{res.label}</div>
                <div className="font-mono text-[12px] leading-[1.4] text-fg-3">at {res.hz} · {res.bigDb}</div>
              </div>
            </div>
          ) : <Skeleton h={70} />}
        </Card>

        <Card title="EMPTY STATE">
          <EmptyState title="Nothing here yet">One honest sentence about what to do next.</EmptyState>
        </Card>

        <Card title="TOAST & SKELETON">
          <div className="flex flex-wrap gap-2">
            <Button small onClick={k.toastOk}>Success toast</Button>
            <Button small onClick={k.toastErr}>Error toast</Button>
          </div>
          <div className="flex flex-col gap-2">
            <Skeleton w="60%" />
            <Skeleton w="85%" />
            <Skeleton w="40%" />
          </div>
        </Card>
      </AutoGrid>
    </div>
  );
}
