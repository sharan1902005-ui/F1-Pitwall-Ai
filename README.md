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
| `GET` | `/api/f1-data/drivers?search=&limit=&offset=` | optional query `search`, `limit`, `offset` | `F1DriverRead[]` |
| `GET` | `/api/f1-data/drivers/{driver_id}` | path `driver_id` | `F1DriverRead` |
| `GET` | `/api/f1-data/constructors?search=&limit=&offset=` | optional query `search`, `limit`, `offset` | `F1ConstructorRead[]` |
| `GET` | `/api/f1-data/constructors/{constructor_id}` | path `constructor_id` | `F1ConstructorRead` |
| `GET` | `/api/f1-data/seasons/{season}/drivers?limit=&offset=` | path `season`, optional query `limit`, `offset` | `F1DriverRead[]` |
| `GET` | `/api/f1-data/seasons/{season}/constructors?limit=&offset=` | path `season`, optional query `limit`, `offset` | `F1ConstructorRead[]` |
| `GET` | `/api/f1-data/seasons/{season}/driver-constructor-associations?limit=&offset=` | path `season`, optional query `limit`, `offset` | `F1DriverConstructorSeasonRead[]` |
| `GET` | `/api/f1-data/circuits?search=&country=&limit=&offset=` | optional query filters | `F1CircuitRead[]` |
| `GET` | `/api/f1-data/circuits/{circuit_id}` | path `circuit_id` | `F1CircuitRead` |
| `GET` | `/api/f1-data/circuits/provider/{provider_circuit_id}` | path `provider_circuit_id` | `F1CircuitRead` |
| `GET` | `/api/f1-data/circuits/{circuit_id}/events?season=&limit=&offset=` | path `circuit_id`, optional filters | `F1CircuitEventRead[]` |
| `GET` | `/api/f1-data/strategy-benchmark?season=&event_id=&circuit_id=` | optional imported-data filters | `F1HistoricalStrategyBenchmarkRead` |
| `GET` | `/api/f1-data/historical-results/seasons` | none | `F1HistoricalSeasonSummary[]` |
| `GET` | `/api/f1-data/historical-results/events?season=` | required query `season` | `F1CircuitEventRead[]` |
| `GET` | `/api/f1-data/historical-results?event_id=&driver_id=&constructor_id=&circuit_id=&search=&limit=&offset=` | optional filters | `F1HistoricalResultRead[]` |
| `GET` | `/api/f1-data/historical-results/{result_id}` | path `result_id` | `F1HistoricalResultRead` |
| `GET` | `/api/f1-data/historical-results/analytics/{season}` | optional `driver_id`, `constructor_id` | `F1HistoricalAnalyticsRead` |
| `GET` | `/api/f1-data/qualifying?season=&event_id=&driver_id=&limit=&offset=` | required `season`, optional filters | `F1QualifyingResultRead[]` |
| `GET` | `/api/f1-data/qualifying/analytics/{season}` | optional `driver_id`, `constructor_id` | `F1QualifyingAnalyticsRead` |
| `GET` | `/api/f1-data/starting-grids/{event_id}` | path `event_id` | `F1StartingGridRead[]` |
| `GET` | `/api/f1-data/lap-times/{event_id}?driver_id=&lap_from=&lap_to=&limit=&offset=` | path `event_id`, optional filters | `F1HistoricalLapTimeRead[]` |
| `GET` | `/api/f1-data/pit-stops/{event_id}?driver_id=&limit=&offset=` | path `event_id`, optional filters | `F1HistoricalPitStopRead[]` |
| `GET` | `/api/f1-data/performance/analytics/{event_id}?driver_id=` | path `event_id`, optional filter | `F1HistoricalPerformanceAnalyticsRead` |
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

## External F1 Data Provider

