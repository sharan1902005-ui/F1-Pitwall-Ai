import type {
  CircuitConfig,
  CircuitRead,
  F1CircuitEventRead,
  F1CircuitRead,
  F1DriverRead,
  F1ConstructorRead,
  F1HistoricalAnalyticsRead,
  F1HistoricalResultRead,
  F1HistoricalSeasonSummary,
  F1QualifyingAnalyticsRead,
  F1QualifyingResultRead,
  F1StartingGridRead,
  F1HistoricalLapTimeRead,
  F1HistoricalPerformanceAnalyticsRead,
  F1SeasonAnalyticsRead,
  F1HistoricalPitStopRead,
  F1HistoricalWeatherObservationRead,
  F1HistoricalWeatherSummaryRead,
  F1HistoricalStrategyBenchmarkRead,
  DecisionRequest,
  EngineerResponse,
  ExplainStrategyRequest,
  LiveRaceAction,
  LiveRaceAdvanceResponse,
  LiveRaceRecommendationResponse,
  LiveRaceStartResponse,
  LiveRaceState,
  CounterfactualRequest,
  CounterfactualResult,
  MultiDriverRaceConfig,
  MultiDriverRaceResult,
  RaceConfig,
  RaceResult,
  ScenarioRequest,
  ScenarioResponse,
  ChampionshipProjectionResponse,
  SeasonCreateRequest,
  SeasonRaceResult,
  SeasonResponse,
  SeasonScenarioRequest,
  SeasonScenarioResponse,
  SeasonStandingsResponse,
  StrategyComparisonRequest,
  StrategyComparisonResponse,
  StrategyAnalysisResponse,
  UndercutRequest,
  UndercutResponse,
  OvercutRequest,
  OvercutResponse,
  PitWindowRequest,
  PitWindowResponse,
  OpponentPredictionRequest,
  OpponentPredictionResponse,
  TrafficRequest,
  TrafficResponse,
  StrategyRiskRequest,
  StrategyRiskResponse,
} from "../types/api";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  detail: unknown;

  constructor(message: string, status: number, detail: unknown) {
    super(message);
    this.status = status;
    this.detail = detail;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    ...init,
  });

  const text = await response.text();
  const data = text ? JSON.parse(text) : null;
  if (!response.ok) {
    throw new ApiError(readableError(data), response.status, data);
  }
  return data as T;
}

