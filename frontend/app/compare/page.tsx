"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowLeft, GitCompare, ArrowUpRight, ArrowDownRight, Minus } from "lucide-react";
import { API_BASE } from "@/lib/api";
import { Results } from "@/lib/types";

export default function ComparePage() {
  const [history, setHistory] = useState<any[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(true);
  
  const [baselineId, setBaselineId] = useState("");
  const [candidateId, setCandidateId] = useState("");
  
  const [baselineData, setBaselineData] = useState<Results | null>(null);
  const [candidateData, setCandidateData] = useState<Results | null>(null);
  const [loadingCompare, setLoadingCompare] = useState(false);

  useEffect(() => {
    fetch(`${API_BASE}/history`)
      .then(res => res.json())
      .then(data => setHistory(data))
      .catch(console.error)
      .finally(() => setLoadingHistory(false));
  }, []);

  const loadComparison = async () => {
    if (!baselineId || !candidateId) return;
    setLoadingCompare(true);
    try {
      const [res1, res2] = await Promise.all([
        fetch(`${API_BASE}/results/${baselineId}`),
        fetch(`${API_BASE}/results/${candidateId}`)
      ]);
      const data1 = await res1.json();
      const data2 = await res2.json();
      setBaselineData(data1);
      setCandidateData(data2);
    } catch (e) {
      console.error(e);
    } finally {
      setLoadingCompare(false);
    }
  };

  const renderDelta = (metric: string, val1: number, val2: number, lowerIsBetter: boolean) => {
    const diff = val2 - val1;
    if (Math.abs(diff) < 0.001) return <div className="flex items-center text-slate-400 font-medium"><Minus className="h-4 w-4 mr-1" /> No change</div>;
    
    // Improvement means diff < 0 if lower is better, or diff > 0 if higher is better.
    // Disparate Impact ideal is 1.0, so it's a bit tricky. We'll simplify: closer to ideal is better.
    let isBetter = false;
    if (metric === "disparate_impact") {
      isBetter = Math.abs(1 - val2) < Math.abs(1 - val1);
    } else {
      isBetter = lowerIsBetter ? diff < 0 : diff > 0;
    }

    return (
      <div className={`flex items-center font-medium ${isBetter ? "text-emerald-600" : "text-rose-600"}`}>
        {diff > 0 ? <ArrowUpRight className="h-4 w-4 mr-1" /> : <ArrowDownRight className="h-4 w-4 mr-1" />}
        {(diff > 0 ? "+" : "")}{diff.toFixed(3)}
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-slate-50 pb-20">
      <header className="bg-white border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link href="/history" className="text-slate-500 hover:text-slate-900 transition-colors">
              <ArrowLeft className="h-6 w-6" />
            </Link>
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-slate-900">Compare Models</h1>
              <p className="text-sm text-slate-500">Analyze fairness improvements between two audits</p>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 items-end">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">Baseline Model</label>
              <select 
                title="Select baseline model"
                className="w-full rounded-xl border border-slate-300 py-3 px-4 outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                value={baselineId}
                onChange={(e) => setBaselineId(e.target.value)}
                disabled={loadingHistory}
              >
                <option value="">Select a previous audit...</option>
                {history.map(h => (
                  <option key={h.job_id} value={h.job_id}>
                    {h.dataset_info?.filename} ({new Date(h.completed_at).toLocaleDateString()}) - Score: {h.fairness_score}
                  </option>
                ))}
              </select>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">Candidate Model</label>
              <select 
                title="Select candidate model"
                className="w-full rounded-xl border border-slate-300 py-3 px-4 outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                value={candidateId}
                onChange={(e) => setCandidateId(e.target.value)}
                disabled={loadingHistory}
              >
                <option value="">Select a newer audit...</option>
                {history.map(h => (
                  <option key={h.job_id} value={h.job_id}>
                    {h.dataset_info?.filename} ({new Date(h.completed_at).toLocaleDateString()}) - Score: {h.fairness_score}
                  </option>
                ))}
              </select>
            </div>
            
            <button 
              onClick={loadComparison}
              disabled={!baselineId || !candidateId || loadingCompare || baselineId === candidateId}
              className="btn-primary py-3 px-4 h-[50px] disabled:opacity-50 flex items-center justify-center gap-2"
            >
              <GitCompare className="h-5 w-5" />
              Compare Results
            </button>
          </div>
        </div>

        {baselineData && candidateData && (
          <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-200 bg-slate-50 grid grid-cols-4 gap-4 font-semibold text-slate-700">
              <div className="col-span-1">Metric</div>
              <div className="col-span-1">Baseline</div>
              <div className="col-span-1">Candidate</div>
              <div className="col-span-1">Delta</div>
            </div>
            
            <div className="divide-y divide-slate-200">
              {/* FairLens Score */}
              <div className="px-6 py-5 grid grid-cols-4 gap-4 items-center hover:bg-slate-50 transition-colors">
                <div className="col-span-1">
                  <div className="font-semibold text-slate-900">FairLens Score</div>
                  <div className="text-xs text-slate-500 font-normal mt-1">Higher is better (0-100)</div>
                </div>
                <div className="col-span-1 font-bold text-slate-900 text-lg">{baselineData.fairness_score?.score || 0}</div>
                <div className="col-span-1 font-bold text-slate-900 text-lg">{candidateData.fairness_score?.score || 0}</div>
                <div className="col-span-1">
                  {renderDelta("score", baselineData.fairness_score?.score || 0, candidateData.fairness_score?.score || 0, false)}
                </div>
              </div>

              {/* Other Metrics processing */}
              {Object.keys(baselineData.metrics).map(metricKey => {
                const bMetric = (baselineData.metrics as any)[metricKey];
                const cMetric = (candidateData.metrics as any)[metricKey];
                if (!bMetric || !cMetric) return null;
                
                return (
                  <div key={metricKey} className="px-6 py-5 grid grid-cols-4 gap-4 items-center hover:bg-slate-50 transition-colors">
                    <div className="col-span-1">
                      <div className="font-semibold text-slate-900">{bMetric.name}</div>
                      <div className="text-xs text-slate-500 font-normal mt-1 max-w-[200px] truncate" title={bMetric.description}>
                        {bMetric.description}
                      </div>
                    </div>
                    
                    <div className="col-span-1 flex items-center gap-2">
                       <span className={`w-2 h-2 rounded-full ${bMetric.passed ? 'bg-green-500' : 'bg-red-500'}`}></span>
                       <span className="font-medium text-slate-900">{bMetric.value.toFixed(3)}</span>
                    </div>
                    
                    <div className="col-span-1 flex items-center gap-2">
                       <span className={`w-2 h-2 rounded-full ${cMetric.passed ? 'bg-green-500' : 'bg-red-500'}`}></span>
                       <span className="font-medium text-slate-900">{cMetric.value.toFixed(3)}</span>
                    </div>
                    
                    <div className="col-span-1">
                      {renderDelta(metricKey, bMetric.value, cMetric.value, metricKey !== "disparate_impact")}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
