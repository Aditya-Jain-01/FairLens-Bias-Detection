import React from 'react';

export const StatusBadge = ({ severity }: { severity: string }) => {
  const colors: Record<string, string> = {
    critical: "bg-purple-100 text-purple-700 border-purple-200",
    high: "bg-red-100 text-red-700 border-red-200",
    medium: "bg-orange-100 text-orange-700 border-orange-200",
    low: "bg-green-100 text-green-700 border-green-200",
    none: "bg-slate-100 text-slate-700 border-slate-200",
  };
  
  const selectedClass = colors[severity.toLowerCase()] || colors.none;
  
  return (
    <span className={`px-4 py-1.5 rounded-full text-sm font-bold border capitalize ${selectedClass}`}>
      {severity} Bias
    </span>
  );
};