Phase 11.2 introduces an isolated, key-free [Jolpica F1 API](https://github.com/jolpica/jolpica-f1/blob/main/docs/README.md) client. It is a provider boundary only: it does not ingest or persist data, add API routes, alter `/health`, or change the simulation engine. Phase 11.3 will define the explicit import and mapping workflow.

Install the backend dependencies before running the service or provider-client tests:

```powershell
cd backend
python -m pip install -r requirements.txt
```

Copy `backend/.env.example` into your local backend environment file and configure the documented settings as needed:

```text
F1_DATA_PROVIDER=jolpica
JOLPICA_BASE_URL=https://api.jolpi.ca
JOLPICA_USER_AGENT=PitWallAI/0.1.0
JOLPICA_CONNECT_TIMEOUT_SECONDS=3
JOLPICA_READ_TIMEOUT_SECONDS=10
JOLPICA_RETRY_LIMIT=2
JOLPICA_MAX_RETRY_DELAY_SECONDS=5
JOLPICA_PAGE_SIZE=100
JOLPICA_MAX_PAGES=100
```

Jolpica has no API-key configuration for this client. The client uses its documented `/ergast/f1/seasons/` endpoint for an explicit programmatic connectivity check and returns unavailable when that request or payload validation fails. It sends the configured `User-Agent`, validates JSON payload shapes, follows documented pagination (maximum 100 records per request), and performs bounded retries for `429`, `500`, `502`, `503`, and `504` responses.

Jolpica documents unauthenticated limits of four requests per second in bursts and 500 requests per hour sustained. The client respects `Retry-After` when supplied, but this is not a caching or ingestion system; callers should batch work and avoid repeated polling. Historical provider records are not live telemetry, and current-season completeness depends on the provider dataset.

## F1 Ingestion Preparation

Phase 11.3 adds `F1IngestionEngine`, a non-persistent boundary between the Jolpica client and future database import mappers. An `IngestionRequest` selects datasets and optionally scopes a season and round. The engine retrieves each provider source once per operation, normalizes validated records into `NormalizedRecord` values, retains raw provider data and identifiers, and produces per-dataset counts and rejected-record details.

Prepared Jolpica datasets are seasons, circuits, drivers, constructors, race events, race results, qualifying results, starting grids, lap timings, and pit stops. Race events and grids are derived from documented race-result records, avoiding duplicate provider requests. Historical weather and track conditions are explicitly unsupported because Jolpica does not expose them; they are reported as unsupported, never synthesized.

This phase does not persist external data, modify existing historical tables, create routes, or change simulation behavior. Future import phases must map normalized records into approved storage models. Jolpica lap data begins in 1996 and pit-stop data in 2011, so empty responses must remain distinct from zero-valued race statistics.

## Driver And Constructor Reference Data

Phase 11.4 persists real provider-backed driver and constructor profiles separately from simulated championship data. The `f1_drivers` and `f1_constructors` tables retain each source identifier, and `f1_driver_constructor_seasons` preserves every observed driver-constructor pairing by real season with its first and last observed race round. This allows a driver to change teams across seasons without overwriting historical affiliations.

Read-only APIs are available under `/api/f1-data`: drivers and constructors support `search`, `limit`, and `offset`; individual records use internal IDs; and `/api/f1-data/seasons/{season}/...` exposes season drivers, constructors, and driver-constructor associations. Import remains a backend service operation so routine read APIs never trigger external provider calls.

Jolpica driver and constructor profile records are global rather than roster snapshots. Season associations are therefore created only from provider race-result records. Reserve drivers without classified result records, team metadata beyond the documented constructor fields, and country codes unavailable from provider profiles are intentionally not inferred.

## Circuit Reference Data

Phase 11.5 adds real circuit reference records in `f1_circuits` and historical race-event links in `f1_circuit_events`. They are deliberately separate from the existing simulator `circuits` table and its `CircuitConfig`; imported coordinates, locations, and names never derive laps, lap time, pit loss, or temperatures. Race Setup may apply a selected real circuit name while leaving every simulation parameter under user control.

Jolpica documents circuit names, IDs, URLs, locations, and coordinates. It does not supply verified track lengths, corner counts, circuit type, layouts, or maps, so PitWall does not display or synthesize those fields. Event links use provider race-result metadata and preserve distinct event names at the same circuit across seasons.

## Historical Results

Phase 11.6 stores provider-backed race classifications in `f1_historical_race_results`, linked to imported event, circuit, driver, and constructor records. Results are insert-only: repeat imports skip the same source/event/driver record, retaining non-finishes, disqualifications, null positions, optional race times, and fastest-lap information exactly as supplied. This is distinct from the simulator's seed-only `historical_races` endpoints.

The Historical Race Explorer reads `/api/f1-data/historical-results` and labels records as imported historical data. Its analytics use only rows currently stored for the selected season and report the number of events used; an imported subset is never represented as a complete championship season.

## Qualifying And Starting Grids

Phase 11.7 stores qualifying classifications in `f1_qualifying_results` and official race-result grid positions in `f1_starting_grids`. The tables are intentionally separate: qualifying position is never used as a substitute for grid position. Q1, Q2, and Q3 times are optional because Jolpica data spans historical formats. The provider result payload does not supply explicit penalty or grid-status fields, so PitWall reports only observed qualifying-to-grid differences and never labels one as a penalty.

## Historical Lap Times And Pit Stops

Phase 11.8 persists documented lap observations in `f1_historical_lap_times` and pit observations in `f1_historical_pit_stops`. They are event-scoped, insert-only records linked to an imported driver and event. Lap data is available from 1996 and pit-stop data from 2011 in Jolpica. The provider lap endpoint has no sectors or timing status, and its pit-stop endpoint has no constructor or pit-out timing; these fields are not synthesized. Pit-stop duration is the provider-recorded stop duration, never a simulated pit-lane time loss.

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

### Live Simulation Race Classification

The original `/api/simulation/run` and `/api/live-race` contracts simulate one car and do not produce a grid, race position, gaps, or a finishing classification. Opponent-pit prediction is a pit-window estimate for one supplied opponent state; it is not a competing-car simulation. Provider-backed historical classifications are stored separately and are not used as live simulation results.

The existing `/api/multi-race/simulate` endpoint does simulate an actual configured grid of 2–20 competitors in shared weather and race-control conditions. Its per-lap and final classifications are now passed from Competitive Lab to Live Simulation. The Live Simulation panel displays them only when the competitive run's `RaceConfig` matches the current configuration; position changes, gaps, status, and final position come from that run's classification and lap results. It does not generate competitors or estimate standings for a single-car run.

The multi-driver model currently classifies RUNNING, PITTING, and FINISHED states. It has no retirement/DNF model, so it cannot produce genuine DNF classifications. Competitive runs remain complete-race, in-memory simulations rather than interactive live-grid sessions.

### Dynamic Lap-by-Lap Leaderboard

The backend `MultiDriverRaceResult` already contains `classification_by_lap`: one `LapClassification` snapshot per lap, each sorted by cumulative race time at that lap. No backend changes were required.

The Live Simulation leaderboard reads the snapshot for the current replay lap directly from `classification_by_lap`. Positions, gaps, and position deltas are all derived from genuine cumulative race-time ordering — not from the final classification. A driver who pits on lap 8 will appear lower in the leaderboard on that lap because their cumulative time increases by the pit-lane time loss; they may recover position on subsequent laps as their fresh tyres produce faster lap times.

The position history chart plots each driver's position at every completed replay lap, using `classification_by_lap` data. The Y-axis is inverted (P1 at top). Each driver has a stable colour. The focused driver's line is drawn thicker.

The Δ column in the leaderboard table shows position gained (▲, green) or lost (▼, red) relative to the previous lap. This is computed from consecutive `classification_by_lap` snapshots and reflects only genuine timing changes.

Replay controls:

- Play/Pause: start or freeze the lap-index timer; the leaderboard freezes at the paused lap.
- Restart: resets `lapIndex` to 0, showing lap 1 classification.
- Timeline slider: dragging to any lap shows that lap's exact classification snapshot.
- Speed: changes the timer interval only; race results are unchanged.

The same lap always produces the same classification for a given race result because `classification_by_lap` is deterministic and immutable once computed.

Test coverage (`backend/tests/test_lap_by_lap_classification.py`, 17 tests):

- Every lap has a classification snapshot.
- Every driver appears in every snapshot.
- Positions are 1-indexed and unique per lap.
- P1 always has the lowest cumulative time.
- Leader gap is always 0.0.
- `gap_to_leader_seconds` equals the cumulative time difference.
- The faster driver leads throughout.
- A driver loses position on their pit lap.
- At least one position change occurs across the race.
- Cumulative time increases monotonically per driver.
- Forward and backward replay return correct snapshots.
- Restart returns lap 1 classification.
- Final classification matches the last lap snapshot.
- Same seed produces identical per-lap classifications.
- Different seeds produce valid full-race results.
- 57-lap 2-driver run completes in under 0.5s (warm time ~4ms).

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

## Weather-Aware Environmental Events And Strategy Decisions

Live Race Control now generates and displays environmental events derived from the actual simulated weather variables. No decorative or fabricated conditions are used.

### Simulated variables

The `WeatherEngine` produces these variables per lap:

| Variable | Type | Notes |
|---|---|---|
| `track_temperature` | float (°C) | Derived from `avg_track_temp` + sinusoidal wave − rain cooling |
| `air_temperature` | float (°C) | Derived from `avg_air_temp` + sinusoidal wave − rain cooling |
| `rain_probability` | float 0–1 | Trend + noise, seeded |
| `rain_intensity` | float 0–1 | Derived from rain probability |
| `track_wetness` | float 0–1 | Accumulates from rain, dries between laps |

Cloud cover, wind speed, wind direction, humidity, and tyre temperature are not simulated. No events or recommendations reference them.

### Environmental event types

New event types added to `RaceEventType`:

| Event | Trigger |
|---|---|
| `HOT_TRACK` | `track_temperature` ≥ `avg_track_temp` + 6°C |
| `TRACK_TEMP_RISING` | lap-to-lap delta ≥ +4°C |
| `TRACK_TEMP_FALLING` | lap-to-lap delta ≤ −4°C |
| `RAIN_DECREASE` | wetness delta ≤ −0.08 (previously only `DRYING_TRACK` was emitted) |
| `HIGH_TYRE_DEGRADATION_RISK` | tyre life ≤ 25% |
| `PIT_WINDOW_OPEN` | race fraction 28–32% |
| `PIT_WINDOW_CLOSING` | race fraction 65–70% |

Existing event types retained: `SAFETY_CAR`, `VIRTUAL_SAFETY_CAR`, `DRYING_TRACK`, `RAIN_INCREASE`, `TRACK_TEMPERATURE_CHANGE`, `TYRE_CROSSOVER`.

All events are deduplicated: the same event type cannot fire again within 3 laps of its previous emission. A genuine second transition after the gap is allowed.

### Weather-aware AI Race Engineer

The `DeterministicRaceEngineerProvider` now produces weather-aware key factors and explanations when a `RaceContext` is available:

- Elevated track temperature (≥ +6°C above average): explains degradation impact and pit window consideration.
- Moderate temperature rise (≥ +3°C): flags tyre wear monitoring.
- Falling temperature (≤ −4°C): notes reduced degradation and wet-tyre crossover threshold effect.
- Rain intensity ≥ 0.3: flags Intermediate/Wet crossover evaluation.
- Track wetness ≥ 0.45: explains slick-tyre performance penalty.
- Track wetness 0.15–0.45: notes slick viability with rain monitoring.
- Cool air temperature: notes slower track drying.

All values cited in explanations are the actual simulated values at that lap. No conditions are inferred or synthesized.

### Live Race Control UI

The Events and Decisions panel now:

- Categorises events as WEATHER, TYRE STRATEGY, PIT STRATEGY, or RACE CONDITIONS.
- Provides category filter tabs.
- Shows event icon, category label, lap number, title, measured value (from the reason string), and strategic consequence.
- Uses distinct colour coding: blue for rain, red for hot/degradation, yellow for warnings, green for opportunities, purple for tyre crossover.
- Shows most recent events first.
- Displays an empty state when no events have occurred.
- User decisions are shown in the ALL tab with AI recommendation and time impact.

The Weather Timeline chart now shows four labelled series from actual `LapResult` fields:

- Track Temp (°C) — orange
- Air Temp (°C) — blue
- Wetness (0–1) — green
- Rain Prob (0–1) — purple dashed

Both Y-axes are labelled. Series are only shown when laps have been completed.

### Strategy recalculation fix

The tyre-age recalculation trigger previously fired on every lap once the tyre exceeded 90% of its useful life, causing up to 49 strategy engine calls in a 57-lap race. It now fires only once when the threshold is first crossed per stint.

### Known limitations

- Cloud cover, wind, humidity, and tyre temperature are not simulated and are not displayed.
- The strategy engine costs ~150ms per call (pre-existing). A 57-lap live race with normal seeds produces approximately 5–10 recalculations.
- `TRACK_TEMPERATURE_CHANGE` is retained as a legacy fallback for cases where neither `TRACK_TEMP_RISING` nor `TRACK_TEMP_FALLING` matches.

### Test coverage (`backend/tests/test_weather_events.py`, 22 tests)

- Hot-track event fires above threshold, not below.
- Track temp rising and falling events fire on correct deltas.
- No temp event for small delta.
- Rain increase and decrease events fire on correct wetness deltas.
- No rain event for small wetness change.
- Hot-track event not duplicated within dedup gap.
- Hot-track event re-emitted after dedup gap.
- Rain increase deduplication.
- High degradation risk event fires below life threshold.
- No degradation risk when life is adequate.
- Pit window open event fires at correct race fraction.
- Pit window closing event fires at correct race fraction.
- Engineer key factors include hot-track context.
- Engineer key factors include wetness context.
- Events belong to correct lap numbers.
- Restart resets event state.
- Same seed produces identical events.
- Different seeds produce valid results.
- 57-lap run completes with bounded recalculation count (< 40).

## Historical Weather And Track Conditions

Phase 11.9 uses [OpenF1](https://openf1.org/docs/) as an explicit secondary provider for historical weather observations. Jolpica remains the primary source for real event, result, qualifying, lap, and pit-stop reference data. OpenF1 weather is available from 2023 onward and includes provider-recorded air/track temperature (°C), humidity (%), pressure (mbar), wind speed (m/s), wind direction (degrees), and rainfall status.

The `f1_historical_weather_observations` table is independent from simulation `weather_history`. Historical observations are session-scoped and only associate to an imported event when country and race-weekend dates match. They never overwrite `RaceConfig`, `WeatherEngine`, simulated weather seeds, or strategy inputs. Missing OpenF1 values remain `null`; they are never replaced with zeroes or inferred values.

Configure the key-free client with optional timeout and retry controls:

```env
OPENF1_BASE_URL=https://api.openf1.org
OPENF1_CONNECT_TIMEOUT_SECONDS=3
OPENF1_READ_TIMEOUT_SECONDS=10
OPENF1_RETRY_LIMIT=2
OPENF1_MAX_RETRY_DELAY_SECONDS=5
```

OpenF1 is an unofficial provider. Its free historical access is limited to data from 2023 onward and has documented rate limits; it is not live telemetry and its terms limit free use to personal, educational, research, and non-commercial fan use. Import must be initiated as an explicit backend service operation using `F1WeatherImportService`; read APIs never contact OpenF1. The Weather Explorer labels source and units, and an empty historical result does not imply dry conditions.

Historical weather read APIs:

- `GET /api/f1-data/historical-weather?event_id=&session_key=&observed_from=&observed_to=&limit=&offset=`
- `GET /api/f1-data/historical-weather/events/{event_id}/summary?session_key=`
- `GET /api/f1-data/historical-weather/events/{event_id}/temperature-trends?session_key=`
- `GET /api/f1-data/historical-weather/events/{event_id}/rainfall?session_key=`

## Database Integrity

The application uses SQLAlchemy sessions from `app.database`: routes receive them through `Depends(get_db)`, and each dependency closes its session after the request. SQLite connections explicitly enable foreign-key enforcement.

Provider-backed F1 data is stored separately from simulator configuration and outputs: `f1_drivers`, `f1_constructors`, `f1_driver_constructor_seasons`, `f1_circuits`, `f1_circuit_events`, `f1_historical_race_results`, `f1_qualifying_results`, `f1_starting_grids`, `f1_historical_lap_times`, `f1_historical_pit_stops`, and `f1_historical_weather_observations`.

Stable provider natural keys are unique per source. Results, qualifying, grids, laps, pit stops, weather observations, and event records are insert-only; a repeat import skips their existing natural key. Profile imports do not overwrite existing non-null provider values and may only fill missing optional fields. Every import service rolls back its transaction on an exception, preserving previously committed records. Unknown values remain `NULL`; zero remains a recorded value.

There is no Alembic or other migration framework in this repository. The established development schema workflow is `Base.metadata.create_all()` at startup, which creates missing tables but does not alter or reset existing tables. Production schema changes therefore require an approved migration strategy before deployment; this phase intentionally does not introduce one or modify existing data.

## Historical F1 Data API

All provider-backed historical APIs are read-only under `/api/f1-data` and use `limit`/`offset` pagination (typically `limit=1..200`; lap and weather observations have documented higher caps). They return empty lists for valid filters with no imported data and `404` for a requested driver, constructor, circuit, or event that does not exist. These are historical reference records, not live telemetry.

- `GET /seasons/{season}/events?limit=&offset=` returns imported event details and the provider-backed circuit.
- `GET /events/{event_id}` returns one imported event.
- `GET /drivers/{driver_id}/historical-results?season=&limit=&offset=` and `GET /constructors/{constructor_id}/historical-results?season=&limit=&offset=` return stored classifications.
- `GET /drivers/{driver_id}/qualifying?season=&limit=&offset=` returns qualifying history; official race grids remain separately available at `GET /starting-grids/{event_id}`.
- `GET /historical-results?season=&event_id=&driver_id=&constructor_id=&circuit_id=&search=&limit=&offset=` supports historical-result filtering without unsafe dynamic sorting.

Example: `GET /api/f1-data/historical-results?season=2024&driver_id=12&limit=50&offset=0`. Result fields are nullable whenever the provider did not supply a classification, timing, fastest-lap, or status value.

## Historical Strategy Benchmark

Strategy Lab can load a separately labelled **Historical Strategy Benchmark** from `GET /api/f1-data/strategy-benchmark?season=&event_id=&circuit_id=`. Its filters use imported F1 record IDs, not simulator circuit IDs. The panel reports only imported coverage and recorded aggregates: race, result, lap, and pit-stop samples; averages for pit stops per race, recorded stop duration, recorded lap time, and official grid-to-finish change.

The benchmark is reference data only. It never changes `RaceConfig`, the strategy engine, simulated pit-lane loss, strategy confidence, weather, or AI Race Engineer recommendations. A recorded historical pit-stop duration is explicitly not a simulated pit-lane time loss. Empty scopes are reported as no imported samples rather than inferred data.

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
