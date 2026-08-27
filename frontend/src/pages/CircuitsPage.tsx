import { useEffect, useState } from "react";
import { MapPin } from "lucide-react";
import { Panel } from "../components/ui/Panel";
import { StatusPill } from "../components/ui/StatusPill";
import { api, ApiError } from "../services/api";
import { useRaceStore } from "../store/raceStore";
import type { CircuitRead } from "../types/api";
import type { PageId } from "../types/navigation";

export function CircuitsPage({ setPage }: { setPage: (page: PageId) => void }) {
  const { circuits, setCircuits, raceConfig, setRaceConfig } = useRaceStore();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.listCircuits().then(setCircuits).catch((err) => setError(err instanceof ApiError ? err.message : "Could not load circuits."));
  }, [setCircuits]);

  async function useCircuit(circuit: CircuitRead) {
    const config = await api.getCircuitConfig(circuit.id);
    setRaceConfig({ ...raceConfig, circuit: config });
    setPage("setup");
  }

  return (
    <div className="space-y-5">
      <Panel title="Circuits">
        {error && <StatusPill tone="red">{error}</StatusPill>}
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {circuits.map((circuit) => (
            <div key={circuit.id} className="rounded-lg border border-white/10 bg-white/[0.035] p-4">
              <div className="mb-4 flex items-start justify-between gap-3">
                <div>
                  <div className="text-2xl font-black text-white">{circuit.name}</div>
                  <div className="mt-1 flex items-center gap-2 text-sm text-slate-400"><MapPin className="h-4 w-4 text-pit-red" /> {circuit.city}, {circuit.country}</div>
                </div>
                <StatusPill tone={circuit.safety_car_factor > 1.1 ? "yellow" : "green"}>SC {circuit.safety_car_factor.toFixed(2)}x</StatusPill>
              </div>
              <div className="grid grid-cols-2 gap-2 text-sm">
                <CircuitField label="Laps" value={`${circuit.total_laps}`} />
                <CircuitField label="Length" value={`${circuit.track_length_km} km`} />
                <CircuitField label="Tyre Wear" value={`${circuit.tyre_wear_factor.toFixed(2)}x`} />
                <CircuitField label="Pit Loss" value={`${circuit.pit_lane_time_loss_seconds}s`} />
              </div>
              <button onClick={() => useCircuit(circuit)} className="mt-4 w-full rounded bg-pit-red px-4 py-2 text-sm font-black uppercase text-white hover:bg-red-500">
                Use For Race
              </button>
            </div>
          ))}
        </div>
      </Panel>
    </div>
  );
}

function CircuitField({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded border border-white/10 bg-black/20 p-2">
      <div className="text-xs uppercase text-slate-500">{label}</div>
      <div className="font-bold text-white">{value}</div>
    </div>
  );
}
