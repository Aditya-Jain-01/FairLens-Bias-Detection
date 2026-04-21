"use client";
import React, { useEffect, useState } from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { getThreshold } from "@/lib/api";
import { mockThresholdSeries } from "@/lib/mockData";

export const ThresholdSimulator = ({
  job_id,
  initialThreshold,
}: {
  job_id: string;
  initialThreshold: number;
  currentResults: unknown;
}) => {
  const [threshold, setThreshold] = useState(initialThreshold);
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [hasError, setHasError] = useState(false);

  useEffect(() => {
    const runFetch = async () => {
      setLoading(true);
      setHasError(false);
      try {
        const thresholds = Array.from({ length: 9 }, (_, i) =>
          parseFloat((0.1 + i * 0.1).toFixed(1))
        );

        // Fetch all 9 threshold points in parallel instead of sequentially
        const results = await Promise.all(
          thresholds.map(async (t) => {
            try {
              const res = await getThreshold(job_id, t);
              return {
                threshold: t,
                accuracy: res.accuracy,
                disparity: res.demographic_parity_difference,
                ...res.per_group,
              };
            } catch {
              const mockData = mockThresholdSeries[t] || mockThresholdSeries[0.5];
              return {
                threshold: t,
                accuracy: mockData.accuracy,
                disparity: mockData.demographic_parity_difference,
              };
            }
          })
        );

        setData(
          results.length > 0
            ? results
            : Object.entries(mockThresholdSeries).map(([t, d]) => ({
                threshold: parseFloat(t),
                accuracy: d.accuracy,
                disparity: d.demographic_parity_difference,
              }))
        );
      } catch (err) {
        console.error("Threshold fetch error:", err);
        setHasError(true);
        setData(
          Object.entries(mockThresholdSeries).map(([t, d]) => ({
            threshold: parseFloat(t),
            accuracy: d.accuracy,
            disparity: d.demographic_parity_difference,
          }))
        );
      }
      setLoading(false);
    };
    runFetch();
  }, [job_id]);


  const activePoint = data.find((d) => Math.abs(d.threshold - threshold) < 0.05);

  return (
    <div className="panel-soft p-8">
      <div className="mb-8">
        <h3 className="mb-2 text-xl font-bold text-neutral-900">Threshold Calibrator</h3>
        <p className="text-sm text-neutral-600">
          Fine-tune the decision threshold to balance model accuracy against demographic parity.
        </p>
        {hasError && <p className="mt-2 text-xs text-amber-700">Using fallback threshold data while the API is unavailable.</p>}
      </div>

      {data.length === 0 && !loading ? (
        <div className="flex h-64 w-full items-center justify-center rounded-[24px] border border-dashed border-neutral-200 bg-neutral-50">
          <p className="text-neutral-500">Loading threshold data...</p>
        </div>
      ) : (
        <div className="mb-8 h-64 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e5e5" />
              <XAxis dataKey="threshold" type="number" domain={[0.1, 0.9]} tickCount={9} stroke="#a3a3a3" />
              <YAxis yAxisId="left" domain={[0, 1]} tickFormatter={(v) => `${(v * 100).toFixed(0)}%`} stroke="#a3a3a3" />
              <YAxis yAxisId="right" orientation="right" domain={[0, 0.5]} stroke="#a3a3a3" />
              <Tooltip
                contentStyle={{
                  background: "#ffffff",
                  border: "1px solid #e5e5e5",
                  borderRadius: "18px",
                  color: "#171717",
                }}
              />
              <Legend wrapperStyle={{ color: "#404040" }} />
              <Line yAxisId="left" type="monotone" dataKey="accuracy" stroke="#62f4d5" strokeWidth={3} name="Accuracy" dot={{ r: 3, fill: "#62f4d5" }} />
              <Line yAxisId="right" type="monotone" dataKey="disparity" stroke="#cb58ff" strokeWidth={3} name="Demographic Disparity" dot={{ r: 3, fill: "#cb58ff" }} />
              <ReferenceLine
                x={threshold}
                stroke="#a3a3a3"
                strokeWidth={1.5}
                strokeDasharray="3 3"
                yAxisId="left"
                label={{ position: "top", value: "Current", fill: "#525252" }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      <div className="surface-muted mb-6 rounded-[24px] border border-neutral-200 p-6">
        <div className="mb-4 flex justify-between">
          <span className="font-semibold text-neutral-900">Set Decision Threshold</span>
          <span className="rounded-full bg-cyan-100 px-3 py-1 font-bold text-cyan-700">{threshold.toFixed(2)}</span>
        </div>
        <input
          type="range"
          min="0.1"
          max="0.9"
          step="0.05"
          value={threshold}
          onChange={(e) => setThreshold(parseFloat(e.target.value))}
          className="h-2 w-full cursor-pointer appearance-none rounded-lg accent-cyan-600"
        />
      </div>

      {activePoint && (
        <div className="grid grid-cols-2 gap-4">
          <div className="metric-border rounded-[24px] p-4">
            <div className="mb-1 text-xs font-semibold uppercase tracking-wider text-neutral-500">Projected Accuracy</div>
            <div className="text-2xl font-bold text-cyan-700">{(activePoint.accuracy * 100).toFixed(1)}%</div>
          </div>
          <div className="metric-border rounded-[24px] p-4">
            <div className="mb-1 text-xs font-semibold uppercase tracking-wider text-neutral-500">Projected Disparity</div>
            <div className="text-2xl font-bold text-fuchsia-700">{(activePoint.disparity * 100).toFixed(1)}%</div>
          </div>
        </div>
      )}
    </div>
  );
};
