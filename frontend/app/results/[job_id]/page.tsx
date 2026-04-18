"use client";
import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  Activity,
  Download,
  Loader2,
  Sparkles,
} from "lucide-react";
import { Results, Explanation } from "@/lib/types";
import { getResults, streamExplanation, downloadReport } from "@/lib/api";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { MetricsGrid } from "@/components/dashboard/MetricsGrid";
import { ThresholdSimulator } from "@/components/dashboard/ThresholdSimulator";
import { upsertRecentJob } from "@/lib/recentJobs";

export default function ResultsDashboard({ params }: { params: { job_id: string } }) {
  const [results, setResults] = useState<Results | null>(null);
  const [explanation, setExplanation] = useState<Explanation | null>(null);
  const [aiStream, setAiStream] = useState("");
  const [error, setError] = useState("");
  const [reportLoading, setReportLoading] = useState(false);
  const [reportError, setReportError] = useState("");

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
      (e) => console.error("SSE Error:", e)
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

  if (error) {
    const isMissingResults =
      error.toLowerCase().includes("results not found") ||
      error.toLowerCase().includes("analysis completed");
    const isDemoJob = params.job_id === "demo";

    return (
      <div className="panel-soft max-w-3xl rounded-[28px] border border-amber-300/20 bg-amber-400/10 p-8">
        <div className="text-xs uppercase tracking-[0.24em] text-amber-100/55">
          Workspace not ready
        </div>
        <h1 className="mt-3 font-[family-name:var(--font-display)] text-3xl font-semibold text-white">
          {isDemoJob ? "Load the demo dataset first" : "This audit is not ready yet"}
        </h1>
        <p className="mt-3 max-w-2xl text-base leading-7 text-cyan-50/68">
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
      <div className="flex min-h-[50vh] items-center justify-center rounded-[28px] border border-cyan-400/10 bg-cyan-400/5 p-8 text-cyan-100/55">
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
              <h1 className="font-[family-name:var(--font-display)] text-3xl font-bold text-white sm:text-4xl">
                Fairness Audit Report
              </h1>
              <StatusBadge severity={severity} />
            </div>
            <p className="max-w-2xl text-lg leading-relaxed text-cyan-50/62">
              Review the current fairness metrics, explanation stream, remediation guidance, and downloadable report for this hosted audit job.
            </p>
            <div className="mt-6 grid gap-4 sm:grid-cols-3">
              <div className="metric-border rounded-2xl px-4 py-4">
                <span className="text-xs font-semibold uppercase tracking-[0.24em] text-cyan-100/40">Target</span>
                <div className="mt-2 font-bold text-cyan-200">{results.dataset_info.target_column}</div>
              </div>
              <div className="metric-border rounded-2xl px-4 py-4">
                <span className="text-xs font-semibold uppercase tracking-[0.24em] text-cyan-100/40">Protected</span>
                <div className="mt-2 font-bold text-cyan-200">{results.dataset_info.protected_attributes.join(", ")}</div>
              </div>
              <div className="metric-border rounded-2xl px-4 py-4">
                <span className="text-xs font-semibold uppercase tracking-[0.24em] text-cyan-100/40">Job</span>
                <div className="mt-2 truncate font-mono text-sm text-cyan-100/75">{results.job_id}</div>
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
            <div className="rounded-2xl border border-cyan-400/10 bg-cyan-400/5 px-4 py-3 text-sm text-cyan-50/60">
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

      <div className="rounded-[30px] border border-cyan-400/14 bg-[linear-gradient(180deg,rgba(11,22,37,0.96),rgba(9,17,29,0.9))] p-8">
        <div className="mb-4 flex items-center gap-2">
          <Sparkles className="h-5 w-5 text-fuchsia-300" />
          <h2 className="text-xl font-bold text-white">AI Synthesis</h2>
        </div>

        <div className="max-w-none text-lg">
          <p className="min-h-[60px] leading-relaxed text-cyan-50/80">
            {explanation ? explanation.plain_english : aiStream || "Gemini AI is analyzing the fairness metrics..."}
            {!explanation && <span className="ml-1 inline-block h-4 w-2 animate-pulse bg-cyan-300" />}
          </p>
        </div>

        {explanation && explanation.findings && (
          <div className="mt-8 space-y-4">
            {explanation.findings.map((finding) => (
              <div key={finding.id} className="flex gap-4 rounded-2xl border border-cyan-400/10 bg-cyan-400/5 p-4">
                <Activity className="mt-1 h-6 w-6 shrink-0 text-rose-300" />
                <div>
                  <h4 className="font-bold text-white">{finding.headline}</h4>
                  <p className="mt-1 text-sm leading-relaxed text-cyan-50/58">{finding.detail}</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div>
        <h2 className="mb-6 px-2 font-[family-name:var(--font-display)] text-2xl font-bold text-white">
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
          <h3 className="mb-2 text-xl font-bold text-white">SHAP Feature Importance</h3>
          <p className="mb-6 text-sm text-cyan-50/55">
            Top drivers of model predictions. Inspect whether protected attributes are exerting outsized influence.
          </p>

          {!results.shap?.top_features || results.shap.top_features.length === 0 ? (
            <div className="flex flex-1 items-center justify-center rounded-[24px] border-2 border-dashed border-cyan-400/12 bg-cyan-400/5">
              <div className="max-w-sm text-center">
                <p className="text-cyan-100/55">SHAP data is not available for this audit.</p>
                <p className="mt-2 text-sm leading-6 text-cyan-50/45">
                  The backend only computes SHAP when a compatible model artifact is uploaded and successfully loaded during analysis.
                </p>
              </div>
            </div>
          ) : (
            <div className="flex-1 space-y-4">
              {results.shap.top_features.map((feat, idx) => (
                <div key={idx} className="flex items-center gap-4">
                  <div className="w-32 truncate text-sm font-medium text-cyan-50/72">{feat.feature}</div>
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
                  <div className="w-12 text-right text-sm text-cyan-50/50">{(feat.importance * 10).toFixed(2)}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
