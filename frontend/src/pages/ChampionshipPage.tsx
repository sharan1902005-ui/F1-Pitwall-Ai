import { BarChart3, Crown, Loader2, Play, SkipForward, Trophy } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Panel } from "../components/ui/Panel";
import { StatusPill } from "../components/ui/StatusPill";
import { api, ApiError } from "../services/api";
import type {
  ChampionshipProjectionResponse,
  CircuitRead,
  DriverConfig,
  DriverStandingResponse,
  SeasonCreateRequest,
  SeasonResponse,
  SeasonScenarioResponse,
  TyreCompound,
} from "../types/api";

const compounds: TyreCompound[] = ["SOFT", "MEDIUM", "HARD"];

const championshipDrivers: DriverConfig[] = [
  {
    driver_id: "drv-a",
    driver_name: "Driver A",
    team_name: "Red Racing",
    starting_compound: "MEDIUM",
    starting_fuel_kg: 100,
    pace_factor: 0.985,
    degradation_factor: 1.0,
    strategy_mode: "MANUAL",
    strategy: [{ lap: 25, compound: "HARD" }],
  },
  {
    driver_id: "drv-b",
    driver_name: "Driver B",
    team_name: "Blue Motorsport",
    starting_compound: "SOFT",
    starting_fuel_kg: 100,
    pace_factor: 1.0,
    degradation_factor: 1.03,
    strategy_mode: "MANUAL",
    strategy: [
      { lap: 18, compound: "MEDIUM" },
      { lap: 36, compound: "HARD" },
    ],
  },
  {
    driver_id: "drv-c",
    driver_name: "Driver C",
    team_name: "Red Racing",
    starting_compound: "HARD",
    starting_fuel_kg: 100,
    pace_factor: 1.01,
    degradation_factor: 0.96,
    strategy_mode: "MANUAL",
    strategy: [{ lap: 30, compound: "MEDIUM" }],
  },
  {
    driver_id: "drv-d",
    driver_name: "Driver D",
    team_name: "Silver GP",
    starting_compound: "MEDIUM",
    starting_fuel_kg: 100,
    pace_factor: 1.005,
    degradation_factor: 0.98,
    strategy_mode: "MANUAL",
    strategy: [{ lap: 27, compound: "HARD" }],
  },
];

const defaultPoints = {
  1: 25,
  2: 18,
  3: 15,
  4: 12,
  5: 10,
  6: 8,
  7: 6,
  8: 4,
  9: 2,
  10: 1,
};

