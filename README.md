# PitWall AI

AI-Powered Race Strategy Simulator for deterministic Formula 1 race strategy analysis.

## Features

- Deterministic race simulation
- Weather simulation and track wetness modeling
- Tyre degradation and tyre crossover detection
- Strategy optimization and confidence analysis
- Historical circuit intelligence
- AI Race Engineer fallback explanations
- Scenario analysis
- Interactive race dashboard
- Competitive multi-driver strategy lab
- Persistent championship season simulation

## Backend API Contract Discovered

The frontend uses the actual FastAPI implementation in `backend/app/routes` and `backend/app/schemas`.

| Method | Path | Request | Response |
|---|---|---|---|
| `GET` | `/health` | none | `{ status: string }` |
| `GET` | `/api/circuits` | none | `CircuitRead[]` |
| `GET` | `/api/circuits/{circuit_id}` | path `circuit_id` | `CircuitRead` |
| `GET` | `/api/circuits/{circuit_id}/config` | path `circuit_id` | `CircuitConfig` |
| `GET` | `/api/races?limit=&offset=` | optional query `limit`, `offset` | `HistoricalRaceRead[]` |
| `GET` | `/api/races/{race_id}` | path `race_id` | `HistoricalRaceRead` |
| `GET` | `/api/races/{race_id}/laps?limit=&offset=` | path `race_id`, optional query `limit`, `offset` | `HistoricalLapRead[]` |
| `GET` | `/api/races/{race_id}/pit-stops?limit=&offset=` | path `race_id`, optional query `limit`, `offset` | `HistoricalPitStopRead[]` |
| `POST` | `/api/simulation/validate` | `RaceConfig` | `{ valid, circuit, total_laps, starting_compound }` |
| `POST` | `/api/simulation/run` | `RaceConfig` | `RaceResult` |
| `POST` | `/api/strategy/analyze` | `RaceConfig` | `StrategyAnalysisResponse` |
| `POST` | `/api/race-engineer/explain-strategy` | `ExplainStrategyRequest` | `EngineerResponse` |
| `POST` | `/api/race-engineer/decision` | `DecisionRequest` | `EngineerResponse` |
| `POST` | `/api/race-engineer/scenario` | `ScenarioRequest` | `ScenarioResponse` |
| `POST` | `/api/live-race/start?event_seed_state=` | `RaceConfig` | `LiveRaceStartResponse` |
| `GET` | `/api/live-race/{race_id}` | path `race_id` | `LiveRaceState` |
| `POST` | `/api/live-race/{race_id}/advance` | path `race_id` | `LiveRaceAdvanceResponse` |
| `POST` | `/api/live-race/{race_id}/action` | `LiveRaceAction` | `LiveRaceState` |
| `POST` | `/api/live-race/{race_id}/pit?compound=` | path `race_id`, query `compound` | `LiveRaceState` |
| `POST` | `/api/live-race/{race_id}/recommendation` | path `race_id` | `LiveRaceRecommendationResponse` |
| `POST` | `/api/multi-race/simulate` | `MultiDriverRaceConfig` | `MultiDriverRaceResult` |
| `POST` | `/api/multi-race/compare-strategies` | `StrategyComparisonRequest` | `StrategyComparisonResponse` |
| `POST` | `/api/multi-race/counterfactual` | `CounterfactualRequest` | `CounterfactualResult` |
| `POST` | `/api/seasons` | `SeasonCreateRequest` | `SeasonResponse` |
| `GET` | `/api/seasons/{season_id}` | path `season_id` | `SeasonResponse` |
| `GET` | `/api/seasons/{season_id}/standings` | path `season_id` | `SeasonStandingsResponse` |
| `GET` | `/api/seasons/{season_id}/calendar` | path `season_id` | `SeasonRaceSummary[]` |
| `POST` | `/api/seasons/{season_id}/next-race` | path `season_id` | `SeasonRaceResult` |
| `POST` | `/api/seasons/{season_id}/simulate` | path `season_id` | `SeasonResponse` |
| `POST` | `/api/seasons/{season_id}/scenario` | `SeasonScenarioRequest` | `SeasonScenarioResponse` |
| `POST` | `/api/seasons/{season_id}/projection?simulations=` | path `season_id`, optional query `simulations` | `ChampionshipProjectionResponse` |

