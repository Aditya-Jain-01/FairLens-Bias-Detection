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
        const points = [];
        for (let t = 0.1; t <= 0.91; t += 0.1) {
          try {
            const res = await getThreshold(job_id, parseFloat(t.toFixed(1)));
            points.push({
              threshold: parseFloat(t.toFixed(1)),
              accuracy: res.accuracy,
              disparity: res.demographic_parity_difference,
              ...res.per_group,
            });
          } catch {
            const rounded = Math.round(t * 10) / 10;
            const mockData = mockThresholdSeries[rounded] || mockThresholdSeries[0.5];
            points.push({
              threshold: rounded,
              accuracy: mockData.accuracy,
              disparity: mockData.demographic_parity_difference,
            });
          }
        }
        setData(
          points.length > 0
            ? points
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
        <h3 className="mb-2 text-xl font-bold text-white">Threshold Calibrator</h3>
        <p className="text-sm text-cyan-50/55">
          Fine-tune the decision threshold to balance model accuracy against demographic parity.
        </p>
        {hasError && <p className="mt-2 text-xs text-amber-200">Using fallback threshold data while the API is unavailable.</p>}
      </div>

      {data.length === 0 && !loading ? (
        <div className="flex h-64 w-full items-center justify-center rounded-[24px] border border-dashed border-cyan-400/15 bg-cyan-400/5">
          <p className="text-cyan-100/45">Loading threshold data...</p>
        </div>
      ) : (
        <div className="mb-8 h-64 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(160,255,243,0.08)" />
              <XAxis dataKey="threshold" type="number" domain={[0.1, 0.9]} tickCount={9} stroke="rgba(212,255,249,0.5)" />
              <YAxis yAxisId="left" domain={[0, 1]} tickFormatter={(v) => `${(v * 100).toFixed(0)}%`} stroke="rgba(212,255,249,0.5)" />
              <YAxis yAxisId="right" orientation="right" domain={[0, 0.5]} stroke="rgba(212,255,249,0.5)" />
              <Tooltip
                contentStyle={{
                  background: "rgba(8, 18, 31, 0.96)",
                  border: "1px solid rgba(104, 246, 232, 0.18)",
                  borderRadius: "18px",
                  color: "#eafffb",
                }}
              />
              <Legend wrapperStyle={{ color: "rgba(232,255,251,0.72)" }} />
              <Line yAxisId="left" type="monotone" dataKey="accuracy" stroke="#62f4d5" strokeWidth={3} name="Accuracy" dot={{ r: 3, fill: "#62f4d5" }} />
              <Line yAxisId="right" type="monotone" dataKey="disparity" stroke="#cb58ff" strokeWidth={3} name="Demographic Disparity" dot={{ r: 3, fill: "#cb58ff" }} />
              <ReferenceLine
                x={threshold}
                stroke="#f3f7ff"
                strokeWidth={1.5}
                strokeDasharray="3 3"
                yAxisId="left"
                label={{ position: "top", value: "Current", fill: "#cffff8" }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      <div className="surface-muted mb-6 rounded-[24px] border border-cyan-400/10 p-6">
        <div className="mb-4 flex justify-between">
          <span className="font-semibold text-cyan-50">Set Decision Threshold</span>
          <span className="rounded-full bg-cyan-300/12 px-3 py-1 font-bold text-cyan-200">{threshold.toFixed(2)}</span>
        </div>
        <input
          type="range"
          min="0.1"
          max="0.9"
          step="0.05"
          value={threshold}
          onChange={(e) => setThreshold(parseFloat(e.target.value))}
          className="h-2 w-full cursor-pointer appearance-none rounded-lg accent-cyan-300"
        />
      </div>

      {activePoint && (
        <div className="grid grid-cols-2 gap-4">
          <div className="metric-border rounded-[24px] p-4">
            <div className="mb-1 text-xs font-semibold uppercase tracking-wider text-cyan-100/42">Projected Accuracy</div>
            <div className="text-2xl font-bold text-cyan-200">{(activePoint.accuracy * 100).toFixed(1)}%</div>
          </div>
          <div className="metric-border rounded-[24px] p-4">
            <div className="mb-1 text-xs font-semibold uppercase tracking-wider text-cyan-100/42">Projected Disparity</div>
            <div className="text-2xl font-bold text-fuchsia-200">{(activePoint.disparity * 100).toFixed(1)}%</div>
          </div>
        </div>
      )}
    </div>
  );
};
