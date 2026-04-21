import React from "react";

export const StatusBadge = ({ severity }: { severity: string }) => {
  const colors: Record<string, string> = {
    critical: "border-fuchsia-600/30 bg-fuchsia-500/10 text-fuchsia-800",
    high: "border-rose-600/30 bg-rose-500/10 text-rose-800",
    medium: "border-amber-600/30 bg-amber-400/10 text-amber-800",
    low: "border-emerald-600/30 bg-emerald-500/10 text-emerald-800",
    none: "border-neutral-400/20 bg-neutral-100 text-neutral-800",
  };

  const selectedClass = colors[severity.toLowerCase()] || colors.none;

  return (
    <span className={`rounded-full border px-4 py-1.5 text-sm font-bold capitalize ${selectedClass}`}>
      {severity} Bias
    </span>
  );
};