All frontend request and response types live in `frontend/src/types/api.ts` and preserve backend snake_case fields.

## Backend Assumptions Corrected

| Assumed | Actual | Frontend Implementation |
|---|---|---|
| Incremental live simulation API might exist | Only complete race endpoint exists: `POST /api/simulation/run` | Frontend replays returned `lap_results` locally |
| Crossover endpoint might exist | No standalone crossover route exists | Frontend displays crossover information inferred from backend strategy stints/reasons, no fabricated values |
| Scenario parameters might be fixed typed fields | Backend accepts `scenario_parameters: dict[str, Any]` | Frontend sends only supported known parameter keys for each `ScenarioType` |
| Live race routes might already exist | No live-race session routes existed | Added `/api/live-race/*` routes using existing `RaceConfig`, deterministic weather, tyre model, strategy engine, and race engineer |
| Multi-driver routes might exist | No multi-driver simulation or comparison endpoints existed | Added `/api/multi-race/*` routes and separate schemas without changing `RaceConfig` |
| Multi-driver weather could be generated per driver | Existing weather was single-driver and seeded per simulation | Added `RaceEnvironmentService` so weather and Safety Car/VSC events are generated once and shared by all drivers |
| Competitive race engineer might calculate projections itself | Existing engineer is explanation-only | Competitive result includes deterministic positions/gaps from simulation; engineer text explains those values |
| Season routes might already exist | No championship routes existed | Added `/api/seasons/*` using the existing FastAPI router and `db: Session = Depends(get_db)` pattern |
| Season persistence could reuse historical race models | Historical models are read-oriented seed data | Added dedicated season tables for persistent championship state |
| Calendar could include arbitrary circuit names | Real circuit data currently comes from `/api/circuits` seeded with Monza, Silverstone, and Monaco | Season creation references real `circuit_id` values; duplicate circuits require explicit opt-in |
| Championship projections might be LLM estimates | The race engineer layer is explanation-only | Projection endpoint uses deterministic replayed season simulations with seeded perturbations |

## Live Race Mode

Live Race Mode adds an in-memory interactive race session on top of the deterministic engines.

Flow:

```text
POST /api/live-race/start
POST /api/live-race/{race_id}/action
POST /api/live-race/{race_id}/advance
POST /api/live-race/{race_id}/recommendation
```

Supported user actions:

- `STAY_OUT`
- `PIT` with `compound`
- `FOLLOW_RECOMMENDATION`

Race statuses:

- `READY`
- `RUNNING`
- `SAFETY_CAR`
- `VIRTUAL_SAFETY_CAR`
- `FINISHED`
- `ABORTED`

Safety Car and VSC are simulated deterministic race-control events. They slow lap times, reduce tyre/fuel consumption, and change pit economics. Events are marked as simulated and are not real-world incidents.

The frontend Live Race Control page advances one lap at a time using the backend endpoint. Auto-play only changes the delay between backend requests; it does not fake lap progression client-side.

## Competitive Strategy Lab

Competitive Strategy Lab adds deterministic multi-driver race simulation.

Core contract:

```text
MultiDriverRaceConfig
race_config: RaceConfig
drivers: DriverConfig[2..20]
event_seed_state: int
```

Each driver can define starting tyre, fuel, pace factor, degradation factor, strategy mode, and pit instructions. The original single-driver `RaceConfig` remains unchanged.

The backend generates one shared race environment per run:

- weather history
- track wetness and temperatures
- Safety Car and VSC events
- global race-control timeline

Every driver consumes the same environment. Driver outcomes differ only through driver-specific pace, fuel, degradation, and pit strategy. Classification is sorted by completed laps, elapsed race time, then stable driver ID.

Competitive APIs:

- `POST /api/multi-race/simulate` runs the full grid and returns classification, per-lap classification replay, driver lap results, shared weather, shared events, opponent insights, and a deterministic race engineer summary.
- `POST /api/multi-race/compare-strategies` runs alternative pit plans for a selected driver against the same baseline weather/events and other driver strategies.
- `POST /api/multi-race/counterfactual` changes only one selected driver's strategy and returns measured time and position impact, plus `weather_identical` and `events_identical` flags.

The frontend Competitive Lab uses the backend response directly. If a completed race is returned, the UI replays `classification_by_lap` instead of fabricating intermediate positions. Opponent pit-window text is shown only when the backend returns a prediction.