export function ChampionshipPage() {
  const [circuits, setCircuits] = useState<CircuitRead[]>([]);
  const [calendarIds, setCalendarIds] = useState<number[]>([]);
  const [drivers, setDrivers] = useState<DriverConfig[]>(championshipDrivers);
  const [season, setSeason] = useState<SeasonResponse | null>(null);
  const [scenario, setScenario] = useState<SeasonScenarioResponse | null>(null);
  const [projection, setProjection] = useState<ChampionshipProjectionResponse | null>(null);
  const [scenarioDriver, setScenarioDriver] = useState(championshipDrivers[1].driver_id);
  const [scenarioRound, setScenarioRound] = useState(1);
  const [scenarioPosition, setScenarioPosition] = useState(1);
  const [loading, setLoading] = useState<"create" | "next" | "season" | "scenario" | "projection" | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .listCircuits()
      .then((items) => {
        setCircuits(items);
        setCalendarIds(items.slice(0, Math.min(3, items.length)).map((item) => item.id));
      })
      .catch(() => setError("Circuit API is unavailable."));
  }, []);

  const leader = season?.driver_standings[0];
  const pointsLead = season && season.driver_standings.length > 1
    ? season.driver_standings[0].points - season.driver_standings[1].points
    : 0;

  const request = useMemo<SeasonCreateRequest | null>(() => {
    if (calendarIds.length < 2) return null;
    return {
      season_name: "2026 PitWall Championship",
      calendar: calendarIds.map((circuitId, index) => ({ round_number: index + 1, circuit_id: circuitId })),
      drivers,
      points_system: { points_by_position: defaultPoints },
      weather_seed: 77,
      event_seed: 9,
      safety_car_base_probability: 0.2,
      allow_duplicate_circuits: false,
    };
  }, [calendarIds, drivers]);

  async function createSeason() {
    if (!request) return;
    setLoading("create");
    setError(null);
    setScenario(null);
    setProjection(null);
    try {
      setSeason(await api.createSeason(request));
      setScenarioRound(1);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not create season.");
    } finally {
      setLoading(null);
    }
  }

  async function runNextRace() {
    if (!season) return;
    setLoading("next");
    setError(null);
    setScenario(null);
    setProjection(null);
    try {
      const response = await api.runNextSeasonRace(season.id);
      setSeason(response.season);
      setScenarioRound(Math.min(response.season.current_round || 1, response.season.total_rounds));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not run next race.");
    } finally {
      setLoading(null);
    }
  }

  async function simulateRemaining() {
    if (!season) return;
    setLoading("season");
    setError(null);
    setScenario(null);
    setProjection(null);
    try {
      setSeason(await api.simulateSeason(season.id));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not simulate season.");
    } finally {
      setLoading(null);
    }
  }

  async function runScenario() {
    if (!season) return;
    setLoading("scenario");
    setError(null);
    try {
      setScenario(await api.seasonScenario(season.id, {
        driver_id: scenarioDriver,
        round_number: scenarioRound,
        hypothetical_position: scenarioPosition,
      }));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Scenario failed.");
    } finally {
      setLoading(null);
    }
  }

  async function runProjection() {
    if (!season) return;
    setLoading("projection");
    setError(null);
    try {
      setProjection(await api.championshipProjection(season.id, 12));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Projection failed.");
    } finally {
      setLoading(null);
    }
  }

  return (
    <div className="space-y-5">
      <Panel
        title="Championship"
        action={
          <button
            onClick={createSeason}
            disabled={!request || loading !== null}
            className="inline-flex items-center gap-2 rounded bg-pit-red px-4 py-2 text-sm font-black uppercase text-white disabled:opacity-60"
          >
            {loading === "create" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Crown className="h-4 w-4" />}
            Create Season
          </button>
        }
      >
        {error && <StatusPill tone="red">{error}</StatusPill>}
        <div className="mt-4 grid gap-4 xl:grid-cols-[0.95fr_1.05fr]">
          <div className="space-y-3">
            <div className="grid gap-3 md:grid-cols-3">
              {calendarIds.map((circuitId, index) => (
                <label key={index} className="text-xs font-bold uppercase tracking-wide text-slate-400">
                  Round {index + 1}
                  <select
                    value={circuitId}
                    onChange={(event) => setCalendarIds((current) => current.map((id, currentIndex) => currentIndex === index ? Number(event.target.value) : id))}
                    className="mt-1 w-full rounded border border-white/10 bg-black/30 px-3 py-2 text-sm text-white"
                  >
                    {circuits.map((circuit) => <option key={circuit.id} value={circuit.id}>{circuit.name}</option>)}
                  </select>
                </label>
              ))}
            </div>
            <div className="grid gap-3 md:grid-cols-2">
              {drivers.map((driver, index) => (
                <div key={driver.driver_id} className="rounded border border-white/10 bg-black/20 p-3">
                  <div className="grid gap-2 sm:grid-cols-2">
                    <input value={driver.driver_name} onChange={(event) => updateDriver(index, { driver_name: event.target.value })} className="rounded border border-white/10 bg-black/30 px-3 py-2 text-sm" />
                    <input value={driver.team_name} onChange={(event) => updateDriver(index, { team_name: event.target.value })} className="rounded border border-white/10 bg-black/30 px-3 py-2 text-sm" />
                    <select value={driver.starting_compound} onChange={(event) => updateDriver(index, { starting_compound: event.target.value as TyreCompound })} className="rounded border border-white/10 bg-black/30 px-3 py-2 text-sm">
                      {compounds.map((compound) => <option key={compound}>{compound}</option>)}
                    </select>
                    <input type="number" min={0.94} max={1.08} step={0.005} value={driver.pace_factor} onChange={(event) => updateDriver(index, { pace_factor: Number(event.target.value) })} className="rounded border border-white/10 bg-black/30 px-3 py-2 text-sm" />
                  </div>
                </div>
              ))}
            </div>
          </div>
          <div className="grid gap-3 md:grid-cols-2">
            <Metric label="Season" value={season?.season_name ?? "Not Created"} sub={season ? season.status : "Create from real circuit data"} />
            <Metric label="Current Round" value={season ? `${season.current_round} / ${season.total_rounds}` : "-- / --"} sub="Persistent season state" />
            <Metric label="Leader" value={leader?.driver_name ?? "--"} sub={leader ? `${leader.points} pts` : "No standings yet"} />
            <Metric label="Points Lead" value={`${pointsLead} pts`} sub="Leader over P2" />
            <div className="flex flex-wrap gap-2 md:col-span-2">
              <button onClick={runNextRace} disabled={!season || season.status === "COMPLETED" || loading !== null} className="inline-flex items-center gap-2 rounded border border-white/10 px-3 py-2 text-sm font-bold disabled:opacity-50">
                {loading === "next" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
                Run Next Race
              </button>
              <button onClick={simulateRemaining} disabled={!season || season.status === "COMPLETED" || loading !== null} className="inline-flex items-center gap-2 rounded border border-white/10 px-3 py-2 text-sm font-bold disabled:opacity-50">
                {loading === "season" ? <Loader2 className="h-4 w-4 animate-spin" /> : <SkipForward className="h-4 w-4" />}
                Simulate Remaining Season
              </button>
            </div>
            {season && (
              <div className="md:col-span-2">
                <div className="h-2 rounded bg-white/10">
                  <div className="h-full rounded bg-pit-green" style={{ width: `${(season.current_round / season.total_rounds) * 100}%` }} />
                </div>
              </div>
            )}
          </div>
        </div>
      </Panel>

      {season && (
        <div className="grid gap-5 xl:grid-cols-[1.2fr_0.8fr]">
          <Standings season={season} />
          <Calendar season={season} />
        </div>
      )}

      {season && (
        <div className="grid gap-5 xl:grid-cols-2">
          <Panel title="Championship Analytics">
            <div className="grid gap-3">
              <Metric label="Average Pit Stops" value={season.analytics.average_pit_stops.toString()} sub="Across completed race entries" />
              <Metric label="Most Successful Strategy" value={season.analytics.most_successful_strategy?.strategy_label ?? "--"} sub={season.analytics.most_successful_strategy ? `${season.analytics.most_successful_strategy.wins} wins, avg P${season.analytics.most_successful_strategy.average_position}` : "No completed race data"} />
              <div className="space-y-2">
                {season.driver_standings.map((driver) => <ProgressRow key={driver.driver_id} label={driver.driver_name} values={driver.points_history} max={25} />)}
              </div>
            </div>
          </Panel>

          <Panel title="What If The Title Race Changes?">
            <div className="grid gap-3">
              <div className="grid gap-3 sm:grid-cols-3">
                <select value={scenarioDriver} onChange={(event) => setScenarioDriver(event.target.value)} className="rounded border border-white/10 bg-black/30 px-3 py-2 text-sm">
                  {season.driver_standings.map((driver) => <option key={driver.driver_id} value={driver.driver_id}>{driver.driver_name}</option>)}
                </select>
                <input type="number" min={1} max={season.total_rounds} value={scenarioRound} onChange={(event) => setScenarioRound(Number(event.target.value))} className="rounded border border-white/10 bg-black/30 px-3 py-2 text-sm" />
                <input type="number" min={1} max={drivers.length} value={scenarioPosition} onChange={(event) => setScenarioPosition(Number(event.target.value))} className="rounded border border-white/10 bg-black/30 px-3 py-2 text-sm" />
              </div>
              <button onClick={runScenario} disabled={loading !== null} className="inline-flex w-fit items-center gap-2 rounded bg-pit-red px-3 py-2 text-sm font-bold disabled:opacity-50">
                {loading === "scenario" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trophy className="h-4 w-4" />}
                Run Scenario
              </button>
              {scenario && (
                <div className="grid gap-3 rounded border border-white/10 bg-black/20 p-3 md:grid-cols-3">
                  <Metric label="Baseline" value={`P${scenario.selected_driver_delta.baseline_position}`} sub={`${scenario.selected_driver_delta.baseline_points} pts`} />
                  <Metric label="Scenario" value={`P${scenario.selected_driver_delta.scenario_position}`} sub={`${scenario.selected_driver_delta.scenario_points} pts`} />
                  <Metric label="Leader Changed" value={scenario.championship_leader_changed ? "YES" : "NO"} sub={`${scenario.selected_driver_delta.points_difference} pts delta`} />
                </div>
              )}
            </div>
          </Panel>
        </div>
      )}

      {season && (
        <Panel
          title="Simulation-Based Projection"
          action={
            <button onClick={runProjection} disabled={loading !== null} className="inline-flex items-center gap-2 rounded border border-white/10 px-3 py-2 text-sm font-bold disabled:opacity-50">
              {loading === "projection" ? <Loader2 className="h-4 w-4 animate-spin" /> : <BarChart3 className="h-4 w-4" />}
              Project Title
            </button>
          }
        >
          {projection ? (
            <div className="space-y-3">
              {projection.projections.map((entry) => (
                <div key={entry.driver_id}>
                  <div className="mb-1 flex justify-between text-sm">
                    <span className="font-bold">{entry.driver_name}</span>
                    <span>{Math.round(entry.championship_win_probability * 100)}%</span>
                  </div>
                  <div className="h-3 rounded bg-white/10">
                    <div className="h-full rounded bg-pit-blue" style={{ width: `${entry.championship_win_probability * 100}%` }} />
                  </div>
                  <div className="mt-1 text-xs text-slate-400">Expected {entry.expected_final_points} pts, average final P{entry.expected_final_position}</div>
                </div>
              ))}
              <div className="text-xs text-slate-500">{projection.simulations} simulations. {projection.seed_behavior}</div>
            </div>
          ) : (
            <div className="text-sm text-slate-400">Run projection after creating a season.</div>
          )}
        </Panel>
      )}
    </div>
  );

  function updateDriver(index: number, patch: Partial<DriverConfig>) {
    setDrivers((current) =>
      current.map((driver, driverIndex) => driverIndex === index ? { ...driver, ...patch } : driver),
    );
  }
}

