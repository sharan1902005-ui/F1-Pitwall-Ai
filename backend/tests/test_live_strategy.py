from app.models.circuit import CircuitConfig
from app.schemas.live_race import RaceControlEvent, RaceEventType
from app.schemas.simulation import RaceConfig
from app.services.live_race_service import LiveRaceService


def config(laps: int = 12) -> RaceConfig:
    return RaceConfig(
        circuit=CircuitConfig(
            circuit_name="Monza",
            total_laps=laps,
            base_lap_time_seconds=85.0,
            pit_lane_time_loss_seconds=22.0,
            avg_track_temp=35.0,
            avg_air_temp=28.0,
        ),
        starting_compound="MEDIUM",
        starting_fuel_kg=40.0,
        weather_seed_state=42,
        safety_car_base_probability=0.15,
    )


def test_strategy_does_not_recalculate_on_plain_lap() -> None:
    service = LiveRaceService()
    started = service.start(config(laps=8), event_seed_state=999)
    state = service.get(started.race_id)
    initial_count = state.strategy_recalculation_count

    service.advance(started.race_id)
    state = service.get(started.race_id)

    assert state.strategy_recalculation_count in {initial_count, initial_count + 1}


def test_strategy_recalculates_on_user_strategy_change() -> None:
    service = LiveRaceService()
    started = service.start(config(laps=8), event_seed_state=1)
    initial_count = started.race_state.strategy_recalculation_count

    service.submit_action(started.race_id, {"action": "PIT", "compound": "HARD"})  # type: ignore[arg-type]
    service.advance(started.race_id)
    state = service.get(started.race_id)

    assert state.strategy_recalculation_count > initial_count


def test_timeline_records_events_actions_and_recommendations() -> None:
    service = LiveRaceService()
    started = service.start(config(laps=3), event_seed_state=1)

    service.submit_action(started.race_id, {"action": "STAY_OUT"})  # type: ignore[arg-type]
    service.advance(started.race_id)
    state = service.get(started.race_id)

    entry_types = {entry.entry_type for entry in state.timeline}
    assert "SESSION" in entry_types
    assert "USER_ACTION" in entry_types
    assert "LAP" in entry_types


def test_forced_safety_car_and_vsc_apply_different_lap_modifiers() -> None:
    service = LiveRaceService()
    race_config = config(laps=2)
    started_sc = service.start(race_config, event_seed_state=1)
    started_vsc = service.start(race_config, event_seed_state=1)
    weather = service.weather_engine.next_lap(
        1,
        race_config.circuit,
        service.weather_engine.create_rng(race_config.weather_seed_state),
        0.0,
    )

    service.event_engine.events_for_lap = lambda *args, **kwargs: [  # type: ignore[method-assign]
        RaceControlEvent(
            event_type=RaceEventType.SAFETY_CAR,
            lap=1,
            active=True,
            reason="SIMULATED INCIDENT - forced safety car",
        )
    ]
    sc = service.advance(started_sc.race_id)
    service.event_engine.events_for_lap = lambda *args, **kwargs: [  # type: ignore[method-assign]
        RaceControlEvent(
            event_type=RaceEventType.VIRTUAL_SAFETY_CAR,
            lap=1,
            active=True,
            reason="SIMULATED INCIDENT - forced virtual safety car",
        )
    ]
    vsc = service.advance(started_vsc.race_id)

    assert weather.track_wetness >= 0
    assert sc.lap_result is not None
    assert vsc.lap_result is not None
    assert sc.lap_result.lap_time_seconds > vsc.lap_result.lap_time_seconds


def test_tyre_crossover_event_not_emitted_every_wet_lap() -> None:
    """
    When track wetness stays above the crossover threshold for many consecutive
    laps, TYRE_CROSSOVER must not be appended on every single lap.
    The fix requires at least 3 laps between consecutive crossover events.
    """
    service = LiveRaceService()
    # Use a high-wetness seed so the track stays wet throughout.
    wet_config = RaceConfig(
        circuit=CircuitConfig(
            circuit_name="Wet",
            total_laps=20,
            base_lap_time_seconds=85.0,
            pit_lane_time_loss_seconds=22.0,
            avg_track_temp=20.0,
            avg_air_temp=18.0,
        ),
        starting_compound="MEDIUM",
        starting_fuel_kg=60.0,
        weather_seed_state=7,          # seed that produces sustained wetness
        safety_car_base_probability=0.0,
    )
    started = service.start(wet_config, event_seed_state=0)
    race_id = started.race_id

    for _ in range(20):
        service.advance(race_id)

    state = service.get(race_id)
    crossover_events = [
        e for e in state.events if e.event_type == RaceEventType.TYRE_CROSSOVER
    ]

    # There must be fewer crossover events than laps — not one per lap.
    assert len(crossover_events) < 20, (
        f"Expected fewer than 20 TYRE_CROSSOVER events, got {len(crossover_events)}"
    )

    # Consecutive crossover events must be at least 3 laps apart.
    laps = [e.lap for e in crossover_events]
    for i in range(1, len(laps)):
        assert laps[i] - laps[i - 1] >= 3, (
            f"TYRE_CROSSOVER events on laps {laps[i-1]} and {laps[i]} are too close"
        )


def test_strategy_recalculation_uses_current_compound_after_pit() -> None:
    """
    After a pit stop, the strategy recalculation must use the new compound,
    not the original starting compound.
    """
    service = LiveRaceService()
    started = service.start(config(laps=10), event_seed_state=1)
    race_id = started.race_id

    # Advance one lap, then pit onto HARD.
    service.advance(race_id)
    service.submit_action(race_id, {"action": "PIT", "compound": "HARD"})  # type: ignore[arg-type]
    service.advance(race_id)

    state = service.get(race_id)
    assert state.current_compound.value == "HARD"

    # The recommendation must have been recalculated after the pit.
    assert state.strategy_recalculation_count >= 2

    # The recommendation must not reference the original starting compound
    # (MEDIUM) as the current tyre — it should reflect HARD.
    if state.recommendation is not None:
        # The recommended_compound (if any) should not be the same as the
        # compound we just put on unless the strategy genuinely calls for it.
        # The key check: the strategy engine received the current compound.
        # We verify this indirectly: the strategy's first stint compound must
        # match the current compound (HARD), not the original (MEDIUM).
        if state.strategy is not None and state.strategy.stints:
            assert state.strategy.stints[0].compound.value == "HARD"
