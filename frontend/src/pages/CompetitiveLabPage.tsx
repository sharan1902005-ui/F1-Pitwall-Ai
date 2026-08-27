import { Activity, Loader2, Plus, RotateCcw, Trash2 } from "lucide-react";
import { useMemo, useState } from "react";
import { Panel } from "../components/ui/Panel";
import { StatusPill } from "../components/ui/StatusPill";
import { TyreBadge } from "../components/ui/TyreBadge";
import { delta, formatRaceTime } from "../lib/format";
import { api, ApiError } from "../services/api";
import { useRaceStore } from "../store/raceStore";
import type {
  ClassificationEntry,
  CounterfactualResult,
  DriverConfig,
  MultiDriverRaceConfig,
  MultiDriverRaceResult,
  PitInstruction,
  TyreCompound,
} from "../types/api";

const compounds: TyreCompound[] = ["SOFT", "MEDIUM", "HARD", "INTERMEDIATE", "WET"];

const defaultDrivers: DriverConfig[] = [
  {
    driver_id: "driver-a",
    driver_name: "Driver A",
    team_name: "Alpha",
    starting_compound: "MEDIUM",
    starting_fuel_kg: 100,
    pace_factor: 0.99,
    degradation_factor: 1,
    strategy_mode: "MANUAL",
    strategy: [{ lap: 28, compound: "HARD" }],
  },
  {
    driver_id: "driver-b",
    driver_name: "Driver B",
    team_name: "Beta",
    starting_compound: "SOFT",
    starting_fuel_kg: 100,
    pace_factor: 1.01,
    degradation_factor: 1.05,
    strategy_mode: "MANUAL",
    strategy: [
      { lap: 20, compound: "MEDIUM" },
      { lap: 40, compound: "HARD" },
    ],
  },
  {
    driver_id: "driver-c",
    driver_name: "Driver C",
    team_name: "Gamma",
    starting_compound: "HARD",
    starting_fuel_kg: 100,
    pace_factor: 1,
    degradation_factor: 0.95,
    strategy_mode: "MANUAL",
    strategy: [{ lap: 32, compound: "MEDIUM" }],
  },
];

