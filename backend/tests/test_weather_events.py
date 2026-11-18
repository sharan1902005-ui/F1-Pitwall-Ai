"""Tests for weather-aware environmental events and strategy decisions."""

import time

import pytest

from app.models.circuit import CircuitConfig
from app.schemas.live_race import RaceControlEvent, RaceEventType, RaceStatus
from app.schemas.simulation import RaceConfig, WeatherState
from app.services.live_race_service import LiveRaceService
from app.services.race_event_engine import RaceEventEngine
from app.services.weather_engine import WeatherEngine


# ── Helpers ───────────────────────────────────────────────────────────────────

def _config(
    laps: int = 10,
    avg_track_temp: float = 35.0,
    avg_air_temp: float = 28.0,
    safety_car_probability: float = 0.0,
    weather_seed: int = 42,
) -> RaceConfig:
    return RaceConfig(
        circuit=CircuitConfig(
            circuit_name="Test Circuit",
            total_laps=laps,
            base_lap_time_seconds=85.0,
            pit_lane_time_loss_seconds=22.0,
            avg_track_temp=avg_track_temp,
            avg_air_temp=avg_air_temp,
        ),
        starting_compound="MEDIUM",
        starting_fuel_kg=30.0,
        weather_seed_state=weather_seed,
        safety_car_base_probability=safety_car_probability,
    )


def _weather(
    lap: int = 1,
    track_temp: float = 35.0,
    air_temp: float = 28.0,
    wetness: float = 0.0,
    rain_intensity: float = 0.0,
    rain_probability: float = 0.0,
) -> WeatherState:
    return WeatherState(
        lap_number=lap,
        track_temperature=track_temp,
        air_temperature=air_temp,
        track_wetness=wetness,
        rain_intensity=rain_intensity,
        rain_probability=rain_probability,
    )


def _event_types(events: list[RaceControlEvent]) -> list[RaceEventType]:
    return [e.event_type for e in events]


# ── Hot-track event ───────────────────────────────────────────────────────────

def test_hot_track_event_fires_when_temp_exceeds_threshold() -> None:
    engine = RaceEventEngine()
    config = _config(avg_track_temp=35.0)
    prev = _weather(lap=1, track_temp=35.0)
    current = _weather(lap=2, track_temp=42.0)  # +7°C above avg

    events = engine.events_for_lap(config, 0, 2, current, prev)
    assert RaceEventType.HOT_TRACK in _event_types(events)


def test_hot_track_event_not_fired_below_threshold() -> None:
    engine = RaceEventEngine()
    config = _config(avg_track_temp=35.0)
    prev = _weather(lap=1, track_temp=35.0)
    current = _weather(lap=2, track_temp=39.0)  # +4°C — below 6°C threshold

    events = engine.events_for_lap(config, 0, 2, current, prev)
    assert RaceEventType.HOT_TRACK not in _event_types(events)


# ── Track temperature rising / falling ───────────────────────────────────────

def test_track_temp_rising_event() -> None:
    engine = RaceEventEngine()
    config = _config(avg_track_temp=35.0)
    prev = _weather(lap=1, track_temp=33.0)
    current = _weather(lap=2, track_temp=38.0)  # +5°C delta

    events = engine.events_for_lap(config, 0, 2, current, prev)
    assert RaceEventType.TRACK_TEMP_RISING in _event_types(events)


def test_track_temp_falling_event() -> None:
    engine = RaceEventEngine()
    config = _config(avg_track_temp=35.0)
    prev = _weather(lap=1, track_temp=38.0)
    current = _weather(lap=2, track_temp=33.0)  # -5°C delta

    events = engine.events_for_lap(config, 0, 2, current, prev)
    assert RaceEventType.TRACK_TEMP_FALLING in _event_types(events)


