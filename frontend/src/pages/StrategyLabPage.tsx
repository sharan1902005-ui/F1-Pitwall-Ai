import { Loader2 } from "lucide-react";
import { useState } from "react";
import { EmptyState } from "../components/ui/EmptyState";
import { Panel } from "../components/ui/Panel";
import { StatusPill } from "../components/ui/StatusPill";
import { StrategyTimeline } from "../components/strategy/StrategyTimeline";
import { formatRaceTime, strategyLabel } from "../lib/format";
import { api, ApiError } from "../services/api";
import { useRaceStore } from "../store/raceStore";
import type { PageId } from "../types/navigation";
import type {
  EngineerResponse,
  OpponentPredictionResponse,
  PitWindowResponse,
  StrategyRiskResponse,
  TrafficResponse,
  UndercutResponse,
  OvercutResponse,
} from "../types/api";

export function StrategyLabPage({ setPage: _setPage }: { setPage: (page: PageId) => void }) {
  const { raceConfig, strategy, setStrategy } = useRaceStore();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [undercut, setUndercut] = useState<UndercutResponse | null>(null);
  const [undercutLoading, setUndercutLoading] = useState(false);
  const [undercutError, setUndercutError] = useState<string | null>(null);

  const [overcut, setOvercut] = useState<OvercutResponse | null>(null);
  const [overcutLoading, setOvercutLoading] = useState(false);
  const [overcutError, setOvercutError] = useState<string | null>(null);

  const [pitWindow, setPitWindow] = useState<PitWindowResponse | null>(null);
  const [pitWindowLoading, setPitWindowLoading] = useState(false);
  const [pitWindowError, setPitWindowError] = useState<string | null>(null);

  const [opponentPrediction, setOpponentPrediction] = useState<OpponentPredictionResponse | null>(null);
  const [opponentPredictionLoading, setOpponentPredictionLoading] = useState(false);
  const [opponentPredictionError, setOpponentPredictionError] = useState<string | null>(null);

  const [traffic, setTraffic] = useState<TrafficResponse | null>(null);
  const [trafficLoading, setTrafficLoading] = useState(false);
  const [trafficError, setTrafficError] = useState<string | null>(null);

  const [strategyRisk, setStrategyRisk] = useState<StrategyRiskResponse | null>(null);
  const [strategyRiskLoading, setStrategyRiskLoading] = useState(false);
  const [strategyRiskError, setStrategyRiskError] = useState<string | null>(null);

  const [engineerAdvice, setEngineerAdvice] = useState<EngineerResponse | null>(null);
  const [engineerAdviceLoading, setEngineerAdviceLoading] = useState(false);
  const [engineerAdviceError, setEngineerAdviceError] = useState<string | null>(null);

  async function analyzeUndercut() {
    setUndercutLoading(true);
    setUndercutError(null);

    try {
      const currentLap = Math.max(
        1,
        Math.floor(raceConfig.circuit.total_laps / 2),
      );

      const result = await api.analyzeUndercut({
        attacker: {
          driver_name: "PitWall Driver",
          position: 5,
          compound: raceConfig.starting_compound,
          tyre_age: Math.floor(currentLap * 0.8),
          gap_to_driver_ahead_seconds: 1.2,
          current_lap: currentLap,
          base_lap_time_seconds: raceConfig.circuit.base_lap_time_seconds,
          degradation_per_lap: 0.08,
        },
        defender: {
          driver_name: "Driver Ahead",
          position: 4,
          compound: raceConfig.starting_compound,
          tyre_age: Math.floor(currentLap * 0.9),
          gap_to_driver_ahead_seconds: 0.8,
          current_lap: currentLap,
          base_lap_time_seconds: raceConfig.circuit.base_lap_time_seconds,
          degradation_per_lap: 0.1,
        },
        pit_lane_time_loss_seconds: raceConfig.circuit.pit_lane_time_loss_seconds,
        new_compound: "HARD",
        defender_stays_out_laps: 2,
      });

      setUndercut(result);
    } catch (err) {
      setUndercutError(
        err instanceof ApiError ? err.message : "Undercut analysis failed.",
      );
    } finally {
      setUndercutLoading(false);
    }
  }

  async function analyzeOvercut() {
    setOvercutLoading(true);
    setOvercutError(null);

    try {
      const currentLap = Math.max(
        1,
        Math.floor(raceConfig.circuit.total_laps / 2),
      );

      const result = await api.analyzeOvercut({
        driver: {
          driver_name: "PitWall Driver",
          position: 5,
          compound: raceConfig.starting_compound,
          tyre_age: Math.floor(currentLap * 0.8),
          gap_to_driver_ahead_seconds: 1.2,
          current_lap: currentLap,
          base_lap_time_seconds: raceConfig.circuit.base_lap_time_seconds,
          degradation_per_lap: 0.08,
        },
        opponent: {
          driver_name: "Opponent",
          position: 4,
          compound: raceConfig.starting_compound,
          tyre_age: Math.floor(currentLap * 0.9),
          gap_to_driver_ahead_seconds: 0.8,
          current_lap: currentLap,
          base_lap_time_seconds: raceConfig.circuit.base_lap_time_seconds,
          degradation_per_lap: 0.1,
        },
        pit_lane_time_loss_seconds: raceConfig.circuit.pit_lane_time_loss_seconds,
        max_stay_out_laps: 3,
      });

      setOvercut(result);
    } catch (err) {
      setOvercutError(
        err instanceof ApiError ? err.message : "Overcut analysis failed.",
      );
    } finally {
      setOvercutLoading(false);
    }
  }

  async function analyzePitWindow() {
    setPitWindowLoading(true);
    setPitWindowError(null);

    try {
      const totalLaps = raceConfig.circuit.total_laps;
      const currentLap = Math.min(totalLaps, Math.max(1, Math.floor(totalLaps / 2)));
      const earliestPitLap = Math.min(totalLaps, currentLap + 1);
      const latestPitLap = Math.min(totalLaps, earliestPitLap + 6);

      const result = await api.analyzePitWindow({
        driver: {
          driver_name: "PitWall Driver",
          current_lap: currentLap,
          total_laps: totalLaps,
          position: 5,
          compound: raceConfig.starting_compound,
          tyre_age: Math.floor(currentLap * 0.8),
          base_lap_time_seconds: raceConfig.circuit.base_lap_time_seconds,
          degradation_per_lap: 0.08,
          gap_to_driver_ahead_seconds: 1.2,
        },
        pit_lane_time_loss_seconds: raceConfig.circuit.pit_lane_time_loss_seconds,
        earliest_pit_lap: earliestPitLap,
        latest_pit_lap: latestPitLap,
        new_compound: "HARD",
      });

      setPitWindow(result);
    } catch (err) {
      setPitWindowError(
        err instanceof ApiError ? err.message : "Pit window analysis failed.",
      );
    } finally {
      setPitWindowLoading(false);
    }
  }

  async function predictOpponent() {
    setOpponentPredictionLoading(true);
    setOpponentPredictionError(null);

    try {
      const totalLaps = raceConfig.circuit.total_laps;
      const currentLap = Math.min(totalLaps - 1, Math.max(1, Math.floor(totalLaps / 2)));

      const result = await api.predictOpponent({
        driver_name: "Driver Ahead",
        position: 4,
        compound: raceConfig.starting_compound,
        tyre_age: Math.floor(currentLap * 0.9),
        current_lap: currentLap,
        total_laps: totalLaps,
        base_lap_time_seconds: raceConfig.circuit.base_lap_time_seconds,
        degradation_per_lap: 0.1,
        pit_stops_completed: 0,
        weather_risk: 0.1,
        prediction_window_laps: Math.min(5, totalLaps - currentLap),
      });

      setOpponentPrediction(result);
    } catch (err) {
      setOpponentPredictionError(
        err instanceof ApiError ? err.message : "Opponent prediction failed.",
      );
    } finally {
      setOpponentPredictionLoading(false);
    }
  }

  async function analyzeTraffic() {
    setTrafficLoading(true);
    setTrafficError(null);

    try {
      const currentLap = Math.max(1, Math.floor(raceConfig.circuit.total_laps / 2));
      const result = await api.analyzeTraffic({
        driver: {
          driver_name: "PitWall Driver",
          current_position: 5,
          current_lap: currentLap,
          base_lap_time_seconds: raceConfig.circuit.base_lap_time_seconds,
        },
        car_ahead: {
          driver_name: "Driver Ahead",
          gap_seconds: 1.2,
          pace_delta_seconds: 0.15,
          overtaking_difficulty: 0.7,
        },
        laps_in_traffic: 5,
      });

      setTraffic(result);
    } catch (err) {
      setTrafficError(
        err instanceof ApiError ? err.message : "Traffic analysis failed.",
      );
    } finally {
      setTrafficLoading(false);
    }
  }

  async function analyzeStrategyRisk() {
    setStrategyRiskLoading(true);
    setStrategyRiskError(null);

    try {
      const currentLap = Math.max(1, Math.floor(raceConfig.circuit.total_laps / 2));
      const estimatedTyreLife = raceConfig.starting_compound === "SOFT"
        ? 18
        : raceConfig.starting_compound === "MEDIUM"
          ? 30
          : raceConfig.starting_compound === "HARD"
            ? 42
            : 25;

      const result = await api.analyzeStrategyRisk({
        weather_risk: 0.1,
        traffic_risk: "MEDIUM",
        tyre_age: Math.floor(currentLap * 0.8),
        estimated_tyre_life: estimatedTyreLife,
        degradation_per_lap: 0.08,
        safety_car_probability: raceConfig.safety_car_base_probability,
        opponent_pit_probability: 50,
        pit_lane_time_loss_seconds: raceConfig.circuit.pit_lane_time_loss_seconds,
      });

      setStrategyRisk(result);
    } catch (err) {
      setStrategyRiskError(
        err instanceof ApiError ? err.message : "Strategy risk analysis failed.",
      );
    } finally {
      setStrategyRiskLoading(false);
    }
  }

  async function askRaceEngineer() {
    setEngineerAdviceLoading(true);
    setEngineerAdviceError(null);

    try {
      const result = await api.explainStrategy({
        race_config: raceConfig,
        strategy_id: strategy?.recommended_strategy?.strategy_id ?? null,
      });

      setEngineerAdvice(result);
    } catch (err) {
      setEngineerAdviceError(
        err instanceof ApiError ? err.message : "Race engineer analysis failed.",
      );
    } finally {
      setEngineerAdviceLoading(false);
    }
  }

  async function analyze() {
    setLoading(true);
    setError(null);
    try {
      setStrategy(await api.analyzeStrategy(raceConfig));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Strategy analysis failed.");
    } finally {
      setLoading(false);
    }
  }

  const recommended = strategy?.recommended_strategy;
  const leader = recommended?.expected_race_time_seconds ?? 0;

  return (
    <div className="flex flex-col gap-5">
      <Panel className="order-2" title="Recommended Strategy" action={<button onClick={analyze} disabled={loading} className="rounded bg-pit-red px-4 py-2 text-sm font-black uppercase text-white disabled:opacity-60">{loading ? <Loader2 className="inline h-4 w-4 animate-spin" /> : null} Analyze</button>}>
        {error && <StatusPill tone="red">{error}</StatusPill>}
        {recommended ? (
          <div className="space-y-4">
            <div className="flex flex-wrap items-end justify-between gap-3">
              <div>
                <div className="text-sm font-bold uppercase tracking-[0.2em] text-pit-green">Recommended</div>
                <div className="mt-1 text-3xl font-black">{strategyLabel(recommended.stints)}</div>
              </div>
              <div className="flex gap-2">
                <StatusPill tone="blue">{formatRaceTime(recommended.expected_race_time_seconds)}</StatusPill>
                <StatusPill tone="purple">{Math.round(recommended.confidence * 100)}% confidence</StatusPill>
                <StatusPill tone={recommended.risk === "HIGH" ? "red" : recommended.risk === "MEDIUM" ? "yellow" : "green"}>{recommended.risk}</StatusPill>
              </div>
            </div>
            <StrategyTimeline strategy={recommended} />
          </div>
        ) : (
          <EmptyState title="No strategies analyzed" message="Run strategy analysis using the current RaceConfig." action={<button onClick={analyze} className="rounded bg-pit-red px-4 py-2 text-sm font-bold">Analyze Strategy</button>} />
        )}
      </Panel>

      <Panel
        className="order-4"
        title="Undercut Intelligence"
        action={
          <button
            onClick={analyzeUndercut}
            disabled={undercutLoading}
            className="rounded bg-pit-red px-4 py-2 text-sm font-black uppercase text-white disabled:opacity-60"
          >
            {undercutLoading ? (
              <Loader2 className="inline h-4 w-4 animate-spin" />
            ) : (
              "Analyze"
            )}
          </button>
        }
      >
        {undercutError && (
          <StatusPill tone="red">{undercutError}</StatusPill>
        )}

        {undercut ? (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <div className="rounded-lg border border-white/10 bg-black/20 p-4">
              <div className="text-xs uppercase text-slate-500">Availability</div>
              <div className="mt-2">
                <StatusPill tone={undercut.undercut_available ? "green" : "red"}>
                  {undercut.undercut_available ? "AVAILABLE" : "NOT AVAILABLE"}
                </StatusPill>
              </div>
            </div>

            <div className="rounded-lg border border-white/10 bg-black/20 p-4">
              <div className="text-xs uppercase text-slate-500">Projected Gain</div>
              <div className="mt-2 text-2xl font-black">{undercut.projected_gain_seconds.toFixed(2)}s</div>
            </div>

            <div className="rounded-lg border border-white/10 bg-black/20 p-4">
              <div className="text-xs uppercase text-slate-500">Confidence</div>
              <div className="mt-2 text-2xl font-black">{Math.round(undercut.confidence * 100)}%</div>
            </div>

            <div className="rounded-lg border border-white/10 bg-black/20 p-4">
              <div className="text-xs uppercase text-slate-500">Recommended Tyre</div>
              <div className="mt-2 text-2xl font-black">{undercut.recommended_compound}</div>
            </div>

            <div className="rounded-lg border border-white/10 bg-black/20 p-4 md:col-span-2 lg:col-span-4">
              <div className="text-xs uppercase text-slate-500">Race Engineer Recommendation</div>
              <div className="mt-2 text-lg font-bold">{undercut.recommendation}</div>
              <div className="mt-3 flex flex-wrap gap-3 text-sm text-slate-400">
                <span>Projected Position: P{undercut.projected_position}</span>
                <span>Gap After Cycle: {undercut.projected_gap_after_cycle_seconds.toFixed(2)}s</span>
                <span>Analysis: {undercut.analysis_laps} laps</span>
              </div>
            </div>
          </div>
        ) : (
          <EmptyState
            title="No undercut analysis"
            message="Analyze the current race configuration to evaluate the undercut opportunity."
            action={
              <button
                onClick={analyzeUndercut}
                className="rounded bg-pit-red px-4 py-2 text-sm font-bold"
              >
                Analyze Undercut
              </button>
            }
          />
        )}
      </Panel>

      <Panel
        className="order-4"
        title="Overcut Intelligence"
        action={
          <button
            onClick={analyzeOvercut}
            disabled={overcutLoading}
            className="rounded bg-pit-red px-4 py-2 text-sm font-black uppercase text-white disabled:opacity-60"
          >
            {overcutLoading ? (
              <Loader2 className="inline h-4 w-4 animate-spin" />
            ) : (
              "Analyze"
            )}
          </button>
        }
      >
        {overcutError && (
          <StatusPill tone="red">{overcutError}</StatusPill>
        )}

        {overcut ? (
          <div className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
              <div className="rounded-lg border border-white/10 bg-black/20 p-4">
                <div className="text-xs uppercase text-slate-500">Availability</div>
                <div className="mt-2">
                  <StatusPill tone={overcut.overcut_available ? "green" : "red"}>
                    {overcut.overcut_available ? "AVAILABLE" : "NOT AVAILABLE"}
                  </StatusPill>
                </div>
              </div>

              <div className="rounded-lg border border-white/10 bg-black/20 p-4">
                <div className="text-xs uppercase text-slate-500">Best Stay Out</div>
                <div className="mt-2 text-2xl font-black">{overcut.best_stay_out_laps} laps</div>
              </div>

              <div className="rounded-lg border border-white/10 bg-black/20 p-4">
                <div className="text-xs uppercase text-slate-500">Projected Advantage</div>
                <div className="mt-2 text-2xl font-black">{overcut.projected_advantage_seconds.toFixed(2)}s</div>
              </div>

              <div className="rounded-lg border border-white/10 bg-black/20 p-4">
                <div className="text-xs uppercase text-slate-500">Confidence</div>
                <div className="mt-2 text-2xl font-black">{Math.round(overcut.confidence * 100)}%</div>
              </div>
            </div>

            <div className="rounded-lg border border-white/10 bg-black/20 p-4">
              <div className="text-xs uppercase text-slate-500">Race Engineer Recommendation</div>
              <div className="mt-2 text-lg font-bold">{overcut.recommendation}</div>
              <div className="mt-3 flex flex-wrap gap-4 text-sm text-slate-400">
                <span>Projected Position: P{overcut.projected_position}</span>
                <span>Gap After Cycle: {overcut.projected_gap_after_cycle_seconds.toFixed(2)}s</span>
              </div>
            </div>

            {overcut.options.length > 0 && (
              <div>
                <div className="mb-2 text-xs font-bold uppercase tracking-wide text-slate-500">Overcut Options</div>
                <div className="grid gap-3 md:grid-cols-3">
                  {overcut.options.map((option) => (
                    <div
                      key={option.stay_out_laps}
                      className="rounded-lg border border-white/10 bg-black/20 p-3"
                    >
                      <div className="font-black">Stay Out: {option.stay_out_laps} laps</div>
                      <div className="mt-2 text-sm text-slate-400">Advantage: {option.projected_advantage_seconds.toFixed(2)}s</div>
                      <div className="text-sm text-slate-400">Gap: {option.projected_gap_after_cycle_seconds.toFixed(2)}s</div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          <EmptyState
            title="No overcut analysis"
            message="Analyze the current race configuration to evaluate whether extending the stint creates an advantage."
            action={
              <button
                onClick={analyzeOvercut}
                className="rounded bg-pit-red px-4 py-2 text-sm font-bold"
              >
                Analyze Overcut
              </button>
            }
          />
        )}
      </Panel>

      <Panel
        className="order-3"
        title="Pit Window Intelligence"
        action={
          <button
            onClick={analyzePitWindow}
            disabled={pitWindowLoading}
            className="rounded bg-pit-red px-4 py-2 text-sm font-black uppercase text-white disabled:opacity-60"
          >
            {pitWindowLoading ? (
              <Loader2 className="inline h-4 w-4 animate-spin" />
            ) : (
              "Analyze"
            )}
          </button>
        }
      >
        {pitWindowError && <StatusPill tone="red">{pitWindowError}</StatusPill>}

        {pitWindow ? (
          <div className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
              <div className="rounded-lg border border-white/10 bg-black/20 p-4">
                <div className="text-xs uppercase text-slate-500">Pit Window</div>
                <div className="mt-2 text-2xl font-black">L{pitWindow.earliest_lap} - L{pitWindow.latest_lap}</div>
              </div>
              <div className="rounded-lg border border-white/10 bg-black/20 p-4">
                <div className="text-xs uppercase text-slate-500">Optimal Pit Lap</div>
                <div className="mt-2 text-2xl font-black">L{pitWindow.optimal_lap}</div>
              </div>
              <div className="rounded-lg border border-white/10 bg-black/20 p-4">
                <div className="text-xs uppercase text-slate-500">Recommended Tyre</div>
                <div className="mt-2 text-2xl font-black">{pitWindow.recommended_compound}</div>
              </div>
              <div className="rounded-lg border border-white/10 bg-black/20 p-4">
                <div className="text-xs uppercase text-slate-500">Confidence</div>
                <div className="mt-2 text-2xl font-black">{Math.round(pitWindow.confidence * 100)}%</div>
              </div>
            </div>

            <div className="rounded-lg border border-white/10 bg-black/20 p-4">
              <div className="text-xs uppercase text-slate-500">Recommendation</div>
              <div className="mt-2 text-lg font-bold">{pitWindow.recommendation}</div>
              <div className="mt-3 flex flex-wrap gap-4 text-sm text-slate-400">
                <span>Projected Gain: {pitWindow.projected_gain_seconds.toFixed(3)}s</span>
                <span>Projected Race Time: {formatRaceTime(pitWindow.projected_race_time_seconds)}</span>
              </div>
            </div>

            {pitWindow.options.length > 0 && (
              <div>
                <div className="mb-2 text-xs font-bold uppercase tracking-wide text-slate-500">Pit Window Options</div>
                <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
                  {pitWindow.options.map((option) => (
                    <div
                      key={option.pit_lap}
                      className="rounded-lg border border-white/10 bg-black/20 p-3"
                    >
                      <div className="font-black">Pit on Lap {option.pit_lap}</div>
                      <div className="mt-2 text-sm text-slate-400">Race Time: {formatRaceTime(option.projected_race_time_seconds)}</div>
                      <div className="text-sm text-slate-400">Gain: {option.projected_gain_seconds.toFixed(3)}s</div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          <EmptyState
            title="No pit window analysis"
            message="Analyze the current race configuration to evaluate the best pit window."
            action={
              <button
                onClick={analyzePitWindow}
                className="rounded bg-pit-red px-4 py-2 text-sm font-bold"
              >
                Analyze Pit Window
              </button>
            }
          />
        )}
      </Panel>

      <Panel
        className="order-5"
        title="Opponent Prediction"
        action={
          <button
            onClick={predictOpponent}
            disabled={opponentPredictionLoading}
            className="rounded bg-pit-red px-4 py-2 text-sm font-black uppercase text-white disabled:opacity-60"
          >
            {opponentPredictionLoading ? (
              <Loader2 className="inline h-4 w-4 animate-spin" />
            ) : (
              "Analyze"
            )}
          </button>
        }
      >
        {opponentPredictionError && <StatusPill tone="red">{opponentPredictionError}</StatusPill>}

        {opponentPrediction ? (
          <div className="space-y-4">
            <div className="grid gap-4 md:grid-cols-3">
              <div className="rounded-lg border border-white/10 bg-black/20 p-4">
                <div className="text-xs uppercase text-slate-500">Opponent</div>
                <div className="mt-2 text-2xl font-black">{opponentPrediction.driver_name}</div>
              </div>
              <div className="rounded-lg border border-white/10 bg-black/20 p-4">
                <div className="text-xs uppercase text-slate-500">Most Likely Pit Lap</div>
                <div className="mt-2 text-2xl font-black">L{opponentPrediction.most_likely_pit_lap}</div>
              </div>
              <div className="rounded-lg border border-white/10 bg-black/20 p-4">
                <div className="text-xs uppercase text-slate-500">Pit Probability</div>
                <div className="mt-2 text-2xl font-black">{opponentPrediction.most_likely_probability.toFixed(1)}%</div>
              </div>
            </div>

            <div className="rounded-lg border border-white/10 bg-black/20 p-4">
              <div className="text-xs uppercase text-slate-500">Recommendation</div>
              <div className="mt-2 text-lg font-bold">{opponentPrediction.recommendation}</div>
              <div className="mt-3 text-sm text-slate-400">Confidence: {Math.round(opponentPrediction.confidence * 100)}%</div>
            </div>

            {opponentPrediction.predictions.length > 0 && (
              <div>
                <div className="mb-2 text-xs font-bold uppercase tracking-wide text-slate-500">Pit Probability by Lap</div>
                <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
                  {opponentPrediction.predictions.map((prediction) => (
                    <div
                      key={prediction.lap}
                      className="rounded-lg border border-white/10 bg-black/20 p-3"
                    >
                      <div className="font-black">Lap {prediction.lap}</div>
                      <div className="mt-2 text-sm text-slate-400">Pit probability: {prediction.probability.toFixed(1)}%</div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          <EmptyState
            title="No opponent prediction"
            message="Analyze the current race configuration to predict the driver ahead's pit behavior."
            action={
              <button
                onClick={predictOpponent}
                className="rounded bg-pit-red px-4 py-2 text-sm font-bold"
              >
                Analyze Opponent
              </button>
            }
          />
        )}
      </Panel>

      <Panel
        className="order-6"
        title="Traffic & Dirty Air"
        action={
          <button
            onClick={analyzeTraffic}
            disabled={trafficLoading}
            className="rounded bg-pit-red px-4 py-2 text-sm font-black uppercase text-white disabled:opacity-60"
          >
            {trafficLoading ? (
              <Loader2 className="inline h-4 w-4 animate-spin" />
            ) : (
              "Analyze"
            )}
          </button>
        }
      >
        {trafficError && <StatusPill tone="red">{trafficError}</StatusPill>}

        {traffic ? (
          <div className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
              <div className="rounded-lg border border-white/10 bg-black/20 p-4">
                <div className="text-xs uppercase text-slate-500">Dirty-Air Penalty</div>
                <div className="mt-2 text-2xl font-black">{traffic.dirty_air_penalty_seconds.toFixed(3)}s</div>
              </div>
              <div className="rounded-lg border border-white/10 bg-black/20 p-4">
                <div className="text-xs uppercase text-slate-500">Projected Traffic Loss</div>
                <div className="mt-2 text-2xl font-black">{traffic.projected_traffic_loss_seconds.toFixed(3)}s</div>
              </div>
              <div className="rounded-lg border border-white/10 bg-black/20 p-4">
                <div className="text-xs uppercase text-slate-500">Overtaking Difficulty</div>
                <div className="mt-2 text-2xl font-black">{Math.round(traffic.overtaking_difficulty * 100)}%</div>
              </div>
              <div className="rounded-lg border border-white/10 bg-black/20 p-4">
                <div className="text-xs uppercase text-slate-500">Traffic Risk</div>
                <div className="mt-2">
                  <StatusPill tone={traffic.traffic_risk === "HIGH" ? "red" : traffic.traffic_risk === "MEDIUM" ? "yellow" : "green"}>
                    {traffic.traffic_risk}
                  </StatusPill>
                </div>
              </div>
            </div>

            <div className="rounded-lg border border-white/10 bg-black/20 p-4">
              <div className="text-xs uppercase text-slate-500">Recommendation</div>
              <div className="mt-2 text-lg font-bold">{traffic.recommendation}</div>
            </div>
          </div>
        ) : (
          <EmptyState
            title="No traffic analysis"
            message="Analyze the current race configuration to estimate traffic and dirty-air impact."
            action={
              <button
                onClick={analyzeTraffic}
                className="rounded bg-pit-red px-4 py-2 text-sm font-bold"
              >
                Analyze Traffic
              </button>
            }
          />
        )}
      </Panel>

      <Panel
        className="order-7"
        title="Strategy Risk"
        action={
          <button
            onClick={analyzeStrategyRisk}
            disabled={strategyRiskLoading}
            className="rounded bg-pit-red px-4 py-2 text-sm font-black uppercase text-white disabled:opacity-60"
          >
            {strategyRiskLoading ? (
              <Loader2 className="inline h-4 w-4 animate-spin" />
            ) : (
              "Analyze"
            )}
          </button>
        }
      >
        {strategyRiskError && <StatusPill tone="red">{strategyRiskError}</StatusPill>}

        {strategyRisk ? (
          <div className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <div className="rounded-lg border border-white/10 bg-black/20 p-4">
                <div className="text-xs uppercase text-slate-500">Overall Risk Score</div>
                <div className="mt-2 text-3xl font-black">{strategyRisk.overall_risk_score.toFixed(2)}</div>
              </div>
              <div className="rounded-lg border border-white/10 bg-black/20 p-4">
                <div className="text-xs uppercase text-slate-500">Risk Level</div>
                <div className="mt-2">
                  <StatusPill tone={strategyRisk.risk_level === "HIGH" ? "red" : strategyRisk.risk_level === "MEDIUM" ? "yellow" : "green"}>
                    {strategyRisk.risk_level}
                  </StatusPill>
                </div>
              </div>
            </div>

            <div>
              <div className="mb-2 text-xs font-bold uppercase tracking-wide text-slate-500">Risk Factors</div>
              <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-5">
                <div className="rounded-lg border border-white/10 bg-black/20 p-3">
                  <div className="text-xs uppercase text-slate-500">Weather</div>
                  <div className="mt-2 text-xl font-black">{strategyRisk.weather_risk_score.toFixed(2)}</div>
                </div>
                <div className="rounded-lg border border-white/10 bg-black/20 p-3">
                  <div className="text-xs uppercase text-slate-500">Traffic</div>
                  <div className="mt-2 text-xl font-black">{strategyRisk.traffic_risk_score.toFixed(2)}</div>
                </div>
                <div className="rounded-lg border border-white/10 bg-black/20 p-3">
                  <div className="text-xs uppercase text-slate-500">Tyre</div>
                  <div className="mt-2 text-xl font-black">{strategyRisk.tyre_risk_score.toFixed(2)}</div>
                </div>
                <div className="rounded-lg border border-white/10 bg-black/20 p-3">
                  <div className="text-xs uppercase text-slate-500">Safety Car</div>
                  <div className="mt-2 text-xl font-black">{strategyRisk.safety_car_risk_score.toFixed(2)}</div>
                </div>
                <div className="rounded-lg border border-white/10 bg-black/20 p-3">
                  <div className="text-xs uppercase text-slate-500">Opponent</div>
                  <div className="mt-2 text-xl font-black">{strategyRisk.opponent_risk_score.toFixed(2)}</div>
                </div>
              </div>
            </div>

            <div className="rounded-lg border border-white/10 bg-black/20 p-4">
              <div className="text-xs uppercase text-slate-500">Recommendation</div>
              <div className="mt-2 text-lg font-bold">{strategyRisk.recommendation}</div>
            </div>
          </div>
        ) : (
          <EmptyState
            title="No strategy risk analysis"
            message="Analyze the current race configuration to assess strategy risk factors."
            action={
              <button
                onClick={analyzeStrategyRisk}
                className="rounded bg-pit-red px-4 py-2 text-sm font-bold"
              >
                Analyze Risk
              </button>
            }
          />
        )}
      </Panel>

      <Panel
        className="order-1"
        title="AI Race Engineer Decision"
        action={
          <button
            onClick={askRaceEngineer}
            disabled={engineerAdviceLoading}
            className="rounded bg-pit-red px-4 py-2 text-sm font-black uppercase text-white disabled:opacity-60"
          >
            {engineerAdviceLoading ? (
              <Loader2 className="inline h-4 w-4 animate-spin" />
            ) : (
              "Ask Engineer"
            )}
          </button>
        }
      >
        {engineerAdviceError && <StatusPill tone="red">{engineerAdviceError}</StatusPill>}

        {engineerAdvice ? (
          <div className="space-y-4">
            <div className="flex flex-wrap items-start justify-between gap-3 rounded-lg border border-white/10 bg-black/20 p-4">
              <div>
                <div className="text-xs uppercase text-slate-500">Action</div>
                <div className="mt-2 text-2xl font-black">{engineerAdvice.decision}</div>
              </div>
              <StatusPill tone={engineerAdvice.urgency === "CRITICAL" || engineerAdvice.urgency === "HIGH" ? "red" : engineerAdvice.urgency === "MEDIUM" ? "yellow" : "green"}>
                Urgency {engineerAdvice.urgency}
              </StatusPill>
            </div>

            <div>
              <div className="mb-2 text-xs font-bold uppercase tracking-wide text-slate-500">Recommendation</div>
              <div className="flex flex-wrap gap-2">
                {engineerAdvice.confidence != null && <StatusPill tone="blue">{Math.round(engineerAdvice.confidence * 100)}% confidence</StatusPill>}
                {engineerAdvice.recommended_compound && <StatusPill tone="green">{engineerAdvice.recommended_compound}</StatusPill>}
                {engineerAdvice.recommended_pit_lap != null && <StatusPill tone="red">Pit lap {engineerAdvice.recommended_pit_lap}</StatusPill>}
                {engineerAdvice.risk && <StatusPill tone={engineerAdvice.risk === "HIGH" ? "red" : engineerAdvice.risk === "MEDIUM" ? "yellow" : "green"}>{engineerAdvice.risk} risk</StatusPill>}
              </div>
            </div>

            <div className="rounded-lg border border-white/10 bg-black/20 p-4">
              <div className="text-xs uppercase text-slate-500">Reasoning</div>
              <div className="mt-2 text-lg font-bold">{engineerAdvice.explanation}</div>
            </div>

            {engineerAdvice.key_factors.length > 0 && (
              <div>
                <div className="mb-2 text-xs font-bold uppercase tracking-wide text-slate-500">Key Factors</div>
                <div className="grid gap-2">
                  {engineerAdvice.key_factors.map((factor) => (
                    <div key={factor} className="rounded border border-white/10 bg-black/20 p-3 text-sm text-slate-300">
                      {factor}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          <EmptyState
            title="Engineer standing by"
            message="Ask the AI Race Engineer to explain the current strategy recommendation."
            action={
              <button
                onClick={askRaceEngineer}
                className="rounded bg-pit-red px-4 py-2 text-sm font-bold"
              >
                Ask Engineer
              </button>
            }
          />
        )}
      </Panel>

      {strategy?.strategies.length ? (
        <div className="order-8">
        <Panel title="Backend Ranked Strategies">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[760px] text-left text-sm">
              <thead className="text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="p-3">Rank</th>
                  <th className="p-3">Strategy</th>
                  <th className="p-3">Pit Laps</th>
                  <th className="p-3">Expected</th>
                  <th className="p-3">Gap</th>
                  <th className="p-3">Confidence</th>
                  <th className="p-3">Risk</th>
                </tr>
              </thead>
              <tbody>
                {strategy.strategies.map((item) => (
                  <tr key={item.strategy_id} className="border-t border-white/10">
                    <td className="p-3 font-black">P{item.projected_finish}</td>
                    <td className="p-3">{strategyLabel(item.stints)}</td>
                    <td className="p-3">{item.pit_laps.join(", ") || "none"}</td>
                    <td className="p-3">{formatRaceTime(item.expected_race_time_seconds)}</td>
                    <td className="p-3">{item.expected_race_time_seconds === leader ? "leader" : `+${(item.expected_race_time_seconds - leader).toFixed(3)}s`}</td>
                    <td className="p-3">{Math.round(item.confidence * 100)}%</td>
                    <td className="p-3"><StatusPill tone={item.risk === "HIGH" ? "red" : item.risk === "MEDIUM" ? "yellow" : "green"}>{item.risk}</StatusPill></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>
        </div>
      ) : null}
    </div>
  );
}
