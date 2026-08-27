import { createContext, useContext, useMemo, useState } from "react";
import type {
  CircuitRead,
  EngineerResponse,
  LiveRaceState,
  RaceConfig,
  RaceResult,
  ScenarioResponse,
  StrategyAnalysisResponse,
} from "../types/api";

interface RaceState {
  circuits: CircuitRead[];
  raceConfig: RaceConfig;
  simulation: RaceResult | null;
  strategy: StrategyAnalysisResponse | null;
  engineer: EngineerResponse | null;
  scenario: ScenarioResponse | null;
  liveRace: LiveRaceState | null;
  setCircuits: (circuits: CircuitRead[]) => void;
  setRaceConfig: (config: RaceConfig) => void;
  setSimulation: (result: RaceResult | null) => void;
  setStrategy: (result: StrategyAnalysisResponse | null) => void;
  setEngineer: (response: EngineerResponse | null) => void;
  setScenario: (response: ScenarioResponse | null) => void;
  setLiveRace: (state: LiveRaceState | null) => void;
}

const defaultRaceConfig: RaceConfig = {
  circuit: {
    circuit_name: "Monza",
    total_laps: 57,
    base_lap_time_seconds: 85,
    pit_lane_time_loss_seconds: 22,
    avg_track_temp: 35,
    avg_air_temp: 28,
  },
  starting_compound: "MEDIUM",
  starting_fuel_kg: 100,
  weather_seed_state: 42,
  safety_car_base_probability: 0.15,
};

const RaceContext = createContext<RaceState | null>(null);

export function RaceProvider({ children }: { children: React.ReactNode }) {
  const [circuits, setCircuits] = useState<CircuitRead[]>([]);
  const [raceConfig, setRaceConfig] = useState<RaceConfig>(defaultRaceConfig);
  const [simulation, setSimulation] = useState<RaceResult | null>(null);
  const [strategy, setStrategy] = useState<StrategyAnalysisResponse | null>(null);
  const [engineer, setEngineer] = useState<EngineerResponse | null>(null);
  const [scenario, setScenario] = useState<ScenarioResponse | null>(null);
  const [liveRace, setLiveRace] = useState<LiveRaceState | null>(null);

  const value = useMemo(
    () => ({
      circuits,
      raceConfig,
      simulation,
      strategy,
      engineer,
      scenario,
      liveRace,
      setCircuits,
      setRaceConfig,
      setSimulation,
      setStrategy,
      setEngineer,
      setScenario,
      setLiveRace,
    }),
    [circuits, raceConfig, simulation, strategy, engineer, scenario, liveRace],
  );

  return <RaceContext.Provider value={value}>{children}</RaceContext.Provider>;
}

export function useRaceStore(): RaceState {
  const value = useContext(RaceContext);
  if (!value) throw new Error("useRaceStore must be used inside RaceProvider");
  return value;
}
