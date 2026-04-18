export type RecentJobRecord = {
  job_id: string;
  label: string;
  stage: string;
  progress: number;
  message: string;
  target_column?: string;
  protected_attributes?: string[];
  severity?: string;
  updated_at: string;
};

const STORAGE_KEY = "fairlens_recent_jobs";
const MAX_RECENT_JOBS = 8;

function canUseStorage() {
  return typeof window !== "undefined" && typeof window.localStorage !== "undefined";
}

export function getRecentJobs(): RecentJobRecord[] {
  if (!canUseStorage()) {
    return [];
  }

  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return [];
    }
    const parsed = JSON.parse(raw) as RecentJobRecord[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function saveRecentJobs(jobs: RecentJobRecord[]) {
  if (!canUseStorage()) {
    return;
  }

  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(jobs.slice(0, MAX_RECENT_JOBS)));
}

export function upsertRecentJob(job: Partial<RecentJobRecord> & { job_id: string }) {
  const jobs = getRecentJobs();
  const existing = jobs.find((entry) => entry.job_id === job.job_id);
  const next: RecentJobRecord = {
    job_id: job.job_id,
    label: job.label || existing?.label || `Audit ${job.job_id.slice(0, 8)}`,
    stage: job.stage || existing?.stage || "uploading",
    progress: job.progress ?? existing?.progress ?? 0,
    message: job.message || existing?.message || "Audit created",
    target_column: job.target_column ?? existing?.target_column,
    protected_attributes: job.protected_attributes ?? existing?.protected_attributes,
    severity: job.severity ?? existing?.severity,
    updated_at: job.updated_at || new Date().toISOString(),
  };

  const filtered = jobs.filter((entry) => entry.job_id !== job.job_id);
  saveRecentJobs([next, ...filtered].sort((a, b) => +new Date(b.updated_at) - +new Date(a.updated_at)));
}

export function getJobLabelFromFileName(fileName: string) {
  const withoutExtension = fileName.replace(/\.[^.]+$/, "");
  return withoutExtension
    .split(/[-_ ]+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}
