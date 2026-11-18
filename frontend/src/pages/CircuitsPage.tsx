import { useEffect, useState } from "react";
import { Loader2, MapPin, Search } from "lucide-react";
import { EmptyState } from "../components/ui/EmptyState";
import { Panel } from "../components/ui/Panel";
import { StatusPill } from "../components/ui/StatusPill";
import { api, ApiError } from "../services/api";
import { useRaceStore } from "../store/raceStore";
import type { CircuitRead, F1CircuitEventRead, F1CircuitRead } from "../types/api";
import type { PageId } from "../types/navigation";

export function CircuitsPage({ setPage }: { setPage: (page: PageId) => void }) {
  const { circuits, setCircuits, raceConfig, setRaceConfig } = useRaceStore();
  const [error, setError] = useState<string | null>(null);
  const [realCircuits, setRealCircuits] = useState<F1CircuitRead[]>([]);
  const [realError, setRealError] = useState<string | null>(null);
  const [realLoading, setRealLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [country, setCountry] = useState("");
  const [events, setEvents] = useState<Record<number, F1CircuitEventRead[]>>({});

  useEffect(() => {
    api.listCircuits().then(setCircuits).catch((err) => setError(err instanceof ApiError ? err.message : "Could not load circuits."));
  }, [setCircuits]);

  useEffect(() => {
    setRealLoading(true);
    api.listImportedCircuits({ search, country }).then(setRealCircuits).catch((err) => setRealError(err instanceof ApiError ? err.message : "Could not load imported circuit data.")).finally(() => setRealLoading(false));
  }, [search, country]);

  async function loadEvents(circuit: F1CircuitRead) {
    if (events[circuit.id]) return;
    try {
      const circuitEvents = await api.getImportedCircuitEvents(circuit.id);
      setEvents((current) => ({ ...current, [circuit.id]: circuitEvents }));
    }
    catch (err) { setRealError(err instanceof ApiError ? err.message : "Could not load circuit events."); }
  }

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
      <Panel title="Imported F1 Circuit Reference">
        <div className="mb-4 grid gap-3 md:grid-cols-2">
          <label className="relative"><Search className="absolute left-3 top-3 h-4 w-4 text-slate-500" /><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search real circuits" className="w-full rounded border border-white/10 bg-black/20 py-2 pl-9 pr-3 text-sm text-white" /></label>
          <input value={country} onChange={(event) => setCountry(event.target.value)} placeholder="Filter by country" className="rounded border border-white/10 bg-black/20 px-3 py-2 text-sm text-white" />
        </div>
        {realError && <StatusPill tone="red">{realError}</StatusPill>}
        {realLoading ? <div className="flex min-h-40 items-center justify-center"><Loader2 className="h-6 w-6 animate-spin text-pit-red" /></div> : realCircuits.length === 0 ? <EmptyState title="No Imported Circuits" message="No real circuit reference records match these filters. Import data through the backend ingestion service." /> : <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {realCircuits.map((circuit) => <div key={circuit.id} className="rounded-lg border border-white/10 bg-white/[0.035] p-4">
            <div className="text-lg font-black text-white">{circuit.name}</div>
            <div className="mt-1 flex items-center gap-2 text-sm text-slate-400"><MapPin className="h-4 w-4 text-pit-red" />{[circuit.city, circuit.country].filter(Boolean).join(", ")}</div>
            <div className="mt-3 grid grid-cols-2 gap-2 text-sm"><CircuitField label="Provider ID" value={circuit.provider_circuit_id} /><CircuitField label="Coordinates" value={circuit.latitude !== null && circuit.longitude !== null ? `${circuit.latitude}, ${circuit.longitude}` : "Unavailable"} /></div>
            <button onClick={() => loadEvents(circuit)} className="mt-4 w-full rounded border border-white/10 px-3 py-2 text-xs font-bold uppercase text-slate-200 hover:bg-white/10">Historical Events</button>
            {events[circuit.id] && <div className="mt-3 space-y-1 text-xs text-slate-400">{events[circuit.id].length ? events[circuit.id].map((event) => <div key={event.id}>{event.season} R{event.round_number}: {event.race_name}</div>) : "No imported event history."}</div>}
          </div>)}
        </div>}
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
