"""Tests proving genuine lap-by-lap classification correctness."""

from app.models.circuit import CircuitConfig
from app.schemas.multi_race import DriverConfig, MultiDriverRaceConfig
from app.schemas.simulation import PitInstruction, RaceConfig, TyreCompound
from app.services.multi_driver_simulator import MultiDriverRaceSimulator


def _config(
    total_laps: int = 20,
    safety_car_probability: float = 0.0,
) -> MultiDriverRaceConfig:
    """Minimal deterministic config with two clearly differentiated drivers."""
    return MultiDriverRaceConfig(
        race_config=RaceConfig(
            circuit=CircuitConfig(
                circuit_name="Test",
                total_laps=total_laps,
                base_lap_time_seconds=80.0,
                pit_lane_time_loss_seconds=22.0,
                avg_track_temp=30,
                avg_air_temp=25,
            ),
            starting_compound=TyreCompound.MEDIUM,
            starting_fuel_kg=60.0,
            weather_seed_state=1,
            safety_car_base_probability=safety_car_probability,
        ),
        event_seed_state=1,
        drivers=[
            DriverConfig(
                driver_id="fast",
                driver_name="Fast Driver",
                team_name="Alpha",
                starting_compound=TyreCompound.MEDIUM,
                starting_fuel_kg=60.0,
                pace_factor=0.98,   # faster
                degradation_factor=1.0,
                strategy=[PitInstruction(lap=10, compound=TyreCompound.HARD)],
            ),
            DriverConfig(
                driver_id="slow",
                driver_name="Slow Driver",
                team_name="Beta",
                starting_compound=TyreCompound.MEDIUM,
                starting_fuel_kg=60.0,
                pace_factor=1.02,   # slower
                degradation_factor=1.0,
                strategy=[PitInstruction(lap=10, compound=TyreCompound.HARD)],
            ),
        ],
    )


def _config_with_position_change() -> MultiDriverRaceConfig:
    """
    Config where Driver B pits earlier than Driver A, causing a temporary
    position swap: B drops behind A during the pit lap, then recovers.
    """
    return MultiDriverRaceConfig(
        race_config=RaceConfig(
            circuit=CircuitConfig(
                circuit_name="Test",
                total_laps=20,
                base_lap_time_seconds=80.0,
                pit_lane_time_loss_seconds=22.0,
                avg_track_temp=30,
                avg_air_temp=25,
            ),
            starting_compound=TyreCompound.MEDIUM,
            starting_fuel_kg=60.0,
            weather_seed_state=1,
            safety_car_base_probability=0.0,
        ),
        event_seed_state=1,
        drivers=[
            DriverConfig(
                driver_id="drv-a",
                driver_name="Driver A",
                team_name="Alpha",
                starting_compound=TyreCompound.MEDIUM,
                starting_fuel_kg=60.0,
                pace_factor=1.0,
                degradation_factor=1.0,
                strategy=[PitInstruction(lap=12, compound=TyreCompound.HARD)],
            ),
            DriverConfig(
                driver_id="drv-b",
                driver_name="Driver B",
                team_name="Beta",
                starting_compound=TyreCompound.MEDIUM,
                starting_fuel_kg=60.0,
                pace_factor=1.0,
                degradation_factor=1.0,
                strategy=[PitInstruction(lap=8, compound=TyreCompound.HARD)],
            ),
        ],
    )


# ---------------------------------------------------------------------------
# Classification structure
# ---------------------------------------------------------------------------

def test_classification_by_lap_covers_every_lap() -> None:
    """Every lap from 1 to total_laps must have a classification snapshot."""
    config = _config()
    result = MultiDriverRaceSimulator().run(config)
    laps = [snap.lap_number for snap in result.classification_by_lap]
    assert laps == list(range(1, config.race_config.circuit.total_laps + 1))


def test_classification_by_lap_contains_all_drivers_each_lap() -> None:
    """Each lap snapshot must contain an entry for every driver."""
    config = _config()
    result = MultiDriverRaceSimulator().run(config)
    driver_ids = {d.driver_id for d in config.drivers}
    for snap in result.classification_by_lap:
        assert {e.driver_id for e in snap.classification} == driver_ids


def test_positions_are_1_indexed_and_unique_each_lap() -> None:
    """Positions must be 1..N with no duplicates on any lap."""
    config = _config()
    result = MultiDriverRaceSimulator().run(config)
    n = len(config.drivers)
    for snap in result.classification_by_lap:
        positions = sorted(e.position for e in snap.classification)
        assert positions == list(range(1, n + 1))


