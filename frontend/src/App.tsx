import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { AppShell } from "./components/layout/AppShell";
import { RaceProvider } from "./store/raceStore";
import { DashboardPage } from "./pages/DashboardPage";
import { RaceSetupPage } from "./pages/RaceSetupPage";
import { LiveSimulationPage } from "./pages/LiveSimulationPage";
import { LiveRaceControlPage } from "./pages/LiveRaceControlPage";
import { CompetitiveLabPage } from "./pages/CompetitiveLabPage";
import { ChampionshipPage } from "./pages/ChampionshipPage";
import { StrategyLabPage } from "./pages/StrategyLabPage";
import { WeatherPage } from "./pages/WeatherPage";
import { EngineerPage } from "./pages/EngineerPage";
import { CircuitsPage } from "./pages/CircuitsPage";
import type { PageId } from "./types/navigation";

function AppContent() {
  const [page, setPage] = useState<PageId>("dashboard");

  useEffect(() => {
    document.title = "PitWall AI";
  }, []);

  const pages: Record<PageId, ReactNode> = {
    dashboard: <DashboardPage setPage={setPage} />,
    setup: <RaceSetupPage />,
    simulation: <LiveSimulationPage setPage={setPage} />,
    liveRace: <LiveRaceControlPage setPage={setPage} />,
    competitive: <CompetitiveLabPage />,
    championship: <ChampionshipPage />,
    strategy: <StrategyLabPage setPage={setPage} />,
    weather: <WeatherPage setPage={setPage} />,
    engineer: <EngineerPage setPage={setPage} />,
    circuits: <CircuitsPage setPage={setPage} />,
  };

  return (
    <AppShell page={page} setPage={setPage}>
      {pages[page]}
    </AppShell>
  );
}

export default function App() {
  return (
    <RaceProvider>
      <AppContent />
    </RaceProvider>
  );
}
