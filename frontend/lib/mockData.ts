// lib/mockData.ts — Mock results.json and explanation.json from CONTRACT.md

import { Results, Explanation } from "./types"

export const mockResults: Results = {
  job_id: "3f7a1b2c-demo",
  completed_at: "2025-01-01T10:05:00Z",
  dataset_info: {
    total_rows: 48842,
    target_column: "loan_approved",
    protected_attributes: ["gender", "race"],
    positive_rate_overall: 0.241,
  },
  metrics: {
    disparate_impact: {
      value: 0.62,
      threshold: 0.8,
      passed: false,
      description:
        "Ratio of positive outcome rate between unprivileged and privileged group. Must be >= 0.8 (80% rule).",
    },
    demographic_parity_difference: {
      value: -0.193,
      threshold: 0.1,
      passed: false,
      description:
        "Difference in positive prediction rates between groups. Should be close to 0.",
    },
    equalized_odds_difference: {
      value: -0.142,
      threshold: 0.1,
      passed: false,
      description:
        "Difference in TPR between groups. Should be close to 0.",
    },
    calibration_difference: {
      value: 0.031,
      threshold: 0.1,
      passed: true,
      description: "Difference in score reliability across groups.",
    },
  },
  per_group_stats: {
    gender: {
      Male: { count: 21790, positive_rate: 0.308, tpr: 0.742, fpr: 0.181 },
      Female: { count: 10771, positive_rate: 0.115, tpr: 0.6, fpr: 0.062 },
    },
    race: {
      White: { count: 27816, positive_rate: 0.261, tpr: 0.731, fpr: 0.162 },
      Black: { count: 3124, positive_rate: 0.122, tpr: 0.589, fpr: 0.091 },
      "Asian-Pac-Islander": {
        count: 1039,
        positive_rate: 0.276,
        tpr: 0.701,
        fpr: 0.13,
      },
      Other: { count: 271, positive_rate: 0.143, tpr: 0.612, fpr: 0.105 },
    },
  },
  overall_severity: "high",
  metrics_passed: 1,
  metrics_failed: 3,
  shap: {
    top_features: [
      { feature: "capital_gain", importance: 0.312, direction: "positive" },
      { feature: "age", importance: 0.198, direction: "positive" },
      { feature: "education_num", importance: 0.167, direction: "positive" },
      { feature: "hours_per_week", importance: 0.143, direction: "positive" },
      { feature: "marital_status", importance: 0.089, direction: "negative" },
      { feature: "occupation", importance: 0.051, direction: "mixed" },
      { feature: "relationship", importance: 0.04, direction: "negative" },
    ],
    protected_attr_shap: {
      gender: 0.028,
      race: 0.019,
    },
  },
  remediation: {
    reweighing: {
      applied: true,
      metrics_after: {
        disparate_impact: { value: 0.84, threshold: 0.8, passed: true, description: "" },
        demographic_parity_difference: {
          value: -0.048,
          threshold: 0.1,
          passed: true,
          description: "",
        },
        equalized_odds_difference: {
          value: -0.071,
          threshold: 0.1,
          passed: true,
          description: "",
        },
        calibration_difference: {
          value: 0.038,
          threshold: 0.1,
          passed: true,
          description: "",
        },
      },
      accuracy_before: 0.847,
      accuracy_after: 0.831,
      accuracy_delta: -0.016,
    },
    threshold: {
      current_threshold: 0.5,
      privileged_group: "Male",
      unprivileged_group: "Female",
    },
  },
}