Measured local performance:

- single-driver 57 laps: `0.002756s`
- 2 drivers x 57 laps: `0.006027s`
- 5 drivers x 57 laps: `0.011499s`
- 10 drivers x 57 laps: `0.021819s`

Known limitations:

- Multi-driver sessions are complete-race simulations, not persisted live sessions.
- No garage queue or stochastic retirement model is implemented.
- Overtaking is represented by race-time classification, not wheel-to-wheel sector modeling.

## Championship Mode

Championship Mode adds persistent season state on top of the Phase 8 multi-driver simulator.

Core creation contract:

```text
SeasonCreateRequest
season_name: string
calendar: SeasonCalendarRound[2..30]
drivers: DriverConfig[2..20]
points_system: PointsSystem
weather_seed: int
event_seed: int
safety_car_base_probability: float
allow_duplicate_circuits: bool
```

New database tables:

- `seasons`
- `season_races`
- `season_driver_standings`
- `season_constructor_standings`

The season service runs races sequentially through the existing multi-driver simulator. Each round derives distinct deterministic weather and event seeds from the season seeds and round number, so the same season config reproduces the same calendar, race results, standings, events, and projections.

Season APIs:

- `POST /api/seasons` creates a persistent season from real circuit IDs.
- `POST /api/seasons/{season_id}/next-race` runs the next incomplete round and updates standings.
- `POST /api/seasons/{season_id}/simulate` runs all remaining rounds.
- `GET /api/seasons/{season_id}` returns complete season state, standings, calendar, and analytics.
- `GET /api/seasons/{season_id}/standings` returns driver and constructor standings.
- `GET /api/seasons/{season_id}/calendar` returns completed/upcoming calendar state.
- `POST /api/seasons/{season_id}/scenario` runs a non-mutating hypothetical points scenario.
- `POST /api/seasons/{season_id}/projection?simulations=` runs optional simulation-based title projection.

The default points system follows F1-style scoring: `25, 18, 15, 12, 10, 8, 6, 4, 2, 1`. It is centralized in `PointsSystem` and can be overridden in season creation.

Tracked driver standings:

- points
- wins
- podiums
- races
- best finish
- average finish
- total race time
- per-round points and position history
- deterministic momentum label

Tracked constructor standings:

- points
- wins
- podiums
- races
- per-round points history
- deterministic momentum label

Constructor points are derived from driver points and covered by tests. Team points equal the sum of all driver points for that team.

Momentum calculation:

```text
Use the last three race point scores.
last - first > 3  => IMPROVING
last - first < -3 => DECLINING
otherwise         => STABLE
```

Season analytics are based only on completed stored race results. They include strategy metrics, average pit stops, most successful strategy, and race-based driver analysis. Qualifying metrics are intentionally omitted because no qualifying simulation exists.

Championship scenarios are explicitly hypothetical and do not mutate the baseline season. They adjust a selected driver's points for a selected round/position and return baseline standings, scenario standings, points difference, position difference, and whether the championship leader changed.

Championship projection is optional and deterministic. Completed rounds remain fixed. Remaining rounds are replayed with seeded perturbations:

```text
projection run n:
weather_seed += n * 7919
event_seed   += n * 3571
```

Measured local performance:

- one season race: `0.039991s`
- 5-race season: `0.135091s`
- 10-race season: `0.346474s`

Known limitations:

- Season race results are persisted as JSON payloads, not normalized lap-by-lap tables.
- No qualifying model exists, so championship analytics are race-result based.
- Retirement scenarios are represented as controlled hypothetical points outcomes, not random failures.
- Projection uses deterministic perturbation runs and should be requested explicitly rather than run automatically on every page load.

## Backend

```powershell
cd backend
& "C:\Users\Sharan S P\AppData\Local\Programs\Python\Python312\python.exe" -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Environment:

```env
AI_PROVIDER=deterministic
LLM_API_KEY=
LLM_MODEL=
DATABASE_URL=sqlite:///./pitwall_ai.db
```

## Frontend

```powershell
cd frontend
npm install
npm run dev
```

Frontend environment:

```env
VITE_API_BASE_URL=http://localhost:8000
```

Production build:

```powershell
cd frontend
npm run build
```
