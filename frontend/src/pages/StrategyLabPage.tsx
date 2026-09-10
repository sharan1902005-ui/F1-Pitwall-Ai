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
import type { UndercutResponse, OvercutResponse } from "../types/api";

export function StrategyLabPage({ setPage: _setPage }: { setPage: (page: PageId) => void }) {
  const { raceConfig, strategy, setStrategy } = useRaceStore();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [undercut, setUndercut] = useState<UndercutResponse | null>(null);
  const [undercutLoading, setUndercutLoading] = useState(false);
  const [undercutError, setUndercutError] = useState<string | null>(null);

  const [overcut, setOvercut] = useState<OvercutResponse | null>(null);
  const [overcutLoading, setOvercutLoading] = useState(false);
  const [overcutError, setOvercutError] = useState<string | null>(null);

  async function analyzeUndercut() {
    setUndercutLoading(true);
    setUndercutError(null);

    try {
      const currentLap = Math.max(
        1,
        Math.floor(raceConfig.circuit.total_laps / 2),
      );

      const result = await api.analyzeUndercut({
        attacker: {
          driver_name: "PitWall Driver",
          position: 5,
          compound: raceConfig.starting_compound,
          tyre_age: Math.floor(currentLap * 0.8),
          gap_to_driver_ahead_seconds: 1.2,
          current_lap: currentLap,
          base_lap_time_seconds: raceConfig.circuit.base_lap_time_seconds,
          degradation_per_lap: 0.08,
        },
        defender: {
          driver_name: "Driver Ahead",
          position: 4,
          compound: raceConfig.starting_compound,
          tyre_age: Math.floor(currentLap * 0.9),
          gap_to_driver_ahead_seconds: 0.8,
          current_lap: currentLap,
          base_lap_time_seconds: raceConfig.circuit.base_lap_time_seconds,
          degradation_per_lap: 0.1,
        },
        pit_lane_time_loss_seconds: raceConfig.circuit.pit_lane_time_loss_seconds,
        new_compound: "HARD",
        defender_stays_out_laps: 2,
      });

      setUndercut(result);
    } catch (err) {
      setUndercutError(
        err instanceof ApiError ? err.message : "Undercut analysis failed.",
      );
    } finally {
      setUndercutLoading(false);
    }
  }

  async function analyzeOvercut() {
    setOvercutLoading(true);
    setOvercutError(null);

    try {
      const currentLap = Math.max(
        1,
        Math.floor(raceConfig.circuit.total_laps / 2),
      );

      const result = await api.analyzeOvercut({
        driver: {
          driver_name: "PitWall Driver",
          position: 5,
          compound: raceConfig.starting_compound,
          tyre_age: Math.floor(currentLap * 0.8),
          gap_to_driver_ahead_seconds: 1.2,
          current_lap: currentLap,
          base_lap_time_seconds: raceConfig.circuit.base_lap_time_seconds,
          degradation_per_lap: 0.08,
        },
        opponent: {
          driver_name: "Opponent",
          position: 4,
          compound: raceConfig.starting_compound,
          tyre_age: Math.floor(currentLap * 0.9),
          gap_to_driver_ahead_seconds: 0.8,
          current_lap: currentLap,
          base_lap_time_seconds: raceConfig.circuit.base_lap_time_seconds,
          degradation_per_lap: 0.1,
        },
        pit_lane_time_loss_seconds: raceConfig.circuit.pit_lane_time_loss_seconds,
        max_stay_out_laps: 3,
      });

      setOvercut(result);
    } catch (err) {
      setOvercutError(
        err instanceof ApiError ? err.message : "Overcut analysis failed.",
      );
    } finally {
      setOvercutLoading(false);
    }
  }

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

      <Panel
        title="Undercut Intelligence"
        action={
          <button
            onClick={analyzeUndercut}
            disabled={undercutLoading}
            className="rounded bg-pit-red px-4 py-2 text-sm font-black uppercase text-white disabled:opacity-60"
          >
            {undercutLoading ? (
              <Loader2 className="inline h-4 w-4 animate-spin" />
            ) : (
              "Analyze"
            )}
          </button>
        }
      >
        {undercutError && (
          <StatusPill tone="red">{undercutError}</StatusPill>
        )}

        {undercut ? (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <div className="rounded-lg border border-white/10 bg-black/20 p-4">
              <div className="text-xs uppercase text-slate-500">Availability</div>
              <div className="mt-2">
                <StatusPill tone={undercut.undercut_available ? "green" : "red"}>
                  {undercut.undercut_available ? "AVAILABLE" : "NOT AVAILABLE"}
                </StatusPill>
              </div>
            </div>

            <div className="rounded-lg border border-white/10 bg-black/20 p-4">
              <div className="text-xs uppercase text-slate-500">Projected Gain</div>
              <div className="mt-2 text-2xl font-black">{undercut.projected_gain_seconds.toFixed(2)}s</div>
            </div>

            <div className="rounded-lg border border-white/10 bg-black/20 p-4">
              <div className="text-xs uppercase text-slate-500">Confidence</div>
              <div className="mt-2 text-2xl font-black">{Math.round(undercut.confidence * 100)}%</div>
            </div>

            <div className="rounded-lg border border-white/10 bg-black/20 p-4">
              <div className="text-xs uppercase text-slate-500">Recommended Tyre</div>
              <div className="mt-2 text-2xl font-black">{undercut.recommended_compound}</div>
            </div>

            <div className="rounded-lg border border-white/10 bg-black/20 p-4 md:col-span-2 lg:col-span-4">
              <div className="text-xs uppercase text-slate-500">Race Engineer Recommendation</div>
              <div className="mt-2 text-lg font-bold">{undercut.recommendation}</div>
              <div className="mt-3 flex flex-wrap gap-3 text-sm text-slate-400">
                <span>Projected Position: P{undercut.projected_position}</span>
                <span>Gap After Cycle: {undercut.projected_gap_after_cycle_seconds.toFixed(2)}s</span>
                <span>Analysis: {undercut.analysis_laps} laps</span>
              </div>
            </div>
          </div>
        ) : (
          <EmptyState
            title="No undercut analysis"
            message="Analyze the current race configuration to evaluate the undercut opportunity."
            action={
              <button
                onClick={analyzeUndercut}
                className="rounded bg-pit-red px-4 py-2 text-sm font-bold"
              >
                Analyze Undercut
              </button>
            }
          />
        )}
      </Panel>

      <Panel
        title="Overcut Intelligence"
        action={
          <button
            onClick={analyzeOvercut}
            disabled={overcutLoading}
            className="rounded bg-pit-red px-4 py-2 text-sm font-black uppercase text-white disabled:opacity-60"
          >
            {overcutLoading ? (
              <Loader2 className="inline h-4 w-4 animate-spin" />
            ) : (
              "Analyze"
            )}
          </button>
        }
      >
        {overcutError && (
          <StatusPill tone="red">{overcutError}</StatusPill>
        )}

        {overcut ? (
          <div className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
              <div className="rounded-lg border border-white/10 bg-black/20 p-4">
                <div className="text-xs uppercase text-slate-500">Availability</div>
                <div className="mt-2">
                  <StatusPill tone={overcut.overcut_available ? "green" : "red"}>
                    {overcut.overcut_available ? "AVAILABLE" : "NOT AVAILABLE"}
                  </StatusPill>
                </div>
              </div>

              <div className="rounded-lg border border-white/10 bg-black/20 p-4">
                <div className="text-xs uppercase text-slate-500">Best Stay Out</div>
                <div className="mt-2 text-2xl font-black">{overcut.best_stay_out_laps} laps</div>
              </div>

              <div className="rounded-lg border border-white/10 bg-black/20 p-4">
                <div className="text-xs uppercase text-slate-500">Projected Advantage</div>
                <div className="mt-2 text-2xl font-black">{overcut.projected_advantage_seconds.toFixed(2)}s</div>
              </div>

              <div className="rounded-lg border border-white/10 bg-black/20 p-4">
                <div className="text-xs uppercase text-slate-500">Confidence</div>
                <div className="mt-2 text-2xl font-black">{Math.round(overcut.confidence * 100)}%</div>
              </div>
            </div>

            <div className="rounded-lg border border-white/10 bg-black/20 p-4">
              <div className="text-xs uppercase text-slate-500">Race Engineer Recommendation</div>
              <div className="mt-2 text-lg font-bold">{overcut.recommendation}</div>
              <div className="mt-3 flex flex-wrap gap-4 text-sm text-slate-400">
                <span>Projected Position: P{overcut.projected_position}</span>
                <span>Gap After Cycle: {overcut.projected_gap_after_cycle_seconds.toFixed(2)}s</span>
              </div>
            </div>

            {overcut.options.length > 0 && (
              <div>
                <div className="mb-2 text-xs font-bold uppercase tracking-wide text-slate-500">Overcut Options</div>
                <div className="grid gap-3 md:grid-cols-3">
                  {overcut.options.map((option) => (
                    <div
                      key={option.stay_out_laps}
                      className="rounded-lg border border-white/10 bg-black/20 p-3"
                    >
                      <div className="font-black">Stay Out: {option.stay_out_laps} laps</div>
                      <div className="mt-2 text-sm text-slate-400">Advantage: {option.projected_advantage_seconds.toFixed(2)}s</div>
                      <div className="text-sm text-slate-400">Gap: {option.projected_gap_after_cycle_seconds.toFixed(2)}s</div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          <EmptyState
            title="No overcut analysis"
            message="Analyze the current race configuration to evaluate whether extending the stint creates an advantage."
            action={
              <button
                onClick={analyzeOvercut}
                className="rounded bg-pit-red px-4 py-2 text-sm font-bold"
              >
                Analyze Overcut
              </button>
            }
          />
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
