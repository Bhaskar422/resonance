export default function More({ v }) {
  return (
    <div className="flex flex-col gap-3">
      <h1 className="m-0 text-[24px] font-semibold">More</h1>
      {(v.more || []).map(n => (
        <a key={n.key} href={n.href} aria-current={n.current}
          className="flex items-center justify-between min-h-[52px] px-4 bg-panel border border-line rounded-[4px] text-fg no-underline hover:no-underline hover:bg-panel-2">
          <span>{n.label}</span><span className="font-mono text-fg-3">→</span>
        </a>
      ))}
      <a href="/" className="flex items-center min-h-[52px] px-4 text-fg-2">Marketing site →</a>
    </div>
  );
}
