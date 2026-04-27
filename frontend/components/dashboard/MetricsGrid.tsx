import React from "react";
import type { Results } from "@/lib/types";
import { AlertCircle, CheckCircle2, Info } from "lucide-react";

// ── Dynamic "What This Means" interpreter ─────────────────────────────────────
// Takes the metric key and its computed value and returns plain-English context
// that reflects the actual severity of the number, not just pass/fail.

function getInterpretation(key: string, value: number): string {
  const pct = (n: number) => `${Math.round(Math.abs(n) * 100)}%`;

  switch (key) {
    case "disparate_impact": {
      // Ratio: unprivileged approval rate ÷ privileged approval rate
      // Higher is better; legal minimum is 0.80
      if (value >= 1.0)
        return "The unprivileged group is at least as likely to receive a positive outcome as the privileged group — no disparity in this direction.";
      if (value >= 0.95)
        return `Approval rates are nearly equal — within ${pct(1 - value)} of each other. No meaningful disparity detected.`;
      if (value >= 0.80)
        return `A minor gap exists: the unprivileged group is approved at ${pct(value)} the rate of the privileged group. This is within the EEOC 80% legal threshold but worth monitoring.`;
      if (value >= 0.70)
        return `The unprivileged group is approved at ${pct(value)} the rate of the privileged group — below the legal minimum of 80%. This constitutes prima facie evidence of discrimination under the EEOC 80% Rule.`;
      if (value >= 0.50)
        return `Significant disparity: the unprivileged group receives positive outcomes at only ${pct(value)} the rate of the privileged group. This is a serious violation requiring immediate remediation.`;
      return `Severe disparity: the unprivileged group is less than half as likely to receive a positive outcome (${pct(value)} ratio). This level of bias carries high legal and reputational risk.`;
    }

    case "demographic_parity_difference": {
      // Difference in positive prediction rates; lower is better; threshold ≤ 0.10
      const gap = Math.abs(value);
      if (gap <= 0.02)
        return "Approval rates across groups are essentially identical — less than 2 percentage points apart. Excellent parity.";
      if (gap <= 0.05)
        return `A ${pct(gap)} gap in approval rates exists between groups. Small, but visible — monitor over time.`;
      if (gap <= 0.10)
        return `A ${pct(gap)} gap in approval rates. This is within the legal threshold (≤10%) but approaching the limit — remediation is advisable before the model reaches production.`;
      if (gap <= 0.20)
        return `A ${pct(gap)} gap in approval rates across demographic groups. This exceeds the legal threshold and indicates that group membership is significantly influencing outcomes.`;
      return `A very large ${pct(gap)} gap in approval rates. This level of disparity is a clear indicator that the model treats different demographic groups fundamentally differently.`;
    }

    case "equalized_odds_difference": {
      // Max of (Δ true-positive rate, Δ false-positive rate); threshold ≤ 0.10
      const gap = Math.abs(value);
      if (gap <= 0.02)
        return "The model makes errors at nearly equal rates across groups — both true positives and false positives are consistent. Strong error-rate parity.";
      if (gap <= 0.05)
        return `A ${pct(gap)} difference in error rates across groups. Minor, but means the model is slightly less accurate for one group than another.`;
      if (gap <= 0.10)
        return `A ${pct(gap)} gap in true or false positive rates. This is within the legal threshold but means one group faces a measurably higher risk of incorrect decisions.`;
      if (gap <= 0.20)
        return `A ${pct(gap)} gap in error rates. The model is meaningfully less reliable for one demographic group — it either misses more qualified individuals or flags more unqualified ones from a specific group.`;
      return `A severe ${pct(gap)} gap in error rates. One group is significantly more likely to be wrongly approved or wrongly denied than another — a strong indicator of systemic model bias.`;
    }

    case "calibration_difference": {
      // Difference in prediction reliability (precision) across groups; threshold ≤ 0.10
      const gap = Math.abs(value);
      if (gap <= 0.02)
        return "The model's confidence scores are equally reliable for all groups. When it predicts a positive outcome, it is correct at the same rate across demographics.";
      if (gap <= 0.05)
        return `A ${pct(gap)} difference in prediction reliability. The model's confidence is slightly more accurate for one group than another — monitor but not yet a concern.`;
      if (gap <= 0.10)
        return `A ${pct(gap)} gap in reliability. When the model says "yes" for one group, it is right less often than when it says "yes" for another group. This affects trustworthiness of individual predictions.`;
      if (gap <= 0.20)
        return `A ${pct(gap)} reliability gap means the model's probability scores are systematically overconfident or underconfident for a specific demographic group — reducing the fairness of risk-based decisions.`;
      return `A severe ${pct(gap)} reliability gap. The model cannot be trusted to produce equally valid probability scores across groups, which undermines any threshold-based decision process.`;
    }

    default:
      return "Review the metric value relative to its threshold to determine compliance status.";
  }
}

