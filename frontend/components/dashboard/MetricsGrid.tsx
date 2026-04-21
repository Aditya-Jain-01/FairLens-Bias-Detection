import React from "react";
import type { Results } from "@/lib/types";
import { AlertCircle, CheckCircle2 } from "lucide-react";

export const MetricsGrid = ({ metrics }: { metrics: Results["metrics"] }) => {
  return (
    <div className="grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-4">
      {Object.entries(metrics).map(([key, data]) => {
        const passed = data.passed;
        const title = key
          .split("_")
          .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
          .join(" ");

        return (
          <div
            key={key}
            className={`metric-border flex flex-col rounded-[28px] p-6 ${
              passed
                ? "shadow-[0_18px_40px_rgba(52,211,153,0.08)]"
                : "shadow-[0_18px_40px_rgba(244,63,94,0.08)]"
            }`}
          >
            <div className="mb-4 flex items-center justify-between">
              <h3 className="font-semibold text-neutral-900">{title}</h3>
              {passed ? (
                <CheckCircle2 className="h-6 w-6 text-emerald-400" />
              ) : (
                <AlertCircle className="h-6 w-6 text-rose-400" />
              )}
            </div>

            <div className="mb-2 flex items-baseline gap-2">
              <span className={`text-4xl font-bold tracking-tight ${passed ? "text-emerald-700" : "text-rose-700"}`}>
                {data.value.toFixed(3)}
              </span>
              <span className="text-sm font-medium text-neutral-600">threshold {data.threshold}</span>
            </div>

            <div className="mt-5">
              <div className="mb-4 h-1.5 rounded-full bg-neutral-200">
                <div
                  className={`h-1.5 rounded-full ${
                    passed
                      ? "bg-gradient-to-r from-emerald-500 to-emerald-400"
                      : "bg-gradient-to-r from-rose-500 to-rose-400"
                  }`}
                  style={{ width: `${Math.min(Math.abs(data.value) / Math.max(data.threshold, 0.001), 1) * 100}%` }}
                />
              </div>
              <p className="text-xs font-medium leading-relaxed text-neutral-600">{data.description}</p>
            </div>
          </div>
        );
      })}
    </div>
  );
};