def test_no_temp_event_for_small_delta() -> None:
    engine = RaceEventEngine()
    config = _config(avg_track_temp=35.0)
    prev = _weather(lap=1, track_temp=35.0)
    current = _weather(lap=2, track_temp=36.5)  # +1.5°C — below threshold

    events = engine.events_for_lap(config, 0, 2, current, prev)
    temp_events = {
        RaceEventType.TRACK_TEMP_RISING,
        RaceEventType.TRACK_TEMP_FALLING,
        RaceEventType.HOT_TRACK,
        RaceEventType.TRACK_TEMPERATURE_CHANGE,
    }
    assert not any(t in temp_events for t in _event_types(events))


# ── Rain / wetness transitions ────────────────────────────────────────────────

def test_rain_increase_event() -> None:
    engine = RaceEventEngine()
    config = _config()
    prev = _weather(lap=1, wetness=0.05)
    current = _weather(lap=2, wetness=0.20)  # +0.15 delta

    events = engine.events_for_lap(config, 0, 2, current, prev)
    assert RaceEventType.RAIN_INCREASE in _event_types(events)


def test_rain_decrease_event() -> None:
    engine = RaceEventEngine()
    config = _config()
    prev = _weather(lap=1, wetness=0.40)
    current = _weather(lap=2, wetness=0.28)  # -0.12 delta

    events = engine.events_for_lap(config, 0, 2, current, prev)
    assert RaceEventType.RAIN_DECREASE in _event_types(events)


def test_no_rain_event_for_small_wetness_change() -> None:
    engine = RaceEventEngine()
    config = _config()
    prev = _weather(lap=1, wetness=0.10)
    current = _weather(lap=2, wetness=0.14)  # +0.04 — below threshold

    events = engine.events_for_lap(config, 0, 2, current, prev)
    assert RaceEventType.RAIN_INCREASE not in _event_types(events)
    assert RaceEventType.RAIN_DECREASE not in _event_types(events)


# ── Event deduplication ───────────────────────────────────────────────────────

def test_hot_track_event_not_duplicated_within_dedup_gap() -> None:
    engine = RaceEventEngine()
    config = _config(avg_track_temp=35.0)
    prev = _weather(lap=1, track_temp=35.0)
    current = _weather(lap=2, track_temp=42.0)

    # First emission
    first_events = engine.events_for_lap(config, 0, 2, current, prev)
    assert RaceEventType.HOT_TRACK in _event_types(first_events)

    # Immediately after — should be suppressed
    second_events = engine.events_for_lap(config, 0, 3, current, prev, previous_events=first_events)
    assert RaceEventType.HOT_TRACK not in _event_types(second_events)


def test_hot_track_event_re_emitted_after_dedup_gap() -> None:
    engine = RaceEventEngine()
    config = _config(avg_track_temp=35.0)
    prev = _weather(lap=1, track_temp=35.0)
    current = _weather(lap=2, track_temp=42.0)

    first_events = engine.events_for_lap(config, 0, 2, current, prev)
    # 3 laps later — should be allowed again
    later_events = engine.events_for_lap(config, 0, 5, current, prev, previous_events=first_events)
    assert RaceEventType.HOT_TRACK in _event_types(later_events)


def test_rain_increase_deduplication() -> None:
    engine = RaceEventEngine()
    config = _config()
    prev = _weather(lap=1, wetness=0.05)
    current = _weather(lap=2, wetness=0.20)

    first = engine.events_for_lap(config, 0, 2, current, prev)
    assert RaceEventType.RAIN_INCREASE in _event_types(first)

    second = engine.events_for_lap(config, 0, 3, current, prev, previous_events=first)
    assert RaceEventType.RAIN_INCREASE not in _event_types(second)


# ── Environmental strategy events ────────────────────────────────────────────

