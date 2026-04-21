"use client";
import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { CheckCircle2, CircleDashed, Loader2 } from "lucide-react";
import { pollStatus } from "@/lib/api";
import { JobStatus } from "@/lib/types";
import { upsertRecentJob } from "@/lib/recentJobs";

const STEPS = [
  { id: "configuring", label: "Saving Configuration" },
  { id: "running_inference", label: "Running Model Inference" },
  { id: "computing_metrics", label: "Computing Fairness Metrics" },
  { id: "generating_explanation", label: "Generating AI Report" },
  { id: "generating_report", label: "Finalizing PDF" },
  { id: "complete", label: "Audit Complete" },
];

export default function LoadingPage({ params }: { params: { job_id: string } }) {
  const router = useRouter();
  const [status, setStatus] = useState<JobStatus | null>(null);

  useEffect(() => {
    let timeout: NodeJS.Timeout;

    const pollStatusFn = async () => {
      try {
        const currentStatus = await pollStatus(params.job_id);
        setStatus(currentStatus);
        upsertRecentJob({
          job_id: currentStatus.job_id,
          stage: currentStatus.stage,
          progress: currentStatus.progress,
          message: currentStatus.error || currentStatus.message,
          updated_at: new Date().toISOString(),
        });

        if (["generating_explanation", "generating_report", "complete"].includes(currentStatus.stage)) {
          setTimeout(() => {
            router.push(`/results/${params.job_id}`);
          }, 1500);
          return;
        }

        if (currentStatus.error) {
          return;
        }

        timeout = setTimeout(pollStatusFn, 1500);
      } catch (err) {
        console.error(err);
        timeout = setTimeout(pollStatusFn, 3000);
      }
    };

    pollStatusFn();
    return () => clearTimeout(timeout);
  }, [params.job_id, router]);

  if (status?.error) {
    return (
      <div className="flex min-h-[60vh] flex-col items-center justify-center animate-fade-in">
        <div className="max-w-lg rounded-[28px] border border-rose-600/25 bg-rose-500/10 p-8 text-center text-rose-900 shadow-lg">
          <h2 className="mb-2 text-2xl font-bold">Audit Failed</h2>
          <p>{status.error || status.message}</p>
          <button onClick={() => router.push("/upload")} className="mt-6 rounded-2xl bg-rose-500 px-6 py-3 font-semibold text-white">
            Try Again
          </button>
        </div>
      </div>
    );
  }

  const currentStepIndex = STEPS.findIndex((s) => s.id === status?.stage);

  return (
    <div className="flex min-h-[70vh] flex-col items-center justify-center animate-fade-in">
      <div className="panel relative w-full max-w-3xl overflow-hidden p-8 shadow-2xl sm:p-12">
        <div className="absolute left-0 top-0 h-1 w-full bg-cyan-950/50">
          <div
            className="h-full bg-gradient-to-r from-cyan-300 via-teal-300 to-fuchsia-500 transition-all duration-500"
            style={{ width: `${status?.progress || 0}%` }}
          />
        </div>

        <div className="mb-10 text-center">
          <div className="relative mb-4 inline-block">
            <div className="absolute inset-0 rounded-full bg-cyan-400/25 blur-xl animate-pulse" />
            <div className="relative flex h-16 w-16 items-center justify-center rounded-2xl border border-cyan-400/15 bg-cyan-400/8 shadow-sm">
              <Loader2 className="h-8 w-8 animate-spin text-cyan-700" />
            </div>
          </div>
          <div className="text-xs uppercase tracking-[0.3em] text-cyan-700">Pipeline status</div>
          <h1 className="mt-2 font-[family-name:var(--font-display)] text-3xl font-bold text-neutral-900">Processing Audit</h1>
          <p className="mt-2 text-sm text-neutral-600">{status?.message || "Initializing pipeline..."}</p>
        </div>

        <div className="space-y-5 pl-1">
          {STEPS.map((step, idx) => {
            const isCompleted = currentStepIndex > idx;
            const isCurrent = currentStepIndex === idx;

            return (
              <div
                key={step.id}
                className={`rounded-2xl border px-4 py-4 transition-all duration-300 ${
                  isCurrent
                    ? "scale-[1.01] border-cyan-300 bg-cyan-50"
                    : isCompleted
                      ? "border-emerald-200 bg-emerald-50"
                      : "border-neutral-200 bg-neutral-50"
                }`}
              >
                <div className="flex items-center gap-4">
                  {isCompleted ? (
                    <CheckCircle2 className="h-6 w-6 shrink-0 text-emerald-600" />
                  ) : isCurrent ? (
                    <Loader2 className="h-6 w-6 shrink-0 animate-spin text-cyan-600" />
                  ) : (
                    <CircleDashed className="h-6 w-6 shrink-0 text-neutral-400" />
                  )}
                  <span className={`${isCurrent ? "text-neutral-900 font-medium" : isCompleted ? "text-emerald-700 font-medium" : "text-neutral-500"}`}>
                    {step.label}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
