"use client";

import Link from "next/link";
import { useState } from "react";
import {
  ArrowRight, BookOpen, ChevronDown, ChevronRight,
  AlertTriangle, BarChart2, Brain, CheckCircle, FileText,
  Scale, Shield, Sliders, Users, Zap,
} from "lucide-react";

// ── Data ──────────────────────────────────────────────────────────────────────

const steps = [
  {
    number: "01",
    icon: FileText,
    color: "text-amber-600",
    bg: "bg-amber-50 border-amber-200",
    glow: "shadow-amber-100",
    title: "Upload Your Data",
    plain: "Think of this like handing a spreadsheet to an auditor.",
    detail:
      "You upload a CSV file — a table of data — that your AI model was trained on or makes decisions with. You can also upload the model itself (.pkl or .onnx format). If you don't have a model file, FairLens can still analyse the data patterns directly.",
    example:
      "Example: A bank uploads a spreadsheet with 50,000 loan applications. Each row is one person — their age, income, credit score, race, and whether they were approved or rejected.",
    tips: [
      "Minimum 50 rows needed for meaningful results",
      "Maximum 2 million rows supported",
      "Accepted model formats: .pkl (scikit-learn) and .onnx (universal)",
      "FairLens scans for personal data (PII) and warns you before any analysis begins",
    ],
  },
  {
    number: "02",
    icon: Users,
    color: "text-purple-600",
    bg: "bg-purple-50 border-purple-200",
    glow: "shadow-purple-100",
    title: "Choose Protected Attributes",
    plain: "Tell FairLens which columns represent people's identities.",
    detail:
      "Protected attributes are characteristics like race, gender, age, or religion — things that should NOT influence an AI's decision. You pick the column that represents the final decision (e.g. 'loan_approved') and the columns representing group identity.",
    example:
      "Example: In the loan dataset, you set Target Column = 'loan_approved' and Protected Attributes = ['race', 'gender']. You're asking: did race or gender unfairly influence who got approved?",
    tips: [
      "You can test multiple protected attributes at once",
      "FairLens auto-detects which group is statistically 'privileged' (has higher approval rates)",
      "Supports both categorical (Male/Female) and encoded (0/1) columns",
      "Protected attributes with more than 50 unique values are flagged — they may need grouping first",
    ],
  },
  {
    number: "03",
    icon: Brain,
    color: "text-blue-600",
    bg: "bg-blue-50 border-blue-200",
    glow: "shadow-blue-100",
    title: "The AI Pipeline Runs",
    plain: "FairLens's engine silently works through five stages automatically.",
    detail:
      "Once configured, the pipeline starts. You see a live progress bar. Behind the scenes: (1) your data is validated, (2) the model makes predictions on every row, (3) four mathematical fairness metrics are computed, (4) Google Gemini AI writes a plain-English explanation, (5) a PDF report is compiled.",
    example:
      "Example: For 50,000 loan rows, the engine runs in under 2 minutes. It discovers that women were approved 34% less often than men with identical financial profiles — a clear disparity.",
    tips: [
      "The pipeline is fully automated — no manual steps required",
      "Results are cached: re-running the same dataset takes milliseconds",
      "No model file? FairLens generates pseudo-predictions from ground truth labels",
      "You can close the tab — results are saved and accessible via Audit History",
    ],
  },
  {
    number: "04",
    icon: BarChart2,
    color: "text-emerald-600",
    bg: "bg-emerald-50 border-emerald-200",
    glow: "shadow-emerald-100",
    title: "Review Your Fairness Score",
    plain: "A score from 0–100 tells you at a glance how fair your model is.",
    detail:
      "The FairLens Score summarises all four fairness metrics into a single number. 100 = perfectly fair across all groups. Below 60 = serious issues. Each of the four metrics is shown with its value, threshold, and whether it passed or failed.",
    example:
      "Example: The loan model scores 54/100. Two metrics failed: Disparate Impact (0.61, below the legal 0.8 threshold) and Demographic Parity Difference (0.22, above the 0.1 limit). This means the model is approving men at nearly twice the rate of women.",
    tips: [
      "Severity: None → Low → Medium → High based on how many metrics fail",
      "Each metric links to the exact regulation it maps to (EU AI Act, EEOC 80% Rule, ECOA)",
      "Per-group breakdown shows approval rates for every group individually",
      "Hovering any metric card shows a plain-English description of what it measures",
    ],
  },
  {
    number: "05",
    icon: Sliders,
    color: "text-rose-600",
    bg: "bg-rose-50 border-rose-200",
    glow: "shadow-rose-100",
    title: "Explore Remediation Options",
    plain: "Try fixes and instantly see how they change fairness and accuracy.",
    detail:
      "FairLens provides two interactive remediation tools. (1) Threshold Simulator: drag a slider to change the decision threshold and watch fairness/accuracy trade-offs update in real time. (2) Reweighing: a technique that mathematically re-balances training data so under-represented groups are weighted more fairly.",
    example:
      "Example: Lowering the approval threshold for women from 0.5 to 0.42 raises their approval rate by 18 percentage points with only a 1.3% drop in overall accuracy — bringing the model into legal compliance.",
    tips: [
      "Threshold changes are instant — results update in under 200ms",
      "Reweighing modifies the dataset, not the model — no retraining needed",
      "Side-by-side comparison shows baseline vs. remediated metrics",
      "All changes are non-destructive — your original data is never modified",
    ],
  },
  {
    number: "06",
    icon: FileText,
    color: "text-cyan-600",
    bg: "bg-cyan-50 border-cyan-200",
    glow: "shadow-cyan-100",
    title: "Export the PDF Audit Report",
    plain: "Download a compliance-ready report you can share with regulators or leadership.",
    detail:
      "FairLens generates a professional PDF that includes all metrics, charts, per-group breakdowns, AI-generated explanations, a regulatory compliance table, and a CONFIDENTIAL watermark. The report is designed to satisfy requests from legal teams, compliance officers, and regulators.",
    example:
      "Example: A fintech company submits the FairLens PDF report to their internal ethics board before deploying an updated loan model. The report documents exactly which metrics were tested, which passed, and what remediation steps were applied.",
    tips: [
      "Report includes a chain-of-custody audit log of every action taken",
      "CONFIDENTIAL watermark applied diagonally across every page",
      "All metric values, thresholds, and pass/fail outcomes are included",
      "AI explanation section written in plain English — no technical jargon",
    ],
  },
];

