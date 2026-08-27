import { Loader2, Pause, Play, RotateCcw, StepForward } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { EmptyState } from "../components/ui/EmptyState";
import { Panel } from "../components/ui/Panel";
import { StatusPill } from "../components/ui/StatusPill";
import { TyreBadge } from "../components/ui/TyreBadge";
import { formatRaceTime, percent } from "../lib/format";
import { api, ApiError } from "../services/api";
import { useRaceStore } from "../store/raceStore";
import type { LiveActionType, TyreCompound } from "../types/api";
import type { PageId } from "../types/navigation";

const compounds: TyreCompound[] = ["SOFT", "MEDIUM", "HARD", "INTERMEDIATE", "WET"];
const speeds = [1, 2, 5, 10];

export function LiveRaceControlPage({ setPage }: { setPage: (page: PageId) => void }) {
  const { raceConfig, liveRace, setLiveRace } = useRaceStore();
  const [loading, setLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [autoPlay, setAutoPlay] = useState(false);
  const [speed, setSpeed] = useState(2);
  const [pitCompound, setPitCompound] = useState<TyreCompound>("INTERMEDIATE");

  async function startRace() {
    setLoading("start");
    setError(null);
    try {
      const response = await api.startLiveRace(raceConfig, raceConfig.weather_seed_state + 17);
      setLiveRace(response.race_state);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not start live race.");
    } finally {
      setLoading(null);
    }
  }

  async function advance() {
    if (!liveRace || liveRace.race_status === "FINISHED") return;
    setLoading("advance");
    setError(null);
    try {
      const response = await api.advanceLiveRace(liveRace.race_id);
      setLiveRace(response.race_state);
      if (response.race_status === "FINISHED") setAutoPlay(false);
    } catch (err) {
      setAutoPlay(false);
      setError(err instanceof ApiError ? err.message : "Could not advance lap.");
    } finally {
      setLoading(null);
    }
  }

  async function submitAction(action: LiveActionType, compound?: TyreCompound) {
    if (!liveRace) return;
    setLoading(action);
    setError(null);
    try {
      const response = await api.submitLiveAction(liveRace.race_id, { action, compound });
      setLiveRace(response);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Action rejected.");
    } finally {
      setLoading(null);
    }
  }

  useEffect(() => {
    if (!autoPlay || !liveRace || liveRace.race_status === "FINISHED") return;
    const timer = window.setInterval(() => {
      void advance();
    }, 1100 / speed);
    return () => window.clearInterval(timer);
  }, [autoPlay, liveRace?.race_id, liveRace?.current_lap, liveRace?.race_status, speed]);

  const chartData = useMemo(() => liveRace?.history.map((lap) => ({
    lap: lap.lap_number,
    lap_time: lap.lap_time_seconds,
    wetness: lap.track_wetness,
    fuel: lap.fuel_remaining_kg,
  })) ?? [], [liveRace]);

  if (!liveRace) {
    return (
      <EmptyState
        title="No live race session"
        message="Start a backend live race session from the current RaceConfig."
        action={<button onClick={startRace} disabled={loading === "start"} className="rounded bg-pit-red px-4 py-2 text-sm font-bold">{loading === "start" ? "Starting..." : "Start Live Race"}</button>}
      />
    );
  }

  const recommendation = liveRace.recommendation;

  return (
    <div className="space-y-5">
      <Panel title="Live Race Control" action={<StatusPill tone={liveRace.race_status === "FINISHED" ? "green" : liveRace.race_status === "SAFETY_CAR" ? "yellow" : liveRace.race_status === "VIRTUAL_SAFETY_CAR" ? "yellow" : "blue"}>{liveRace.race_status}</StatusPill>}>
        <div className="grid gap-4 xl:grid-cols-[1fr_0.9fr]">
          <div>
            <div className="text-5xl font-black text-white">LAP {liveRace.current_lap} / {liveRace.total_laps}</div>
            <div className="mt-2 text-sm text-slate-400">Race time {formatRaceTime(liveRace.current_race_time)}</div>
            <div className="mt-5 grid gap-3 sm:grid-cols-4">
              <Metric label="Current Tyre" value={<TyreBadge compound={liveRace.current_compound} />} />
              <Metric label="Tyre Age" value={`${liveRace.tyre_age} laps`} />
              <Metric label="Fuel" value={`${liveRace.fuel_remaining_kg.toFixed(1)} kg`} />
              <Metric label="Track Wetness" value={percent(liveRace.track_wetness)} />
            </div>
          </div>
          <div className="rounded-lg border border-white/10 bg-black/20 p-4">
            <div className="text-xs font-bold uppercase tracking-[0.18em] text-pit-purple">AI Race Engineer</div>
            <div className="mt-3 text-2xl font-black text-white">{recommendation?.decision ?? "Awaiting recommendation"}</div>
            <p className="mt-2 text-sm text-slate-400">{recommendation?.explanation ?? "Start advancing laps to receive live race-control advice."}</p>
            <div className="mt-4 flex flex-wrap gap-2">
              {recommendation?.recommended_compound && <StatusPill tone="green">{recommendation.recommended_compound}</StatusPill>}
              {recommendation?.recommended_pit_lap && <StatusPill tone="red">Pit lap {recommendation.recommended_pit_lap}</StatusPill>}
              {recommendation?.confidence != null && <StatusPill tone="blue">{Math.round(recommendation.confidence * 100)}%</StatusPill>}
            </div>
          </div>
        </div>

        <div className="mt-5 flex flex-wrap gap-2">
          <button onClick={advance} disabled={loading === "advance" || liveRace.race_status === "FINISHED"} className="rounded bg-pit-blue px-4 py-2 font-bold text-black disabled:opacity-50">
            {loading === "advance" ? <Loader2 className="inline h-4 w-4 animate-spin" /> : <StepForward className="inline h-4 w-4" />} Next Lap
          </button>
          <button onClick={() => setAutoPlay(true)} disabled={liveRace.race_status === "FINISHED"} className="rounded bg-pit-green px-4 py-2 font-bold text-black"><Play className="inline h-4 w-4" /> Auto Play</button>
          <button onClick={() => setAutoPlay(false)} className="rounded border border-white/10 px-4 py-2 font-bold"><Pause className="inline h-4 w-4" /> Pause</button>
          <button onClick={() => { setAutoPlay(false); void startRace(); }} className="rounded border border-white/10 px-4 py-2 font-bold"><RotateCcw className="inline h-4 w-4" /> Restart</button>
          <select value={speed} onChange={(event) => setSpeed(Number(event.target.value))} className="rounded border border-white/10 bg-pit-panel2 px-3">
            {speeds.map((item) => <option key={item} value={item}>{item}x</option>)}
          </select>
        </div>

        <div className="mt-4 flex flex-wrap gap-2">
          <button onClick={() => submitAction("STAY_OUT")} className="rounded border border-white/10 px-4 py-2 font-bold hover:bg-white/10">Stay Out</button>
          <select value={pitCompound} onChange={(event) => setPitCompound(event.target.value as TyreCompound)} className="rounded border border-white/10 bg-pit-panel2 px-3">
            {compounds.map((compound) => <option key={compound} value={compound}>{compound}</option>)}
          </select>
          <button onClick={() => submitAction("PIT", pitCompound)} className="rounded bg-pit-red px-4 py-2 font-black text-white">Pit</button>
          <button onClick={() => submitAction("FOLLOW_RECOMMENDATION")} className="rounded bg-pit-purple px-4 py-2 font-black text-white">Follow AI</button>
        </div>
        {error && <div className="mt-3"><StatusPill tone="red">{error}</StatusPill></div>}
      </Panel>

      <div className="grid gap-5 xl:grid-cols-[1.1fr_0.9fr]">
        <Panel title="Race Timeline / Weather">
          {chartData.length ? (
            <div className="h-72 min-w-[620px]">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData}>
                  <CartesianGrid stroke="#2a3140" strokeDasharray="3 3" />
                  <XAxis dataKey="lap" stroke="#94a3b8" />
                  <YAxis stroke="#94a3b8" />
                  <Tooltip contentStyle={{ background: "#10131a", border: "1px solid #2a3140" }} />
                  <Line type="monotone" dataKey="lap_time" stroke="#39a9ff" dot={false} strokeWidth={2} />
                  <Line type="monotone" dataKey="wetness" stroke="#38d996" dot={false} strokeWidth={2} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <EmptyState title="No laps completed" message="Advance the live race to populate telemetry." />
          )}
        </Panel>

        <Panel title="Events and Decisions">
          <div className="max-h-80 space-y-2 overflow-auto">
            {liveRace.events.slice(-8).map((event, index) => (
              <div key={`${event.lap}-${event.event_type}-${index}`} className="rounded border border-pit-yellow/30 bg-pit-yellow/10 p-3 text-sm">
                <strong>L{event.lap} {event.event_type}</strong>
                <div className="text-slate-300">{event.reason}</div>
              </div>
            ))}
            {liveRace.actions.slice(-8).map((action) => (
              <div key={`${action.lap}-${action.user_action}-${action.time_impact}`} className="rounded border border-white/10 bg-white/[0.035] p-3 text-sm">
                <strong>L{action.lap} user {action.user_action}</strong>
                <div className="text-slate-300">AI: {action.recommended_action}</div>
                <div className="text-slate-400">Impact {action.time_impact.toFixed(3)}s · Followed {action.followed_recommendation ? "yes" : "no"}</div>
              </div>
            ))}
            {!liveRace.events.length && !liveRace.actions.length && <EmptyState title="No decisions yet" message="Events and user actions will appear here." />}
          </div>
        </Panel>
      </div>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="rounded border border-white/10 bg-white/[0.035] p-3">
      <div className="text-xs font-bold uppercase tracking-wide text-slate-500">{label}</div>
      <div className="mt-2 text-lg font-black text-white">{value}</div>
    </div>
  );
}