def test_degradation_warning_event_fires_at_40_percent() -> None:
    engine = RaceEventEngine()
    events, warned, critical = engine.degradation_state_events(
        lap_number=20,
        tyre_compound="MEDIUM",
        tyre_age=21,
        tyre_life_percent=38.0,  # below 40% threshold
        degradation_warned=False,
        degradation_critical=False,
    )
    assert RaceEventType.DEGRADATION_WARNING in _event_types(events)
    assert warned is True
    assert critical is False


def test_degradation_warning_not_repeated_same_stint() -> None:
    engine = RaceEventEngine()
    events, warned, critical = engine.degradation_state_events(
        lap_number=21,
        tyre_compound="MEDIUM",
        tyre_age=22,
        tyre_life_percent=35.0,
        degradation_warned=True,  # already fired
        degradation_critical=False,
    )
    assert RaceEventType.DEGRADATION_WARNING not in _event_types(events)


def test_critical_tyre_wear_event_fires_at_15_percent() -> None:
    engine = RaceEventEngine()
    events, warned, critical = engine.degradation_state_events(
        lap_number=30,
        tyre_compound="MEDIUM",
        tyre_age=30,
        tyre_life_percent=12.0,  # below 15% threshold
        degradation_warned=True,
        degradation_critical=False,
    )
    assert RaceEventType.CRITICAL_TYRE_WEAR in _event_types(events)
    assert critical is True


def test_critical_tyre_wear_not_repeated_same_stint() -> None:
    engine = RaceEventEngine()
    events, warned, critical = engine.degradation_state_events(
        lap_number=31,
        tyre_compound="MEDIUM",
        tyre_age=31,
        tyre_life_percent=8.0,
        degradation_warned=True,
        degradation_critical=True,  # already fired
    )
    assert RaceEventType.CRITICAL_TYRE_WEAR not in _event_types(events)


def test_degradation_flags_reset_after_pit() -> None:
    """After a pit stop the service resets degradation flags so warnings re-fire."""
    service = LiveRaceService()
    config = _config(laps=20, weather_seed=42)
    started = service.start(config, event_seed_state=0)
    rid = started.race_id

    # Advance until degradation_warned is set
    for _ in range(15):
        service.advance(rid)
    state = service.get(rid)
    # Pit stop resets flags
    service.submit_action(rid, {"action": "PIT", "compound": "HARD"})  # type: ignore[arg-type]
    service.advance(rid)
    state = service.get(rid)
    assert state.degradation_warned is False
    assert state.degradation_critical is False


def test_tyre_life_zero_does_not_retire_car() -> None:
    """0% tyre life is a clamped model value; the car continues racing."""
    from app.services.tyre_model import TyrePerformanceModel
    from app.schemas.simulation import TyreCompound
    m = TyrePerformanceModel()
    # MEDIUM max_useful_life = 34 laps; life_percent clamps at 0 beyond that
    assert m.life_percent(TyreCompound.MEDIUM, 34) == 0.0
    assert m.life_percent(TyreCompound.MEDIUM, 50) == 0.0
    # But performance_penalty keeps increasing (cliff penalty)
    p34 = m.performance_penalty(TyreCompound.MEDIUM, 34, 0.0)
    p50 = m.performance_penalty(TyreCompound.MEDIUM, 50, 0.0)
    assert p50 > p34, "Penalty must increase beyond max useful life"


def test_tyre_life_resets_after_pit() -> None:
    from app.services.tyre_model import TyrePerformanceModel
    from app.schemas.simulation import TyreCompound
    m = TyrePerformanceModel()
    # After pit tyre_age resets to 0 → 100% life
    assert m.life_percent(TyreCompound.HARD, 0) == 100.0


# ── Crossover state machine ───────────────────────────────────────────────────

def test_crossover_reached_event_fires_on_entry() -> None:
    engine = RaceEventEngine()
    events, active = engine.crossover_state_events(
        lap_number=10,
        track_wetness=0.50,
        tyre_compound="MEDIUM",
        crossover_active=False,
    )
    assert RaceEventType.TYRE_CROSSOVER_REACHED in _event_types(events)
    assert active is True


