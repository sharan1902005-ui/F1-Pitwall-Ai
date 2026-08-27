"""Historical race comparison foundation."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.historical import HistoricalLap, HistoricalPitStop
from app.schemas.historical import RaceComparison
from app.schemas.simulation import RaceResult


class RaceComparisonService:
    """Compare simulated race output with lightweight historical samples."""

    def compare(
        self,
        simulated_race: RaceResult,
        historical_race_id: int,
        db: Session,
    ) -> RaceComparison:
        """Return simple aggregate differences for one historical race."""
        laps = list(
            db.scalars(
                select(HistoricalLap)
                .where(HistoricalLap.race_id == historical_race_id)
                .order_by(HistoricalLap.driver_code, HistoricalLap.lap_number)
            )
        )
        pit_stops = list(
            db.scalars(
                select(HistoricalPitStop).where(
                    HistoricalPitStop.race_id == historical_race_id
                )
            )
        )
        historical_average = (
            sum(lap.lap_time_seconds for lap in laps) / len(laps) if laps else None
        )
        simulated_average = (
            simulated_race.final_race_time_seconds / simulated_race.completed_laps
            if simulated_race.completed_laps
            else 0.0
        )
        return RaceComparison(
            simulated_total_time_seconds=simulated_race.final_race_time_seconds,
            historical_average_lap_time_seconds=historical_average,
            simulated_average_lap_time_seconds=simulated_average,
            simulated_pit_stop_count=len(simulated_race.pit_stops),
            historical_pit_stop_count=len(pit_stops),
            simulated_tyre_stint_lengths=self._simulated_stint_lengths(simulated_race),
            historical_tyre_stint_lengths=self._historical_stint_lengths(laps),
        )

    @staticmethod
    def _simulated_stint_lengths(simulated_race: RaceResult) -> list[int]:
        """Calculate stint lengths from simulated lap compounds."""
        lengths: list[int] = []
        last_compound = None
        current_length = 0
        for lap in simulated_race.lap_results:
            if lap.compound != last_compound and current_length:
                lengths.append(current_length)
                current_length = 0
            last_compound = lap.compound
            current_length += 1
        if current_length:
            lengths.append(current_length)
        return lengths

    @staticmethod
    def _historical_stint_lengths(laps: list[HistoricalLap]) -> list[int]:
        """Calculate approximate stint lengths by driver and compound sequence."""
        lengths: list[int] = []
        grouped: dict[str, list[HistoricalLap]] = {}
        for lap in laps:
            grouped.setdefault(lap.driver_code, []).append(lap)
        for driver_laps in grouped.values():
            last_compound = None
            current_length = 0
            for lap in sorted(driver_laps, key=lambda item: item.lap_number):
                if lap.compound != last_compound and current_length:
                    lengths.append(current_length)
                    current_length = 0
                last_compound = lap.compound
                current_length += 1
            if current_length:
                lengths.append(current_length)
        return lengths
