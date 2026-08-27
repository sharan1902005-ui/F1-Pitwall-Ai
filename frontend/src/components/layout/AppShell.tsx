import {
  Bot,
  CloudRain,
  Gauge,
  LayoutDashboard,
  Map,
  PlayCircle,
  Settings2,
  Trophy,
  Radio,
  Users,
  Crown,
} from "lucide-react";
import type { PageId } from "../../types/navigation";
import { StatusPill } from "../ui/StatusPill";

const navItems: Array<{ id: PageId; label: string; icon: React.ComponentType<{ className?: string }> }> = [
  { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
  { id: "setup", label: "Race Setup", icon: Settings2 },
  { id: "simulation", label: "Live Simulation", icon: PlayCircle },
  { id: "liveRace", label: "Live Race Control", icon: Radio },
  { id: "competitive", label: "Competitive Lab", icon: Users },
  { id: "championship", label: "Championship", icon: Crown },
  { id: "strategy", label: "Strategy Lab", icon: Trophy },
  { id: "weather", label: "Weather", icon: CloudRain },
  { id: "engineer", label: "AI Race Engineer", icon: Bot },
  { id: "circuits", label: "Circuits", icon: Map },
];

export function AppShell({
  page,
  setPage,
  children,
}: {
  page: PageId;
  setPage: (page: PageId) => void;
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen text-slate-100">
      <header className="sticky top-0 z-20 border-b border-white/10 bg-pit-black/92 backdrop-blur">
        <div className="flex min-h-16 items-center justify-between gap-4 px-4 lg:px-6">
          <button onClick={() => setPage("dashboard")} className="text-left">
            <div className="text-xl font-black tracking-[0.16em] text-white">PITWALL AI</div>
            <div className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-400">AI-Powered Race Strategy Simulator</div>
          </button>
          <div className="hidden items-center gap-3 md:flex">
            <StatusPill tone="red">Race Control</StatusPill>
            <StatusPill tone="green">Live / Simulation</StatusPill>
          </div>
        </div>
      </header>
      <div className="grid min-h-[calc(100vh-4rem)] grid-cols-1 lg:grid-cols-[250px_1fr]">
        <aside className="border-b border-white/10 bg-pit-panel/82 p-3 lg:border-b-0 lg:border-r">
          <nav className="grid grid-cols-2 gap-2 sm:grid-cols-4 lg:grid-cols-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const active = item.id === page;
              return (
                <button
                  key={item.id}
                  onClick={() => setPage(item.id)}
                  className={`flex items-center gap-3 rounded-md px-3 py-3 text-sm font-semibold transition ${
                    active
                      ? "bg-pit-red text-white shadow-lg shadow-pit-red/20"
                      : "text-slate-300 hover:bg-white/8 hover:text-white"
                  }`}
                >
                  <Icon className="h-4 w-4" />
                  <span>{item.label}</span>
                </button>
              );
            })}
          </nav>
          <div className="mt-6 hidden rounded-lg border border-white/10 bg-black/20 p-3 lg:block">
            <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.18em] text-slate-400">
              <Gauge className="h-4 w-4 text-pit-blue" />
              Telemetry Link
            </div>
            <div className="mt-3 h-1.5 rounded-full bg-white/10">
              <div className="h-full w-4/5 rounded-full bg-pit-green" />
            </div>
          </div>
        </aside>
        <main className="p-4 lg:p-6">{children}</main>
      </div>
    </div>
  );
}
