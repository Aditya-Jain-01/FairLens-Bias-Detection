"use client";
import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  Activity,
  Download,
  Loader2,
  Sparkles,
  Send,
} from "lucide-react";
import { Results, Explanation } from "@/lib/types";
import { getResults, streamExplanation, downloadReport, askQuestion } from "@/lib/api";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { MetricsGrid } from "@/components/dashboard/MetricsGrid";
import { ThresholdSimulator } from "@/components/dashboard/ThresholdSimulator";
import { upsertRecentJob } from "@/lib/recentJobs";

export default function ResultsDashboard({ params }: { params: { job_id: string } }) {
  const [results, setResults] = useState<Results | null>(null);
  const [explanation, setExplanation] = useState<Explanation | null>(null);
  const [aiStream, setAiStream] = useState("");
  const [aiError, setAiError] = useState("");   // ← shows Gemini errors in UI
  const [error, setError] = useState("");
  const [reportLoading, setReportLoading] = useState(false);
  const [reportError, setReportError] = useState("");

  const [qaHistory, setQaHistory] = useState<{question: string, answer: string}[]>([]);
  const [questionInput, setQuestionInput] = useState("");
  const [isAsking, setIsAsking] = useState(false);

  const handleAskQuestion = async () => {
    if (!questionInput.trim() || isAsking) return;
    const q = questionInput.trim();
    setQuestionInput("");
    setIsAsking(true);
    try {
      const res = await askQuestion(params.job_id, q);
      setQaHistory((prev) => [...prev, { question: q, answer: res.answer }]);
    } catch (e) {
      setQaHistory((prev) => [
        ...prev,
        { question: q, answer: `⚠ Error: ${e instanceof Error ? e.message : "Failed to get answer"}` },
      ]);
    } finally {
      setIsAsking(false);
    }
  };

  useEffect(() => {
    getResults(params.job_id)
      .then((res) => {
        const typed = res as Results;
        setResults(typed);
        upsertRecentJob({
          job_id: typed.job_id,
          stage: "complete",
          progress: 100,
          message: "Audit complete. Results ready.",
          target_column: typed.dataset_info.target_column,
          protected_attributes: typed.dataset_info.protected_attributes,
          severity: typed.overall_severity,
          updated_at: new Date().toISOString(),
        });
      })
      .catch((e) => setError(e.message));

    const cleanup = streamExplanation(
      params.job_id,
      (chunk) => setAiStream((prev) => prev + chunk),
      (exp) => setExplanation(exp),
      (e) => setAiError(e.message)   // ← surface errors instead of console.error
    );

    return cleanup;
  }, [params.job_id]);

  const handleDownloadReport = async () => {
    try {
      setReportError("");
      setReportLoading(true);
      await downloadReport(params.job_id);
    } catch (err) {
      setReportError(err instanceof Error ? err.message : "Report download failed");
    } finally {
      setReportLoading(false);
    }
  };

  const isMissingResults = error.includes("not found") || error.includes("404");
  const isDemoJob = params.job_id === "demo";

  if (error && !results) {
    return (
      <div className="flex min-h-[60vh] flex-col items-center justify-center rounded-[32px] border border-amber-600/15 bg-amber-500/10 p-12 text-center">
        <div className="mb-3 text-sm font-semibold uppercase tracking-widest text-amber-700/80">
          Workspace not ready
        </div>
        <h1 className="mt-3 font-[family-name:var(--font-display)] text-3xl font-semibold text-amber-950">
          {isDemoJob ? "Load the demo dataset first" : "This audit is not ready yet"}
        </h1>
        <p className="mt-3 max-w-2xl text-base leading-7 text-amber-900/70">
          {isMissingResults
            ? isDemoJob
              ? "The demo workspace does not have results loaded yet. Start a demo audit or upload a dataset to generate the dashboard."
              : "Results are not available for this job yet. Load a dataset and run the audit before opening the results workspace."
            : error}
        </p>

        <div className="mt-6 flex flex-col gap-3 sm:flex-row">
          <Link href="/upload" className="btn-primary px-6 py-3 text-sm">
            Load dataset
          </Link>
          {isDemoJob && (
            <Link href="/upload" className="btn-secondary px-6 py-3 text-sm">
              Start demo audit
            </Link>
          )}
        </div>
      </div>
    );
  }

  if (!results) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center rounded-[28px] border border-amber-600/15 bg-amber-500/10 p-8 text-neutral-500">
        Loading Dashboard...
      </div>
    );
  }

  const severity = results.overall_severity;

  return (
    <div className="animate-fade-in space-y-8 pb-24">
      <div className="panel rounded-[32px] p-8">
        <div className="flex flex-col gap-8 lg:flex-row lg:justify-between">
          <div className="max-w-3xl">
            <div className="mb-4 flex flex-wrap items-center gap-4">
              <h1 className="font-[family-name:var(--font-display)] text-3xl font-bold text-amber-950 sm:text-4xl">
                Fairness Audit Report
              </h1>
              <StatusBadge severity={severity} />
            </div>
            <p className="max-w-2xl text-lg leading-relaxed text-amber-900/70">
              Review the current fairness metrics, explanation stream, remediation guidance, and downloadable report for this hosted audit job.
            </p>
            <div className="mt-6 grid gap-4 sm:grid-cols-4">
              {results.fairness_score && (
                <div className="metric-border rounded-2xl p-4 flex items-center justify-between gap-4 sm:col-span-1">
                  <div>
                    <span className="text-xs font-semibold uppercase tracking-[0.24em] text-amber-800/60">FairLens Score</span>
                    <div className="mt-1 text-sm font-medium text-amber-950">Grade {results.fairness_score.grade}</div>
                  </div>
                  <div className="relative h-14 w-14 shrink-0">
                    <svg className="h-full w-full -rotate-90 transform" viewBox="0 0 36 36">
                      <circle cx="18" cy="18" r="16" fill="none" className="stroke-cyan-950" strokeWidth="3" />
                      <circle 
                        cx="18" 
                        cy="18" 
                        r="16" 
                        fill="none" 
                        className={
                          results.fairness_score.score >= 80 ? "stroke-emerald-400" :
                          results.fairness_score.score >= 60 ? "stroke-amber-400" : "stroke-rose-400"
                        } 
                        strokeWidth="3" 
                        strokeDasharray={`${results.fairness_score.score} 100`} 
                        pathLength="100"
                        strokeLinecap="round"
                      />
                    </svg>
                    <div className="absolute inset-0 flex items-center justify-center">
                      <span className={`text-lg font-bold ${
                        results.fairness_score.score >= 80 ? "text-emerald-400" :
                        results.fairness_score.score >= 60 ? "text-amber-400" : "text-rose-400"
                      }`}>
                        {Math.round(results.fairness_score.score)}
                      </span>
                    </div>
                  </div>
                </div>
              )}
              <div className="metric-border rounded-2xl px-4 py-4">
                <span className="text-xs font-semibold uppercase tracking-[0.24em] text-amber-800/60">Target</span>
                <div className="mt-2 font-bold text-neutral-900">{results.dataset_info.target_column}</div>
              </div>
              <div className="metric-border rounded-2xl px-4 py-4">
                <span className="text-xs font-semibold uppercase tracking-[0.24em] text-amber-800/60">Protected</span>
                <div className="mt-2 font-bold text-neutral-900">{results.dataset_info.protected_attributes.join(", ")}</div>
              </div>
              <div className="metric-border rounded-2xl px-4 py-4">
                <span className="text-xs font-semibold uppercase tracking-[0.24em] text-amber-800/60">Job</span>
                <div className="mt-2 truncate font-mono text-sm text-amber-800/80">{results.job_id}</div>
              </div>
            </div>
          </div>

          <div className="w-full max-w-sm space-y-3">
            <button
              onClick={handleDownloadReport}
              disabled={reportLoading}
              className="btn-primary w-full disabled:cursor-not-allowed disabled:opacity-60"
            >
              {reportLoading ? <Loader2 className="h-5 w-5 animate-spin" /> : <Download className="h-5 w-5" />}
              {reportLoading ? "Preparing report..." : "Download PDF Report"}
            </button>
            <div className="rounded-2xl border border-amber-600/15 bg-amber-500/10 px-4 py-3 text-sm text-neutral-600">
              The report request uses the existing backend endpoint and opens the generated file in a hosted-safe way.
            </div>
            {reportError && (
              <div className="rounded-2xl border border-rose-400/20 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
                {reportError}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* AI Synthesis */}
      <div className="bg-white border border-neutral-200 p-6 rounded-2xl shadow-sm text-neutral-900">
        <div className="mb-4 flex items-center gap-2">
          <Sparkles className="h-5 w-5 text-fuchsia-600" />
          <h2 className="text-xl font-semibold text-neutral-900">AI Synthesis</h2>
        </div>

        <div className="max-w-none text-lg">
          <div className="min-h-[60px] leading-relaxed text-neutral-700">
            {explanation
              ? <p>{explanation.plain_english}</p>
              : aiError
              ? <div className="rounded-xl bg-amber-50 border border-amber-200 p-4 text-amber-800 font-medium">⚠ AI analysis failed: {aiError}</div>
              : <p>{aiStream || "Gemini AI is analyzing the fairness metrics..."}</p>}
            {!explanation && !aiError && (
              <span className="ml-1 inline-block h-4 w-2 animate-pulse bg-neutral-400" />
            )}
          </div>
        </div>

        {explanation && explanation.findings && (
          <div className="mt-8 space-y-4">
            {explanation.findings.map((finding) => (
              <div key={finding.id} className="flex gap-4 rounded-2xl border border-neutral-200 bg-neutral-50 p-4">
                <Activity className="mt-1 h-6 w-6 shrink-0 text-amber-600" />
                <div>
                  <h4 className="font-semibold text-neutral-900">{finding.headline}</h4>
                  <p className="mt-1 text-sm leading-relaxed text-neutral-700">{finding.detail}</p>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Q&A Section */}
        {explanation && (
          <div className="mt-8 border-t border-neutral-200 pt-6">
            <h3 className="mb-4 text-lg font-semibold text-neutral-900">Follow-up Questions</h3>
            
            {qaHistory.length > 0 && (
              <div className="mb-4 space-y-4">
                {qaHistory.map((qa, i) => (
                   <div key={i} className="space-y-2 text-sm leading-relaxed">
                     <div className="flex gap-3">
                       <span className="font-bold text-fuchsia-600">You:</span>
                       <span className="text-neutral-700">{qa.question}</span>
                     </div>
                     <div className="flex gap-3 rounded-2xl border border-neutral-100 bg-neutral-50 p-4">
                       <Sparkles className="h-4 w-4 shrink-0 text-fuchsia-600 mt-0.5" />
                       <span className="min-w-0 whitespace-pre-wrap break-words text-neutral-700">{qa.answer}</span>
                     </div>
                   </div>
                ))}
              </div>
            )}

            <div className="flex items-center gap-3">
              <input
                type="text"
                placeholder="Ask FairLens about these results..."
                value={questionInput}
                onChange={(e) => setQuestionInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") handleAskQuestion();
                }}
                disabled={isAsking}
                className="flex-1 rounded-2xl border border-neutral-200 bg-neutral-100 px-4 py-3 text-sm text-neutral-900 placeholder-neutral-400 outline-none transition focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 disabled:opacity-50"
              />
              <button
                onClick={handleAskQuestion}
                disabled={isAsking || !questionInput.trim()}
                className="flex items-center justify-center rounded-2xl bg-fuchsia-100 p-3 text-fuchsia-700 hover:bg-fuchsia-200 disabled:opacity-50"
              >
                {isAsking ? <Loader2 className="h-5 w-5 animate-spin" /> : <Send className="h-5 w-5" />}
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Metrics */}
      <div>
        <h2 className="mb-6 px-2 font-[family-name:var(--font-display)] text-2xl font-bold text-neutral-900">
          Core Fairness Metrics
        </h2>
        <MetricsGrid metrics={results.metrics} />
      </div>

      <div className="grid grid-cols-1 gap-8 lg:grid-cols-2">
        <ThresholdSimulator
          job_id={params.job_id}
          initialThreshold={results.remediation?.threshold?.current_threshold || 0.5}
          currentResults={results}
        />

        <div className="panel-soft flex flex-col p-8">
          <h3 className="mb-2 text-xl font-bold text-amber-950">SHAP Feature Importance</h3>
          <p className="mb-6 text-sm text-neutral-600">
            Top drivers of model predictions. Inspect whether protected attributes are exerting outsized influence.
          </p>

          {!results.shap?.top_features || results.shap.top_features.length === 0 ? (
            <div className="flex flex-1 items-center justify-center rounded-[24px] border-2 border-dashed border-cyan-400/12 bg-amber-500/10">
              <div className="max-w-sm text-center">
                <p className="text-neutral-500">SHAP data is not available for this audit.</p>
                <p className="mt-2 text-sm leading-6 text-neutral-500">
                  The backend only computes SHAP when a compatible model artifact is uploaded and successfully loaded during analysis.
                </p>
              </div>
            </div>
          ) : (
            <div className="flex-1 space-y-4">
              {results.shap.top_features.map((feat, idx) => (
                <div key={idx} className="flex items-center gap-4">
                  <div className="w-32 truncate text-sm font-medium text-neutral-700">{feat.feature}</div>
                  <div className="relative h-6 flex-1 overflow-hidden rounded-md bg-cyan-950/70">
                    <div
                      className={`absolute left-0 h-full ${
                        feat.direction === "positive"
                          ? "bg-emerald-400"
                          : feat.direction === "negative"
                            ? "bg-rose-400"
                            : "bg-amber-400"
                      }`}
                      style={{
                        width: `${(feat.importance / (results.shap?.top_features?.[0]?.importance || 1)) * 100}%`,
                      }}
                    />
                  </div>
                  <div className="w-12 text-right text-sm text-neutral-500">{(feat.importance * 10).toFixed(2)}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
