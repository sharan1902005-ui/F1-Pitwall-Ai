import { Bot, Loader2, Send } from "lucide-react";
import { useMemo, useState } from "react";
import { EmptyState } from "../components/ui/EmptyState";
import { Panel } from "../components/ui/Panel";
import { StatusPill } from "../components/ui/StatusPill";
import { api, ApiError } from "../services/api";
import { useRaceStore } from "../store/raceStore";
import type { RaceContext, ScenarioType } from "../types/api";
import type { PageId } from "../types/navigation";

export function EngineerPage({ setPage }: { setPage: (page: PageId) => void }) {
  const { raceConfig, simulation, strategy, engineer, scenario, setEngineer, setScenario } = useRaceStore();
  const [loading, setLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [scenarioType, setScenarioType] = useState<ScenarioType>("DEGRADATION_INCREASE");

  const context = useMemo<RaceContext | null>(() => {
    const latest = simulation?.lap_results[Math.min(26, simulation.lap_results.length - 1)];
    const weather = simulation?.weather_history.find((item) => item.lap_number === latest?.lap_number);
    if (!latest || !weather || !simulation) return null;
    return {
      current_lap: latest.lap_number,
      total_laps: simulation.total_laps,
      current_compound: latest.compound,
      tyre_age: latest.tyre_age,
      fuel_remaining_kg: latest.fuel_remaining_kg,
      track_wetness: latest.track_wetness,
      rain_probability: latest.rain_probability,
      rain_intensity: weather.rain_intensity,
      track_temperature: latest.track_temperature,
      air_temperature: latest.air_temperature,
      current_position: null,
      recent_lap_times: simulation.lap_results.slice(Math.max(0, latest.lap_number - 4), latest.lap_number).map((lap) => lap.lap_time_seconds),
    };
  }, [simulation]);

  async function callEngineer(action: "explain" | "decision" | "scenario") {
    setLoading(action);
    setError(null);
    try {
      if (action === "explain") {
        setEngineer(await api.explainStrategy({ race_config: raceConfig, strategy_id: strategy?.recommended_strategy?.strategy_id ?? null, context }));
      }
      if (action === "decision") {
        if (!context) throw new Error("Run a simulation before requesting a live decision.");
        setEngineer(await api.decision({ race_config: raceConfig, context }));
      }
      if (action === "scenario") {
        const params = scenarioType === "DEGRADATION_INCREASE" ? { percent: 0.1 } : scenarioType === "RAIN_ARRIVES_EARLIER" ? { laps: 5 } : scenarioType === "TRACK_WETNESS_STAYS_LOW" ? { cap: 0.3 } : { percent: 0.2 };
        setScenario(await api.scenario({ race_config: raceConfig, scenario_type: scenarioType, scenario_parameters: params }));
      }
    } catch (err) {
      setError(err instanceof ApiError || err instanceof Error ? err.message : "Race engineer request failed.");
    } finally {
      setLoading(null);
    }
  }

  return (
    <div className="grid gap-5 xl:grid-cols-[0.95fr_1.05fr]">
      <Panel title="Race Engineer">
        <div className="mb-4 flex items-center gap-3">
          <Bot className="h-8 w-8 text-pit-purple" />
          <div>
            <div className="text-2xl font-black text-white">STRATEGY CHANNEL ACTIVE</div>
            <div className="text-sm text-slate-400">Grounded deterministic fallback enabled</div>
          </div>
        </div>
        <div className="grid gap-2 sm:grid-cols-2">
          <Action label="Why this strategy?" loading={loading === "explain"} onClick={() => callEngineer("explain")} />
          <Action label="Should I pit now?" loading={loading === "decision"} onClick={() => callEngineer("decision")} />
          <Action label="Explain current risk" loading={loading === "explain"} onClick={() => callEngineer("explain")} />
          <Action label="What if rain changes?" loading={loading === "scenario"} onClick={() => callEngineer("scenario")} />
        </div>
        <div className="mt-5">
          <label className="text-xs font-bold uppercase tracking-wide text-slate-400">Scenario</label>
          <select value={scenarioType} onChange={(e) => setScenarioType(e.target.value as ScenarioType)} className="mt-2 w-full rounded border border-white/10 bg-pit-panel2 px-3 py-3">
            <option value="DEGRADATION_INCREASE">Degradation increases by 10%</option>
            <option value="RAIN_INTENSITY_INCREASE">Rain intensity increases</option>
            <option value="RAIN_ARRIVES_EARLIER">Rain arrives earlier</option>
            <option value="TRACK_WETNESS_STAYS_LOW">Track stays drier</option>
          </select>
        </div>
        {error && <div className="mt-4"><StatusPill tone="red">{error}</StatusPill></div>}
      </Panel>

      <div className="space-y-5">
        <Panel title="Engineer Decision">
          {engineer ? (
            <div className="space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="text-3xl font-black text-white">{engineer.decision}</div>
                <StatusPill tone={engineer.urgency === "CRITICAL" || engineer.urgency === "HIGH" ? "red" : engineer.urgency === "MEDIUM" ? "yellow" : "green"}>Urgency {engineer.urgency}</StatusPill>
              </div>
              <p className="text-slate-300">{engineer.explanation}</p>
              <div className="grid gap-2">
                {engineer.key_factors.map((factor) => (
                  <div key={factor} className="rounded border border-white/10 bg-white/[0.035] p-3 text-sm text-slate-300">{factor}</div>
                ))}
              </div>
              <div className="flex flex-wrap gap-2">
                {engineer.recommended_compound && <StatusPill tone="green">{engineer.recommended_compound}</StatusPill>}
                {engineer.recommended_pit_lap && <StatusPill tone="red">Pit lap {engineer.recommended_pit_lap}</StatusPill>}
                {engineer.confidence != null && <StatusPill tone="blue">{Math.round(engineer.confidence * 100)}% confidence</StatusPill>}
                {engineer.risk && <StatusPill tone={engineer.risk === "HIGH" ? "red" : "yellow"}>{engineer.risk} risk</StatusPill>}
              </div>
            </div>
          ) : (
            <EmptyState title="Engineer standing by" message="Ask for a strategy explanation or live decision after analysis." action={<button onClick={() => setPage("setup")} className="rounded bg-pit-red px-4 py-2 text-sm font-bold">Prepare Race</button>} />
          )}
        </Panel>

        <Panel title="Scenario Analysis">
          {scenario ? (
            <div className="grid gap-4 md:grid-cols-2">
              <ScenarioMetric label="Baseline" value={scenario.baseline_strategy} />
              <ScenarioMetric label="Scenario" value={scenario.scenario_strategy} />
              <ScenarioMetric label="Time Difference" value={`${scenario.time_difference >= 0 ? "+" : ""}${scenario.time_difference.toFixed(3)}s`} />
              <ScenarioMetric label="Strategy Changed" value={scenario.strategy_changed ? "YES" : "NO"} />
              <div className="md:col-span-2 space-y-2">
                {scenario.key_changes.map((change) => <div key={change} className="rounded border border-white/10 bg-white/[0.035] p-3 text-sm">{change}</div>)}
              </div>
            </div>
          ) : (
            <EmptyState title="No scenario result" message="Run a controlled what-if analysis from the race engineer panel." />
          )}
        </Panel>
      </div>
    </div>
  );
}

function Action({ label, loading, onClick }: { label: string; loading: boolean; onClick: () => void }) {
  return (
    <button onClick={onClick} disabled={loading} className="flex items-center justify-between rounded border border-white/10 bg-white/[0.04] px-4 py-3 text-left font-bold hover:bg-white/10 disabled:opacity-60">
      {label}
      {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4 text-pit-blue" />}
    </button>
  );
}

function ScenarioMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded border border-white/10 bg-black/20 p-3">
      <div className="text-xs font-bold uppercase tracking-wide text-slate-500">{label}</div>
      <div className="mt-2 text-lg font-black text-white">{value}</div>
    </div>
  );
}
