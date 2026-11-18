"""Deterministic analytics over persisted historical F1 records only."""
from __future__ import annotations
from statistics import median, pstdev
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.models.f1_reference import F1CircuitEvent, F1HistoricalLapTime, F1HistoricalPitStop, F1HistoricalRaceResult, F1QualifyingResult
from app.services.f1_reference_service import F1ReferenceNotFoundError

class F1HistoricalAnalyticsService:
    def driver(self, db: Session, driver_id: int, season: int | None) -> dict[str, object]: return self._performance(db, "driver_id", driver_id, season)
    def constructor(self, db: Session, constructor_id: int, season: int | None) -> dict[str, object]: return self._performance(db, "constructor_id", constructor_id, season)
    def _performance(self, db: Session, column: str, subject_id: int, season: int | None) -> dict[str, object]:
        field = getattr(F1HistoricalRaceResult, column); rows = list(db.scalars(select(F1HistoricalRaceResult).join(F1CircuitEvent).where(field == subject_id, *((F1CircuitEvent.season == season,) if season else ()))))
        if not rows: return {"subject_id": subject_id, "season": season, "starts": 0, "wins": 0, "podiums": 0, "points": None, "average_finish": None, "best_finish": None, "dnf_count": 0, "finish_rate": None, "average_qualifying_position": None, "average_grid_to_finish_change": None}
        finishes=[r.position for r in rows if r.position is not None]; points=[r.points for r in rows if r.points is not None]; dnf=sum(r.position is None for r in rows); changes=[r.grid_position-r.position for r in rows if r.grid_position is not None and r.position is not None]
        qualifying=[]
        if column == "driver_id": qualifying=list(db.scalars(select(F1QualifyingResult.position).join(F1CircuitEvent).where(F1QualifyingResult.driver_id == subject_id, *((F1CircuitEvent.season == season,) if season else ()))))
        return {"subject_id": subject_id, "season": season, "starts": len(rows), "wins": sum(x == 1 for x in finishes), "podiums": sum(x <= 3 for x in finishes), "points": sum(points) if points else None, "average_finish": sum(finishes)/len(finishes) if finishes else None, "best_finish": min(finishes) if finishes else None, "dnf_count": dnf, "finish_rate": len(finishes)/len(rows), "average_qualifying_position": sum(qualifying)/len(qualifying) if qualifying else None, "average_grid_to_finish_change": sum(changes)/len(changes) if changes else None}
    def lap(self, db: Session, event_id: int, driver_id: int | None) -> dict[str, object]:
        self._event(db,event_id); values=list(db.scalars(select(F1HistoricalLapTime.lap_time_seconds).where(F1HistoricalLapTime.event_id==event_id,*((F1HistoricalLapTime.driver_id==driver_id,) if driver_id else ()))))
        return {"event_id":event_id,"driver_id":driver_id,"samples":len(values),"average_lap_time_seconds":sum(values)/len(values) if values else None,"median_lap_time_seconds":median(values) if values else None,"fastest_lap_seconds":min(values) if values else None,"slowest_lap_seconds":max(values) if values else None,"variation_seconds":pstdev(values) if len(values)>1 else None}
    def pit(self, db: Session, event_id: int, driver_id: int | None) -> dict[str, object]:
        self._event(db,event_id); values=list(db.scalars(select(F1HistoricalPitStop.duration_seconds).where(F1HistoricalPitStop.event_id==event_id,*((F1HistoricalPitStop.driver_id==driver_id,) if driver_id else ()))))
        return {"event_id":event_id,"driver_id":driver_id,"samples":len(values),"average_duration_seconds":sum(values)/len(values) if values else None,"fastest_duration_seconds":min(values) if values else None,"slowest_duration_seconds":max(values) if values else None}
    def season(self, db: Session, season: int) -> dict[str, object]:
        rows=list(db.scalars(select(F1HistoricalRaceResult).join(F1CircuitEvent).where(F1CircuitEvent.season==season))); events={r.event_id for r in rows}; wins={}; points={}
        for r in rows:
            if r.position==1: wins[r.driver.provider_driver_id]=wins.get(r.driver.provider_driver_id,0)+1
            if r.points is not None: points[r.constructor.provider_constructor_id]=points.get(r.constructor.provider_constructor_id,0)+r.points
        return {"season":season,"imported_events":len(events),"imported_results":len(rows),"classified_results":sum(r.position is not None for r in rows),"dnfs":sum(r.position is None for r in rows),"driver_wins":wins,"constructor_points":points}
    @staticmethod
    def _event(db: Session,event_id:int)->None:
        if db.get(F1CircuitEvent,event_id) is None: raise F1ReferenceNotFoundError("Historical event not found")
