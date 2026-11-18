import { StatusPill } from "./StatusPill";

export type DataState = "available" | "not-imported" | "unavailable";

const copy: Record<DataState, { label: string; tone: "green" | "yellow" | "neutral" }> = {
  available: { label: "Data available", tone: "green" },
  "not-imported": { label: "Not yet imported", tone: "yellow" },
  unavailable: { label: "Unavailable from provider", tone: "neutral" },
};

export function DataStateBadge({ state }: { state: DataState }) {
  const item = copy[state];
  return <StatusPill tone={item.tone}>{item.label}</StatusPill>;
}
