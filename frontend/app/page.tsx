"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { Activity, ArrowRight, BookOpen, FileSpreadsheet, ShieldCheck, SlidersHorizontal, Loader2 } from "lucide-react";
import { pollStatus, configureJob } from "@/lib/api";
import { RecentJobRecord, getRecentJobs, saveRecentJobs, upsertRecentJob } from "@/lib/recentJobs";

const workflow = [
  {
    title: "Upload source data",
    description: "Send a CSV and optional model artifact to start a fairness job.",
  },
  {
    title: "Map protected attributes",
    description: "Choose the target and the columns that should be evaluated for bias.",
  },
  {
    title: "Review and export",
    description: "Inspect metrics, explanation output, and download the generated PDF report.",
  },
];

const capabilityCards = [
  {
    title: "Protected Groups",
    description: "Track parity across multiple demographic cuts.",
    icon: ShieldCheck,
    color: "text-fuchsia-300",
  },
  {
    title: "Threshold Testing",
    description: "Inspect fairness and accuracy tradeoffs quickly.",
    icon: SlidersHorizontal,
    color: "text-emerald-300",
  },
  {
    title: "PDF Export",
    description: "Generate hosted-friendly compliance reports.",
    icon: FileSpreadsheet,
    color: "text-cyan-700",
  },
];

function formatStage(stage: string) {
  return stage.replace(/_/g, " ");
}

function formatStatus(stage: string) {
  if (stage === "complete") return "Ready";
  if (stage === "error") return "Attention";
  return "In progress";
}

function getJobHref(job: RecentJobRecord) {
  return job.stage === "complete" ? `/results/${job.job_id}` : `/loading/${job.job_id}`;
}

