// lib/types.ts — All TypeScript interfaces matching CONTRACT.md exactly

export interface JobStatus {
  job_id: string
  stage:
    | "uploading"
    | "configuring"
    | "running_inference"
    | "computing_metrics"
    | "generating_explanation"
    | "generating_report"
    | "complete"
    | "error"
  progress: number
  message: string
  error: string | null
}

export interface MetricResult {
  value: number
  threshold: number
  passed: boolean
  description: string
}

export interface Results {
  job_id: string
  completed_at: string
  dataset_info: {
    total_rows: number
    target_column: string
    protected_attributes: string[]
    positive_rate_overall: number
  }
  metrics: {
    disparate_impact: MetricResult
    demographic_parity_difference: MetricResult
    equalized_odds_difference: MetricResult
    calibration_difference: MetricResult
  }
  per_group_stats: Record<
    string,
    Record<
      string,
      {
        count: number
        positive_rate: number
        tpr: number
        fpr: number
      }
    >
  >
  overall_severity: "high" | "medium" | "low" | "none"
  metrics_passed: number
  metrics_failed: number
  fairness_score?: {
    score: number
    grade: string
    breakdown: Record<string, number>
  }
  shap: {
    top_features: Array<{
      feature: string
      importance: number
      direction: string
    }>
    protected_attr_shap: Record<string, number>
  }
  remediation: {
    reweighing: {
      applied: boolean
      metrics_after: Record<string, MetricResult>
      accuracy_before: number
      accuracy_after: number
      accuracy_delta: number
    }
    threshold: {
      current_threshold: number
      privileged_group: string
      unprivileged_group: string
    }
  }
}

export interface Finding {
  id: string
  attribute: string
  metric: string
  headline: string
  detail: string
  severity: "high" | "medium" | "low"
}

export interface Explanation {
  job_id: string
  generated_at: string
  summary: string
  severity_label: string
  findings: Finding[]
  recommended_fix: string
  recommended_fix_reason: string
  plain_english: string
}

export interface ThresholdResult {
  threshold: number
  accuracy: number
  demographic_parity_difference: number
  equalized_odds_difference: number
  per_group: Record<string, { positive_rate: number; tpr: number; fpr: number }>
  latency_ms?: number
}

export interface UploadCSVResponse {
  job_id: string
  columns: string[]
  row_count: number
}

export interface UploadModelResponse {
  job_id: string
  model_type: string
}

export interface ConfigureJobResponse {
  job_id: string
  status: string
}
