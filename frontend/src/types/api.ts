export type TyreCompound = "SOFT" | "MEDIUM" | "HARD" | "INTERMEDIATE" | "WET";
export type Risk = "LOW" | "MEDIUM" | "HIGH";
export type Urgency = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
export type ScenarioType =
  | "RAIN_INTENSITY_INCREASE"
  | "RAIN_ARRIVES_EARLIER"
  | "DEGRADATION_INCREASE"
  | "TRACK_WETNESS_STAYS_LOW";
export type RaceStatus =
  | "READY"
  | "RUNNING"
  | "SAFETY_CAR"
  | "VIRTUAL_SAFETY_CAR"
  | "FINISHED"
  | "ABORTED";
export type LiveActionType = "STAY_OUT" | "PIT" | "FOLLOW_RECOMMENDATION";
export type DriverRaceStatus = "RUNNING" | "PITTING" | "FINISHED";
export type DriverStrategyMode = "MANUAL" | "AI";
export type RaceEventType =
  | "SAFETY_CAR"
  | "VIRTUAL_SAFETY_CAR"
  | "DRYING_TRACK"
  | "RAIN_INCREASE"
  | "RAIN_DECREASE"
  | "TRACK_TEMPERATURE_CHANGE"
  | "TYRE_CROSSOVER";

export interface CircuitConfig {
  circuit_name: string;
  total_laps: number;
  base_lap_time_seconds: number;
  pit_lane_time_loss_seconds: number;
  avg_track_temp: number;
  avg_air_temp: number;
}

export interface RaceConfig {
  circuit: CircuitConfig;
  starting_compound: TyreCompound;
  starting_fuel_kg: number;
  weather_seed_state: number;
  safety_car_base_probability: number;
}

export interface CircuitRead {
  id: number;
  name: string;
  country: string;
  city: string;
  total_laps: number;
  base_lap_time_seconds: number;
  pit_lane_time_loss_seconds: number;
  avg_track_temp: number;
  avg_air_temp: number;
  track_length_km: number;
  tyre_wear_factor: number;
  overtaking_difficulty: number;
  safety_car_factor: number;
}

export interface WeatherState {
  lap_number: number;
  rain_probability: number;
  rain_intensity: number;
  track_temperature: number;
  air_temperature: number;
  track_wetness: number;
}

export interface LapResult {
  lap_number: number;
  lap_time_seconds: number;
  compound: TyreCompound;
  tyre_age: number;
  tyre_life_percent: number;
  fuel_remaining_kg: number;
  track_temperature: number;
  air_temperature: number;
  rain_probability: number;
  track_wetness: number;
  cumulative_race_time: number;
}

export interface PitStop {
  lap_number: number;
  old_compound: TyreCompound;
  new_compound: TyreCompound;
  pit_time_loss_seconds: number;
}

export interface PitInstruction {
  lap: number;
  compound: TyreCompound;
}

export interface RaceResult {
  total_laps: number;
  completed_laps: number;
  final_race_time_seconds: number;
  final_compound: TyreCompound;
  final_tyre_age: number;
  final_fuel_remaining_kg: number;
  lap_results: LapResult[];
  pit_stops: PitStop[];
  weather_history: WeatherState[];
}

export interface StrategyStint {
  compound: TyreCompound;
  start_lap: number;
  end_lap: number;
}

export interface StrategyResult {
  strategy_id: string;
  stints: StrategyStint[];
  pit_laps: number[];
  expected_race_time_seconds: number;
  pit_stop_count: number;
  projected_finish: number;
  confidence: number;
  risk: Risk | string;
  recommendation_reason: string;
}

export interface StrategyAnalysisResponse {
  recommended_strategy: StrategyResult | null;
  strategies: StrategyResult[];
}

export interface RaceContext {
  current_lap: number;
  total_laps: number;
  current_compound: TyreCompound;
  tyre_age: number;
  fuel_remaining_kg: number;
  track_wetness: number;
  rain_probability: number;
  rain_intensity: number;
  track_temperature: number;
  air_temperature: number;
  current_position?: number | null;
  gap_ahead_seconds?: number | null;
  gap_behind_seconds?: number | null;
  opponent_strategies?: string[];
  safety_car_status?: string | null;
  relative_tyre_state?: string | null;
  recent_lap_times: number[];
}

export interface EngineerResponse {
  decision: string;
  urgency: Urgency;
  explanation: string;
  key_factors: string[];
  estimated_time_gain_seconds: number | null;
  recommended_compound: TyreCompound | null;
  recommended_pit_lap: number | null;
  confidence: number | null;
  risk: string | null;
}

export interface ExplainStrategyRequest {
  race_config: RaceConfig;
  strategy_id?: string | null;
  context?: RaceContext | null;
}