export default function Home() {
  const router = useRouter();
  const [jobs, setJobs] = useState<RecentJobRecord[]>([]);
  const [hydrated, setHydrated] = useState(false);
  const [demoLoading, setDemoLoading] = useState<string | null>(null);

  const handleDemo = async (
    jobId: string,
    targetCol: string,
    protectedAttrs: string[]
  ) => {
    setDemoLoading(jobId);
    try {
      await configureJob(jobId, targetCol, protectedAttrs, 1);
      upsertRecentJob({
        job_id: jobId,
        label: `Demo: ${jobId.replace("demo-", "").toUpperCase()}`,
        stage: "configuring",
        progress: 10,
        message: "Demo audit queued.",
        target_column: targetCol,
        protected_attributes: protectedAttrs,
        updated_at: new Date().toISOString(),
      });
      router.push(`/loading/${jobId}`);
    } catch (e) {
      console.error("Demo failed to start", e);
      setDemoLoading(null);
    }
  };

  useEffect(() => {
    const initialJobs = getRecentJobs();
    setJobs(initialJobs);
    setHydrated(true);
  }, []);

  useEffect(() => {
    if (!hydrated) {
      return;
    }

    let cancelled = false;

    const refreshStatuses = async () => {
      const currentJobs = getRecentJobs();
      const refreshable = currentJobs.filter((job) => !["complete", "error"].includes(job.stage)).slice(0, 3);
      if (refreshable.length === 0) {
        setJobs(currentJobs);
        return;
      }

      const updates = await Promise.all(
        refreshable.map(async (job) => {
          try {
            const status = await pollStatus(job.job_id);
            upsertRecentJob({
              job_id: status.job_id,
              stage: status.stage,
              progress: status.progress,
              message: status.error || status.message,
              updated_at: new Date().toISOString(),
            });
            return true;
          } catch {
            return false;
          }
        })
      );

      if (!cancelled) {
        const nextJobs = getRecentJobs();
        setJobs(nextJobs);
        if (updates.some(Boolean)) {
          saveRecentJobs(nextJobs);
        }
      }
    };

    refreshStatuses();
    const interval = setInterval(refreshStatuses, 12000);

    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [hydrated]);

  const queueJob = jobs[0];
  const topMetrics = useMemo(() => {
    const activeAudits = jobs.filter((job) => !["complete", "error"].includes(job.stage)).length;
    const reportsExported = jobs.filter((job) => job.stage === "complete").length;
    const highRiskFindings = jobs.filter((job) => ["high", "critical"].includes((job.severity || "").toLowerCase())).length;

    return [
      { label: "Active Audits", value: String(activeAudits).padStart(2, "0"), detail: activeAudits ? "Live jobs tracked" : "No active jobs" },
      { label: "Reports Ready", value: String(reportsExported).padStart(2, "0"), detail: reportsExported ? "Completed in this browser" : "No completed reports yet" },
      { label: "High-Risk Findings", value: String(highRiskFindings).padStart(2, "0"), detail: highRiskFindings ? "Completed audits marked high" : "No high-risk audits stored" },
    ];
  }, [jobs]);

  return (
    <div className="space-y-8 animate-fade-in">
      <section className="panel px-6 py-8 sm:px-8">
        <div className="grid gap-8 xl:grid-cols-[1.15fr_0.85fr]">
          <div className="space-y-6">
            <div className="inline-flex items-center gap-2 rounded-full border border-neutral-200 bg-neutral-100 px-4 py-2 text-xs uppercase tracking-[0.24em] text-cyan-700">
              Fairness Audit Workspace
            </div>

            <div className="space-y-4">
              <h1 className="max-w-4xl font-[family-name:var(--font-display)] text-4xl font-bold tracking-tight text-amber-950 sm:text-5xl">
                Bias review, remediation, and export in one operational dashboard.
              </h1>
              <p className="max-w-2xl text-lg leading-8 text-amber-900/80">
                FairLens now reflects the audits you actually run in this browser session, so the homepage behaves like a working workspace instead of a static showcase.
              </p>
            </div>

            <div className="flex flex-wrap gap-4">
              <Link href="/upload" className="btn-primary px-7 py-4 text-base">
                Start audit
                <ArrowRight className="h-5 w-5" />
              </Link>
              <button 
                onClick={() => handleDemo("demo-compas", "two_year_recid", ["race", "sex"])} 
                disabled={!!demoLoading}
                className="btn-secondary px-7 py-4 text-base disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {demoLoading === "demo-compas" ? <Loader2 className="h-5 w-5 animate-spin" /> : null}
                COMPAS Demo
              </button>
              <button 
                onClick={() => handleDemo("demo-german", "credit_risk", ["age_group", "sex"])} 
                disabled={!!demoLoading}
                className="btn-secondary px-7 py-4 text-base disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {demoLoading === "demo-german" ? <Loader2 className="h-5 w-5 animate-spin" /> : null}
                German Credit
              </button>
              <button 
                onClick={() => handleDemo("demo-hmda", "loan_approved", ["applicant_race", "applicant_sex"])} 
                disabled={!!demoLoading}
                className="btn-secondary px-7 py-4 text-base disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {demoLoading === "demo-hmda" ? <Loader2 className="h-5 w-5 animate-spin" /> : null}
                Mortgage Demo
              </button>
            </div>

            <div className="grid gap-4 sm:grid-cols-3">
              {topMetrics.map((metric) => (
                <div key={metric.label} className="metric-border rounded-3xl p-5">
                  <div className="text-xs uppercase tracking-[0.24em] text-amber-900/50">{metric.label}</div>
                  <div className="mt-3 text-4xl font-bold text-amber-600">{metric.value}</div>
                  <div className="mt-2 text-sm text-amber-900/60">{metric.detail}</div>
                </div>
              ))}
            </div>
          </div>

          <div className="panel-soft p-6">
            <div className="mb-5 flex items-center justify-between">
              <div>
                <div className="text-xs uppercase tracking-[0.24em] text-amber-900/50">System view</div>
                <div className="mt-2 font-[family-name:var(--font-display)] text-2xl font-semibold text-amber-950">
                  Audit Queue
                </div>
              </div>
              <div className="rounded-full border border-amber-600/20 bg-amber-500/10 px-3 py-1 text-sm text-amber-700">
                {queueJob ? formatStatus(queueJob.stage) : "Idle"}
              </div>
            </div>

            <div className="space-y-4">
              <div className="metric-border rounded-3xl p-5">
                {queueJob ? (
                  <>
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <div className="text-sm font-semibold text-amber-950">{queueJob.label}</div>
                        <div className="mt-1 text-sm text-amber-900/60">{queueJob.message}</div>
                      </div>
                      <div className="flex items-center gap-3">
                        <Link href={getJobHref(queueJob)} className="text-xs font-medium text-amber-700 transition hover:text-amber-800">
                          Open
                        </Link>
                        <Activity className="h-5 w-5 text-amber-600" />
                      </div>
                    </div>
                    <div className="mt-4 h-2 rounded-full bg-amber-500/10">
                      <div
                        className="h-2 rounded-full bg-gradient-to-r from-amber-400 to-emerald-400 transition-all"
                        style={{ width: `${Math.max(queueJob.progress, 6)}%` }}
                      />
                    </div>
                    <div className="mt-3 flex justify-between text-xs text-amber-900/60">
                      <span>Stage: {formatStage(queueJob.stage)}</span>
                      <span>{queueJob.progress}%</span>
                    </div>
                  </>
                ) : (
                  <>
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <div className="text-sm font-semibold text-amber-950">No recent audit loaded</div>
                        <div className="mt-1 text-sm text-amber-900/60">Start a new audit to populate the queue with real job status.</div>
                      </div>
                      <Activity className="h-5 w-5 text-amber-500" />
                    </div>
                    <div className="mt-4 h-2 rounded-full bg-amber-500/10" />
                    <div className="mt-3 flex justify-between text-xs text-amber-900/60">
                      <span>Stage: idle</span>
                      <span>0%</span>
                    </div>
                  </>
                )}
              </div>

              <div className="grid gap-4 md:grid-cols-3">
                {capabilityCards.map((card) => (
                  <div key={card.title} className="metric-border rounded-3xl p-5">
                    <card.icon className={`h-5 w-5 ${card.color}`} />
                    <div className="mt-4 text-lg font-semibold text-amber-950">{card.title}</div>
                    <div className="mt-2 text-sm text-amber-900/70">{card.description}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="grid gap-6 lg:grid-cols-[0.9fr_1.1fr]">
        <div className="panel-soft p-6 sm:p-8">
          <div className="text-xs uppercase tracking-[0.24em] text-amber-900/50">Workflow</div>
          <h2 className="mt-2 font-[family-name:var(--font-display)] text-3xl font-semibold text-amber-950">
            How teams use this
          </h2>
          <div className="mt-6 space-y-4">
            {workflow.map((item, index) => (
              <div key={item.title} className="metric-border rounded-3xl p-5">
                <div className="text-xs uppercase tracking-[0.24em] text-amber-900/50">
                  Step {index + 1}
                </div>
                <div className="mt-2 text-lg font-semibold text-amber-950">{item.title}</div>
                <div className="mt-2 text-sm leading-6 text-amber-900/70">{item.description}</div>
              </div>
            ))}
          </div>
        </div>

        <div className="panel-soft p-6 sm:p-8">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-xs uppercase tracking-[0.24em] text-amber-900/50">Workspace state</div>
              <h2 className="mt-2 font-[family-name:var(--font-display)] text-3xl font-semibold text-amber-950">
                Current focus
              </h2>
            </div>
            <Link href="/upload" className="btn-secondary px-4 py-2 text-sm">
              New job
            </Link>
          </div>

          <div className="mt-6 overflow-hidden rounded-3xl border border-amber-600/10">
            <div className="grid grid-cols-[1.3fr_0.8fr_0.8fr] bg-amber-500/5 px-5 py-4 text-xs uppercase tracking-[0.22em] text-amber-900/50">
              <div>Audit</div>
              <div>Status</div>
              <div>Scope</div>
            </div>

            {jobs.length > 0 ? (
              jobs.slice(0, 4).map((job) => (
                <Link
                  key={job.job_id}
                  href={getJobHref(job)}
                  className="grid grid-cols-[1.3fr_0.8fr_0.8fr] border-t border-amber-600/10 px-5 py-4 text-sm text-amber-900/70 transition hover:bg-amber-500/5"
                >
                  <div className="font-medium text-amber-950">{job.label}</div>
                  <div>{formatStatus(job.stage)}</div>
                  <div>{job.target_column || "Dataset loaded"}</div>
                </Link>
              ))
            ) : (
              <div className="border-t border-amber-600/10 px-5 py-6 text-sm text-amber-900/60">
                No audits have been run in this browser session yet.
              </div>
            )}
          </div>
        </div>
      </section>

      {/* ── How It Works teaser ── */}
      <section className="panel overflow-hidden">
        <div className="grid md:grid-cols-[1fr_auto] items-center gap-6 px-7 py-7">
          <div className="flex items-start gap-5">
            <div className="rounded-2xl border border-amber-200 bg-amber-50 p-3 shrink-0">
              <BookOpen className="h-6 w-6 text-amber-600" />
            </div>
            <div>
              <div className="text-xs uppercase tracking-widest text-amber-700 mb-1">New to FairLens?</div>
              <div className="font-[family-name:var(--font-display)] text-xl font-semibold text-amber-950">
                Understand exactly how AI bias auditing works
              </div>
              <p className="mt-1.5 text-sm text-amber-900/60 leading-6 max-w-lg">
                Plain-English guide covering what AI bias is, why it matters legally, how each fairness
                metric is calculated, and how to get the most out of every FairLens feature — with real
                worked examples. No technical background needed.
              </p>
            </div>
          </div>
          <Link
            href="/how-it-works"
            className="btn-primary px-6 py-3 whitespace-nowrap shrink-0"
          >
            Read the guide <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
        {/* decorative strip */}
        <div className="h-1 w-full bg-gradient-to-r from-amber-400 via-emerald-400 to-amber-300 opacity-60" />
      </section>
    </div>
  );
}
