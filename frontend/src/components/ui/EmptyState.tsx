import { RadioTower } from "lucide-react";

export function EmptyState({
  title,
  message,
  action,
}: {
  title: string;
  message: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex min-h-56 flex-col items-center justify-center rounded-lg border border-dashed border-white/15 bg-white/[0.03] p-8 text-center">
      <RadioTower className="mb-3 h-8 w-8 text-pit-blue" />
      <h3 className="text-lg font-bold uppercase tracking-wide text-white">{title}</h3>
      <p className="mt-2 max-w-md text-sm text-slate-400">{message}</p>
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}
