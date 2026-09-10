import type {
  CircuitConfig,
  CircuitRead,
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
};