function readableError(data: unknown): string {
  if (typeof data === "object" && data && "detail" in data) {
    const detail = (data as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
    return "The backend rejected this request. Check the race configuration.";
  }
  return "The backend is unavailable or returned an unexpected response.";
}

export const api = {
  health: () => request<{ status: string }>("/health"),
  listCircuits: () => request<CircuitRead[]>("/api/circuits"),
  getCircuitConfig: (id: number) => request<CircuitConfig>(`/api/circuits/${id}/config`),
  listImportedCircuits: (filters: { search?: string; country?: string } = {}) => {
    const query = new URLSearchParams();
    if (filters.search) query.set("search", filters.search);
    if (filters.country) query.set("country", filters.country);
    const suffix = query.size ? `?${query}` : "";
    return request<F1CircuitRead[]>(`/api/f1-data/circuits${suffix}`);
  },
  getImportedCircuitEvents: (id: number) => request<F1CircuitEventRead[]>(`/api/f1-data/circuits/${id}/events`),
  listDrivers: () => request<F1DriverRead[]>("/api/f1-data/drivers?limit=200"),
  listConstructors: () => request<F1ConstructorRead[]>("/api/f1-data/constructors?limit=200"),
  listHistoricalResultSeasons: () => request<F1HistoricalSeasonSummary[]>("/api/f1-data/historical-results/seasons"),
  listHistoricalResultEvents: (season: number) => request<F1CircuitEventRead[]>(`/api/f1-data/historical-results/events?season=${season}`),
  listHistoricalResults: (filters: { season?: number; eventId?: number; driverId?: number; constructorId?: number; circuitId?: number; search?: string; limit?: number; offset?: number } = {}) => {
    const query = new URLSearchParams(); if (filters.season) query.set("season", String(filters.season)); if (filters.eventId) query.set("event_id", String(filters.eventId)); if (filters.driverId) query.set("driver_id", String(filters.driverId)); if (filters.constructorId) query.set("constructor_id", String(filters.constructorId)); if (filters.circuitId) query.set("circuit_id", String(filters.circuitId)); if (filters.search) query.set("search", filters.search); if (filters.limit) query.set("limit", String(filters.limit)); if (filters.offset) query.set("offset", String(filters.offset));
    return request<F1HistoricalResultRead[]>(`/api/f1-data/historical-results${query.size ? `?${query}` : ""}`);
  },
  historicalAnalytics: (season: number) => request<F1HistoricalAnalyticsRead>(`/api/f1-data/historical-results/analytics/${season}`),
  listQualifying: (season: number, eventId?: number) => request<F1QualifyingResultRead[]>(`/api/f1-data/qualifying?season=${season}${eventId ? `&event_id=${eventId}` : ""}`),
  getStartingGrid: (eventId: number) => request<F1StartingGridRead[]>(`/api/f1-data/starting-grids/${eventId}`),
  qualifyingAnalytics: (season: number) => request<F1QualifyingAnalyticsRead>(`/api/f1-data/qualifying/analytics/${season}`),
  listLapTimes: (eventId: number, driverId?: number) => request<F1HistoricalLapTimeRead[]>(`/api/f1-data/lap-times/${eventId}?limit=200${driverId ? `&driver_id=${driverId}` : ""}`),
  listPitStops: (eventId: number, driverId?: number) => request<F1HistoricalPitStopRead[]>(`/api/f1-data/pit-stops/${eventId}?limit=100${driverId ? `&driver_id=${driverId}` : ""}`),
  performanceAnalytics: (eventId: number, driverId?: number) => request<F1HistoricalPerformanceAnalyticsRead>(`/api/f1-data/performance/analytics/${eventId}${driverId ? `?driver_id=${driverId}` : ""}`),
  seasonHistoricalAnalytics: (season: number) => request<F1SeasonAnalyticsRead>(`/api/f1-data/analytics/seasons/${season}`),
  listHistoricalWeather: (eventId: number, sessionKey?: number) => request<F1HistoricalWeatherObservationRead[]>(`/api/f1-data/historical-weather?event_id=${eventId}&limit=2000${sessionKey ? `&session_key=${sessionKey}` : ""}`),
  historicalWeatherSummary: (eventId: number, sessionKey?: number) => request<F1HistoricalWeatherSummaryRead>(`/api/f1-data/historical-weather/events/${eventId}/summary${sessionKey ? `?session_key=${sessionKey}` : ""}`),
  historicalStrategyBenchmark: (filters: { season?: number; eventId?: number; circuitId?: number } = {}) => {
    const query = new URLSearchParams();
    if (filters.season !== undefined) query.set("season", String(filters.season));
    if (filters.eventId !== undefined) query.set("event_id", String(filters.eventId));
    if (filters.circuitId !== undefined) query.set("circuit_id", String(filters.circuitId));
    return request<F1HistoricalStrategyBenchmarkRead>(`/api/f1-data/strategy-benchmark${query.size ? `?${query}` : ""}`);
  },
  runSimulation: (config: RaceConfig) =>
    request<RaceResult>("/api/simulation/run", {
      method: "POST",
      body: JSON.stringify(config),
    }),
  analyzeStrategy: (config: RaceConfig) =>
    request<StrategyAnalysisResponse>("/api/strategy/analyze", {
      method: "POST",
      body: JSON.stringify(config),
    }),
  explainStrategy: (body: ExplainStrategyRequest) =>
    request<EngineerResponse>("/api/race-engineer/explain-strategy", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  decision: (body: DecisionRequest) =>
    request<EngineerResponse>("/api/race-engineer/decision", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  scenario: (body: ScenarioRequest) =>
    request<ScenarioResponse>("/api/race-engineer/scenario", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  startLiveRace: (config: RaceConfig, eventSeedState = 0) =>
    request<LiveRaceStartResponse>(`/api/live-race/start?event_seed_state=${eventSeedState}`, {
      method: "POST",
      body: JSON.stringify(config),
    }),
  getLiveRace: (raceId: string) => request<LiveRaceState>(`/api/live-race/${raceId}`),
  advanceLiveRace: (raceId: string) =>
    request<LiveRaceAdvanceResponse>(`/api/live-race/${raceId}/advance`, {
      method: "POST",
    }),
  submitLiveAction: (raceId: string, action: LiveRaceAction) =>
    request<LiveRaceState>(`/api/live-race/${raceId}/action`, {
      method: "POST",
      body: JSON.stringify(action),
    }),
  liveRecommendation: (raceId: string) =>
    request<LiveRaceRecommendationResponse>(`/api/live-race/${raceId}/recommendation`, {
      method: "POST",
    }),
  simulateMultiRace: (config: MultiDriverRaceConfig) =>
    request<MultiDriverRaceResult>("/api/multi-race/simulate", {
      method: "POST",
      body: JSON.stringify(config),
    }),
  compareStrategies: (body: StrategyComparisonRequest) =>
    request<StrategyComparisonResponse>("/api/multi-race/compare-strategies", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  counterfactual: (body: CounterfactualRequest) =>
    request<CounterfactualResult>("/api/multi-race/counterfactual", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  createSeason: (body: SeasonCreateRequest) =>
    request<SeasonResponse>("/api/seasons", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  getSeason: (seasonId: number) => request<SeasonResponse>(`/api/seasons/${seasonId}`),
  getSeasonStandings: (seasonId: number) =>
    request<SeasonStandingsResponse>(`/api/seasons/${seasonId}/standings`),
  runNextSeasonRace: (seasonId: number) =>
    request<SeasonRaceResult>(`/api/seasons/${seasonId}/next-race`, {
      method: "POST",
    }),
  simulateSeason: (seasonId: number) =>
    request<SeasonResponse>(`/api/seasons/${seasonId}/simulate`, {
      method: "POST",
    }),
  seasonScenario: (seasonId: number, body: SeasonScenarioRequest) =>
    request<SeasonScenarioResponse>(`/api/seasons/${seasonId}/scenario`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  championshipProjection: (seasonId: number, simulations = 20) =>
    request<ChampionshipProjectionResponse>(`/api/seasons/${seasonId}/projection?simulations=${simulations}`, {
      method: "POST",
    }),
  analyzeUndercut: (body: UndercutRequest) =>
    request<UndercutResponse>("/api/strategy/undercut", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  analyzeOvercut: (body: OvercutRequest) =>
    request<OvercutResponse>("/api/strategy/overcut", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  analyzePitWindow: (body: PitWindowRequest) =>
    request<PitWindowResponse>("/api/strategy/pit-window", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  predictOpponent: (body: OpponentPredictionRequest) =>
    request<OpponentPredictionResponse>("/api/strategy/opponent-prediction", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  analyzeTraffic: (body: TrafficRequest) =>
    request<TrafficResponse>("/api/strategy/traffic", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  analyzeStrategyRisk: (body: StrategyRiskRequest) =>
    request<StrategyRiskResponse>("/api/strategy/risk", {
      method: "POST",
      body: JSON.stringify(body),
    }),
};