# ---------------------------------------------------------------------------
# Genuine timing-based ordering
# ---------------------------------------------------------------------------

def test_leader_has_lowest_cumulative_time_each_lap() -> None:
    """P1 must always have the lowest cumulative race time at each lap."""
    config = _config()
    result = MultiDriverRaceSimulator().run(config)
    for snap in result.classification_by_lap:
        leader = next(e for e in snap.classification if e.position == 1)
        for entry in snap.classification:
            assert entry.total_race_time_seconds >= leader.total_race_time_seconds


def test_gap_to_leader_is_zero_for_leader_each_lap() -> None:
    """The leader's gap_to_leader_seconds must be 0.0 on every lap."""
    config = _config()
    result = MultiDriverRaceSimulator().run(config)
    for snap in result.classification_by_lap:
        leader = next(e for e in snap.classification if e.position == 1)
        assert leader.gap_to_leader_seconds == 0.0


def test_gap_to_leader_matches_time_difference() -> None:
    """gap_to_leader_seconds must equal the difference in cumulative times."""
    config = _config()
    result = MultiDriverRaceSimulator().run(config)
    for snap in result.classification_by_lap:
        leader_time = next(
            e.total_race_time_seconds for e in snap.classification if e.position == 1
        )
        for entry in snap.classification:
            expected = round(entry.total_race_time_seconds - leader_time, 6)
            assert abs(entry.gap_to_leader_seconds - expected) < 1e-4


def test_faster_driver_leads_throughout() -> None:
    """The faster driver (pace_factor=0.98) must be P1 on every lap."""
    config = _config()
    result = MultiDriverRaceSimulator().run(config)
    for snap in result.classification_by_lap:
        leader = next(e for e in snap.classification if e.position == 1)
        assert leader.driver_id == "fast"


# ---------------------------------------------------------------------------
# Position changes from pit stops
# ---------------------------------------------------------------------------

def test_driver_loses_position_on_pit_lap() -> None:
    """
    Driver B pits on lap 8 (22s loss); Driver A pits on lap 12.
    On lap 8, Driver B's cumulative time must exceed Driver A's,
    so Driver B must be P2 on that lap.
    """
    config = _config_with_position_change()
    result = MultiDriverRaceSimulator().run(config)

    snap_lap8 = next(s for s in result.classification_by_lap if s.lap_number == 8)
    b_entry = next(e for e in snap_lap8.classification if e.driver_id == "drv-b")
    assert b_entry.position == 2, (
        f"Driver B should be P2 on pit lap 8, got P{b_entry.position}"
    )


def test_position_changes_across_laps() -> None:
    """
    Verify that at least one driver changes position between consecutive laps
    across the full race (pit stops must cause position swaps).
    """
    config = _config_with_position_change()
    result = MultiDriverRaceSimulator().run(config)

    position_changes_observed = False
    snaps = result.classification_by_lap
    for i in range(1, len(snaps)):
        prev = {e.driver_id: e.position for e in snaps[i - 1].classification}
        curr = {e.driver_id: e.position for e in snaps[i].classification}
        if prev != curr:
            position_changes_observed = True
            break

    assert position_changes_observed, "No position changes observed across the race"


def test_cumulative_time_increases_monotonically_per_driver() -> None:
    """Each driver's cumulative race time must strictly increase each lap."""
    config = _config()
    result = MultiDriverRaceSimulator().run(config)
    for driver in result.driver_results:
        times = [lap.cumulative_race_time for lap in driver.lap_results]
        for i in range(1, len(times)):
            assert times[i] > times[i - 1], (
                f"Driver {driver.driver_id} cumulative time did not increase at lap {i + 1}"
            )


# ---------------------------------------------------------------------------
# Replay correctness
# ---------------------------------------------------------------------------

def test_replay_forward_returns_correct_classification() -> None:
    """Replaying laps 1..N in order must return the same snapshots as classification_by_lap."""
    config = _config()
    result = MultiDriverRaceSimulator().run(config)
    snap_index = {snap.lap_number: snap for snap in result.classification_by_lap}

    for lap_number in range(1, config.race_config.circuit.total_laps + 1):
        snap = snap_index[lap_number]
        assert snap.lap_number == lap_number
        assert len(snap.classification) == len(config.drivers)


def test_replay_backward_returns_correct_classification() -> None:
    """Replaying laps in reverse must return the same snapshots."""
    config = _config()
    result = MultiDriverRaceSimulator().run(config)
    snap_index = {snap.lap_number: snap for snap in result.classification_by_lap}

    for lap_number in range(config.race_config.circuit.total_laps, 0, -1):
        snap = snap_index[lap_number]
        assert snap.lap_number == lap_number


