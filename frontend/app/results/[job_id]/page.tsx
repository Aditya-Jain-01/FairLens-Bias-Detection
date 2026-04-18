"use client";
import React, { useEffect, useState } from 'react';
import { Results, Explanation } from '@/lib/types';
import { getResults, streamExplanation, downloadReport } from '@/lib/api';
import { StatusBadge } from '@/components/shared/StatusBadge';
import { MetricsGrid } from '@/components/dashboard/MetricsGrid';
import { ThresholdSimulator } from '@/components/dashboard/ThresholdSimulator';
import { Activity, ShieldCheck, Download, Sparkles } from 'lucide-react';

export default function ResultsDashboard({ params }: { params: { job_id: string } }) {
  const [results, setResults] = useState<Results | null>(null);
  const [explanation, setExplanation] = useState<Explanation | null>(null);
  const [aiStream, setAiStream] = useState("");
  const [aiError, setAiError] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    getResults(params.job_id)
      .then(res => setResults(res as Results))
      .catch(e => setError(e.message));
      
    const cleanup = streamExplanation(
       params.job_id,
       (chunk) => setAiStream(prev => prev + chunk),
       (exp) => setExplanation(exp),
       (e) => setAiError(e.message)
    );
    return cleanup;
  }, [params.job_id]);

  if (error) return <div className="p-8 text-rose-500 bg-rose-50">Error: {error}</div>;
  if (!results) return <div className="p-8 text-slate-500 flex items-center justify-center min-h-[50vh]">Loading Dashboard...</div>;

  const severity = results.overall_severity;

  return (
    <div className="space-y-8 animate-fade-in pb-24">
      {/* HEADER CARD */}
      <div className="glass rounded-2xl p-8 flex flex-col lg:flex-row gap-8 justify-between items-start">
        <div>
          <div className="flex items-center gap-4 mb-4">
            <h1 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-br from-indigo-900 to-slate-700">Fairness Audit Report</h1>
            <StatusBadge severity={severity} />
          </div>
          <p className="text-slate-500 max-w-2xl text-lg leading-relaxed">
            Audit generated for Job IDs: <span className="font-mono text-xs bg-slate-100 p-1 rounded">{results.job_id}</span>
          </p>
          <div className="flex gap-4 mt-6">
             <div className="bg-slate-50 border border-slate-100 px-4 py-3 rounded-lg flex flex-col">
               <span className="text-xs font-semibold text-slate-400 uppercase">Target</span>
               <span className="text-indigo-700 font-bold">{results.dataset_info.target_column}</span>
             </div>
             <div className="bg-slate-50 border border-slate-100 px-4 py-3 rounded-lg flex flex-col">
               <span className="text-xs font-semibold text-slate-400 uppercase">Protected</span>
               <span className="text-indigo-700 font-bold">{results.dataset_info.protected_attributes.join(", ")}</span>
             </div>
          </div>
        </div>

        <div className="flex gap-3">
            <button onClick={() => downloadReport(params.job_id)} className="flex items-center gap-2 px-6 py-3 bg-slate-900 hover:bg-slate-800 text-white font-medium rounded-xl transition-colors shadow-lg">
              <Download className="w-5 h-5" />
              Download PDF Report
            </button>
        </div>
      </div>

      {/* GEMINI AI EXPLANATION */}
      <div className="relative rounded-2xl p-[2px] bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500">
        <div className="bg-white p-8 rounded-[14px] h-full">
          <div className="flex items-center gap-2 mb-4">
             <Sparkles className="text-purple-600 w-5 h-5" />
             <h2 className="text-xl font-bold text-slate-900">Gemini AI Synthesis</h2>
          </div>
          
          <div className="prose prose-slate max-w-none prose-lg">
              <p className="text-slate-700 leading-relaxed min-h-[60px]">
                {explanation
                  ? explanation.plain_english
                  : aiError
                  ? <span className="text-rose-600 font-medium">⚠ AI analysis failed: {aiError}</span>
                  : aiStream || "Gemini AI is analyzing the fairness metrics..."}
                {!explanation && !aiError && <span className="inline-block w-2 h-4 ml-1 bg-slate-400 animate-pulse"></span>}
              </p>
          </div>
          
          {explanation && explanation.findings && (
            <div className="mt-8 space-y-4">
              {explanation.findings.map(finding => (
                <div key={finding.id} className="p-4 rounded-xl border border-rose-100 bg-rose-50/50 flex gap-4">
                  <Activity className="w-6 h-6 text-rose-500 shrink-0 mt-1" />
                  <div>
                    <h4 className="font-bold text-slate-900">{finding.headline}</h4>
                    <p className="text-slate-600 text-sm mt-1 leading-relaxed">{finding.detail}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* METRICS GRID */}
      <div>
         <h2 className="text-2xl font-bold text-slate-900 mb-6 px-2">Core Fairness Metrics</h2>
         <MetricsGrid metrics={results.metrics} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <ThresholdSimulator 
          job_id={params.job_id} 
          initialThreshold={results.remediation?.threshold?.current_threshold || 0.5} 
          currentResults={results}
        />
        
        {/* SHAP CHART Placehoder / Component inline */}
        <div className="glass p-8 rounded-2xl flex flex-col">
          <h3 className="text-xl font-bold text-slate-900 mb-2">SHAP Feature Importance</h3>
          <p className="text-sm text-slate-500 mb-6">Top drivers of model predictions. Check if protected attributes have high impact.</p>
          
          {!results.shap?.top_features || results.shap.top_features.length === 0 ? (
            <div className="flex-1 flex items-center justify-center bg-slate-50 rounded-lg border-2 border-dashed border-slate-200">
              <p className="text-slate-400">SHAP data not available yet</p>
            </div>
          ) : (
            <div className="flex-1 space-y-4">
              {results.shap.top_features.map((feat, idx) => (
                <div key={idx} className="flex items-center gap-4">
                  <div className="w-32 text-sm font-medium text-slate-600 truncate">{feat.feature}</div>
                  <div className="flex-1 h-6 bg-slate-100 rounded-md overflow-hidden relative">
                    <div 
                      className={`h-full absolute left-0 ${feat.direction === 'positive' ? 'bg-emerald-500' : feat.direction === 'negative' ? 'bg-rose-500' : 'bg-amber-500'}`}
                      style={{ width: `${(feat.importance / (results.shap?.top_features?.[0]?.importance || 1)) * 100}%`}}
                    />
                  </div>
                  <div className="w-12 text-right text-sm text-slate-500">{(feat.importance*10).toFixed(2)}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