const metrics = [
  {
    name: "Disparate Impact",
    icon: Scale,
    color: "text-amber-600",
    border: "border-amber-200",
    bg: "bg-amber-50",
    threshold: "≥ 0.80",
    law: "EEOC 80% Rule",
    simple:
      "Compares the approval rate of the unprivileged group to the privileged group as a ratio.",
    formula: "P(approved | women) ÷ P(approved | men)",
    example:
      "If men are approved 80% of the time and women 50% of the time: 50 ÷ 80 = 0.625. This fails the 0.8 threshold — meaning women are approved at less than 80% the rate of men, which is a legal violation under the US EEOC 80% Rule.",
    good: "≥ 0.80 (women approved at least 80% as often as men)",
    bad: "0.61 (women approved only 61% as often — fails legal threshold)",
  },
  {
    name: "Demographic Parity Difference",
    icon: Users,
    color: "text-purple-600",
    border: "border-purple-200",
    bg: "bg-purple-50",
    threshold: "≤ 0.10",
    law: "EU AI Act Art. 10",
    simple:
      "Measures the raw gap in positive prediction rates between groups. Should be close to zero.",
    formula: "P(ŷ=1 | women) − P(ŷ=1 | men)",
    example:
      "Men are predicted positive 75% of the time, women 53%. The difference is 75% − 53% = 0.22. This exceeds the 0.10 limit, meaning the model systematically predicts positive outcomes for men far more often.",
    good: "0.02 (nearly identical rates across groups)",
    bad: "0.22 (22 percentage point gap — fails threshold)",
  },
  {
    name: "Equalized Odds Difference",
    icon: BarChart2,
    color: "text-blue-600",
    border: "border-blue-200",
    bg: "bg-blue-50",
    threshold: "≤ 0.10",
    law: "EU AI Act Art. 13",
    simple:
      "Checks whether the model's error rates (false positives and false negatives) are the same across groups.",
    formula: "max(|TPR_men − TPR_women|, |FPR_men − FPR_women|)",
    example:
      "The model correctly identifies 90% of creditworthy men (TPR = 0.90) but only 70% of creditworthy women (TPR = 0.70). The gap is 0.20 — far above the 0.10 threshold. Women who deserve approval are being incorrectly rejected at twice the rate.",
    good: "0.04 (nearly equal error rates across groups)",
    bad: "0.20 (20% gap in true positive rate — model much better for men)",
  },
  {
    name: "Calibration Difference",
    icon: CheckCircle,
    color: "text-emerald-600",
    border: "border-emerald-200",
    bg: "bg-emerald-50",
    threshold: "≤ 0.10",
    law: "ISO/IEC 42001",
    simple:
      "When the model says someone will be approved, how often is it right? This checks if that reliability is equal across groups.",
    formula: "|Precision_women − Precision_men|",
    example:
      "When the model says a man will be approved, it's correct 88% of the time. When it says a woman will be approved, it's correct only 71% of the time. The 17% gap means the model's confidence scores are less trustworthy for women.",
    good: "0.03 (equally reliable predictions for all groups)",
    bad: "0.17 (predictions for women are 17% less reliable)",
  },
];

