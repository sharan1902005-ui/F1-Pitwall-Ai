export function Panel({
  title,
  action,
  children,
  className = "",
}: {
  title?: string;
  action?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <section className={`rounded-lg border border-white/10 bg-pit-panel/88 p-4 shadow-telemetry ${className}`}>
      {(title || action) && (
        <div className="mb-4 flex items-center justify-between gap-3">
          {title && <h2 className="text-sm font-bold uppercase tracking-[0.18em] text-slate-300">{title}</h2>}
          {action}
        </div>
      )}
      {children}
    </section>
  );
}
