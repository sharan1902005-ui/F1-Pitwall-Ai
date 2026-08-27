import { Flag } from "lucide-react";
import type { StrategyResult } from "../../types/api";
import { TyreBadge } from "../ui/TyreBadge";

export function StrategyTimeline({ strategy }: { strategy: StrategyResult }) {
  const total = strategy.stints[strategy.stints.length - 1]?.end_lap ?? 1;
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 text-xs text-slate-400">
        <Flag className="h-4 w-4 text-pit-red" />
        Pit laps: {strategy.pit_laps.length ? strategy.pit_laps.join(", ") : "none"}
      </div>
      <div className="flex h-12 overflow-hidden rounded border border-white/10 bg-white/[0.04]">
        {strategy.stints.map((stint) => {
          const width = ((stint.end_lap - stint.start_lap + 1) / total) * 100;
          return (
            <div
              key={`${stint.compound}-${stint.start_lap}`}
              className="flex min-w-12 items-center justify-center border-r border-black/30 px-2 text-xs font-bold"
              style={{ width: `${width}%` }}
            >
              <span className="truncate">{stint.compound}</span>
            </div>
          );
        })}
      </div>
      <div className="flex flex-wrap gap-2">
        {strategy.stints.map((stint) => (
          <div key={`${stint.compound}-${stint.start_lap}-label`} className="rounded border border-white/10 bg-black/20 px-2 py-1 text-xs text-slate-300">
            <TyreBadge compound={stint.compound} /> <span className="ml-2">L{stint.start_lap}-{stint.end_lap}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