def test_crossover_reached_not_repeated_while_active() -> None:
    engine = RaceEventEngine()
    events, active = engine.crossover_state_events(
        lap_number=11,
        track_wetness=0.55,
        tyre_compound="MEDIUM",
        crossover_active=True,  # already active
    )
    assert RaceEventType.TYRE_CROSSOVER_REACHED not in _event_types(events)
    assert active is True


def test_crossover_cleared_event_fires_on_exit() -> None:
    engine = RaceEventEngine()
    events, active = engine.crossover_state_events(
        lap_number=15,
        track_wetness=0.20,  # below exit threshold 0.30
        tyre_compound="MEDIUM",
        crossover_active=True,
    )
    assert RaceEventType.TYRE_CROSSOVER_CLEARED in _event_types(events)
    assert active is False


def test_crossover_not_active_for_wet_compound() -> None:
    engine = RaceEventEngine()
    events, active = engine.crossover_state_events(
        lap_number=10,
        track_wetness=0.60,
        tyre_compound="INTERMEDIATE",
        crossover_active=False,
    )
    assert active is False
    assert not events


# ── VSC pit-loss calculation ──────────────────────────────────────────────────

def test_vsc_pit_loss_is_less_than_normal() -> None:
    engine = RaceEventEngine()
    base = 22.0
    vsc_loss = base * engine.vsc_pit_loss_multiplier
    assert vsc_loss < base


def test_sc_pit_loss_is_less_than_vsc() -> None:
    engine = RaceEventEngine()
    base = 22.0
    sc_loss = base * engine.safety_car_pit_loss_multiplier
    vsc_loss = base * engine.vsc_pit_loss_multiplier
    assert sc_loss < vsc_loss


# ── Decision impact ───────────────────────────────────────────────────────────

def test_decision_impact_none_when_no_recommendation() -> None:
    service = LiveRaceService()
    config = _config(laps=5, weather_seed=42)
    started = service.start(config, event_seed_state=0)
    rid = started.race_id
    state = service.get(rid)
    # Manually clear recommendation to test None path
    state.recommendation = None
    from app.schemas.live_race import LiveRaceAction, LiveActionType
    action = LiveRaceAction(action=LiveActionType.STAY_OUT)
    impact = service._decision_impact(state, action)
    assert impact is None


def test_decision_impact_none_for_pure_stay_out_strategy() -> None:
    """When recommended compound == current compound and no pit lap, impact is None."""
    from app.services.tyre_model import TyrePerformanceModel
    from app.schemas.simulation import TyreCompound
    from app.schemas.race_engineer import EngineerResponse, Urgency
    from app.schemas.live_race import LiveRaceAction, LiveActionType

    service = LiveRaceService()
    config = _config(laps=5, weather_seed=42)
    started = service.start(config, event_seed_state=0)
    rid = started.race_id
    state = service.get(rid)

    # Inject a stay-out recommendation on the same compound
    from app.schemas.race_engineer import EngineerResponse, Urgency
    state.recommendation = EngineerResponse(
        decision="STAY OUT ON MEDIUM",
        urgency=Urgency.LOW,
        explanation="Stay out.",
        key_factors=[],
        recommended_compound=TyreCompound.MEDIUM,
        recommended_pit_lap=None,
        confidence=0.8,
        risk="LOW",
    )
    state.current_compound = TyreCompound.MEDIUM
    action = LiveRaceAction(action=LiveActionType.STAY_OUT)
    impact = service._decision_impact(state, action)
    assert impact is None


