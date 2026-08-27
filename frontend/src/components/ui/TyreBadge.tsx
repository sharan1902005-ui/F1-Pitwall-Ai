import type { TyreCompound } from "../../types/api";

const tyreStyles: Record<TyreCompound, string> = {
  SOFT: "border-red-400/60 bg-red-500/15 text-red-100",
  MEDIUM: "border-yellow-300/60 bg-yellow-400/15 text-yellow-100",
  HARD: "border-slate-200/60 bg-white/10 text-white",
  INTERMEDIATE: "border-green-400/60 bg-green-500/15 text-green-100",
  WET: "border-blue-400/60 bg-blue-500/15 text-blue-100",
};

export function TyreBadge({ compound }: { compound: TyreCompound }) {
  return (
    <span className={`inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-black ${tyreStyles[compound]}`}>
      <span className="mr-1.5 h-2 w-2 rounded-full bg-current" />
      {compound}
    </span>
  );
}
