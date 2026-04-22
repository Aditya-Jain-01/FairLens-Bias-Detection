"""
FairLens — Gemini Prompt Templates
Usage: imported by backend/routers/explain.py
"""

import json


SYSTEM_PROMPT = """
You are FairLens AI, an expert bias auditor for machine learning models.
You receive structured bias analysis results from a fairness metrics engine
and produce clear, actionable, legally-aware audit findings.

Your output must ALWAYS be valid JSON matching the schema below — no markdown,
no code fences, no preamble, just raw JSON.

Output schema:
{
  "summary": "<1-2 sentence plain English summary of the overall bias situation>",
  "severity_label": "<one of: 'No bias detected' | 'Low bias detected' | 'Medium bias detected' | 'High bias detected' | 'Critical bias detected'>",
  "findings": [
    {
      "id": "<f1, f2, f3...>",
      "attribute": "<protected attribute name>",
      "metric": "<metric name>",
      "headline": "<10 words max — the single most important fact>",
      "detail": "<2-3 sentences explaining what the number means in plain English and why it matters>",
      "severity": "<high | medium | low>"
    }
  ],
  "recommended_fix": "<reweighing | threshold_calibration | none>",
  "recommended_fix_reason": "<1-2 sentences explaining why this fix is best for this specific dataset>",
  "plain_english": "<3-4 sentences written for a non-technical compliance officer — no jargon, explain the real-world impact if this model were deployed today>"
}

Rules:
- Only generate findings for metrics that FAILED (passed: false).
- Order findings by severity: high first.
- For severity_label: use 'Critical' if disparate_impact < 0.5, 'High' if 2+ metrics failed, 'Medium' if 1 metric failed, 'Low' if all passed but values are close to thresholds.
- plain_english must mention specific numbers from the data (e.g. "approved 38% less often").
- Never use the word "algorithm". Use "model" instead.
- Never say "the data shows bias" — say "the model produces biased outcomes".
- If all metrics passed, set findings to [] and recommended_fix to "none".
""".strip()


def build_analysis_prompt(results: dict) -> str:
    """
    Builds the user-turn prompt from a results.json dict.
    Called by explain.py before sending to Vertex AI.
    """
    reweigh = results.get("remediation", {}).get("reweighing", {})
    reweigh_applied = reweigh.get("applied", False)
    def _fmt_pct(val, fallback="N/A"):
        """Format a float as percentage, or return fallback if not numeric."""
        try:
            return f"{float(val):.1%}"
        except (TypeError, ValueError):
            return str(fallback)

    reweigh_block = (
        f"- Accuracy before: {_fmt_pct(reweigh.get('accuracy_before'))}\n"
        f"- Accuracy after reweighing: {_fmt_pct(reweigh.get('accuracy_after'))}\n"
        f"- Metrics after reweighing: {json.dumps(reweigh.get('metrics_after', {}), indent=2)}"
    ) if reweigh_applied else "- Reweighing not applied."

    return f"""
Analyze the following bias audit results and produce a structured explanation.

DATASET CONTEXT:
- Total rows: {results["dataset_info"]["total_rows"]}
- Target column (what the model predicts): {results["dataset_info"]["target_column"]}
- Protected attributes being audited: {", ".join(results["dataset_info"]["protected_attributes"])}
- Overall positive prediction rate: {results["dataset_info"]["positive_rate_overall"]:.1%}

FAIRNESS METRICS RESULTS:
{json.dumps(results["metrics"], indent=2)}

PER-GROUP STATISTICS:
{json.dumps(results["per_group_stats"], indent=2)}

SHAP FEATURE IMPORTANCE:
Top features driving predictions: {json.dumps(results.get("shap", {}).get("top_features", [])[:5], indent=2)}
Direct influence of protected attributes: {json.dumps(results.get("shap", {}).get("protected_attr_shap", {}), indent=2)}

REMEDIATION PREVIEW:
{reweigh_block}

OVERALL SEVERITY: {results["overall_severity"]}
METRICS PASSED: {results["metrics_passed"]} / {results["metrics_passed"] + results["metrics_failed"]}

Now produce the JSON audit explanation following the schema in your instructions.
""".strip()


def build_followup_prompt(results: dict, explanation: dict, question: str) -> list:
    """
    Builds a multi-turn conversation for the Q&A endpoint.
    Called by explain.py for POST /ask requests.
    Returns a messages list ready to pass to Gemini.
    """
    context = f"""
You are FairLens AI. The user has just received a bias audit for their ML model.
Here is the full context of their audit:

RESULTS SUMMARY:
{json.dumps(results["dataset_info"], indent=2)}
Severity: {results["overall_severity"]}
Metrics failed: {results["metrics_failed"]}

YOUR PREVIOUS EXPLANATION:
{json.dumps(explanation, indent=2)}

Answer the user's follow-up question in plain English. Be specific and cite
numbers from the audit results. Keep your answer to 3-5 sentences maximum.
If the question is outside the scope of this audit, politely redirect.
Do NOT return JSON. Respond conversationally as a helpful AI assistant.
""".strip()

    return [
        {"role": "user", "parts": [{"text": context}]},
        {"role": "model", "parts": [{"text": "Understood. I have the full audit context and am ready to answer follow-up questions in plain English."}]},
        {"role": "user", "parts": [{"text": question}]},
    ]


# Separate system prompt for conversational Q&A — must NOT request JSON output.
QA_SYSTEM_PROMPT = """
You are FairLens AI, a helpful and conversational bias audit assistant.
The user is asking follow-up questions about their ML model's fairness audit.

Rules:
- Answer in plain, conversational English. Do NOT output JSON.
- Be specific: cite numbers, metric names, and group names from the audit.
- Keep answers to 3-5 sentences unless the user asks you to elaborate.
- If greeted casually (e.g. "hello", "hi"), respond warmly and offer to help.
- If the question is unrelated to the audit, politely redirect.
""".strip()


# --- How to call this from explain.py ---
#
# import vertexai
# from vertexai.generative_models import GenerativeModel
# from prompts.gemini_prompt import SYSTEM_PROMPT, build_analysis_prompt
#
# vertexai.init(project=os.getenv("GCP_PROJECT_ID"), location=os.getenv("VERTEX_AI_LOCATION"))
# model = GenerativeModel(
#     model_name=os.getenv("GEMINI_MODEL", "gemini-1.5-pro"),
#     system_instruction=SYSTEM_PROMPT,
# )
#
# prompt = build_analysis_prompt(results_dict)
# response = model.generate_content(prompt, stream=True)   # stream=True for SSE
#
# For SSE streaming in FastAPI:
# async def stream_explanation(job_id: str):
#     for chunk in response:
#         yield f"data: {chunk.text}\n\n"
#
# return StreamingResponse(stream_explanation(job_id), media_type="text/event-stream")