export function CompetitiveLabPage() {
  const { raceConfig } = useRaceStore();
  const [drivers, setDrivers] = useState<DriverConfig[]>(defaultDrivers);
  const [eventSeed, setEventSeed] = useState(7);
  const [result, setResult] = useState<MultiDriverRaceResult | null>(null);
  const [counterfactual, setCounterfactual] = useState<CounterfactualResult | null>(null);
  const [replayLap, setReplayLap] = useState(0);
  const [whatIfDriver, setWhatIfDriver] = useState(defaultDrivers[0].driver_id);
  const [whatIfLap, setWhatIfLap] = useState(31);
  const [whatIfCompound, setWhatIfCompound] = useState<TyreCompound>("HARD");
  const [loading, setLoading] = useState<"race" | "whatif" | null>(null);
  const [error, setError] = useState<string | null>(null);

  const config = useMemo<MultiDriverRaceConfig>(
    () => ({ race_config: raceConfig, drivers, event_seed_state: eventSeed }),
    [raceConfig, drivers, eventSeed],
  );

  const currentClassification =
    replayLap > 0
      ? result?.classification_by_lap.find((lap) => lap.lap_number === replayLap)?.classification
      : result?.classification;

  async function simulate() {
    setLoading("race");
    setError(null);
    setCounterfactual(null);
    try {
      const response = await api.simulateMultiRace(config);
      setResult(response);
      setReplayLap(response.total_laps);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Multi-driver simulation failed.");
    } finally {
      setLoading(null);
    }
  }

  async function runWhatIf(offset: number | "custom") {
    const baseline = drivers.find((driver) => driver.driver_id === whatIfDriver);
    if (!baseline) return;
    const targetLap =
      offset === "custom"
        ? whatIfLap
        : Math.min(raceConfig.circuit.total_laps, Math.max(2, nextPitLap(baseline) + offset));
    const alternativeStrategy = replaceFirstPit(baseline.strategy, targetLap, whatIfCompound);
    setLoading("whatif");
    setError(null);
    try {
      setCounterfactual(
        await api.counterfactual({
          base_config: config,
          driver_id: whatIfDriver,
          alternative_strategy: alternativeStrategy,
        }),
      );
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Counterfactual analysis failed.");
    } finally {
      setLoading(null);
    }
  }

  function updateDriver(index: number, patch: Partial<DriverConfig>) {
    setDrivers((current) =>
      current.map((driver, driverIndex) => (driverIndex === index ? { ...driver, ...patch } : driver)),
    );
  }

  function updateStrategy(index: number, pitIndex: number, patch: Partial<PitInstruction>) {
    setDrivers((current) =>
      current.map((driver, driverIndex) => {
        if (driverIndex !== index) return driver;
        return {
          ...driver,
          strategy: driver.strategy.map((pit, currentPitIndex) =>
            currentPitIndex === pitIndex ? { ...pit, ...patch } : pit,
          ),
        };
      }),
    );
  }

  return (
    <div className="space-y-5">
      <Panel
        title="Competitive Lab"
        action={
          <button
            onClick={simulate}
            disabled={loading !== null}
            className="inline-flex items-center gap-2 rounded bg-pit-red px-4 py-2 text-sm font-black uppercase text-white disabled:opacity-60"
          >
            {loading === "race" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Activity className="h-4 w-4" />}
            Simulate
          </button>
        }
      >
        {error && <StatusPill tone="red">{error}</StatusPill>}
        <div className="mt-4 grid gap-4 xl:grid-cols-[1.15fr_0.85fr]">
          <div className="space-y-3">
            <div className="flex flex-wrap items-center gap-3">
              <label className="text-xs font-bold uppercase tracking-wide text-slate-400">
                Event Seed
                <input
                  value={eventSeed}
                  onChange={(event) => setEventSeed(Number(event.target.value))}
                  type="number"
                  className="ml-2 w-24 rounded border border-white/10 bg-black/30 px-2 py-1 text-sm text-white"
                />
              </label>
              <button
                onClick={() =>
                  setDrivers((current) => [
                    ...current,
                    {
                      ...defaultDrivers[current.length % defaultDrivers.length],
                      driver_id: `driver-${current.length + 1}`,
                      driver_name: `Driver ${String.fromCharCode(65 + current.length)}`,
                    },
                  ])
                }
                disabled={drivers.length >= 20}
                className="inline-flex items-center gap-2 rounded border border-white/10 px-3 py-2 text-sm font-bold text-slate-200 disabled:opacity-50"
              >
                <Plus className="h-4 w-4" />
                Driver
              </button>
            </div>
            <div className="grid gap-3">
              {drivers.map((driver, index) => (
                <div key={driver.driver_id} className="rounded border border-white/10 bg-black/20 p-3">
                  <div className="grid gap-3 md:grid-cols-3">
                    <input value={driver.driver_name} onChange={(event) => updateDriver(index, { driver_name: event.target.value })} className="rounded border border-white/10 bg-black/30 px-3 py-2 text-sm" />
                    <input value={driver.team_name} onChange={(event) => updateDriver(index, { team_name: event.target.value })} className="rounded border border-white/10 bg-black/30 px-3 py-2 text-sm" />
                    <select value={driver.starting_compound} onChange={(event) => updateDriver(index, { starting_compound: event.target.value as TyreCompound })} className="rounded border border-white/10 bg-black/30 px-3 py-2 text-sm">
                      {compounds.map((compound) => <option key={compound}>{compound}</option>)}
                    </select>
                  </div>
                  <div className="mt-3 grid gap-3 md:grid-cols-4">
                    <NumberField label="Fuel" value={driver.starting_fuel_kg} min={0} max={160} step={1} onChange={(value) => updateDriver(index, { starting_fuel_kg: value })} />
                    <NumberField label="Pace" value={driver.pace_factor} min={0.94} max={1.08} step={0.005} onChange={(value) => updateDriver(index, { pace_factor: value })} />
                    <NumberField label="Degradation" value={driver.degradation_factor} min={0.7} max={1.4} step={0.01} onChange={(value) => updateDriver(index, { degradation_factor: value })} />
                    <select value={driver.strategy_mode} onChange={(event) => updateDriver(index, { strategy_mode: event.target.value as DriverConfig["strategy_mode"] })} className="rounded border border-white/10 bg-black/30 px-3 py-2 text-sm">
                      <option value="MANUAL">MANUAL</option>
                      <option value="AI">AI</option>
                    </select>
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {driver.strategy.map((pit, pitIndex) => (
                      <div key={`${driver.driver_id}-${pitIndex}`} className="flex items-center gap-2 rounded border border-white/10 bg-white/[0.04] px-2 py-2">
                        <span className="text-xs font-bold text-slate-400">PIT</span>
                        <input type="number" value={pit.lap} min={2} max={raceConfig.circuit.total_laps} onChange={(event) => updateStrategy(index, pitIndex, { lap: Number(event.target.value) })} className="w-16 rounded bg-black/40 px-2 py-1 text-sm" />
                        <select value={pit.compound} onChange={(event) => updateStrategy(index, pitIndex, { compound: event.target.value as TyreCompound })} className="rounded bg-black/40 px-2 py-1 text-sm">
                          {compounds.map((compound) => <option key={compound}>{compound}</option>)}
                        </select>
                      </div>
                    ))}
                    <button onClick={() => updateDriver(index, { strategy: [...driver.strategy, { lap: Math.min(raceConfig.circuit.total_laps, 30), compound: "HARD" }] })} className="rounded border border-white/10 px-3 py-2 text-xs font-bold">Add Pit</button>
                    {drivers.length > 2 && (
                      <button onClick={() => setDrivers((current) => current.filter((_, driverIndex) => driverIndex !== index))} className="rounded border border-white/10 p-2 text-slate-300">
                        <Trash2 className="h-4 w-4" />
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
          <ClassificationPanel classification={currentClassification ?? []} replayLap={replayLap} result={result} setReplayLap={setReplayLap} />
        </div>
      </Panel>

      {result && (
        <div className="grid gap-5 xl:grid-cols-[1fr_0.8fr]">
          <Panel title="Strategy Timelines">
            <div className="space-y-4">
              {result.classification.map((entry) => (
                <div key={entry.driver_id}>
                  <div className="mb-2 flex items-center justify-between text-sm">
                    <span className="font-black">P{entry.position} {entry.driver_name}</span>
                    <span className="text-slate-400">{entry.final_strategy.map((pit) => `L${pit.lap} ${pit.compound}`).join(" / ") || "No stops"}</span>
                  </div>
                  <StrategyBar entry={entry} totalLaps={result.total_laps} />
                </div>
              ))}
            </div>
          </Panel>
          <Panel title="What If?">
            <div className="grid gap-3">
              <select value={whatIfDriver} onChange={(event) => setWhatIfDriver(event.target.value)} className="rounded border border-white/10 bg-black/30 px-3 py-2 text-sm">
                {drivers.map((driver) => <option key={driver.driver_id} value={driver.driver_id}>{driver.driver_name}</option>)}
              </select>
              <div className="flex flex-wrap gap-2">
                <button onClick={() => runWhatIf(0)} className="rounded bg-pit-red px-3 py-2 text-sm font-bold">Pit Now</button>
                <button onClick={() => runWhatIf(1)} className="rounded border border-white/10 px-3 py-2 text-sm font-bold">Wait 1 Lap</button>
                <button onClick={() => runWhatIf(3)} className="rounded border border-white/10 px-3 py-2 text-sm font-bold">Wait 3 Laps</button>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <input type="number" value={whatIfLap} min={2} max={raceConfig.circuit.total_laps} onChange={(event) => setWhatIfLap(Number(event.target.value))} className="w-24 rounded border border-white/10 bg-black/30 px-3 py-2 text-sm" />
                <select value={whatIfCompound} onChange={(event) => setWhatIfCompound(event.target.value as TyreCompound)} className="rounded border border-white/10 bg-black/30 px-3 py-2 text-sm">
                  {compounds.map((compound) => <option key={compound}>{compound}</option>)}
                </select>
                <button onClick={() => runWhatIf("custom")} disabled={loading === "whatif"} className="inline-flex items-center gap-2 rounded border border-white/10 px-3 py-2 text-sm font-bold">
                  {loading === "whatif" ? <Loader2 className="h-4 w-4 animate-spin" /> : <RotateCcw className="h-4 w-4" />}
                  Run
                </button>
              </div>
              {counterfactual && (
                <div className="grid gap-3 rounded border border-white/10 bg-black/20 p-3 md:grid-cols-3">
                  <Metric label="Current Plan" value={`P${counterfactual.baseline.position}`} sub={formatRaceTime(counterfactual.baseline.race_time_seconds)} />
                  <Metric label="What If" value={`P${counterfactual.counterfactual.position}`} sub={delta(counterfactual.time_difference_seconds)} />
                  <Metric label="Position Impact" value={`${counterfactual.position_difference > 0 ? "+" : ""}${counterfactual.position_difference}`} sub={counterfactual.weather_identical && counterfactual.events_identical ? "Shared conditions" : "Condition mismatch"} />
                </div>
              )}
            </div>
          </Panel>
        </div>
      )}

      {result && (
        <Panel title="Opponent Analysis">
          <div className="grid gap-3 md:grid-cols-3">
            {result.opponent_insights.map((insight) => (
              <div key={insight.driver_id} className="rounded border border-white/10 bg-black/20 p-3">
                <div className="font-black">{insight.driver_name}</div>
                <div className="mt-2 text-sm text-slate-300">Current Tyre: <TyreBadge compound={insight.current_tyre} /></div>
                <div className="mt-1 text-sm text-slate-400">Tyre Age: {insight.tyre_age}</div>
                <div className="mt-1 text-sm text-slate-400">
                  {insight.prediction_available ? `Likely Pit Window: L${insight.likely_pit_window_start}-${insight.likely_pit_window_end}` : "No prediction available."}
                </div>
              </div>
            ))}
          </div>
        </Panel>
      )}
    </div>
  );
}

function ClassificationPanel({ classification, replayLap, result, setReplayLap }: { classification: ClassificationEntry[]; replayLap: number; result: MultiDriverRaceResult | null; setReplayLap: (lap: number) => void }) {
  return (
    <div className="rounded border border-white/10 bg-black/20 p-4">
      <div className="mb-3 flex items-center justify-between">
        <div className="text-sm font-black uppercase tracking-[0.18em] text-slate-300">Classification</div>
        {result && <StatusPill tone="blue">Lap {replayLap}/{result.total_laps}</StatusPill>}
      </div>
      {result && (
        <input type="range" min={1} max={result.total_laps} value={replayLap} onChange={(event) => setReplayLap(Number(event.target.value))} className="mb-4 w-full" />
      )}
      <div className="space-y-2">
        {classification.length ? classification.map((entry) => (
          <div key={entry.driver_id} className="grid grid-cols-[48px_1fr_auto] items-center gap-3 rounded border border-white/10 bg-white/[0.04] px-3 py-2">
            <div className="text-lg font-black">P{entry.position}</div>
            <div>
              <div className="font-bold">{entry.driver_name}</div>
              <div className="text-xs text-slate-400">{entry.team_name}</div>
            </div>
            <div className="text-sm font-bold">{entry.position === 1 ? "LEADER" : `+${entry.gap_to_leader_seconds.toFixed(3)}s`}</div>
          </div>
        )) : <div className="text-sm text-slate-400">Run a multi-driver simulation.</div>}
      </div>
    </div>
  );
}

function StrategyBar({ entry, totalLaps }: { entry: ClassificationEntry; totalLaps: number }) {
  const pitLaps = entry.final_strategy.map((pit) => pit.lap);
  return (
    <div className="flex h-9 overflow-hidden rounded border border-white/10 bg-white/[0.04]">
      {Array.from({ length: totalLaps }, (_, index) => index + 1).map((lap) => (
        <div key={lap} className={`min-w-1 flex-1 border-r border-black/30 ${pitLaps.includes(lap) ? "bg-pit-red" : "bg-pit-blue/35"}`} title={`Lap ${lap}`} />
      ))}
    </div>
  );
}

function Metric({ label, value, sub }: { label: string; value: string; sub: string }) {
  return (
    <div>
      <div className="text-xs font-bold uppercase tracking-wide text-slate-500">{label}</div>
      <div className="mt-1 text-2xl font-black">{value}</div>
      <div className="text-sm text-slate-400">{sub}</div>
    </div>
  );
}

function NumberField({ label, value, min, max, step, onChange }: { label: string; value: number; min: number; max: number; step: number; onChange: (value: number) => void }) {
  return (
    <label className="text-xs font-bold uppercase tracking-wide text-slate-400">
      {label}
      <input type="number" value={value} min={min} max={max} step={step} onChange={(event) => onChange(Number(event.target.value))} className="mt-1 w-full rounded border border-white/10 bg-black/30 px-3 py-2 text-sm text-white" />
    </label>
  );
}

function nextPitLap(driver: DriverConfig): number {
  return driver.strategy[0]?.lap ?? 2;
}

function replaceFirstPit(strategy: PitInstruction[], lap: number, compound: TyreCompound): PitInstruction[] {
  if (!strategy.length) return [{ lap, compound }];
  return [{ lap, compound }, ...strategy.slice(1)].sort((left, right) => left.lap - right.lap);
}
