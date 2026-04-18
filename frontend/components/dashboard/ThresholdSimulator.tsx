"use client";
import React, { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceLine } from 'recharts';
import { getThreshold } from '@/lib/api';
import { mockThresholdSeries } from '@/lib/mockData';

export const ThresholdSimulator = ({ job_id, initialThreshold, currentResults }: { job_id: string, initialThreshold: number, currentResults: any }) => {
  const [threshold, setThreshold] = useState(initialThreshold);
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [hasError, setHasError] = useState(false);

  // Extract primary protected attribute from results
  const protectedAttr: string | undefined =
    currentResults?.dataset_info?.protected_attributes?.[0];

  // Use the mock or initial results to seed the chart immediately
  useEffect(() => {
    // Generate data range 0.1 to 0.9. Real system would fetch each or prefetch.
    // Assuming mock pre-fetches it. We'll simulate fetching if mock is not available.
    const runFetch = async () => {
      setLoading(true);
      setHasError(false);
      try {
        const points = [];
        for(let t=0.1; t<=0.91; t+=0.1) {
          try {
            const res = await getThreshold(job_id, parseFloat(t.toFixed(1)), protectedAttr);
            points.push({
              threshold: parseFloat(t.toFixed(1)),
              accuracy: res.accuracy,
              disparity: res.demographic_parity_difference,
              ...res.per_group
            });
          } catch (err) {
            // Fallback to mock data if endpoint fails
            const rounded = Math.round(t * 10) / 10;
            const mockData = mockThresholdSeries[rounded] || mockThresholdSeries[0.5];
            points.push({
              threshold: rounded,
              accuracy: mockData.accuracy,
              disparity: mockData.demographic_parity_difference,
            });
          }
        }
        setData(points.length > 0 ? points : Object.entries(mockThresholdSeries).map(([t, d]) => ({
          threshold: parseFloat(t),
          accuracy: d.accuracy,
          disparity: d.demographic_parity_difference,
        })));
      } catch (err) {
        console.error("Threshold fetch error:", err);
        setHasError(true);
        // Use mock data as fallback
        setData(Object.entries(mockThresholdSeries).map(([t, d]) => ({
          threshold: parseFloat(t),
          accuracy: d.accuracy,
          disparity: d.demographic_parity_difference,
        })));
      }
      setLoading(false);
    };
    runFetch();
  }, [job_id]);

  const activePoint = data.find(d => Math.abs(d.threshold - threshold) < 0.05);

  return (
    <div className="glass p-8 rounded-2xl">
      <div className="mb-8">
        <h3 className="text-xl font-bold text-slate-900 mb-2">Threshold Calibrator</h3>
        <p className="text-sm text-slate-500">Fine-tune your decision threshold to balance Model Accuracy against Demographic Parity (Fairness).</p>
        {hasError && <p className="text-xs text-amber-600 mt-2">📊 Using simulated data (API unavailable)</p>}
      </div>

      {data.length === 0 && !loading ? (
        <div className="h-64 w-full flex items-center justify-center bg-slate-50 rounded-lg border-2 border-dashed border-slate-200">
          <p className="text-slate-400">Loading threshold data...</p>
        </div>
      ) : (
        <div className="h-64 w-full mb-8">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
              <XAxis dataKey="threshold" type="number" domain={[0.1, 0.9]} tickCount={9} />
              <YAxis yAxisId="left" domain={[0, 1]} tickFormatter={v => `${(v*100).toFixed(0)}%`} />
              <YAxis yAxisId="right" orientation="right" domain={[0, 0.5]} />
              <Tooltip />
              <Legend />
              <Line yAxisId="left" type="monotone" dataKey="accuracy" stroke="#4f46e5" strokeWidth={3} name="Accuracy" dot={{r: 4}} />
              <Line yAxisId="right" type="monotone" dataKey="disparity" stroke="#f43f5e" strokeWidth={3} name="Demographic Disparity" dot={{r: 4}} />
              <ReferenceLine x={threshold} stroke="#14b8a6" strokeWidth={2} strokeDasharray="3 3" yAxisId="left" label={{ position: 'top', value: 'Current' }}/>
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      <div className="bg-slate-50 p-6 rounded-xl border border-slate-100 mb-6">
        <div className="flex justify-between mb-4">
          <span className="font-semibold text-slate-700">Set Decision Threshold:</span>
          <span className="font-bold text-indigo-600 bg-indigo-100 px-3 py-1 rounded-full">{threshold.toFixed(2)}</span>
        </div>
        <input 
          type="range" 
          min="0.1" 
          max="0.9" 
          step="0.05"
          value={threshold}
          onChange={(e) => setThreshold(parseFloat(e.target.value))}
          className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-indigo-600"
        />
      </div>

      {activePoint && (
        <div className="grid grid-cols-2 gap-4">
           <div className="bg-indigo-50 p-4 rounded-lg">
             <div className="text-xs font-semibold text-indigo-400 uppercase tracking-wider mb-1">Projected Accuracy</div>
             <div className="text-2xl font-bold text-indigo-700">{(activePoint.accuracy * 100).toFixed(1)}%</div>
           </div>
           <div className="bg-rose-50 p-4 rounded-lg">
             <div className="text-xs font-semibold text-rose-400 uppercase tracking-wider mb-1">Projected Disparity</div>
             <div className="text-2xl font-bold text-rose-700">{(activePoint.disparity * 100).toFixed(1)}%</div>
           </div>
        </div>
      )}
    </div>
  );
};
