"""Read-only historical context; never an input to the simulation strategy engine."""
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.models.f1_reference import F1CircuitEvent,F1HistoricalLapTime,F1HistoricalPitStop,F1HistoricalRaceResult

class HistoricalStrategyBenchmarkService:
 def benchmark(self,db:Session,season:int|None,event_id:int|None,circuit_id:int|None)->dict[str,object]:
  event_filters=[]
  if season is not None:event_filters.append(F1CircuitEvent.season==season)
  if event_id is not None:event_filters.append(F1CircuitEvent.id==event_id)
  if circuit_id is not None:event_filters.append(F1CircuitEvent.circuit_id==circuit_id)
  events=list(db.scalars(select(F1CircuitEvent.id).where(*event_filters)))
  if not events:return {"season":season,"event_id":event_id,"circuit_id":circuit_id,"races_used":0,"result_samples":0,"pit_stop_samples":0,"lap_samples":0,"average_pit_stops_per_race":None,"average_pit_stop_duration_seconds":None,"average_lap_time_seconds":None,"average_grid_to_finish_change":None,"note":"No imported historical records match this scope."}
  ids=list(events); results=list(db.scalars(select(F1HistoricalRaceResult).where(F1HistoricalRaceResult.event_id.in_(ids)))); pits=list(db.scalars(select(F1HistoricalPitStop).where(F1HistoricalPitStop.event_id.in_(ids)))); laps=list(db.scalars(select(F1HistoricalLapTime.lap_time_seconds).where(F1HistoricalLapTime.event_id.in_(ids))))
  changes=[r.grid_position-r.position for r in results if r.grid_position is not None and r.position is not None]
  return {"season":season,"event_id":event_id,"circuit_id":circuit_id,"races_used":len(ids),"result_samples":len(results),"pit_stop_samples":len(pits),"lap_samples":len(laps),"average_pit_stops_per_race":len(pits)/len(ids),"average_pit_stop_duration_seconds":sum(p.duration_seconds for p in pits)/len(pits) if pits else None,"average_lap_time_seconds":sum(laps)/len(laps) if laps else None,"average_grid_to_finish_change":sum(changes)/len(changes) if changes else None,"note":"Historical benchmark only; it does not change simulated strategy, weather, tyres, pit-lane loss, or confidence."}