// ── Component ─────────────────────────────────────────────────────────────────

export const MetricsGrid = ({ metrics }: { metrics: Results["metrics"] }) => {
  return (
    <div className="grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-4">
      {Object.entries(metrics).map(([key, data]) => {
        const passed = data.passed;
        const title = key
          .split("_")
          .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
          .join(" ");
        const interpretation = getInterpretation(key, data.value);

        return (
          <div
            key={key}
            className={`metric-border flex flex-col rounded-[28px] p-6 ${
              passed
                ? "shadow-[0_18px_40px_rgba(52,211,153,0.08)]"
                : "shadow-[0_18px_40px_rgba(244,63,94,0.08)]"
            }`}
          >
            {/* Header */}
            <div className="mb-4 flex items-center justify-between">
              <h3 className="font-semibold text-amber-950 dark:text-amber-100">{title}</h3>
              {passed ? (
                <CheckCircle2 className="h-6 w-6 text-emerald-400" />
              ) : (
                <AlertCircle className="h-6 w-6 text-rose-400" />
              )}
            </div>

            {/* Value + threshold */}
            <div className="mb-2 flex items-baseline gap-2">
              <span
                className={`text-4xl font-bold tracking-tight ${
                  passed ? "text-emerald-600 dark:text-emerald-400" : "text-rose-600 dark:text-rose-400"
                }`}
              >
                {data.value.toFixed(3)}
              </span>
              <span className="text-sm font-medium text-amber-900/50 dark:text-amber-300/50">
                threshold {data.threshold}
              </span>
            </div>

            {/* Progress bar */}
            <div className="mt-3 mb-4 h-1.5 rounded-full bg-amber-500/10 dark:bg-amber-400/10">
              <div
                className={`h-1.5 rounded-full ${
                  passed
                    ? "bg-gradient-to-r from-emerald-500 to-emerald-400"
                    : "bg-gradient-to-r from-rose-500 to-rose-400"
                }`}
                style={{
                  width: `${Math.min(Math.abs(data.value) / Math.max(data.threshold, 0.001), 1) * 100}%`,
                }}
              />
            </div>

            {/* Backend description */}
            <p className="text-xs font-medium leading-relaxed text-amber-900/60 dark:text-amber-300/60">
              {data.description}
            </p>

            {/* What This Means */}
            <div className="mt-4 rounded-2xl border border-amber-500/15 bg-amber-500/5 p-3 dark:border-amber-400/15 dark:bg-amber-400/5">
              <div className="mb-1.5 flex items-center gap-1.5">
                <Info className="h-3.5 w-3.5 shrink-0 text-amber-600 dark:text-amber-400" />
                <span className="text-[10px] font-semibold uppercase tracking-widest text-amber-700 dark:text-amber-400">
                  What this means
                </span>
              </div>
              <p className="text-xs leading-relaxed text-amber-900/70 dark:text-amber-200/70">
                {interpretation}
              </p>
            </div>
          </div>
        );
      })}
    </div>
  );
};