export interface DecisionRequest {
  race_config: RaceConfig;
  context: RaceContext;
}

export interface ScenarioRequest {
  race_config: RaceConfig;
  scenario_type: ScenarioType;
  scenario_parameters: Record<string, unknown>;
}

export interface ScenarioResponse {
  baseline_strategy: string;
  scenario_strategy: string;
  baseline_race_time: number;
  scenario_race_time: number;
  time_difference: number;
  strategy_changed: boolean;
  key_changes: string[];
  engineer_explanation: EngineerResponse;
}

export interface RaceControlEvent {
  event_type: RaceEventType;
  lap: number;
  active: boolean;
  reason: string;
}

export interface RaceActionRecord {
  lap: number;
  recommended_action: string;
  user_action: LiveActionType;
  followed_recommendation: boolean;
  time_impact: number;
}

export interface RaceTimelineEntry {
  lap: number;
  entry_type: string;
  description: string;
}

export interface LiveRaceState {
  race_id: string;
  race_config: RaceConfig;
  current_lap: number;
  total_laps: number;
  current_compound: TyreCompound;
  tyre_age: number;
  fuel_remaining_kg: number;
  track_wetness: number;
  rain_probability: number;
  rain_intensity: number;
  track_temperature: number;
  air_temperature: number;
  current_race_time: number;
  pit_stop_count: number;
  race_status: RaceStatus;
  weather_seed_state: number;
  event_seed_state: number;
  history: LapResult[];
  weather_history: WeatherState[];
  events: RaceControlEvent[];
  actions: RaceActionRecord[];
  timeline: RaceTimelineEntry[];
  recommendation: EngineerResponse | null;
  strategy: StrategyResult | null;
  strategy_recalculation_count: number;
}

export interface LiveRaceStartResponse {
  race_id: string;
  race_state: LiveRaceState;
}

export interface LiveRaceAdvanceResponse {
  race_id: string;
  current_lap: number;
  total_laps: number;
  lap_result: LapResult | null;
  race_state: LiveRaceState;
  events: RaceControlEvent[];
  race_status: RaceStatus;
}

export interface LiveRaceAction {
  action: LiveActionType;
  compound?: TyreCompound | null;
}

export interface LiveRaceRecommendationResponse {
  race_id: string;
  recommendation: EngineerResponse;
  strategy: StrategyResult | null;
}

export interface DriverConfig {
  driver_id: string;
  driver_name: string;
  team_name: string;
  starting_compound: TyreCompound;
  starting_fuel_kg: number;
  pace_factor: number;
  degradation_factor: number;
  strategy_mode: DriverStrategyMode;
  strategy: PitInstruction[];
}

export interface MultiDriverRaceConfig {
  race_config: RaceConfig;
  drivers: DriverConfig[];
  event_seed_state: number;
}

export interface DriverLapResult {
  driver_id: string;
  lap_number: number;
  position: number;
  lap_time_seconds: number;
  compound: TyreCompound;
  tyre_age: number;
  tyre_life_percent: number;
  fuel_remaining_kg: number;
  pit_time_loss_seconds: number;
  race_status: DriverRaceStatus;
  cumulative_race_time: number;
}

export interface ClassificationEntry {
  position: number;
  driver_id: string;
  driver_name: string;
  team_name: string;
  completed_laps: number;
  total_race_time_seconds: number;
  gap_to_leader_seconds: number;
  pit_stop_count: number;
  final_compound: TyreCompound;
  final_strategy: PitInstruction[];
}

export interface LapClassification {
  lap_number: number;
  classification: ClassificationEntry[];
}

export interface DriverRaceResult {
  driver_id: string;
  driver_name: string;
  team_name: string;
  completed_laps: number;
  total_race_time_seconds: number;
  final_compound: TyreCompound;
  final_tyre_age: number;
  final_fuel_remaining_kg: number;
  pit_stop_count: number;
  final_strategy: PitInstruction[];
  lap_results: DriverLapResult[];
}

export interface OpponentStrategyInsight {
  driver_id: string;
  driver_name: string;
  current_tyre: TyreCompound;
  tyre_age: number;
  likely_pit_window_start: number | null;
  likely_pit_window_end: number | null;
  prediction_available: boolean;
}

export interface MultiDriverRaceResult {
  total_laps: number;
  shared_weather_history: WeatherState[];
  shared_events: RaceControlEvent[];
  driver_results: DriverRaceResult[];
  classification: ClassificationEntry[];
  classification_by_lap: LapClassification[];
  opponent_insights: OpponentStrategyInsight[];
  engineer_explanation: EngineerResponse | null;
}

export interface StrategyScenario {
  scenario_name: string;
  driver_id: string;
  strategy: PitInstruction[];
}

export interface StrategyComparisonRequest {
  base_config: MultiDriverRaceConfig;
  scenarios: StrategyScenario[];
}

