import {
  AlertTriangle,
  CloudRain,
  Flame,
  Flag,
  Loader2,
  Pause,
  Play,
  RotateCcw,
  StepForward,
  Thermometer,
  TrendingDown,
  TrendingUp,
  Wind,
  Zap,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
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
import type { LiveActionType, RaceControlEvent, RaceEventType, TyreCompound } from "../types/api";
import type { PageId } from "../types/navigation";

const compounds: TyreCompound[] = ["SOFT", "MEDIUM", "HARD", "INTERMEDIATE", "WET"];
const speeds = [1, 2, 5, 10];

// ── Event metadata ────────────────────────────────────────────────────────────

type EventCategory = "WEATHER" | "TYRE_STRATEGY" | "PIT_STRATEGY" | "RACE_CONDITIONS";

interface EventMeta {
  category: EventCategory;
  label: string;
  icon: React.ReactNode;
  tone: "blue" | "yellow" | "red" | "green" | "purple";
}

function eventMeta(type: RaceEventType): EventMeta {
  switch (type) {
    case "RAIN_INCREASE":
      return { category: "WEATHER", label: "Rain Increasing", icon: <CloudRain className="h-4 w-4" />, tone: "blue" };
    case "RAIN_DECREASE":
    case "DRYING_TRACK":
      return { category: "WEATHER", label: "Track Drying", icon: <TrendingDown className="h-4 w-4" />, tone: "green" };
    case "HOT_TRACK":
      return { category: "WEATHER", label: "Hot Track", icon: <Flame className="h-4 w-4" />, tone: "red" };
    case "TRACK_TEMP_RISING":
      return { category: "WEATHER", label: "Temp Rising", icon: <TrendingUp className="h-4 w-4" />, tone: "yellow" };
    case "TRACK_TEMP_FALLING":
      return { category: "WEATHER", label: "Temp Falling", icon: <TrendingDown className="h-4 w-4" />, tone: "blue" };
    case "TRACK_TEMPERATURE_CHANGE":
      return { category: "WEATHER", label: "Temp Change", icon: <Thermometer className="h-4 w-4" />, tone: "yellow" };
    case "TYRE_CROSSOVER_APPROACHING":
      return { category: "TYRE_STRATEGY", label: "Crossover Approaching", icon: <Wind className="h-4 w-4" />, tone: "yellow" };
    case "TYRE_CROSSOVER":
    case "TYRE_CROSSOVER_REACHED":
      return { category: "TYRE_STRATEGY", label: "Crossover Reached", icon: <Wind className="h-4 w-4" />, tone: "purple" };
    case "TYRE_CROSSOVER_CLEARED":
      return { category: "TYRE_STRATEGY", label: "Crossover Cleared", icon: <TrendingDown className="h-4 w-4" />, tone: "green" };
    case "DEGRADATION_WARNING":
    case "HIGH_TYRE_DEGRADATION_RISK":
      return { category: "TYRE_STRATEGY", label: "Degradation Warning", icon: <AlertTriangle className="h-4 w-4" />, tone: "yellow" };
    case "CRITICAL_TYRE_WEAR":
      return { category: "TYRE_STRATEGY", label: "Critical Tyre Wear", icon: <AlertTriangle className="h-4 w-4" />, tone: "red" };
    case "TYRE_STATE_RECOVERED":
      return { category: "TYRE_STRATEGY", label: "Tyre Recovered", icon: <TrendingUp className="h-4 w-4" />, tone: "green" };
    case "PIT_WINDOW_OPEN":
      return { category: "PIT_STRATEGY", label: "Pit Window Open", icon: <Zap className="h-4 w-4" />, tone: "green" };
    case "PIT_WINDOW_CLOSING":
      return { category: "PIT_STRATEGY", label: "Pit Window Closing", icon: <AlertTriangle className="h-4 w-4" />, tone: "yellow" };
    case "SAFETY_CAR":
      return { category: "RACE_CONDITIONS", label: "Safety Car", icon: <Flag className="h-4 w-4" />, tone: "yellow" };
    case "VIRTUAL_SAFETY_CAR":
      return { category: "RACE_CONDITIONS", label: "Virtual SC", icon: <Flag className="h-4 w-4" />, tone: "yellow" };
    default:
      return { category: "RACE_CONDITIONS", label: type, icon: <Flag className="h-4 w-4" />, tone: "blue" };
  }
}

function strategicConsequence(type: RaceEventType): string {
  switch (type) {
    case "RAIN_INCREASE":
      return "Track wetness rising — evaluate Intermediate/Wet crossover.";
    case "RAIN_DECREASE":
    case "DRYING_TRACK":
      return "Track drying — slick tyres recovering performance advantage.";
    case "HOT_TRACK":
      return "Elevated temperature increases tyre degradation rate. Consider earlier pit.";
    case "TRACK_TEMP_RISING":
      return "Rising track temperature will increase tyre wear. Monitor stint length.";
    case "TRACK_TEMP_FALLING":
      return "Falling temperature reduces degradation. Stint extension may be viable.";
    case "TRACK_TEMPERATURE_CHANGE":
      return "Temperature shift affects tyre performance. Review strategy.";
    case "TYRE_CROSSOVER":
    case "TYRE_CROSSOVER_REACHED":
      return "Wet-tyre crossover reached. Pit for Intermediate or Wet now.";
    case "TYRE_CROSSOVER_APPROACHING":
      return "Crossover threshold approaching. Prepare for potential compound change.";
    case "TYRE_CROSSOVER_CLEARED":
      return "Track drying — slick tyres viable again.";
    case "DEGRADATION_WARNING":
    case "HIGH_TYRE_DEGRADATION_RISK":
      return "Tyre wear entering warning zone. Plan pit stop.";
    case "CRITICAL_TYRE_WEAR":
      return "Tyre critically worn. Pit stop required.";
    case "TYRE_STATE_RECOVERED":
      return "Fresh tyres fitted — degradation state reset.";
    case "PIT_WINDOW_OPEN":
      return "Primary pit window is open. Optimal pit lap range now active.";
    case "PIT_WINDOW_CLOSING":
      return "Pit window closing. Late pit will compromise race time.";
    case "SAFETY_CAR":
      return "Safety car reduces pit loss. Opportunistic pit stop recommended.";
    case "VIRTUAL_SAFETY_CAR":
      return "VSC reduces pit loss. Evaluate pit stop opportunity.";
    default:
      return "";
  }
}

const toneBorder: Record<string, string> = {
  blue: "border-pit-blue/40 bg-pit-blue/10",
  yellow: "border-pit-yellow/40 bg-pit-yellow/10",
  red: "border-red-500/40 bg-red-500/10",
  green: "border-pit-green/40 bg-pit-green/10",
  purple: "border-pit-purple/40 bg-pit-purple/10",
};

const toneText: Record<string, string> = {
  blue: "text-pit-blue",
  yellow: "text-pit-yellow",
  red: "text-red-400",
  green: "text-pit-green",
  purple: "text-pit-purple",
};

const categoryLabel: Record<EventCategory, string> = {
  WEATHER: "WEATHER",
  TYRE_STRATEGY: "TYRE STRATEGY",
  PIT_STRATEGY: "PIT STRATEGY",
  RACE_CONDITIONS: "RACE CONDITIONS",
};

// ── Component ─────────────────────────────────────────────────────────────────

export function LiveRaceControlPage({ setPage: _setPage }: { setPage: (page: PageId) => void }) {
  const { raceConfig, liveRace, setLiveRace } = useRaceStore();
  const [loading, setLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [autoPlay, setAutoPlay] = useState(false);
  const [speed, setSpeed] = useState(2);
  const [pitCompound, setPitCompound] = useState<TyreCompound>("INTERMEDIATE");
  const [activeCategory, setActiveCategory] = useState<EventCategory | "ALL">("ALL");

  const liveRaceRef = useRef(liveRace);
  useEffect(() => { liveRaceRef.current = liveRace; }, [liveRace]);
  const loadingRef = useRef(loading);
  useEffect(() => { loadingRef.current = loading; }, [loading]);

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

  const advance = useCallback(async () => {
    const current = liveRaceRef.current;
    if (!current || current.race_status === "FINISHED") return;
    if (loadingRef.current === "advance") return;
    setLoading("advance");
    setError(null);
    try {
      const response = await api.advanceLiveRace(current.race_id);
      setLiveRace(response.race_state);
      if (response.race_status === "FINISHED") setAutoPlay(false);
    } catch (err) {
      setAutoPlay(false);
      setError(err instanceof ApiError ? err.message : "Could not advance lap.");
    } finally {
      setLoading(null);
    }
  }, [setLiveRace]);

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
    if (!autoPlay) return;
    const timer = window.setInterval(() => { void advance(); }, 1100 / speed);
    return () => window.clearInterval(timer);
  }, [autoPlay, speed, advance]);

  // Weather chart: track temp, air temp, wetness (all real simulated variables)
  const chartData = useMemo(() =>
    liveRace?.history.map((lap) => ({
      lap: lap.lap_number,
      "Track Temp (°C)": lap.track_temperature,
      "Air Temp (°C)": lap.air_temperature,
      "Wetness": lap.track_wetness,
      "Rain Prob": lap.rain_probability,
    })) ?? [],
    [liveRace],
  );

  // Merged and sorted events+actions for the panel
  const allEvents = useMemo(() => {
    if (!liveRace) return [];
    return [...liveRace.events].sort((a, b) => b.lap - a.lap);
  }, [liveRace]);

  const filteredEvents = useMemo(() =>
    activeCategory === "ALL"
      ? allEvents
      : allEvents.filter((e) => eventMeta(e.event_type).category === activeCategory),
    [allEvents, activeCategory],
  );

  const categories: Array<EventCategory | "ALL"> = ["ALL", "WEATHER", "TYRE_STRATEGY", "PIT_STRATEGY", "RACE_CONDITIONS"];

  if (!liveRace) {
    return (
      <EmptyState
        title="No live race session"
        message="Start a backend live race session from the current RaceConfig."
        action={
          <button
            onClick={startRace}
            disabled={loading === "start"}
            className="rounded bg-pit-red px-4 py-2 text-sm font-bold"
          >
            {loading === "start" ? "Starting..." : "Start Live Race"}
          </button>
        }
      />
    );
  }

  const recommendation = liveRace.recommendation;

  return (
    <div className="space-y-5">
      {/* ── Race Control ── */}
      <Panel
        title="Live Race Control"
        action={
          <StatusPill
            tone={
              liveRace.race_status === "FINISHED" ? "green"
              : liveRace.race_status === "SAFETY_CAR" ? "yellow"
              : liveRace.race_status === "VIRTUAL_SAFETY_CAR" ? "yellow"
              : "blue"
            }
          >
            {liveRace.race_status}
          </StatusPill>
        }
      >
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
            <div className="mt-3 grid gap-3 sm:grid-cols-2">
              <Metric label="Track Temp" value={`${liveRace.track_temperature.toFixed(1)}°C`} />
              <Metric label="Air Temp" value={`${liveRace.air_temperature.toFixed(1)}°C`} />
            </div>
          </div>
          <div className="rounded-lg border border-white/10 bg-black/20 p-4">
            <div className="text-xs font-bold uppercase tracking-[0.18em] text-pit-purple">AI Race Engineer</div>
            <div className="mt-3 text-2xl font-black text-white">{recommendation?.decision ?? "Awaiting recommendation"}</div>
            <p className="mt-2 text-sm text-slate-400">{recommendation?.explanation ?? "Start advancing laps to receive live race-control advice."}</p>
            {recommendation?.key_factors && recommendation.key_factors.length > 0 && (
              <ul className="mt-3 space-y-1">
                {recommendation.key_factors.slice(0, 4).map((f, i) => (
                  <li key={i} className="text-xs text-slate-400">· {f}</li>
                ))}
              </ul>
            )}
            <div className="mt-4 flex flex-wrap gap-2">
              {recommendation?.recommended_compound && <StatusPill tone="green">{recommendation.recommended_compound}</StatusPill>}
              {recommendation?.recommended_pit_lap && <StatusPill tone="red">Pit lap {recommendation.recommended_pit_lap}</StatusPill>}
              {recommendation?.confidence != null && <StatusPill tone="blue">{Math.round(recommendation.confidence * 100)}%</StatusPill>}
              {recommendation?.urgency && recommendation.urgency !== "LOW" && (
                <StatusPill tone={recommendation.urgency === "CRITICAL" ? "red" : recommendation.urgency === "HIGH" ? "yellow" : "blue"}>
                  {recommendation.urgency}
                </StatusPill>
              )}
            </div>
          </div>
        </div>

        <div className="mt-5 flex flex-wrap gap-2">
          <button onClick={advance} disabled={loading === "advance" || liveRace.race_status === "FINISHED"} className="rounded bg-pit-blue px-4 py-2 font-bold text-black disabled:opacity-50">
            {loading === "advance" ? <Loader2 className="inline h-4 w-4 animate-spin" /> : <StepForward className="inline h-4 w-4" />} Next Lap
          </button>
          <button onClick={() => setAutoPlay(true)} disabled={liveRace.race_status === "FINISHED"} className="rounded bg-pit-green px-4 py-2 font-bold text-black">
            <Play className="inline h-4 w-4" /> Auto Play
          </button>
          <button onClick={() => setAutoPlay(false)} className="rounded border border-white/10 px-4 py-2 font-bold">
            <Pause className="inline h-4 w-4" /> Pause
          </button>
          <button onClick={() => { setAutoPlay(false); void startRace(); }} className="rounded border border-white/10 px-4 py-2 font-bold">
            <RotateCcw className="inline h-4 w-4" /> Restart
          </button>
          <select value={speed} onChange={(e) => setSpeed(Number(e.target.value))} className="rounded border border-white/10 bg-pit-panel2 px-3">
            {speeds.map((s) => <option key={s} value={s}>{s}x</option>)}
          </select>
        </div>

        <div className="mt-4 flex flex-wrap gap-2">
          <button onClick={() => submitAction("STAY_OUT")} className="rounded border border-white/10 px-4 py-2 font-bold hover:bg-white/10">Stay Out</button>
          <select value={pitCompound} onChange={(e) => setPitCompound(e.target.value as TyreCompound)} className="rounded border border-white/10 bg-pit-panel2 px-3">
            {compounds.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
          <button onClick={() => submitAction("PIT", pitCompound)} className="rounded bg-pit-red px-4 py-2 font-black text-white">Pit</button>
          <button onClick={() => submitAction("FOLLOW_RECOMMENDATION")} className="rounded bg-pit-purple px-4 py-2 font-black text-white">Follow AI</button>
        </div>
        {error && <div className="mt-3"><StatusPill tone="red">{error}</StatusPill></div>}
      </Panel>

      {/* ── Weather Timeline + Events ── */}
      <div className="grid gap-5 xl:grid-cols-[1.1fr_0.9fr]">
        <Panel title="Weather Timeline">
          {chartData.length ? (
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData}>
                  <CartesianGrid stroke="#2a3140" strokeDasharray="3 3" />
                  <XAxis dataKey="lap" stroke="#94a3b8" label={{ value: "Lap", position: "insideBottomRight", offset: -4, fill: "#94a3b8", fontSize: 11 }} />
                  <YAxis yAxisId="temp" stroke="#94a3b8" label={{ value: "°C", angle: -90, position: "insideLeft", fill: "#94a3b8", fontSize: 11 }} />
                  <YAxis yAxisId="frac" orientation="right" stroke="#94a3b8" domain={[0, 1]} label={{ value: "0–1", angle: 90, position: "insideRight", fill: "#94a3b8", fontSize: 11 }} />
                  <Tooltip contentStyle={{ background: "#10131a", border: "1px solid #2a3140", fontSize: 12 }} />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  <Line yAxisId="temp" type="monotone" dataKey="Track Temp (°C)" stroke="#f97316" dot={false} strokeWidth={2} />
                  <Line yAxisId="temp" type="monotone" dataKey="Air Temp (°C)" stroke="#39a9ff" dot={false} strokeWidth={2} />
                  <Line yAxisId="frac" type="monotone" dataKey="Wetness" stroke="#38d996" dot={false} strokeWidth={2} />
                  <Line yAxisId="frac" type="monotone" dataKey="Rain Prob" stroke="#818cf8" dot={false} strokeWidth={1} strokeDasharray="4 2" />
                </LineChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <EmptyState title="No laps completed" message="Advance the live race to populate weather telemetry." />
          )}
        </Panel>

        {/* ── Events and Decisions ── */}
        <Panel title="Events and Decisions">
          {/* Category filter tabs */}
          <div className="mb-3 flex flex-wrap gap-1">
            {categories.map((cat) => (
              <button
                key={cat}
                onClick={() => setActiveCategory(cat)}
                className={`rounded px-2 py-1 text-xs font-bold uppercase tracking-wide transition-colors ${
                  activeCategory === cat
                    ? "bg-pit-purple text-white"
                    : "border border-white/10 text-slate-400 hover:bg-white/10"
                }`}
              >
                {cat === "ALL" ? "All" : categoryLabel[cat as EventCategory]}
              </button>
            ))}
          </div>

          <div className="max-h-96 space-y-2 overflow-auto">
            {filteredEvents.length === 0 && liveRace.actions.length === 0 && (
              <EmptyState title="No events yet" message="Environmental and strategy events will appear here as the race progresses." />
            )}

            {filteredEvents.map((event: RaceControlEvent, index: number) => {
              const meta = eventMeta(event.event_type);
              const consequence = strategicConsequence(event.event_type);
              return (
                <div
                  key={`${event.lap}-${event.event_type}-${index}`}
                  className={`rounded border p-3 text-sm ${toneBorder[meta.tone]}`}
                >
                  <div className="flex items-center gap-2">
                    <span className={toneText[meta.tone]}>{meta.icon}</span>
                    <span className={`text-xs font-bold uppercase tracking-wide ${toneText[meta.tone]}`}>
                      {categoryLabel[meta.category]}
                    </span>
                    <span className="ml-auto text-xs text-slate-500">L{event.lap}</span>
                  </div>
                  <div className="mt-1 font-bold text-white">{meta.label}</div>
                  <div className="mt-0.5 text-xs text-slate-400">{event.reason.replace(/^SIMULATED (WEATHER|STRATEGY|INCIDENT) - /, "")}</div>
                  {consequence && (
                    <div className={`mt-1.5 text-xs font-medium ${toneText[meta.tone]}`}>
                      → {consequence}
                    </div>
                  )}
                </div>
              );
            })}

            {/* User decisions — always shown regardless of category filter */}
            {activeCategory === "ALL" && liveRace.actions.slice(-6).map((action) => (
              <div
                key={`${action.lap}-${action.user_action}-${action.time_impact}`}
                className="rounded border border-white/10 bg-white/[0.035] p-3 text-sm"
              >
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold uppercase tracking-wide text-slate-400">DECISION</span>
                  <span className="ml-auto text-xs text-slate-500">L{action.lap}</span>
                </div>
                <div className="mt-1 font-bold text-white">{action.user_action}</div>
                <div className="mt-0.5 text-xs text-slate-400">AI recommended: {action.recommended_action}</div>
                <div className="mt-0.5 text-xs text-slate-500">
                  {action.time_impact != null
                    ? `Impact ${action.time_impact.toFixed(3)}s`
                    : "Impact: not calculable"} · Followed AI: {action.followed_recommendation ? "yes" : "no"}
                </div>
              </div>
            ))}
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
