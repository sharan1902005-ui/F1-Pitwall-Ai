import { Loader2 } from "lucide-react";
import { useState } from "react";
import { EmptyState } from "../components/ui/EmptyState";
import { Panel } from "../components/ui/Panel";
import { StatusPill } from "../components/ui/StatusPill";
import { StrategyTimeline } from "../components/strategy/StrategyTimeline";
import { formatRaceTime, strategyLabel } from "../lib/format";
import { api, ApiError } from "../services/api";
import { useRaceStore } from "../store/raceStore";
import type { PageId } from "../types/navigation";

export function StrategyLabPage({ setPage }: { setPage: (page: PageId) => void }) {
  const { raceConfig, strategy, setStrategy } = useRaceStore();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function analyze() {
    setLoading(true);
    setError(null);
    try {
      setStrategy(await api.analyzeStrategy(raceConfig));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Strategy analysis failed.");
    } finally {
      setLoading(false);
    }
  }

  const recommended = strategy?.recommended_strategy;
  const leader = recommended?.expected_race_time_seconds ?? 0;

  return (
    <div className="space-y-5">
      <Panel title="Strategy Lab" action={<button onClick={analyze} disabled={loading} className="rounded bg-pit-red px-4 py-2 text-sm font-black uppercase text-white disabled:opacity-60">{loading ? <Loader2 className="inline h-4 w-4 animate-spin" /> : null} Analyze</button>}>
        {error && <StatusPill tone="red">{error}</StatusPill>}
        {recommended ? (
          <div className="space-y-4">
            <div className="flex flex-wrap items-end justify-between gap-3">
              <div>
                <div className="text-sm font-bold uppercase tracking-[0.2em] text-pit-green">Recommended</div>
                <div className="mt-1 text-3xl font-black">{strategyLabel(recommended.stints)}</div>
              </div>
              <div className="flex gap-2">
                <StatusPill tone="blue">{formatRaceTime(recommended.expected_race_time_seconds)}</StatusPill>
                <StatusPill tone={recommended.risk === "HIGH" ? "red" : recommended.risk === "MEDIUM" ? "yellow" : "green"}>{recommended.risk}</StatusPill>
              </div>
            </div>
            <StrategyTimeline strategy={recommended} />
          </div>
        ) : (
          <EmptyState title="No strategies analyzed" message="Run strategy analysis using the current RaceConfig." action={<button onClick={analyze} className="rounded bg-pit-red px-4 py-2 text-sm font-bold">Analyze Strategy</button>} />
        )}
      </Panel>

      {strategy?.strategies.length ? (
        <Panel title="Backend Ranked Strategies">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[760px] text-left text-sm">
              <thead className="text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="p-3">Rank</th>
                  <th className="p-3">Strategy</th>
                  <th className="p-3">Pit Laps</th>
                  <th className="p-3">Expected</th>
                  <th className="p-3">Gap</th>
                  <th className="p-3">Confidence</th>
                  <th className="p-3">Risk</th>
                </tr>
              </thead>
              <tbody>
                {strategy.strategies.map((item) => (
                  <tr key={item.strategy_id} className="border-t border-white/10">
                    <td className="p-3 font-black">P{item.projected_finish}</td>
                    <td className="p-3">{strategyLabel(item.stints)}</td>
                    <td className="p-3">{item.pit_laps.join(", ") || "none"}</td>
                    <td className="p-3">{formatRaceTime(item.expected_race_time_seconds)}</td>
                    <td className="p-3">{item.expected_race_time_seconds === leader ? "leader" : `+${(item.expected_race_time_seconds - leader).toFixed(3)}s`}</td>
                    <td className="p-3">{Math.round(item.confidence * 100)}%</td>
                    <td className="p-3"><StatusPill tone={item.risk === "HIGH" ? "red" : item.risk === "MEDIUM" ? "yellow" : "green"}>{item.risk}</StatusPill></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>
      ) : null}
    </div>
  );
}
