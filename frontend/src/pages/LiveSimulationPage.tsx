import { Loader2, Pause, Play, RotateCcw } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { EmptyState } from "../components/ui/EmptyState";
import { Panel } from "../components/ui/Panel";
import { StatusPill } from "../components/ui/StatusPill";
import { TyreBadge } from "../components/ui/TyreBadge";
import { formatRaceTime, percent } from "../lib/format";
import { api, ApiError } from "../services/api";
import { useRaceStore } from "../store/raceStore";
import type {
  ClassificationEntry,
  MultiDriverRaceConfig,
  MultiDriverRaceResult,
} from "../types/api";
import type { PageId } from "../types/navigation";

const speeds = [1, 2, 5, 10];

// Stable colour palette for up to 20 drivers in the position history chart.
const DRIVER_COLOURS = [
  "#39a9ff", "#ff314f", "#38d996", "#f5c542", "#b66cff",
  "#ff8c42", "#00d4aa", "#ff6b9d", "#7ecfff", "#ffd166",
  "#06d6a0", "#ef476f", "#118ab2", "#ffd60a", "#8338ec",
  "#fb5607", "#3a86ff", "#ffbe0b", "#ff006e", "#8ecae6",
];

export function LiveSimulationPage({ setPage }: { setPage: (page: PageId) => void }) {
  const { raceConfig, simulation, multiDriverSimulation, setMultiDriverSimulation } = useRaceStore();
  const [lapIndex, setLapIndex] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(2);
  const [selectedDriverId, setSelectedDriverId] = useState("");
  const [multiLoading, setMultiLoading] = useState(false);
  const [multiError, setMultiError] = useState<string | null>(null);

  const competitiveResult =
    multiDriverSimulation &&
    JSON.stringify(multiDriverSimulation.config.race_config) === JSON.stringify(raceConfig)
      ? multiDriverSimulation.result
      : null;

  const hasStaleResult = multiDriverSimulation !== null && competitiveResult === null;

  async function launchMultiDriverRace() {
    setMultiLoading(true);
    setMultiError(null);
    try {
      const laps = raceConfig.circuit.total_laps;
      const mid = Math.round(laps * 0.48);
      const multiConfig: MultiDriverRaceConfig = {
        race_config: raceConfig,
        drivers: [
          { driver_id: "driver-a", driver_name: "Driver A", team_name: "Alpha", starting_compound: raceConfig.starting_compound, starting_fuel_kg: raceConfig.starting_fuel_kg, pace_factor: 0.99, degradation_factor: 1.0, strategy_mode: "MANUAL", strategy: [{ lap: mid, compound: "HARD" }] },
          { driver_id: "driver-b", driver_name: "Driver B", team_name: "Beta", starting_compound: "SOFT", starting_fuel_kg: raceConfig.starting_fuel_kg, pace_factor: 1.01, degradation_factor: 1.05, strategy_mode: "MANUAL", strategy: [{ lap: Math.round(laps * 0.35), compound: "MEDIUM" }, { lap: Math.round(laps * 0.65), compound: "HARD" }] },
          { driver_id: "driver-c", driver_name: "Driver C", team_name: "Gamma", starting_compound: "HARD", starting_fuel_kg: raceConfig.starting_fuel_kg, pace_factor: 1.0, degradation_factor: 0.95, strategy_mode: "MANUAL", strategy: [{ lap: Math.round(laps * 0.55), compound: "MEDIUM" }] },
        ],
        event_seed_state: raceConfig.weather_seed_state,
      };
      const result = await api.simulateMultiRace(multiConfig);
      setMultiDriverSimulation({ config: multiConfig, result });
    } catch (err) {
      setMultiError(err instanceof ApiError ? err.message : "Multi-driver simulation failed.");
    } finally {
      setMultiLoading(false);
    }
  }

  // Replay timer — driven by single-car lap_results length.
  useEffect(() => {
    if (!playing || !simulation) return;
    const timer = window.setInterval(() => {
      setLapIndex((current) => {
        if (current >= simulation.lap_results.length - 1) {
          setPlaying(false);
          return current;
        }
        return current + 1;
      });
    }, 900 / speed);
    return () => window.clearInterval(timer);
  }, [playing, simulation, speed]);

  const lap = simulation?.lap_results[lapIndex];
  const chartData = useMemo(() => simulation?.lap_results.map((item) => ({
    lap: item.lap_number,
    lap_time: item.lap_time_seconds,
    compound: item.compound,
    tyre_age: item.tyre_age,
    fuel: item.fuel_remaining_kg,
    wetness: item.track_wetness,
  })) ?? [], [simulation]);

  if (!simulation || !lap) {
    return (
      <div className="space-y-5">
        <EmptyState
          title="No race data available"
          message="Configure a race and run the complete backend simulation first."
          action={<button onClick={() => setPage("setup")} className="rounded bg-pit-red px-4 py-2 text-sm font-bold">Configure Race</button>}
        />
        <RacePositionPanel
          result={competitiveResult}
          hasStaleResult={hasStaleResult}
          lapNumber={competitiveResult?.total_laps ?? null}
          selectedDriverId={selectedDriverId}
          onSelectDriver={setSelectedDriverId}
          onRunMultiDriver={launchMultiDriverRace}
          multiLoading={multiLoading}
          onOpenCompetitive={() => setPage("competitive")}
        />
        {multiError && <StatusPill tone="red">{multiError}</StatusPill>}
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <Panel title="Live Replay Controls">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <div className="text-4xl font-black text-white">LAP {lap.lap_number} / {simulation.total_laps}</div>
            <div className="text-sm text-slate-400">Cumulative {formatRaceTime(lap.cumulative_race_time)}</div>
          </div>
          <div className="flex flex-wrap gap-2">
            <button onClick={() => setPlaying(true)} disabled={playing} className="rounded bg-pit-green px-4 py-2 font-bold text-black disabled:opacity-50"><Play className="inline h-4 w-4" /> Play</button>
            <button onClick={() => setPlaying(false)} disabled={!playing} className="rounded border border-white/10 px-4 py-2 font-bold disabled:opacity-50"><Pause className="inline h-4 w-4" /> Pause</button>
            <button onClick={() => { setPlaying(false); setLapIndex(0); }} className="rounded border border-white/10 px-4 py-2 font-bold"><RotateCcw className="inline h-4 w-4" /> Restart</button>
            <select value={speed} onChange={(e) => setSpeed(Number(e.target.value))} className="rounded border border-white/10 bg-pit-panel2 px-3">
              {speeds.map((item) => <option key={item} value={item}>{item}x</option>)}
            </select>
          </div>
        </div>
        <input
          className="mt-5 w-full accent-pit-red"
          type="range"
          min={0}
          max={simulation.lap_results.length - 1}
          value={lapIndex}
          onChange={(e) => { setPlaying(false); setLapIndex(Number(e.target.value)); }}
        />
      </Panel>

      <div className="grid gap-4 md:grid-cols-5">
        <Telemetry label="Current Tyre" value={<TyreBadge compound={lap.compound} />} />
        <Telemetry label="Tyre Age" value={`${lap.tyre_age} laps`} />
        <Telemetry label="Fuel" value={`${lap.fuel_remaining_kg.toFixed(1)} kg`} />
        <Telemetry label="Track Wetness" value={percent(lap.track_wetness)} />
        <Telemetry label="Rain Probability" value={percent(lap.rain_probability)} />
      </div>

      <RacePositionPanel
        result={competitiveResult}
        hasStaleResult={hasStaleResult}
        lapNumber={lap.lap_number}
        selectedDriverId={selectedDriverId}
        onSelectDriver={setSelectedDriverId}
        onRunMultiDriver={launchMultiDriverRace}
        multiLoading={multiLoading}
        onOpenCompetitive={() => setPage("competitive")}
      />

      {multiError && <StatusPill tone="red">{multiError}</StatusPill>}

      <Panel title="Lap Time Trace">
        <div className="h-80 min-w-[640px]">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData}>
              <CartesianGrid stroke="#2a3140" strokeDasharray="3 3" />
              <XAxis dataKey="lap" stroke="#94a3b8" />
              <YAxis stroke="#94a3b8" domain={["dataMin - 1", "dataMax + 1"]} />
              <Tooltip contentStyle={{ background: "#10131a", border: "1px solid #2a3140" }} />
              {simulation.pit_stops.map((pit) => <ReferenceLine key={pit.lap_number} x={pit.lap_number} stroke="#ff314f" label="PIT" />)}
              <Line type="monotone" dataKey="lap_time" stroke="#39a9ff" dot={false} strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </Panel>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Position history chart
// ---------------------------------------------------------------------------

function PositionHistoryChart({
  result,
  currentLap,
  selectedDriverId,
}: {
  result: MultiDriverRaceResult;
  currentLap: number;
  selectedDriverId: string;
}) {
  // Build one data point per lap: { lap, [driver_id]: position }
  const driverIds = result.driver_results.map((d) => d.driver_id);
  const driverNames: Record<string, string> = Object.fromEntries(
    result.driver_results.map((d) => [d.driver_id, d.driver_name]),
  );

  const chartData = useMemo(() => {
    return result.classification_by_lap
      .filter((snap) => snap.lap_number <= currentLap)
      .map((snap) => {
        const point: Record<string, number> = { lap: snap.lap_number };
        for (const entry of snap.classification) {
          point[entry.driver_id] = entry.position;
        }
        return point;
      });
  }, [result.classification_by_lap, currentLap]);

  const maxPos = driverIds.length;

  return (
    <div className="h-64 min-w-[480px]">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData}>
          <CartesianGrid stroke="#2a3140" strokeDasharray="3 3" />
          <XAxis dataKey="lap" stroke="#94a3b8" label={{ value: "Lap", position: "insideBottomRight", offset: -4, fill: "#94a3b8", fontSize: 11 }} />
          <YAxis
            stroke="#94a3b8"
            domain={[1, maxPos]}
            reversed
            ticks={Array.from({ length: maxPos }, (_, i) => i + 1)}
            tickFormatter={(v: number) => `P${v}`}
          />
          <Tooltip
            contentStyle={{ background: "#10131a", border: "1px solid #2a3140" }}
            formatter={(value: number, key: string) => [`P${value}`, driverNames[key] ?? key]}
          />
          {driverIds.map((id, index) => (
            <Line
              key={id}
              type="stepAfter"
              dataKey={id}
              stroke={DRIVER_COLOURS[index % DRIVER_COLOURS.length]}
              strokeWidth={id === selectedDriverId ? 3 : 1.5}
              strokeOpacity={id === selectedDriverId ? 1 : 0.55}
              dot={false}
              isAnimationActive={false}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Race position panel
// ---------------------------------------------------------------------------

function RacePositionPanel({
  result,
  hasStaleResult,
  lapNumber,
  selectedDriverId,
  onSelectDriver,
  onRunMultiDriver,
  multiLoading,
  onOpenCompetitive,
}: {
  result: MultiDriverRaceResult | null;
  hasStaleResult: boolean;
  lapNumber: number | null;
  selectedDriverId: string;
  onSelectDriver: (driverId: string) => void;
  onRunMultiDriver: () => void;
  multiLoading: boolean;
  onOpenCompetitive: () => void;
}) {
  const classification =
    result?.classification_by_lap.find((snap) => snap.lap_number === lapNumber)?.classification ?? [];
  const prevClassification =
    result && lapNumber !== null && lapNumber > 1
      ? result.classification_by_lap.find((snap) => snap.lap_number === lapNumber - 1)?.classification ?? []
      : [];

  const selectedDriver =
    classification.find((e) => e.driver_id === selectedDriverId) ?? classification[0];
  const prevSelected = selectedDriver
    ? prevClassification.find((e) => e.driver_id === selectedDriver.driver_id)
    : undefined;

  const finalClassification =
    result?.classification.find((e) => e.driver_id === selectedDriver?.driver_id);
  const ahead = selectedDriver && selectedDriver.position > 1
    ? classification.find((e) => e.position === selectedDriver.position - 1)
    : undefined;
  const driverResult =
    result?.driver_results.find((d) => d.driver_id === selectedDriver?.driver_id);
  const currentLapResult =
    driverResult?.lap_results.find((l) => l.lap_number === lapNumber);
  const positionChange = prevSelected
    ? prevSelected.position - selectedDriver.position
    : null;
  const gapToAhead = selectedDriver && ahead
    ? gapLabel(selectedDriver, ahead)
    : null;

  // Build driver-id → colour index map (stable across renders)
  const driverColourMap = useMemo(() => {
    if (!result) return {} as Record<string, string>;
    return Object.fromEntries(
      result.driver_results.map((d, i) => [d.driver_id, DRIVER_COLOURS[i % DRIVER_COLOURS.length]]),
    );
  }, [result]);

  return (
    <Panel
      title="Race Position / Classification"
      action={
        result && lapNumber !== null
          ? <StatusPill tone="blue">Lap {lapNumber}/{result.total_laps} · {classification.length} cars</StatusPill>
          : undefined
      }
    >
      {!result || !selectedDriver ? (
        <div className="space-y-3">
          {hasStaleResult && (
            <StatusPill tone="yellow">
              A previous multi-driver result exists but does not match the current race configuration.
            </StatusPill>
          )}
          <div className="flex flex-wrap items-center justify-between gap-3 text-sm text-slate-400">
            <p>
              {hasStaleResult
                ? "Update the configuration or run a new multi-driver race to see classification here."
                : "No multi-driver race has been run for this configuration. Run one to see race positions here."}
            </p>
            <div className="flex flex-wrap gap-2">
              <button
                onClick={onRunMultiDriver}
                disabled={multiLoading}
                className="inline-flex shrink-0 items-center gap-2 rounded bg-pit-blue px-3 py-2 font-bold text-white disabled:opacity-60"
              >
                {multiLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                Run Multi-Driver Race
              </button>
              <button onClick={onOpenCompetitive} className="shrink-0 rounded border border-white/10 px-3 py-2 font-bold text-slate-200">
                Open Competitive Lab
              </button>
            </div>
          </div>
        </div>
      ) : (
        <>
          {/* Driver selector + summary metrics */}
          <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
            <label className="text-xs font-bold uppercase tracking-wide text-slate-400">
              Focused driver
              <select
                value={selectedDriver.driver_id}
                onChange={(e) => onSelectDriver(e.target.value)}
                className="mt-1 block max-w-full rounded border border-white/10 bg-pit-panel2 px-3 py-2 text-sm text-white"
              >
                {result.driver_results.map((d) => (
                  <option key={d.driver_id} value={d.driver_id}>
                    {d.driver_name} · {d.team_name}
                  </option>
                ))}
              </select>
            </label>
            <div className="text-right text-xs text-slate-500">
              Positions from genuine cumulative race-time ordering.
            </div>
          </div>

          <div className="mb-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <PositionMetric label="Current position" value={`P${selectedDriver.position}`} />
            <PositionMetric
              label="Gap to leader"
              value={formatGap(selectedDriver.gap_to_leader_seconds, selectedDriver.completed_laps, classification[0])}
            />
            <PositionMetric label="Gap to ahead" value={gapToAhead ?? "LEADER"} />
            <PositionMetric
              label="Position Δ this lap"
              value={
                positionChange === null ? "--"
                  : positionChange > 0 ? `▲ ${positionChange}`
                  : positionChange < 0 ? `▼ ${Math.abs(positionChange)}`
                  : "—"
              }
              valueClass={
                positionChange === null ? ""
                  : positionChange > 0 ? "text-pit-green"
                  : positionChange < 0 ? "text-pit-red"
                  : "text-slate-400"
              }
            />
          </div>

          <div className="mb-4 flex flex-wrap items-center gap-2 text-sm">
            <span className="text-slate-400">Status:</span>
            <StatusPill tone={currentLapResult?.race_status === "FINISHED" ? "green" : currentLapResult?.race_status === "PITTING" ? "yellow" : "blue"}>
              {currentLapResult?.race_status ?? "UNKNOWN"}
            </StatusPill>
            <span className="ml-2 text-slate-400">Final:</span>
            <strong className="text-white">{finalClassification ? `P${finalClassification.position}` : "Not classified"}</strong>
          </div>

          {/* Leaderboard table */}
          <div className="overflow-x-auto">
            <table className="w-full min-w-[720px] text-left text-sm">
              <thead className="text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="p-3">Pos</th>
                  <th className="p-3">Δ</th>
                  <th className="p-3">Driver</th>
                  <th className="p-3">Constructor</th>
                  <th className="p-3">Gap to leader</th>
                  <th className="p-3">Gap ahead</th>
                  <th className="p-3">Status</th>
                  <th className="p-3">Final</th>
                </tr>
              </thead>
              <tbody>
                {classification.map((entry) => {
                  const aheadEntry = entry.position > 1
                    ? classification.find((c) => c.position === entry.position - 1)
                    : undefined;
                  const finalEntry = result.classification.find((c) => c.driver_id === entry.driver_id);
                  const lapEntry = result.driver_results
                    .find((d) => d.driver_id === entry.driver_id)
                    ?.lap_results.find((l) => l.lap_number === lapNumber);
                  const prevEntry = prevClassification.find((c) => c.driver_id === entry.driver_id);
                  const delta = prevEntry ? prevEntry.position - entry.position : null;
                  const driverColour = driverColourMap[entry.driver_id] ?? "#94a3b8";
                  const isSelected = entry.driver_id === selectedDriver.driver_id;

                  return (
                    <tr
                      key={entry.driver_id}
                      className={`border-t border-white/10 cursor-pointer transition-colors hover:bg-white/5 ${isSelected ? "bg-pit-blue/10" : ""}`}
                      onClick={() => onSelectDriver(entry.driver_id)}
                    >
                      <td className="p-3">
                        <span className="inline-flex items-center gap-1.5">
                          <span
                            className="inline-block h-2.5 w-2.5 rounded-full"
                            style={{ background: driverColour }}
                          />
                          <span className="font-black">P{entry.position}</span>
                        </span>
                      </td>
                      <td className="p-3 w-10 text-center font-bold">
                        {delta === null ? (
                          <span className="text-slate-600">—</span>
                        ) : delta > 0 ? (
                          <span className="text-pit-green">▲{delta}</span>
                        ) : delta < 0 ? (
                          <span className="text-pit-red">▼{Math.abs(delta)}</span>
                        ) : (
                          <span className="text-slate-500">—</span>
                        )}
                      </td>
                      <td className="p-3 font-bold">{entry.driver_name}</td>
                      <td className="p-3 text-slate-400">{entry.team_name}</td>
                      <td className="p-3">{formatGap(entry.gap_to_leader_seconds, entry.completed_laps, classification[0])}</td>
                      <td className="p-3">{aheadEntry ? gapLabel(entry, aheadEntry) : "LEADER"}</td>
                      <td className="p-3">{lapEntry?.race_status ?? "UNKNOWN"}</td>
                      <td className="p-3 font-bold">{finalEntry ? `P${finalEntry.position}` : "--"}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Position history chart */}
          {lapNumber !== null && lapNumber > 1 && (
            <div className="mt-5">
              <div className="mb-2 text-xs font-bold uppercase tracking-wide text-slate-500">
                Position History (Laps 1–{lapNumber})
              </div>
              <PositionHistoryChart
                result={result}
                currentLap={lapNumber}
                selectedDriverId={selectedDriver.driver_id}
              />
              <div className="mt-2 flex flex-wrap gap-3">
                {result.driver_results.map((d, i) => (
                  <span key={d.driver_id} className="flex items-center gap-1.5 text-xs text-slate-400">
                    <span
                      className="inline-block h-2 w-5 rounded"
                      style={{ background: DRIVER_COLOURS[i % DRIVER_COLOURS.length] }}
                    />
                    {d.driver_name}
                  </span>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </Panel>
  );
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function gapLabel(entry: ClassificationEntry, ahead: ClassificationEntry): string {
  if (entry.completed_laps < ahead.completed_laps) {
    const diff = ahead.completed_laps - entry.completed_laps;
    return `${diff} lap${diff === 1 ? "" : "s"}`;
  }
  return `${(entry.total_race_time_seconds - ahead.total_race_time_seconds).toFixed(3)}s`;
}

function formatGap(
  gapSeconds: number,
  completedLaps: number,
  leader: ClassificationEntry | undefined,
): string {
  if (!leader || completedLaps < leader.completed_laps) {
    return leader ? `${leader.completed_laps - completedLaps} lap` : "--";
  }
  return gapSeconds === 0 ? "LEADER" : `+${gapSeconds.toFixed(3)}s`;
}

function PositionMetric({
  label,
  value,
  valueClass = "",
}: {
  label: string;
  value: string;
  valueClass?: string;
}) {
  return (
    <div className="rounded border border-white/10 bg-black/20 p-3">
      <div className="text-xs font-bold uppercase tracking-wide text-slate-500">{label}</div>
      <div className={`mt-1 text-xl font-black text-white ${valueClass}`}>{value}</div>
    </div>
  );
}

function Telemetry({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-white/10 bg-pit-panel p-4">
      <div className="text-xs font-bold uppercase tracking-wide text-slate-500">{label}</div>
      <div className="mt-2 text-xl font-black text-white">{value}</div>
    </div>
  );
}