export interface StrategyComparisonResult {
  scenario_name: string;
  driver_id: string;
  final_position: number;
  total_race_time_seconds: number;
  gap_to_leader_seconds: number;
  strategy: PitInstruction[];
  time_difference_seconds: number;
  position_difference: number;
}

export interface StrategyComparisonResponse {
  baseline: MultiDriverRaceResult;
  results: StrategyComparisonResult[];
}

export interface CounterfactualRequest {
  base_config: MultiDriverRaceConfig;
  driver_id: string;
  alternative_strategy: PitInstruction[];
}

export interface CounterfactualDriverSummary {
  position: number;
  race_time_seconds: number;
  gap_to_leader_seconds: number;
  strategy: PitInstruction[];
}

export interface CounterfactualResult {
  driver_id: string;
  baseline: CounterfactualDriverSummary;
  counterfactual: CounterfactualDriverSummary;
  time_difference_seconds: number;
  position_difference: number;
  weather_identical: boolean;
  events_identical: boolean;
}

export type SeasonStatus = "CREATED" | "IN_PROGRESS" | "COMPLETED";
export type MomentumLabel = "IMPROVING" | "STABLE" | "DECLINING";

export interface SeasonCalendarRound {
  round_number: number;
  circuit_id: number;
}

export interface PointsSystem {
  points_by_position: Record<number, number>;
}

export interface SeasonCreateRequest {
  season_name: string;
  calendar: SeasonCalendarRound[];
  drivers: DriverConfig[];
  points_system: PointsSystem;
  weather_seed: number;
  event_seed: number;
  safety_car_base_probability: number;
  allow_duplicate_circuits: boolean;
}

export interface DriverStandingResponse {
  position: number;
  driver_id: string;
  driver_name: string;
  team_name: string;
  points: number;
  wins: number;
  podiums: number;
  races: number;
  best_finish: number | null;
  average_finish: number | null;
  total_race_time: number;
  momentum: MomentumLabel;
  points_history: number[];
  position_history: number[];
}

export interface ConstructorStandingResponse {
  position: number;
  team_name: string;
  points: number;
  wins: number;
  podiums: number;
  races: number;
  momentum: MomentumLabel;
  points_history: number[];
}

export interface SeasonRaceSummary {
  round_number: number;
  circuit_id: number;
  circuit_name: string;
  completed: boolean;
  winner_driver_id: string | null;
  winner_driver_name: string | null;
}

export interface StrategySeasonMetric {
  strategy_label: string;
  races: number;
  average_position: number;
  average_race_time: number;
  wins: number;
  podiums: number;
  average_pit_stops: number;
}

export interface DriverSeasonAnalysis {
  driver_id: string;
  driver_name: string;
  average_race_position: number | null;
  wins: number;
  podiums: number;
  points_per_race: number;
  best_circuit: string | null;
  worst_circuit: string | null;
}

export interface SeasonAnalyticsResponse {
  strategy_metrics: StrategySeasonMetric[];
  most_successful_strategy: StrategySeasonMetric | null;
  average_pit_stops: number;
  driver_analysis: DriverSeasonAnalysis[];
  momentum_method: string;
}

export interface SeasonResponse {
  id: number;
  season_name: string;
  current_round: number;
  total_rounds: number;
  status: SeasonStatus;
  calendar: SeasonRaceSummary[];
  driver_standings: DriverStandingResponse[];
  constructor_standings: ConstructorStandingResponse[];
  analytics: SeasonAnalyticsResponse;
}

export interface SeasonStandingsResponse {
  drivers: DriverStandingResponse[];
  constructors: ConstructorStandingResponse[];
}

export interface SeasonRaceResult {
  season: SeasonResponse;
  race_result: MultiDriverRaceResult | null;
}

export interface SeasonScenarioRequest {
  driver_id: string;
  round_number: number;
  hypothetical_position: number;
}

export interface SeasonScenarioStandingDelta {
  driver_id: string;
  baseline_position: number;
  scenario_position: number;
  baseline_points: number;
  scenario_points: number;
  points_difference: number;
  position_difference: number;
}

export interface SeasonScenarioResponse {
  hypothetical: boolean;
  baseline_standings: DriverStandingResponse[];
  scenario_standings: DriverStandingResponse[];
  selected_driver_delta: SeasonScenarioStandingDelta;
  championship_leader_changed: boolean;
}

export interface ChampionshipProjectionEntry {
  driver_id: string;
  driver_name: string;
  championship_win_probability: number;
  expected_final_points: number;
  expected_final_position: number;
}

export interface ChampionshipProjectionResponse {
  simulations: number;
  methodology: string;
  seed_behavior: string;
  projections: ChampionshipProjectionEntry[];
}
