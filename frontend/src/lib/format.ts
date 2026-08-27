import type { StrategyStint } from "../types/api";

export function formatRaceTime(seconds: number | null | undefined): string {
  if (seconds == null || Number.isNaN(seconds)) return "--:--.---";
  const minutes = Math.floor(seconds / 60);
  const remaining = seconds - minutes * 60;
  return `${minutes}:${remaining.toFixed(3).padStart(6, "0")}`;
}

export function percent(value: number | null | undefined, digits = 0): string {
  if (value == null || Number.isNaN(value)) return "--";
  return `${(value * 100).toFixed(digits)}%`;
}

export function strategyLabel(stints: StrategyStint[] | undefined): string {
  if (!stints || stints.length === 0) return "No strategy";
  return stints.map((stint) => stint.compound).join(" -> ");
}

export function delta(value: number): string {
  const sign = value >= 0 ? "+" : "";
  return `${sign}${value.toFixed(3)}s`;
}