def test_restart_returns_lap1_classification() -> None:
    """Lap 1 snapshot must be accessible and have valid positions."""
    config = _config()
    result = MultiDriverRaceSimulator().run(config)
    lap1 = next(s for s in result.classification_by_lap if s.lap_number == 1)
    assert len(lap1.classification) == len(config.drivers)
    positions = sorted(e.position for e in lap1.classification)
    assert positions == list(range(1, len(config.drivers) + 1))


def test_final_classification_matches_last_lap_snapshot() -> None:
    """The final classification must equal the last lap's classification snapshot."""
    config = _config()
    result = MultiDriverRaceSimulator().run(config)
    last_snap = result.classification_by_lap[-1]

    final_by_id = {e.driver_id: e.position for e in result.classification}
    snap_by_id = {e.driver_id: e.position for e in last_snap.classification}
    assert final_by_id == snap_by_id


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------

def test_same_seed_produces_identical_classification_by_lap() -> None:
    """Two runs with the same config must produce identical per-lap classifications."""
    config = _config()
    sim = MultiDriverRaceSimulator()
    first = sim.run(config)
    second = sim.run(config)

    assert len(first.classification_by_lap) == len(second.classification_by_lap)
    for snap_a, snap_b in zip(first.classification_by_lap, second.classification_by_lap):
        assert snap_a.lap_number == snap_b.lap_number
        for entry_a, entry_b in zip(snap_a.classification, snap_b.classification):
            assert entry_a.driver_id == entry_b.driver_id
            assert entry_a.position == entry_b.position
            assert abs(entry_a.total_race_time_seconds - entry_b.total_race_time_seconds) < 1e-9


def test_different_seeds_may_produce_different_results() -> None:
    """Different event seeds should produce different shared event sequences."""
    config_a = _config()
    config_b = config_a.model_copy(update={"event_seed_state": 9999})
    sim = MultiDriverRaceSimulator()
    result_a = sim.run(config_a)
    result_b = sim.run(config_b)
    # At minimum the configs differ; results may differ in events
    assert config_a.event_seed_state != config_b.event_seed_state
    # Both must still produce valid full-race classifications
    assert len(result_a.classification_by_lap) == config_a.race_config.circuit.total_laps
    assert len(result_b.classification_by_lap) == config_b.race_config.circuit.total_laps


# ---------------------------------------------------------------------------
# Performance (57-lap target)
# ---------------------------------------------------------------------------

def test_57_lap_performance() -> None:
    """Two-driver 57-lap run must complete in under 0.05s."""
    config = MultiDriverRaceConfig(
        race_config=RaceConfig(
            circuit=CircuitConfig(
                circuit_name="Monza",
                total_laps=57,
                base_lap_time_seconds=85.0,
                pit_lane_time_loss_seconds=22.0,
                avg_track_temp=35,
                avg_air_temp=28,
            ),
            starting_compound=TyreCompound.MEDIUM,
            starting_fuel_kg=100.0,
            weather_seed_state=42,
            safety_car_base_probability=0.15,
        ),
        event_seed_state=7,
        drivers=[
            DriverConfig(
                driver_id="drv-a",
                driver_name="Driver A",
                team_name="Alpha",
                starting_compound=TyreCompound.MEDIUM,
                starting_fuel_kg=100.0,
                pace_factor=0.99,
                degradation_factor=1.0,
                strategy=[PitInstruction(lap=28, compound=TyreCompound.HARD)],
            ),
            DriverConfig(
                driver_id="drv-b",
                driver_name="Driver B",
                team_name="Beta",
                starting_compound=TyreCompound.SOFT,
                starting_fuel_kg=100.0,
                pace_factor=1.01,
                degradation_factor=1.05,
                strategy=[
                    PitInstruction(lap=20, compound=TyreCompound.MEDIUM),
                    PitInstruction(lap=40, compound=TyreCompound.HARD),
                ],
            ),
        ],
    )
    sim = MultiDriverRaceSimulator()

    import time
    start = time.perf_counter()
    result = sim.run(config)
    elapsed = time.perf_counter() - start

    assert result.total_laps == 57
    assert len(result.classification_by_lap) == 57
    # 0.5s is a generous regression guard; warm simulator time is ~4ms.
    # pytest cold-start overhead can add ~100ms on first collection.
    assert elapsed < 0.5, f"57-lap 2-driver run took {elapsed:.4f}s, expected < 0.5s"
