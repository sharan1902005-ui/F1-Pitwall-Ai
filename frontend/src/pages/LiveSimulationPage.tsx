import { Pause, Play, RotateCcw } from "lucide-react";
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
import { TyreBadge } from "../components/ui/TyreBadge";
import { formatRaceTime, percent } from "../lib/format";
import { useRaceStore } from "../store/raceStore";
import type { PageId } from "../types/navigation";

const speeds = [1, 2, 5, 10];

export function LiveSimulationPage({ setPage }: { setPage: (page: PageId) => void }) {
  const { simulation } = useRaceStore();
  const [lapIndex, setLapIndex] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(2);

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
    return <EmptyState title="No race data available" message="Configure a race and run the complete backend simulation first." action={<button onClick={() => setPage("setup")} className="rounded bg-pit-red px-4 py-2 text-sm font-bold">Configure Race</button>} />;
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
            <button onClick={() => setPlaying(true)} className="rounded bg-pit-green px-4 py-2 font-bold text-black"><Play className="inline h-4 w-4" /> Play</button>
            <button onClick={() => setPlaying(false)} className="rounded border border-white/10 px-4 py-2 font-bold"><Pause className="inline h-4 w-4" /> Pause</button>
            <button onClick={() => { setPlaying(false); setLapIndex(0); }} className="rounded border border-white/10 px-4 py-2 font-bold"><RotateCcw className="inline h-4 w-4" /> Restart</button>
            <select value={speed} onChange={(e) => setSpeed(Number(e.target.value))} className="rounded border border-white/10 bg-pit-panel2 px-3">
              {speeds.map((item) => <option key={item} value={item}>{item}x</option>)}
            </select>
          </div>
        </div>
        <input className="mt-5 w-full accent-pit-red" type="range" min={0} max={simulation.lap_results.length - 1} value={lapIndex} onChange={(e) => setLapIndex(Number(e.target.value))} />
      </Panel>

      <div className="grid gap-4 md:grid-cols-5">
        <Telemetry label="Current Tyre" value={<TyreBadge compound={lap.compound} />} />
        <Telemetry label="Tyre Age" value={`${lap.tyre_age} laps`} />
        <Telemetry label="Fuel" value={`${lap.fuel_remaining_kg.toFixed(1)} kg`} />
        <Telemetry label="Track Wetness" value={percent(lap.track_wetness)} />
        <Telemetry label="Rain Probability" value={percent(lap.rain_probability)} />
      </div>

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

function Telemetry({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-white/10 bg-pit-panel p-4">
      <div className="text-xs font-bold uppercase tracking-wide text-slate-500">{label}</div>
      <div className="mt-2 text-xl font-black text-white">{value}</div>
    </div>
  );
}
