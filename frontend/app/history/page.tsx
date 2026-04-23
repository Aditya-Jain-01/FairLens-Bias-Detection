"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowLeft, Clock, Activity } from "lucide-react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { API_BASE } from "@/lib/api";

type HistoryItem = {
  job_id: string;
  completed_at: string;
  dataset_info: {
    filename: string;
    total_rows: number;
    target_column: string;
  };
  overall_severity: string;
  fairness_score: number;
  metrics_passed: number;
  metrics_failed: number;
};

export default function HistoryPage() {
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchHistory() {
      try {
        const res = await fetch(`${API_BASE}/history`);
        if (!res.ok) throw new Error("Failed to fetch history");
        const data = await res.json();
        setHistory(data);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    }
    fetchHistory();
  }, []);

  const chartData = [...history].reverse().map((item) => ({
    date: new Date(item.completed_at).toLocaleDateString(),
    score: item.fairness_score,
    label: item.dataset_info?.filename || "Unknown",
    job_id: item.job_id
  }));

  return (
    <div className="min-h-screen bg-slate-50 pb-20">
      <header className="bg-white border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link href="/" className="text-slate-500 hover:text-slate-900 transition-colors">
              <ArrowLeft className="h-6 w-6" />
            </Link>
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-slate-900">Audit History</h1>
              <p className="text-sm text-slate-500">Compare past model fairness analyses over time</p>
            </div>
          </div>
          <Link href="/compare" className="btn-secondary px-4 py-2 text-sm bg-white">
            Compare Models Side-by-Side
          </Link>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        
        {/* Trend Chart */}
        {!loading && history.length > 1 && (
          <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
            <h2 className="text-lg font-semibold text-slate-900 mb-6 flex items-center gap-2">
              <Activity className="h-5 w-5 text-indigo-500" />
              FairLens Score Trend
            </h2>
            <div className="h-64 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                  <XAxis 
                    dataKey="date" 
                    axisLine={false}
                    tickLine={false}
                    tick={{ fill: '#64748b', fontSize: 12 }}
                    dy={10}
                  />
                  <YAxis 
                    domain={[0, 100]}
                    axisLine={false}
                    tickLine={false}
                    tick={{ fill: '#64748b', fontSize: 12 }}
                    dx={-10}
                  />
                  <Tooltip 
                    contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                    formatter={(value: any) => [`${value}/100`, 'FairLens Score']}
                    labelFormatter={(label, payload) => payload[0]?.payload.label || label}
                  />
                  <Line 
                    type="monotone" 
                    dataKey="score" 
                    stroke="#4f46e5" 
                    strokeWidth={3}
                    dot={{ fill: '#4f46e5', strokeWidth: 2, r: 4 }}
                    activeDot={{ r: 6 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}

        {/* History List */}
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
          <div className="px-6 py-4 border-b border-slate-200 flex items-center gap-2">
            <Clock className="h-5 w-5 text-slate-500" />
            <h2 className="text-lg font-semibold text-slate-900">Past Audits</h2>
          </div>
          
          {loading ? (
            <div className="p-12 text-center text-slate-500">Loading history...</div>
          ) : history.length === 0 ? (
            <div className="p-12 text-center text-slate-500">
              No completed audits found. <Link href="/upload" className="text-indigo-600 hover:underline">Start a new audit</Link> to see history.
            </div>
          ) : (
            <div className="divide-y divide-slate-200">
              {history.map((item) => (
                <Link 
                  key={item.job_id} 
                  href={`/results/${item.job_id}`}
                  className="block hover:bg-slate-50 transition-colors p-6"
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-base font-semibold text-slate-900 flex items-center gap-3">
                        {item.dataset_info?.filename || item.job_id.slice(0, 8)}
                        <span className={`px-2.5 py-0.5 rounded-full text-xs font-medium border ${
                          item.overall_severity === "low" ? "bg-green-50 text-green-700 border-green-200" :
                          item.overall_severity === "medium" ? "bg-yellow-50 text-yellow-700 border-yellow-200" :
                          "bg-red-50 text-red-700 border-red-200"
                        }`}>
                          {item.overall_severity.toUpperCase()}
                        </span>
                      </h3>
                      <div className="mt-1 flex items-center gap-4 text-sm text-slate-500">
                        <span>{new Date(item.completed_at).toLocaleString()}</span>
                        <span>•</span>
                        <span>{item.metrics_passed} passed, {item.metrics_failed} failed</span>
                        <span>•</span>
                        <span>Job: {item.job_id.split('-')[0]}</span>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-2xl font-bold text-slate-900">
                        {item.fairness_score}
                        <span className="text-sm font-normal text-slate-500 ml-1">/ 100</span>
                      </div>
                      <div className="text-xs text-slate-500">FairLens Score</div>
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