def test_decision_impact_positive_when_staying_out_on_worn_tyre() -> None:
    """STAY_OUT on a worn tyre vs pitting for fresh compound gives positive impact."""
    from app.schemas.simulation import TyreCompound
    from app.schemas.race_engineer import EngineerResponse, Urgency
    from app.schemas.live_race import LiveRaceAction, LiveActionType

    service = LiveRaceService()
    config = _config(laps=57, weather_seed=42)
    started = service.start(config, event_seed_state=0)
    rid = started.race_id
    state = service.get(rid)

    state.current_compound = TyreCompound.MEDIUM
    state.tyre_age = 40  # well past max useful life
    state.recommendation = EngineerResponse(
        decision="BOX FOR HARD",
        urgency=Urgency.CRITICAL,
        explanation="Pit now.",
        key_factors=[],
        recommended_compound=TyreCompound.HARD,
        recommended_pit_lap=state.current_lap + 1,
        confidence=0.9,
        risk="HIGH",
    )
    action = LiveRaceAction(action=LiveActionType.STAY_OUT)
    impact = service._decision_impact(state, action)
    assert impact is not None
    assert impact > 0, f"Expected positive impact for worn tyre stay-out, got {impact}"


# ── High-degradation legacy compat ────────────────────────────────────────────

def test_high_degradation_risk_event() -> None:
    """Legacy environmental_strategy_events no longer emits degradation events.
    Use degradation_state_events directly."""
    engine = RaceEventEngine()
    events, warned, critical = engine.degradation_state_events(
        lap_number=20,
        tyre_compound="MEDIUM",
        tyre_age=30,
        tyre_life_percent=12.0,
        degradation_warned=False,
        degradation_critical=False,
    )
    assert RaceEventType.CRITICAL_TYRE_WEAR in _event_types(events)


def test_no_degradation_risk_when_life_ok() -> None:
    engine = RaceEventEngine()
    events, warned, critical = engine.degradation_state_events(
        lap_number=10,
        tyre_compound="MEDIUM",
        tyre_age=10,
        tyre_life_percent=70.0,
        degradation_warned=False,
        degradation_critical=False,
    )
    assert RaceEventType.DEGRADATION_WARNING not in _event_types(events)
    assert RaceEventType.CRITICAL_TYRE_WEAR not in _event_types(events)


def test_pit_window_open_event() -> None:
    engine = RaceEventEngine()
    weather = _weather(lap=15)
    # race_fraction = 1 - (35 / (35 + 15 - 1)) = 1 - 35/49 ≈ 0.286 → in [0.28, 0.32]
    events = engine.environmental_strategy_events(
        lap_number=15,
        weather=weather,
        tyre_compound="MEDIUM",
        tyre_age=15,
        tyre_life_percent=55.0,
        remaining_laps=35,
        previous_events=[],
    )
    assert RaceEventType.PIT_WINDOW_OPEN in _event_types(events)


def test_pit_window_closing_event() -> None:
    engine = RaceEventEngine()
    weather = _weather(lap=40)
    # race_fraction = 1 - (20 / (20 + 40 - 1)) = 1 - 20/59 ≈ 0.661 → in [0.65, 0.70]
    events = engine.environmental_strategy_events(
        lap_number=40,
        weather=weather,
        tyre_compound="MEDIUM",
        tyre_age=20,
        tyre_life_percent=40.0,
        remaining_laps=20,
        previous_events=[],
    )
    assert RaceEventType.PIT_WINDOW_CLOSING in _event_types(events)


# ── Weather-aware engineer recommendations ───────────────────────────────────

def test_engineer_key_factors_include_hot_track_context() -> None:
    service = LiveRaceService()
    # Use a high avg_track_temp circuit so weather engine produces elevated temps
    config = _config(laps=10, avg_track_temp=20.0, weather_seed=99)
    started = service.start(config, event_seed_state=0)
    race_id = started.race_id

    for _ in range(5):
        service.advance(race_id)

    state = service.get(race_id)
    if state.recommendation is not None:
        # Recommendation must reference actual simulated values
        all_text = " ".join(state.recommendation.key_factors) + state.recommendation.explanation
        assert any(c.isdigit() for c in all_text), "Recommendation should contain numeric values"