const faqs = [
  {
    q: "Do I need a machine learning background to use FairLens?",
    a: "Not at all. FairLens is designed for compliance officers, legal teams, product managers, and executives — not just data scientists. Every metric is explained in plain English. The AI explanation panel translates technical results into a narrative anyone can understand and share.",
  },
  {
    q: "What if my model file is in a format FairLens doesn't support?",
    a: "FairLens accepts .pkl (scikit-learn, XGBoost, LightGBM) and .onnx (universal interchange format). If your model is in another format (TensorFlow, PyTorch), export it to ONNX first using the official conversion tools. Alternatively, you can run FairLens without a model — upload just the CSV with ground-truth labels and predictions pre-computed.",
  },
  {
    q: "How is the FairLens Score calculated?",
    a: "It's a weighted composite of the four fairness metrics. Each metric is scored 0–100 based on how close its value is to the ideal (passing) threshold. Two metrics failing = High severity. One failing = Medium. All passing but close to threshold = Low. All comfortably passing = None.",
  },
  {
    q: "Is my data stored anywhere?",
    a: "In local mode, data is stored only on the server disk in a temporary job directory. In production (GCP), files go to your private GCS buckets in your own Google Cloud project. FairLens never shares your data with third parties. The Gemini AI explanation only receives statistical results — not your raw data.",
  },
  {
    q: "What is reweighing and does it change my model?",
    a: "Reweighing is a pre-processing fairness technique that assigns different importance weights to training examples from under-represented groups. It does NOT modify your model or its weights — it produces a new, re-balanced version of your dataset that you could use to retrain the model. Your original data is always preserved.",
  },
  {
    q: "What regulations does FairLens map to?",
    a: "FairLens maps failed metrics to: the US EEOC 80% Rule (Disparate Impact), the EU AI Act Articles 10 and 13, the US Equal Credit Opportunity Act (ECOA), and ISO/IEC 42001 AI Management System standard. Each failed metric in the report explicitly cites the relevant regulation.",
  },
];

// ── Component ─────────────────────────────────────────────────────────────────

function FAQItem({ q, a }: { q: string; a: string }) {
  const [open, setOpen] = useState(false);
  return (
    <button
      onClick={() => setOpen(!open)}
      className="w-full text-left metric-border rounded-2xl p-5 transition-all duration-200 hover:shadow-md"
    >
      <div className="flex items-center justify-between gap-4">
        <span className="font-semibold text-amber-950">{q}</span>
        {open ? (
          <ChevronDown className="h-4 w-4 shrink-0 text-amber-600" />
        ) : (
          <ChevronRight className="h-4 w-4 shrink-0 text-amber-600" />
        )}
      </div>
      {open && (
        <p className="mt-3 text-sm leading-7 text-amber-900/70 border-t border-amber-100 pt-3">
          {a}
        </p>
      )}
    </button>
  );
}

