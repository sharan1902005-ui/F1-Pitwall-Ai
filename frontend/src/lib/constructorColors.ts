export const constructorColors: Record<string, string> = {
  ferrari: "#ef4444", mercedes: "#38d996", red_bull: "#3b82f6", mclaren: "#f97316", aston_martin: "#22c55e", alpine: "#ec4899", williams: "#60a5fa", haas: "#9ca3af", sauber: "#84cc16", rb: "#6366f1",
};

export function constructorColor(identifier: string) { return constructorColors[identifier] ?? "#94a3b8"; }
