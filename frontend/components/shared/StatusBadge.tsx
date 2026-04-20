import React from "react";

export const StatusBadge = ({ severity }: { severity: string }) => {
  const colors: Record<string, string> = {
    critical: "border-fuchsia-400/30 bg-fuchsia-500/10 text-fuchsia-200",
    high: "border-rose-400/30 bg-rose-500/10 text-rose-200",
    medium: "border-amber-300/30 bg-amber-400/10 text-amber-100",
    low: "border-emerald-400/30 bg-emerald-500/10 text-emerald-200",
    none: "border-cyan-400/20 bg-cyan-400/10 text-cyan-100",
  };

  const selectedClass = colors[severity.toLowerCase()] || colors.none;

  return (
    <span className={`rounded-full border px-4 py-1.5 text-sm font-bold capitalize ${selectedClass}`}>
      {severity} Bias
    </span>
  );
};
