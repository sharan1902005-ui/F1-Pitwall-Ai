import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { EmptyState } from "../components/ui/EmptyState";
import { Panel } from "../components/ui/Panel";
import { StatusPill } from "../components/ui/StatusPill";
import { percent } from "../lib/format";
import { useRaceStore } from "../store/raceStore";
import type { PageId } from "../types/navigation";

export function WeatherPage({ setPage }: { setPage: (page: PageId) => void }) {
  const { simulation, strategy } = useRaceStore();
  if (!simulation) {
    return <EmptyState title="Weather history unavailable" message="Run a simulation to view backend-generated weather evolution." action={<button onClick={() => setPage("setup")} className="rounded bg-pit-red px-4 py-2 text-sm font-bold">Run Simulation</button>} />;
  }
  const data = simulation.weather_history.map((weather) => ({
    lap: weather.lap_number,
    rain_probability: weather.rain_probability,
    rain_intensity: weather.rain_intensity,
    track_wetness: weather.track_wetness,
    track_temperature: weather.track_temperature,
    air_temperature: weather.air_temperature,
  }));
  const wetSwitch = strategy?.recommended_strategy?.stints.find((stint) => stint.compound === "INTERMEDIATE" || stint.compound === "WET");

  return (
    <div className="space-y-5">
      <Panel title="Weather Command Center">
        <div className="grid gap-4 md:grid-cols-5">
          <WeatherMetric label="Rain Probability" value={percent(data[data.length - 1]?.rain_probability)} />
          <WeatherMetric label="Rain Intensity" value={percent(data[data.length - 1]?.rain_intensity)} />
          <WeatherMetric label="Track Wetness" value={percent(data[data.length - 1]?.track_wetness)} />
          <WeatherMetric label="Track Temp" value={`${data[data.length - 1]?.track_temperature.toFixed(1)} C`} />
          <WeatherMetric label="Air Temp" value={`${data[data.length - 1]?.air_temperature.toFixed(1)} C`} />
        </div>
      </Panel>
      <Panel title="Race Weather Evolution" action={wetSwitch ? <StatusPill tone="green">Crossover zone from lap {wetSwitch.start_lap}</StatusPill> : <StatusPill tone="neutral">No wet crossover in top strategy</StatusPill>}>
        <div className="h-96 min-w-[680px]">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data}>
              <CartesianGrid stroke="#2a3140" strokeDasharray="3 3" />
              <XAxis dataKey="lap" stroke="#94a3b8" />
              <YAxis stroke="#94a3b8" />
              <Tooltip contentStyle={{ background: "#10131a", border: "1px solid #2a3140" }} />
              <Line type="monotone" dataKey="rain_probability" name="Rain Probability" stroke="#39a9ff" dot={false} strokeWidth={2} />
              <Line type="monotone" dataKey="rain_intensity" name="Rain Intensity" stroke="#b66cff" dot={false} strokeWidth={2} />
              <Line type="monotone" dataKey="track_wetness" name="Track Wetness" stroke="#38d996" dot={false} strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </Panel>
    </div>
  );
}

function WeatherMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded border border-white/10 bg-white/[0.035] p-3">
      <div className="text-xs font-bold uppercase tracking-wide text-slate-500">{label}</div>
      <div className="mt-2 text-2xl font-black text-white">{value}</div>
    </div>
  );
}
