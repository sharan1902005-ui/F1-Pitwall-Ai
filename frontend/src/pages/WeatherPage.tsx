import { Loader2 } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { EmptyState } from "../components/ui/EmptyState";
import { Panel } from "../components/ui/Panel";
import { StatusPill } from "../components/ui/StatusPill";
import { percent } from "../lib/format";
import { ApiError, api } from "../services/api";
import { useRaceStore } from "../store/raceStore";
import type { F1CircuitEventRead, F1HistoricalSeasonSummary, F1HistoricalWeatherObservationRead, F1HistoricalWeatherSummaryRead } from "../types/api";
import type { PageId } from "../types/navigation";

export function WeatherPage({ setPage }: { setPage: (page: PageId) => void }) {
  const { simulation, strategy } = useRaceStore();
  const [seasons, setSeasons] = useState<F1HistoricalSeasonSummary[]>([]);
  const [season, setSeason] = useState<number | "">("");
  const [events, setEvents] = useState<F1CircuitEventRead[]>([]);
  const [eventId, setEventId] = useState<number | "">("");
  const [observations, setObservations] = useState<F1HistoricalWeatherObservationRead[]>([]);
  const [sessionKey, setSessionKey] = useState<number | "">("");
  const [summary, setSummary] = useState<F1HistoricalWeatherSummaryRead | null>(null);
  const [loading, setLoading] = useState(true);
  const [weatherLoading, setWeatherLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.listHistoricalResultSeasons().then((data) => { setSeasons(data); setSeason(data[0]?.season ?? ""); })
      .catch((err) => setError(err instanceof ApiError ? err.message : "Could not load imported historical event coverage."))
      .finally(() => setLoading(false));
  }, []);
  useEffect(() => {
    if (season === "") { setEvents([]); return; }
    api.listHistoricalResultEvents(season).then((data) => { setEvents(data); setEventId(data[0]?.id ?? ""); }).catch(() => setEvents([]));
  }, [season]);
  useEffect(() => {
    if (eventId === "") { setObservations([]); setSummary(null); return; }
    setWeatherLoading(true); setError(null);
    Promise.all([api.listHistoricalWeather(eventId, sessionKey || undefined), api.historicalWeatherSummary(eventId, sessionKey || undefined)])
      .then(([weather, weatherSummary]) => { setObservations(weather); setSummary(weatherSummary); })
      .catch((err) => { setObservations([]); setSummary(null); setError(err instanceof ApiError ? err.message : "Could not load historical weather observations."); })
      .finally(() => setWeatherLoading(false));
  }, [eventId, sessionKey]);

  const sessions = useMemo(() => [...new Set(observations.map((item) => item.provider_session_key))], [observations]);
  const historicalChart = observations.map((item) => ({ timestamp: new Date(item.observed_at).toLocaleString(), air: item.air_temperature_celsius, track: item.track_temperature_celsius, humidity: item.humidity_percent }));
  const simulated = simulation?.weather_history.map((weather) => ({ lap: weather.lap_number, rain_probability: weather.rain_probability, rain_intensity: weather.rain_intensity, track_wetness: weather.track_wetness, track_temperature: weather.track_temperature, air_temperature: weather.air_temperature })) ?? [];
  const latestSimulated = simulated[simulated.length - 1];
  const wetSwitch = strategy?.recommended_strategy?.stints.find((stint) => stint.compound === "INTERMEDIATE" || stint.compound === "WET");

  return <div className="space-y-5">
    <Panel title="Historical Weather Explorer" action={<StatusPill tone="blue">OpenF1 historical data · 2023+</StatusPill>}>
      <div className="mb-4 grid gap-3 md:grid-cols-3">
        <select value={season} onChange={(e) => { setSeason(e.target.value ? Number(e.target.value) : ""); setSessionKey(""); }} className="rounded border border-white/10 bg-black/20 p-2 text-sm text-white"><option value="">Select imported season</option>{seasons.map((item) => <option key={item.season} value={item.season}>{item.season}</option>)}</select>
        <select value={eventId} onChange={(e) => { setEventId(e.target.value ? Number(e.target.value) : ""); setSessionKey(""); }} className="rounded border border-white/10 bg-black/20 p-2 text-sm text-white" disabled={!events.length}><option value="">Select event</option>{events.map((item) => <option key={item.id} value={item.id}>{item.race_name}</option>)}</select>
        <select value={sessionKey} onChange={(e) => setSessionKey(e.target.value ? Number(e.target.value) : "")} className="rounded border border-white/10 bg-black/20 p-2 text-sm text-white" disabled={!sessions.length}><option value="">All imported sessions</option>{sessions.map((key) => <option key={key} value={key}>Session {key}</option>)}</select>
      </div>
      {error && <div className="mb-3"><StatusPill tone="red">{error}</StatusPill></div>}
      {loading || weatherLoading ? <div className="flex min-h-40 items-center justify-center"><Loader2 className="h-6 w-6 animate-spin text-pit-red" /></div> : !eventId ? <EmptyState title="Select an imported event" message="Historical weather becomes available only after OpenF1 observations have been imported for an event." /> : !observations.length ? <EmptyState title="No historical weather observations" message="No OpenF1 observations are stored for this event or session. This does not represent simulated weather." /> : <>
        <div className="mb-4 grid gap-3 md:grid-cols-4"><WeatherMetric label="Observations" value={String(summary?.observations ?? observations.length)} /><WeatherMetric label="Avg Track Temp" value={degrees(summary?.average_track_temperature_celsius)} /><WeatherMetric label="Avg Air Temp" value={degrees(summary?.average_air_temperature_celsius)} /><WeatherMetric label="Rain Samples" value={String(summary?.rainfall_observations ?? 0)} /></div>
        <div className="h-80 min-w-[680px]"><ResponsiveContainer width="100%" height="100%"><LineChart data={historicalChart}><CartesianGrid stroke="#2a3140" strokeDasharray="3 3" /><XAxis dataKey="timestamp" hide /><YAxis stroke="#94a3b8" /><Tooltip contentStyle={{ background: "#10131a", border: "1px solid #2a3140" }} /><Line type="monotone" dataKey="air" name="Air °C" stroke="#39a9ff" dot={false} /><Line type="monotone" dataKey="track" name="Track °C" stroke="#ef4444" dot={false} /><Line type="monotone" dataKey="humidity" name="Humidity %" stroke="#38d996" dot={false} /></LineChart></ResponsiveContainer></div>
        <div className="mt-3 text-xs text-slate-400">Temperatures: °C · humidity: % · pressure: mbar · wind: m/s. Observation timestamps are provider UTC timestamps.</div>
      </>}
    </Panel>
    {!simulation ? <EmptyState title="Simulation weather unavailable" message="Historical observations and generated simulation weather remain separate. Run a simulation to view the deterministic weather evolution." action={<button onClick={() => setPage("setup")} className="rounded bg-pit-red px-4 py-2 text-sm font-bold">Run Simulation</button>} /> : <>
      <Panel title="Weather Command Center" action={<StatusPill tone="neutral">Generated simulation weather</StatusPill>}><div className="grid gap-4 md:grid-cols-5"><WeatherMetric label="Rain Probability" value={percent(latestSimulated?.rain_probability)} /><WeatherMetric label="Rain Intensity" value={percent(latestSimulated?.rain_intensity)} /><WeatherMetric label="Track Wetness" value={percent(latestSimulated?.track_wetness)} /><WeatherMetric label="Track Temp" value={degrees(latestSimulated?.track_temperature)} /><WeatherMetric label="Air Temp" value={degrees(latestSimulated?.air_temperature)} /></div></Panel>
      <Panel title="Race Weather Evolution" action={wetSwitch ? <StatusPill tone="green">Crossover zone from lap {wetSwitch.start_lap}</StatusPill> : <StatusPill tone="neutral">No wet crossover in top strategy</StatusPill>}><div className="h-96 min-w-[680px]"><ResponsiveContainer width="100%" height="100%"><LineChart data={simulated}><CartesianGrid stroke="#2a3140" strokeDasharray="3 3" /><XAxis dataKey="lap" stroke="#94a3b8" /><YAxis stroke="#94a3b8" /><Tooltip contentStyle={{ background: "#10131a", border: "1px solid #2a3140" }} /><Line type="monotone" dataKey="rain_probability" name="Rain Probability" stroke="#39a9ff" dot={false} strokeWidth={2} /><Line type="monotone" dataKey="rain_intensity" name="Rain Intensity" stroke="#b66cff" dot={false} strokeWidth={2} /><Line type="monotone" dataKey="track_wetness" name="Track Wetness" stroke="#38d996" dot={false} strokeWidth={2} /></LineChart></ResponsiveContainer></div></Panel>
    </>}
  </div>;
}

function degrees(value: number | null | undefined) { return value == null ? "Unavailable" : `${value.toFixed(1)} °C`; }
function WeatherMetric({ label, value }: { label: string; value: string }) { return <div className="rounded border border-white/10 bg-white/[0.035] p-3"><div className="text-xs font-bold uppercase tracking-wide text-slate-500">{label}</div><div className="mt-2 text-2xl font-black text-white">{value}</div></div>; }