function Standings({ season }: { season: SeasonResponse }) {
  return (
    <Panel title="Driver Standings">
      <div className="overflow-x-auto">
        <table className="w-full min-w-[760px] text-left text-sm">
          <thead className="text-xs uppercase tracking-wide text-slate-500">
            <tr>
              <th className="p-3">Pos</th>
              <th className="p-3">Driver</th>
              <th className="p-3">Team</th>
              <th className="p-3">Points</th>
              <th className="p-3">Wins</th>
              <th className="p-3">Podiums</th>
              <th className="p-3">Momentum</th>
            </tr>
          </thead>
          <tbody>
            {season.driver_standings.map((driver) => (
              <tr key={driver.driver_id} className="border-t border-white/10">
                <td className="p-3 font-black">P{driver.position}</td>
                <td className="p-3">{driver.driver_name}</td>
                <td className="p-3 text-slate-400">{driver.team_name}</td>
                <td className="p-3 font-black">{driver.points}</td>
                <td className="p-3">{driver.wins}</td>
                <td className="p-3">{driver.podiums}</td>
                <td className="p-3"><Momentum momentum={driver.momentum} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="mt-4 grid gap-2 md:grid-cols-3">
        {season.constructor_standings.map((team) => (
          <div key={team.team_name} className="rounded border border-white/10 bg-black/20 p-3">
            <div className="text-xs font-bold uppercase tracking-wide text-slate-500">P{team.position}</div>
            <div className="font-black">{team.team_name}</div>
            <div className="text-sm text-slate-400">{team.points} pts, {team.wins} wins, {team.podiums} podiums</div>
          </div>
        ))}
      </div>
    </Panel>
  );
}

function Calendar({ season }: { season: SeasonResponse }) {
  return (
    <Panel title="Season Calendar">
      <div className="space-y-2">
        {season.calendar.map((race) => {
          const next = !race.completed && race.round_number === season.current_round + 1;
          return (
            <div key={race.round_number} className="grid grid-cols-[42px_1fr] gap-3 rounded border border-white/10 bg-black/20 p-3">
              <div className={`grid h-8 w-8 place-items-center rounded ${race.completed ? "bg-pit-green text-black" : next ? "bg-pit-red text-white" : "bg-white/10 text-slate-400"}`}>
                {race.completed ? "OK" : next ? "GO" : race.round_number}
              </div>
              <div>
                <div className="text-xs font-bold uppercase tracking-wide text-slate-500">Round {race.round_number}</div>
                <div className="font-black">{race.circuit_name}</div>
                <div className="text-sm text-slate-400">{race.completed ? `Winner: ${race.winner_driver_name}` : next ? "Next Race" : "Upcoming"}</div>
              </div>
            </div>
          );
        })}
      </div>
    </Panel>
  );
}

function Metric({ label, value, sub }: { label: string; value: string; sub: string }) {
  return (
    <div className="rounded border border-white/10 bg-black/20 p-3">
      <div className="text-xs font-bold uppercase tracking-wide text-slate-500">{label}</div>
      <div className="mt-1 text-2xl font-black">{value}</div>
      <div className="text-sm text-slate-400">{sub}</div>
    </div>
  );
}

function Momentum({ momentum }: { momentum: DriverStandingResponse["momentum"] }) {
  const tone = momentum === "IMPROVING" ? "green" : momentum === "DECLINING" ? "red" : "yellow";
  return <StatusPill tone={tone}>{momentum}</StatusPill>;
}

function ProgressRow({ label, values, max }: { label: string; values: number[]; max: number }) {
  return (
    <div>
      <div className="mb-1 flex justify-between text-xs text-slate-400">
        <span>{label}</span>
        <span>{values.join(" / ") || "No races"}</span>
      </div>
      <div className="flex h-3 gap-1">
        {values.length ? values.map((value, index) => (
          <div key={index} className="h-full flex-1 rounded bg-pit-green" style={{ opacity: Math.max(0.25, value / max) }} />
        )) : <div className="h-full flex-1 rounded bg-white/10" />}
      </div>
    </div>
  );
}
