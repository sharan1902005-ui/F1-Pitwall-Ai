export function StatusPill({
  tone = "blue",
  children,
}: {
  tone?: "red" | "blue" | "green" | "yellow" | "purple" | "neutral";
  children: React.ReactNode;
}) {
  const tones = {
    red: "border-pit-red/40 bg-pit-red/12 text-red-200",
    blue: "border-pit-blue/40 bg-pit-blue/12 text-blue-200",
    green: "border-pit-green/40 bg-pit-green/12 text-green-200",
    yellow: "border-pit-yellow/40 bg-pit-yellow/12 text-yellow-200",
    purple: "border-pit-purple/40 bg-pit-purple/12 text-purple-200",
    neutral: "border-white/15 bg-white/6 text-slate-200",
  } as const;
  return (
    <span className={`inline-flex items-center rounded border px-2 py-1 text-xs font-semibold uppercase tracking-wide ${tones[tone]}`}>
      {children}
    </span>
  );
}