export const mockExplanation: Explanation = {
  job_id: "3f7a1b2c-demo",
  generated_at: "2025-01-01T10:06:00Z",
  summary:
    "Your model shows significant gender and racial bias. Women are approved at 37% the rate of men despite similar financial profiles.",
  severity_label: "High bias detected",
  findings: [
    {
      id: "f1",
      attribute: "gender",
      metric: "disparate_impact",
      headline: "Women approved 38% less often than men",
      detail:
        "The disparate impact ratio of 0.62 falls well below the legal 80% threshold. This means female applicants receive positive outcomes at 62% the rate of male applicants.",
      severity: "high",
    },
    {
      id: "f2",
      attribute: "race",
      metric: "equalized_odds_difference",
      headline: "Black applicants face lower true positive rates",
      detail:
        "Even when Black applicants qualify, the model correctly identifies them 14.2 percentage points less often than White applicants.",
      severity: "high",
    },
  ],
  recommended_fix: "reweighing",
  recommended_fix_reason:
    "Reweighing reduces disparate impact to 0.84 (above the 0.8 legal threshold) with only a 1.6% accuracy trade-off — the best balance for this dataset.",
  plain_english:
    "If you deployed this model today, it would systematically disadvantage women and Black applicants in ways that could violate equal credit opportunity laws. The good news: applying reweighing correction brings the model into compliance while keeping accuracy above 83%.",
}

// Mock threshold results for pre-computed steps 0.1 → 0.9
export const mockThresholdSeries: Record<number, {
  threshold: number
  accuracy: number
  demographic_parity_difference: number
  equalized_odds_difference: number
  per_group: Record<string, { positive_rate: number; tpr: number; fpr: number }>
}> = {
  0.1: { threshold: 0.1, accuracy: 0.71, demographic_parity_difference: 0.22, equalized_odds_difference: 0.18, per_group: { Male: { positive_rate: 0.82, tpr: 0.95, fpr: 0.45 }, Female: { positive_rate: 0.60, tpr: 0.88, fpr: 0.30 } } },
  0.2: { threshold: 0.2, accuracy: 0.76, demographic_parity_difference: 0.20, equalized_odds_difference: 0.17, per_group: { Male: { positive_rate: 0.72, tpr: 0.92, fpr: 0.35 }, Female: { positive_rate: 0.52, tpr: 0.82, fpr: 0.22 } } },
  0.3: { threshold: 0.3, accuracy: 0.80, demographic_parity_difference: 0.17, equalized_odds_difference: 0.15, per_group: { Male: { positive_rate: 0.60, tpr: 0.88, fpr: 0.28 }, Female: { positive_rate: 0.43, tpr: 0.75, fpr: 0.16 } } },
  0.4: { threshold: 0.4, accuracy: 0.83, demographic_parity_difference: 0.15, equalized_odds_difference: 0.14, per_group: { Male: { positive_rate: 0.48, tpr: 0.82, fpr: 0.22 }, Female: { positive_rate: 0.33, tpr: 0.70, fpr: 0.12 } } },
  0.5: { threshold: 0.5, accuracy: 0.847, demographic_parity_difference: 0.193, equalized_odds_difference: 0.142, per_group: { Male: { positive_rate: 0.308, tpr: 0.742, fpr: 0.181 }, Female: { positive_rate: 0.115, tpr: 0.600, fpr: 0.062 } } },
  0.6: { threshold: 0.6, accuracy: 0.84, demographic_parity_difference: 0.12, equalized_odds_difference: 0.11, per_group: { Male: { positive_rate: 0.25, tpr: 0.68, fpr: 0.14 }, Female: { positive_rate: 0.13, tpr: 0.55, fpr: 0.05 } } },
  0.7: { threshold: 0.7, accuracy: 0.82, demographic_parity_difference: 0.09, equalized_odds_difference: 0.08, per_group: { Male: { positive_rate: 0.18, tpr: 0.58, fpr: 0.09 }, Female: { positive_rate: 0.09, tpr: 0.45, fpr: 0.03 } } },
  0.8: { threshold: 0.8, accuracy: 0.79, demographic_parity_difference: 0.06, equalized_odds_difference: 0.05, per_group: { Male: { positive_rate: 0.12, tpr: 0.42, fpr: 0.05 }, Female: { positive_rate: 0.06, tpr: 0.32, fpr: 0.02 } } },
  0.9: { threshold: 0.9, accuracy: 0.74, demographic_parity_difference: 0.03, equalized_odds_difference: 0.03, per_group: { Male: { positive_rate: 0.06, tpr: 0.22, fpr: 0.02 }, Female: { positive_rate: 0.03, tpr: 0.15, fpr: 0.01 } } },
}

