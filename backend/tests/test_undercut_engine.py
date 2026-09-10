from app.services.undercut_engine import (
    DriverUndercutState,
    UndercutEngine,
)


def test_undercut_can_be_successful():

    engine = UndercutEngine()

    attacker = DriverUndercutState(
        driver_name="Driver B",
        position=2,
        compound="MEDIUM",
        tyre_age=20,
        gap_to_driver_ahead_seconds=2.0,
        current_lap=25,
        base_lap_time_seconds=85.0,
        degradation_per_lap=0.12,
    )

    defender = DriverUndercutState(
        driver_name="Driver A",
        position=1,
        compound="MEDIUM",
        tyre_age=28,
        gap_to_driver_ahead_seconds=0.0,
        current_lap=25,
        base_lap_time_seconds=85.0,
        degradation_per_lap=0.18,
    )

    result = engine.analyze(
        attacker=attacker,
        defender=defender,
        pit_lane_time_loss_seconds=22.0,
        new_compound="HARD",
        defender_stays_out_laps=2,
    )

    assert result.projected_gain_seconds > 0
    assert result.confidence >= 0
    assert result.recommendation is not None


def test_invalid_defender_stay_out_laps():

    engine = UndercutEngine()

    attacker = DriverUndercutState(
        driver_name="Driver B",
        position=2,
        compound="MEDIUM",
        tyre_age=20,
        gap_to_driver_ahead_seconds=2.0,
        current_lap=25,
        base_lap_time_seconds=85.0,
        degradation_per_lap=0.12,
    )

    defender = DriverUndercutState(
        driver_name="Driver A",
        position=1,
        compound="MEDIUM",
        tyre_age=25,
        gap_to_driver_ahead_seconds=0.0,
        current_lap=25,
        base_lap_time_seconds=85.0,
        degradation_per_lap=0.12,
    )

    try:
        engine.analyze(
            attacker=attacker,
            defender=defender,
            pit_lane_time_loss_seconds=22.0,
            defender_stays_out_laps=0,
        )

        assert False

    except ValueError:
        assert True