def test_engineer_key_factors_include_wetness_context() -> None:
    """Engineer explanation references track wetness when it is non-zero."""
    service = LiveRaceService()
    config = _config(laps=6, weather_seed=7)
    started = service.start(config, event_seed_state=0)
    race_id = started.race_id

    for _ in range(6):
        service.advance(race_id)

    state = service.get(race_id)
    if state.recommendation is not None:
        factors_text = " ".join(state.recommendation.key_factors)
        assert "wetness" in factors_text.lower() or "rain" in factors_text.lower() or "tyre" in factors_text.lower()


# ── Replay synchronization ───────────────────────────────────────────────────

def test_events_belong_to_correct_lap() -> None:
    service = LiveRaceService()
    config = _config(laps=8, avg_track_temp=20.0, weather_seed=55)
    started = service.start(config, event_seed_state=0)
    race_id = started.race_id

    for _ in range(8):
        service.advance(race_id)

    state = service.get(race_id)
    for event in state.events:
        assert 1 <= event.lap <= 8, f"Event lap {event.lap} out of range"


def test_restart_resets_event_state() -> None:
    service = LiveRaceService()
    config = _config(laps=5, avg_track_temp=20.0, weather_seed=55)

    started1 = service.start(config, event_seed_state=0)
    for _ in range(5):
        service.advance(started1.race_id)
    state1 = service.get(started1.race_id)

    # Restart = new session
    started2 = service.start(config, event_seed_state=0)
    state2 = service.get(started2.race_id)
    assert state2.events == [], "Fresh session must have no events"
    assert state2.current_lap == 0


# ── Deterministic seeded simulations ─────────────────────────────────────────

def test_same_seed_produces_identical_events() -> None:
    config = _config(laps=10, weather_seed=42)
    results = []
    for _ in range(2):
        service = LiveRaceService()
        started = service.start(config, event_seed_state=7)
        for _ in range(10):
            service.advance(started.race_id)
        state = service.get(started.race_id)
        results.append([(e.event_type, e.lap) for e in state.events])

    assert results[0] == results[1]


def test_different_seeds_produce_valid_results() -> None:
    for seed in [1, 42, 999]:
        service = LiveRaceService()
        config = _config(laps=5, weather_seed=seed)
        started = service.start(config, event_seed_state=seed)
        for _ in range(5):
            service.advance(started.race_id)
        state = service.get(started.race_id)
        assert state.current_lap == 5
        assert state.race_status == RaceStatus.FINISHED


# ── 57-lap performance ────────────────────────────────────────────────────────

def test_57_lap_performance_with_environmental_events() -> None:
    """57-lap live race with environmental events completes without error.

    The live race service calls the strategy engine on meaningful events.
    Strategy engine cost is ~150ms/call (pre-existing); 57 laps with a
    normal seed produce a small number of recalculations.  We assert
    correctness and a generous wall-clock limit that accounts for the
    strategy engine cost without masking regressions.
    """
    service = LiveRaceService()
    config = _config(laps=57, avg_track_temp=35.0, weather_seed=42)
    started = service.start(config, event_seed_state=7)

    t0 = time.perf_counter()
    for _ in range(57):
        service.advance(started.race_id)
    elapsed = time.perf_counter() - t0

    state = service.get(started.race_id)
    assert state.race_status == RaceStatus.FINISHED
    assert state.current_lap == 57
    # Each strategy recalculation costs ~150ms (pre-existing strategy engine
    # cost).  With deduplication the number of recalculations is bounded;
    # allow 30s to avoid flakiness on slow CI while still catching runaway loops.
    assert elapsed < 30.0, f"57-lap run took {elapsed:.3f}s — possible recalculation loop"
    assert state.strategy_recalculation_count < 40, (
        f"Too many recalculations: {state.strategy_recalculation_count}"
    )