export default function HowItWorks() {
  return (
    <div className="space-y-16 animate-fade-in pb-16">

      {/* ── Hero ── */}
      <section className="panel px-6 py-12 sm:px-10 text-center">
        <div className="inline-flex items-center gap-2 rounded-full border border-amber-200 bg-amber-50 px-4 py-2 text-xs uppercase tracking-widest text-amber-700 mb-6">
          <BookOpen className="h-3 w-3" />
          Complete Guide
        </div>
        <h1 className="font-[family-name:var(--font-display)] text-4xl sm:text-5xl font-bold text-amber-950 max-w-3xl mx-auto leading-tight">
          How FairLens Works
        </h1>
        <p className="mt-5 text-lg text-amber-900/70 max-w-2xl mx-auto leading-8">
          A plain-English guide to AI bias auditing — from what the problem is,
          to how FairLens detects it, to what you can do about it. No technical
          background required.
        </p>
        <div className="mt-8 flex flex-wrap gap-3 justify-center">
          <Link href="/upload" className="btn-primary px-6 py-3">
            Start your first audit <ArrowRight className="h-4 w-4" />
          </Link>
          <Link href="/" className="btn-secondary px-6 py-3">
            Back to dashboard
          </Link>
        </div>
      </section>

      {/* ── The Problem ── */}
      <section className="space-y-6">
        <div className="text-center">
          <div className="inline-flex items-center gap-2 text-xs uppercase tracking-widest text-amber-700 mb-3">
            <AlertTriangle className="h-3 w-3" />
            The Problem
          </div>
          <h2 className="font-[family-name:var(--font-display)] text-3xl font-bold text-amber-950">
            What is AI bias, and why does it matter?
          </h2>
        </div>

        <div className="grid gap-6 lg:grid-cols-2">
          <div className="panel-soft p-7 space-y-4">
            <div className="text-2xl font-bold text-amber-600">The core issue</div>
            <p className="text-amber-900/80 leading-7">
              An AI model learns patterns from historical data. If that historical data
              reflects past discrimination — for example, women were historically denied
              loans more often than men — the model learns to replicate that discrimination,
              even if gender is never explicitly given as an input.
            </p>
            <p className="text-amber-900/80 leading-7">
              This is called <strong>algorithmic bias</strong>. The model isn't intentionally
              prejudiced, but its outputs systematically disadvantage certain groups. 
              The scary part: without tools like FairLens, this bias is invisible.
            </p>
          </div>

          <div className="panel-soft p-7 space-y-4">
            <div className="text-2xl font-bold text-amber-600">A real example</div>
            <div className="metric-border rounded-2xl p-4 space-y-3">
              <p className="text-sm text-amber-900/80 leading-6">
                📋 <strong>COMPAS (2016)</strong> — A risk-scoring algorithm used by US courts
                to predict criminal recidivism. ProPublica found it was nearly twice as likely
                to falsely flag Black defendants as future criminals compared to white defendants,
                while simultaneously under-flagging white defendants.
              </p>
              <p className="text-sm text-amber-900/80 leading-6">
                🏦 <strong>Amazon Hiring Tool (2018)</strong> — Amazon's AI résumé screener
                trained on 10 years of hiring data. Since the tech industry historically hired
                mostly men, it learned to penalise CVs containing the word "women's"
                (e.g. "women's chess club captain"). Amazon scrapped the tool.
              </p>
            </div>
          </div>
        </div>

        <div className="panel px-7 py-6">
          <div className="flex gap-4 items-start">
            <Shield className="h-8 w-8 text-amber-600 shrink-0 mt-1" />
            <div>
              <div className="font-bold text-amber-950 text-lg">Why regulators now require bias audits</div>
              <p className="mt-2 text-amber-900/70 leading-7">
                The <strong>EU AI Act (2024)</strong> classifies hiring, credit, and justice AI systems
                as "high-risk" and mandates documented bias testing before deployment. In the US, the 
                <strong> EEOC 80% Rule</strong> has required disparate impact analysis in hiring for
                decades. The <strong>Equal Credit Opportunity Act (ECOA)</strong> makes discriminatory
                lending decisions illegal. FairLens generates the documentation required to satisfy
                all three frameworks.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ── Step by Step ── */}
      <section className="space-y-6">
        <div className="text-center">
          <div className="inline-flex items-center gap-2 text-xs uppercase tracking-widest text-amber-700 mb-3">
            <Zap className="h-3 w-3" />
            Step by Step
          </div>
          <h2 className="font-[family-name:var(--font-display)] text-3xl font-bold text-amber-950">
            Using FairLens from start to finish
          </h2>
          <p className="mt-3 text-amber-900/60 max-w-xl mx-auto">
            Six clear stages. Each one explained with a concrete example.
          </p>
        </div>

        <div className="space-y-6">
          {steps.map((step) => (
            <div key={step.number} className="panel-soft p-0 overflow-hidden">
              <div className="grid lg:grid-cols-[280px_1fr]">
                {/* Left */}
                <div className={`${step.bg} border-r p-7 flex flex-col justify-between`}>
                  <div>
                    <div className="text-5xl font-black text-black/10 leading-none">{step.number}</div>
                    <step.icon className={`h-7 w-7 ${step.color} mt-3`} />
                    <div className="mt-3 font-bold text-amber-950 text-xl leading-tight">{step.title}</div>
                  </div>
                  <div className="mt-5 text-sm italic text-amber-900/60 leading-6">"{step.plain}"</div>
                </div>
                {/* Right */}
                <div className="p-7 space-y-5">
                  <p className="text-amber-900/80 leading-7">{step.detail}</p>
                  <div className="metric-border rounded-2xl p-4">
                    <div className="text-xs uppercase tracking-wider text-amber-700 mb-2 font-semibold">Real Example</div>
                    <p className="text-sm text-amber-900/80 leading-6">{step.example}</p>
                  </div>
                  <div>
                    <div className="text-xs uppercase tracking-wider text-amber-700 mb-2 font-semibold">Things to know</div>
                    <ul className="space-y-1">
                      {step.tips.map((tip) => (
                        <li key={tip} className="flex items-start gap-2 text-sm text-amber-900/70">
                          <CheckCircle className="h-4 w-4 text-emerald-500 shrink-0 mt-0.5" />
                          {tip}
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ── The 4 Metrics ── */}
      <section className="space-y-6">
        <div className="text-center">
          <div className="inline-flex items-center gap-2 text-xs uppercase tracking-widest text-amber-700 mb-3">
            <BarChart2 className="h-3 w-3" />
            The Science
          </div>
          <h2 className="font-[family-name:var(--font-display)] text-3xl font-bold text-amber-950">
            The four fairness metrics — explained simply
          </h2>
          <p className="mt-3 text-amber-900/60 max-w-xl mx-auto">
            FairLens computes four industry-standard metrics. Here's what each one measures and what it means in practice.
          </p>
        </div>

        <div className="grid gap-6 lg:grid-cols-2">
          {metrics.map((m) => (
            <div key={m.name} className={`panel-soft border ${m.border} p-7 space-y-4`}>
              <div className="flex items-center gap-3">
                <div className={`${m.bg} ${m.border} border rounded-xl p-2`}>
                  <m.icon className={`h-5 w-5 ${m.color}`} />
                </div>
                <div>
                  <div className="font-bold text-amber-950">{m.name}</div>
                  <div className="text-xs text-amber-900/50">Threshold: {m.threshold} · Regulation: {m.law}</div>
                </div>
              </div>
              <p className="text-sm text-amber-900/80 leading-6">{m.simple}</p>
              <div className="metric-border rounded-xl p-3">
                <div className="text-xs text-amber-700 font-mono font-semibold mb-1">Formula</div>
                <div className="text-sm font-mono text-amber-950">{m.formula}</div>
              </div>
              <div className="space-y-2 text-sm leading-6">
                <p className="text-amber-900/80">{m.example}</p>
                <div className="grid grid-cols-2 gap-3 pt-1">
                  <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-3">
                    <div className="text-xs font-semibold text-emerald-700 mb-1">✓ Passing</div>
                    <div className="text-emerald-800 font-mono text-xs">{m.good}</div>
                  </div>
                  <div className="bg-rose-50 border border-rose-200 rounded-xl p-3">
                    <div className="text-xs font-semibold text-rose-700 mb-1">✗ Failing</div>
                    <div className="text-rose-800 font-mono text-xs">{m.bad}</div>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ── FAQ ── */}
      <section className="space-y-6">
        <div className="text-center">
          <h2 className="font-[family-name:var(--font-display)] text-3xl font-bold text-amber-950">
            Frequently Asked Questions
          </h2>
        </div>
        <div className="space-y-3 max-w-3xl mx-auto">
          {faqs.map((faq) => (
            <FAQItem key={faq.q} q={faq.q} a={faq.a} />
          ))}
        </div>
      </section>

      {/* ── CTA ── */}
      <section className="panel px-8 py-12 text-center">
        <div className="text-3xl font-bold text-amber-950 mb-3">Ready to audit your model?</div>
        <p className="text-amber-900/60 mb-7 max-w-lg mx-auto">
          Upload a CSV and get a full fairness report in under 2 minutes.
          No technical background required.
        </p>
        <Link href="/upload" className="btn-primary px-8 py-4 text-base">
          Start audit now <ArrowRight className="h-5 w-5" />
        </Link>
      </section>
    </div>
  );
}
