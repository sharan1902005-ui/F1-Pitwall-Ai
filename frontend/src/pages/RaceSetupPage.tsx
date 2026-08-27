import { Dice5, Loader2, Play } from "lucide-react";
import { useEffect, useState } from "react";
import { Panel } from "../components/ui/Panel";
import { StatusPill } from "../components/ui/StatusPill";
import { TyreBadge } from "../components/ui/TyreBadge";
import { api, ApiError } from "../services/api";
import { useRaceStore } from "../store/raceStore";
import type { TyreCompound } from "../types/api";

const compounds: TyreCompound[] = ["SOFT", "MEDIUM", "HARD", "INTERMEDIATE", "WET"];

export function RaceSetupPage() {
  const { circuits, setCircuits, raceConfig, setRaceConfig, setSimulation, setStrategy, setEngineer } = useRaceStore();
  const [selectedCircuitId, setSelectedCircuitId] = useState<number | "">("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    api.listCircuits().then(setCircuits).catch(() => setMessage("Circuit service unavailable."));
  }, [setCircuits]);

  async function loadCircuit(id: number) {
    setSelectedCircuitId(id);
    const config = await api.getCircuitConfig(id);
    setRaceConfig({ ...raceConfig, circuit: config });
  }

  async function runSimulation() {
    setLoading(true);
    setMessage("SIMULATING 57 LAPS...");
    try {
      const [simulation, strategy] = await Promise.all([
        api.runSimulation(raceConfig),
        api.analyzeStrategy(raceConfig),
      ]);
      setSimulation(simulation);
      setStrategy(strategy);
      setEngineer(null);
      setMessage("Simulation and strategy analysis complete.");
    } catch (error) {
      setMessage(error instanceof ApiError ? error.message : "Simulation failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="grid gap-5 xl:grid-cols-[1.1fr_0.9fr]">
      <Panel title="Race Configuration">
        <div className="space-y-5">
          <label className="block">
            <span className="text-xs font-bold uppercase tracking-wide text-slate-400">Circuit</span>
            <select
              value={selectedCircuitId}
              onChange={(event) => loadCircuit(Number(event.target.value))}
              className="mt-2 w-full rounded border border-white/10 bg-pit-panel2 px-3 py-3 text-white"
            >
              <option value="">Select backend circuit</option>
              {circuits.map((circuit) => (
                <option key={circuit.id} value={circuit.id}>{circuit.name} - {circuit.country}</option>
              ))}
            </select>
          </label>

          <div className="grid gap-3 sm:grid-cols-2">
            <NumberField label="Total Laps" value={raceConfig.circuit.total_laps} onChange={(v) => setRaceConfig({ ...raceConfig, circuit: { ...raceConfig.circuit, total_laps: v } })} />
            <NumberField label="Base Lap Time" value={raceConfig.circuit.base_lap_time_seconds} onChange={(v) => setRaceConfig({ ...raceConfig, circuit: { ...raceConfig.circuit, base_lap_time_seconds: v } })} />
            <NumberField label="Pit Loss" value={raceConfig.circuit.pit_lane_time_loss_seconds} onChange={(v) => setRaceConfig({ ...raceConfig, circuit: { ...raceConfig.circuit, pit_lane_time_loss_seconds: v } })} />
            <NumberField label="Track Temp" value={raceConfig.circuit.avg_track_temp} onChange={(v) => setRaceConfig({ ...raceConfig, circuit: { ...raceConfig.circuit, avg_track_temp: v } })} />
          </div>

          <div>
            <div className="mb-2 text-xs font-bold uppercase tracking-wide text-slate-400">Starting Tyre</div>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-5">
              {compounds.map((compound) => (
                <button
                  key={compound}
                  onClick={() => setRaceConfig({ ...raceConfig, starting_compound: compound })}
                  className={`rounded border p-3 transition ${raceConfig.starting_compound === compound ? "border-pit-red bg-pit-red/15" : "border-white/10 bg-white/[0.04] hover:bg-white/10"}`}
                >
                  <TyreBadge compound={compound} />
                </button>
              ))}
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-3">
            <label>
              <span className="text-xs font-bold uppercase tracking-wide text-slate-400">Fuel KG</span>
              <input min={0} max={110} type="number" value={raceConfig.starting_fuel_kg} onChange={(e) => setRaceConfig({ ...raceConfig, starting_fuel_kg: Number(e.target.value) })} className="mt-2 w-full rounded border border-white/10 bg-pit-panel2 px-3 py-3" />
            </label>
            <label>
              <span className="text-xs font-bold uppercase tracking-wide text-slate-400">Weather Seed</span>
              <div className="mt-2 flex gap-2">
                <input type="number" value={raceConfig.weather_seed_state} onChange={(e) => setRaceConfig({ ...raceConfig, weather_seed_state: Number(e.target.value) })} className="min-w-0 flex-1 rounded border border-white/10 bg-pit-panel2 px-3 py-3" />
                <button title="Randomize weather" onClick={() => setRaceConfig({ ...raceConfig, weather_seed_state: Math.floor(Math.random() * 100000) })} className="rounded border border-white/10 px-3 hover:bg-white/10">
                  <Dice5 className="h-5 w-5" />
                </button>
              </div>
            </label>
            <label>
              <span className="text-xs font-bold uppercase tracking-wide text-slate-400">Safety Car {Math.round(raceConfig.safety_car_base_probability * 100)}%</span>
              <input type="range" min={0} max={1} step={0.01} value={raceConfig.safety_car_base_probability} onChange={(e) => setRaceConfig({ ...raceConfig, safety_car_base_probability: Number(e.target.value) })} className="mt-5 w-full accent-pit-red" />
            </label>
          </div>

          <button disabled={loading} onClick={runSimulation} className="flex w-full items-center justify-center gap-2 rounded bg-pit-red px-5 py-4 text-sm font-black uppercase tracking-wide text-white hover:bg-red-500 disabled:cursor-not-allowed disabled:opacity-60">
            {loading ? <Loader2 className="h-5 w-5 animate-spin" /> : <Play className="h-5 w-5" />}
            Run Race Simulation
          </button>
          {message && <StatusPill tone={message.includes("failed") || message.includes("unavailable") ? "red" : "green"}>{message}</StatusPill>}
        </div>
      </Panel>

      <Panel title="Current Payload">
        <pre className="max-h-[620px] overflow-auto rounded bg-black/40 p-4 text-xs text-slate-300">{JSON.stringify(raceConfig, null, 2)}</pre>
      </Panel>
    </div>
  );
}

function NumberField({ label, value, onChange }: { label: string; value: number; onChange: (value: number) => void }) {
  return (
    <label>
      <span className="text-xs font-bold uppercase tracking-wide text-slate-400">{label}</span>
      <input type="number" value={value} onChange={(event) => onChange(Number(event.target.value))} className="mt-2 w-full rounded border border-white/10 bg-pit-panel2 px-3 py-3" />
    </label>
  );
}
