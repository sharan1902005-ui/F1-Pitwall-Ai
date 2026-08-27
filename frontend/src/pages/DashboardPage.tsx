import { Activity, BrainCircuit, Flag, Timer } from "lucide-react";
import { motion } from "framer-motion";
import { Panel } from "../components/ui/Panel";
import { EmptyState } from "../components/ui/EmptyState";
import { StatusPill } from "../components/ui/StatusPill";
import { StrategyTimeline } from "../components/strategy/StrategyTimeline";
import { formatRaceTime, strategyLabel } from "../lib/format";
import { useRaceStore } from "../store/raceStore";
import type { PageId } from "../types/navigation";

export function DashboardPage({ setPage }: { setPage: (page: PageId) => void }) {
  const { raceConfig, simulation, strategy } = useRaceStore();
  const recommended = strategy?.recommended_strategy;
  const leaderTime = recommended?.expected_race_time_seconds;

  return (
    <div className="space-y-5">
      <div className="grid gap-3 md:grid-cols-5">
        {[
          ["CIRCUIT", raceConfig.circuit.circuit_name, Flag],
          ["RACE DISTANCE", `${raceConfig.circuit.total_laps} LAPS`, Activity],
          ["CURRENT STRATEGY", strategyLabel(recommended?.stints), BrainCircuit],
          ["CONFIDENCE", recommended ? `${Math.round(recommended.confidence * 100)}%` : "--", Timer],
          ["RACE STATUS", simulation ? "SIMULATED" : "READY", Activity],
        ].map(([label, value, Icon]) => (
          <motion.div
            key={label as string}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            className="rounded-lg border border-white/10 bg-pit-panel p-4"
          >
            <div className="mb-3 flex items-center justify-between text-xs font-bold text-slate-500">
              {label as string}
              <Icon className="h-4 w-4 text-pit-blue" />
            </div>
            <div className="truncate text-lg font-black text-white">{value as string}</div>
          </motion.div>
        ))}
      </div>

      <div className="grid gap-5 xl:grid-cols-[1fr_1.2fr]">
        <Panel title="Strategy Recommendation">
          {recommended ? (
            <div className="space-y-5">
              <div>
                <div className="text-3xl font-black text-white">{strategyLabel(recommended.stints)}</div>
                <p className="mt-2 text-sm text-slate-400">{recommended.recommendation_reason}</p>
              </div>
              <div className="grid gap-3 sm:grid-cols-3">
                <Metric label="Expected Race Time" value={formatRaceTime(recommended.expected_race_time_seconds)} />
                <Metric label="Confidence" value={`${Math.round(recommended.confidence * 100)}%`} />
                <Metric label="Risk" value={recommended.risk} tone={recommended.risk === "HIGH" ? "red" : recommended.risk === "MEDIUM" ? "yellow" : "green"} />
              </div>
              <button onClick={() => setPage("strategy")} className="rounded bg-pit-red px-4 py-3 text-sm font-black uppercase tracking-wide text-white hover:bg-red-500">
                Analyze Strategy
              </button>
            </div>
          ) : (
            <EmptyState
              title="No strategy data available"
              message="Run a strategy analysis from Race Setup or Strategy Lab."
              action={<button onClick={() => setPage("setup")} className="rounded bg-pit-red px-4 py-2 text-sm font-bold">Configure Race</button>}
            />
          )}
        </Panel>

        <Panel title="Strategy Comparison">
          {strategy?.strategies.length ? (
            <div className="space-y-3">
              {strategy.strategies.slice(0, 5).map((item) => {
                const gap = leaderTime == null ? 0 : item.expected_race_time_seconds - leaderTime;
                return (
                  <div key={item.strategy_id} className="rounded border border-white/10 bg-white/[0.035] p-3">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div>
                        <div className="font-bold text-white">P{item.projected_finish} {strategyLabel(item.stints)}</div>
                        <div className="text-xs text-slate-400">{formatRaceTime(item.expected_race_time_seconds)} {gap > 0 ? `+${gap.toFixed(3)}s` : "leader"}</div>
                      </div>
                      <div className="flex gap-2">
                        <StatusPill tone={item.risk === "HIGH" ? "red" : item.risk === "MEDIUM" ? "yellow" : "green"}>{item.risk}</StatusPill>
                        <StatusPill tone="blue">{Math.round(item.confidence * 100)}%</StatusPill>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <EmptyState title="No rankings yet" message="Backend rankings will appear here after analysis." />
          )}
        </Panel>
      </div>

      {recommended && (
        <Panel title="Recommended Timeline">
          <StrategyTimeline strategy={recommended} />
        </Panel>
      )}
    </div>
  );
}

function Metric({ label, value, tone = "blue" }: { label: string; value: string; tone?: "red" | "blue" | "green" | "yellow" }) {
  return (
    <div className="rounded border border-white/10 bg-black/20 p-3">
      <div className="text-xs font-bold uppercase tracking-wide text-slate-500">{label}</div>
      <div className="mt-2 flex items-center text-xl font-black text-white">
        <StatusPill tone={tone}>{value}</StatusPill>
      </div>
    </div>
  );
}
