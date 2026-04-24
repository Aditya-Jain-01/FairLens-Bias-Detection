"""
FairLens -- PDF Report Generator (Rich Visuals Edition)

Generates a visually rich, multi-page PDF audit report using reportlab + matplotlib.
All charts are dataset-agnostic: they dynamically adapt to any number of metrics,
protected attributes, groups, and SHAP features.

Chart pipeline:
  1. Severity Header Badge
  2. Fairness Score Gauge
  3. Metrics Pass/Fail Bar Chart
  4. Per-Group Positive Rate Comparison (one per attribute)
  5. SHAP Feature Importance
  6. Remediation Before/After Comparison
"""

import io
import os
import logging
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

_TEMPLATES_DIR = Path(__file__).parent.parent / "templates"

# ── Colour Palette ────────────────────────────────────────────────────────────

_PASS_COLOR = "#16a34a"
_FAIL_COLOR = "#dc2626"
_THRESHOLD_COLOR = "#6366f1"
_BG_COLOR = "#fafafa"

_SEVERITY_COLORS = {
    "critical": "#7c3aed",
    "high": "#dc2626",
    "medium": "#d97706",
    "low": "#16a34a",
    "none": "#6b7280",
}

_DIRECTION_COLORS = {
    "positive": "#16a34a",
    "negative": "#dc2626",
    "mixed": "#d97706",
}

_GROUP_PALETTE = [
    "#6366f1", "#f59e0b", "#10b981", "#ef4444", "#8b5cf6",
    "#ec4899", "#14b8a6", "#f97316", "#06b6d4", "#84cc16",
    "#e11d48", "#0ea5e9", "#a855f7", "#22d3ee", "#facc15",
]


# ── Chart Generators ──────────────────────────────────────────────────────────

def _make_chart_image(fig) -> str:
    """Save a matplotlib figure to a temp PNG and return its path."""
    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    fig.savefig(tmp.name, format="png", dpi=150, bbox_inches="tight",
                facecolor="#ffffff", edgecolor="none")
    import matplotlib.pyplot as plt
    plt.close(fig)
    return tmp.name


def _chart_severity_badge(severity: str, job_id: str) -> str:
    """Create a wide severity banner image."""
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches

    color = _SEVERITY_COLORS.get(severity.lower(), "#dc2626")
    fig, ax = plt.subplots(figsize=(7.5, 1.2))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 1)
    ax.axis("off")

    badge = mpatches.FancyBboxPatch(
        (0.05, 0.1), 9.9, 0.8, boxstyle="round,pad=0.1",
        facecolor=color, edgecolor="none", alpha=0.9
    )
    ax.add_patch(badge)
    ax.text(5, 0.55, f"SEVERITY: {severity.upper()}",
            ha="center", va="center", fontsize=18, fontweight="bold",
            color="white", family="sans-serif")
    ax.text(5, 0.2, f"Job: {job_id}",
            ha="center", va="center", fontsize=9, color="white", alpha=0.85,
            family="sans-serif")

    return _make_chart_image(fig)


def _chart_fairness_gauge(score: float, grade: str) -> str:
    """Create a semi-circular fairness score gauge."""
    import matplotlib.pyplot as plt
    import numpy as np

    fig, ax = plt.subplots(figsize=(4, 2.8), subplot_kw={"projection": "polar"})

    # Gauge spans from pi to 0 (left to right semicircle)
    theta_bg = np.linspace(np.pi, 0, 100)
    ax.fill_between(theta_bg, 0.6, 1.0, color="#e5e7eb", alpha=0.5)

    # Score arc
    score_clamped = max(0, min(100, score))
    theta_score = np.linspace(np.pi, np.pi - (score_clamped / 100) * np.pi, 100)

    if score_clamped >= 70:
        arc_color = "#16a34a"
    elif score_clamped >= 40:
        arc_color = "#d97706"
    else:
        arc_color = "#dc2626"

    ax.fill_between(theta_score, 0.6, 1.0, color=arc_color, alpha=0.85)

    # Labels
    ax.set_ylim(0, 1.3)
    ax.set_thetamin(0)
    ax.set_thetamax(180)
    ax.axis("off")

    fig.text(0.5, 0.25, f"{score_clamped:.0f}", ha="center", va="center",
             fontsize=36, fontweight="bold", color=arc_color, family="sans-serif")
    fig.text(0.5, 0.12, f"Grade: {grade}", ha="center", va="center",
             fontsize=14, color="#374151", family="sans-serif")
    fig.text(0.5, 0.95, "FairLens Score", ha="center", va="center",
             fontsize=12, fontweight="bold", color="#111827", family="sans-serif")

    return _make_chart_image(fig)


def _chart_metrics_bar(metrics: dict) -> str:
    """Horizontal bar chart: metric values vs thresholds, colored pass/fail."""
    import matplotlib.pyplot as plt
    import numpy as np

    names = []
    values = []
    thresholds = []
    colors = []

    for key, m in metrics.items():
        names.append(key.replace("_", " ").title())
        values.append(m.get("value", 0))
        thresholds.append(m.get("threshold", 0))
        colors.append(_PASS_COLOR if m.get("passed") else _FAIL_COLOR)

    if not names:
        return ""

    y = np.arange(len(names))
    fig, ax = plt.subplots(figsize=(7, max(2.5, len(names) * 0.7)))

    bars = ax.barh(y, values, height=0.45, color=colors, alpha=0.85,
                   edgecolor="white", linewidth=0.5, label="Value")

    # Threshold markers
    for i, t in enumerate(thresholds):
        ax.plot(t, i, marker="D", color=_THRESHOLD_COLOR, markersize=8, zorder=5)

    ax.set_yticks(y)
    ax.set_yticklabels(names, fontsize=10)
    ax.set_xlabel("Value", fontsize=10)
    ax.set_title("Fairness Metrics (◆ = Threshold)", fontsize=13, fontweight="bold", pad=12)
    ax.invert_yaxis()
    ax.set_facecolor(_BG_COLOR)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    # Value labels on bars
    for bar, val, passed in zip(bars, values, [m.get("passed") for m in metrics.values()]):
        label = f"{val:.3f} {'✓' if passed else '✗'}"
        ax.text(bar.get_width() + 0.01, bar.get_y() + bar.get_height() / 2,
                label, va="center", fontsize=9, color="#374151")

    fig.tight_layout()
    return _make_chart_image(fig)


def _chart_group_comparison(attr_name: str, groups: dict) -> str:
    """Grouped bar chart: positive rate per demographic group for one attribute."""
    import matplotlib.pyplot as plt
    import numpy as np

    if not groups:
        return ""

    group_ids = list(groups.keys())
    pos_rates = [groups[g].get("positive_rate", 0) for g in group_ids]
    counts = [groups[g].get("count", 0) for g in group_ids]

    # Label groups with their count
    labels = [f"Group {g}\n(n={counts[i]:,})" for i, g in enumerate(group_ids)]
    colors = [_GROUP_PALETTE[i % len(_GROUP_PALETTE)] for i in range(len(group_ids))]

    x = np.arange(len(labels))
    fig, ax = plt.subplots(figsize=(max(4, len(labels) * 1.1), 3.5))

    bars = ax.bar(x, pos_rates, color=colors, alpha=0.85, edgecolor="white", linewidth=0.5)

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=8)
    ax.set_ylabel("Positive Outcome Rate", fontsize=10)
    ax.set_title(f"Group Outcomes — {attr_name.replace('_', ' ').title()}",
                 fontsize=13, fontweight="bold", pad=12)
    ax.set_ylim(0, 1.0)
    ax.set_facecolor(_BG_COLOR)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    # Value labels
    for bar, rate in zip(bars, pos_rates):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.02,
                f"{rate:.1%}", ha="center", fontsize=9, color="#374151")

    fig.tight_layout()
    return _make_chart_image(fig)


def _chart_shap_importance(top_features: list) -> str:
    """Horizontal bar chart for SHAP feature importance."""
    import matplotlib.pyplot as plt
    import numpy as np

    if not top_features:
        return ""

    features = [f["feature"] for f in top_features]
    importances = [f["importance"] for f in top_features]
    directions = [f.get("direction", "mixed") for f in top_features]
    colors = [_DIRECTION_COLORS.get(d, "#6366f1") for d in directions]

    y = np.arange(len(features))
    fig, ax = plt.subplots(figsize=(7, max(2.5, len(features) * 0.55)))

    bars = ax.barh(y, importances, color=colors, alpha=0.85,
                   edgecolor="white", linewidth=0.5)

    ax.set_yticks(y)
    ax.set_yticklabels(features, fontsize=10)
    ax.set_xlabel("SHAP Importance", fontsize=10)
    ax.set_title("Feature Importance (SHAP)", fontsize=13, fontweight="bold", pad=12)
    ax.invert_yaxis()
    ax.set_facecolor(_BG_COLOR)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    for bar, imp in zip(bars, importances):
        ax.text(bar.get_width() + 0.005, bar.get_y() + bar.get_height() / 2,
                f"{imp:.3f}", va="center", fontsize=9, color="#374151")

    # Legend for directions
    from matplotlib.patches import Patch
    legend_items = []
    seen = set()
    for d in directions:
        if d not in seen:
            seen.add(d)
            legend_items.append(Patch(color=_DIRECTION_COLORS.get(d, "#6366f1"),
                                     label=d.title()))
    if legend_items:
        ax.legend(handles=legend_items, loc="lower right", fontsize=8, framealpha=0.8)

    fig.tight_layout()
    return _make_chart_image(fig)


def _chart_remediation(metrics_before: dict, metrics_after: dict) -> str:
    """Side-by-side bar chart comparing before vs after reweighing."""
    import matplotlib.pyplot as plt
    import numpy as np

    if not metrics_after:
        return ""

    names = []
    before_vals = []
    after_vals = []

    for key in metrics_before:
        if key in metrics_after:
            names.append(key.replace("_", " ").title())
            before_vals.append(metrics_before[key].get("value", 0))
            after_vals.append(metrics_after[key].get("value", 0))

    if not names:
        return ""

    x = np.arange(len(names))
    width = 0.35
    fig, ax = plt.subplots(figsize=(max(5, len(names) * 1.5), 3.5))

    ax.bar(x - width / 2, before_vals, width, label="Before", color="#ef4444", alpha=0.8)
    ax.bar(x + width / 2, after_vals, width, label="After", color="#22c55e", alpha=0.8)

    ax.set_xticks(x)
    ax.set_xticklabels(names, fontsize=9, rotation=15, ha="right")
    ax.set_ylabel("Value", fontsize=10)
    ax.set_title("Remediation Impact (Before vs After)", fontsize=13,
                 fontweight="bold", pad=12)
    ax.legend(fontsize=9)
    ax.set_facecolor(_BG_COLOR)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    fig.tight_layout()
    return _make_chart_image(fig)


# ── PDF Assembly ──────────────────────────────────────────────────────────────

def generate_pdf_report(results: dict, explanation: dict) -> bytes:
    """
    Generate a visually rich PDF report using reportlab + matplotlib charts.

    Args:
        results:     Parsed results.json dict.
        explanation: Parsed explanation.json dict (Gemini output).

    Returns:
        PDF content as bytes.
    """
    try:
        return _generate_rich_report(results, explanation)
    except Exception as exc:
        logger.error(f"Rich PDF generation failed: {exc}")
        # Final fallback — bare minimum text PDF
        return _generate_minimal_pdf(results, explanation)


def _generate_rich_report(results: dict, explanation: dict) -> bytes:
    """Full reportlab PDF with embedded matplotlib charts."""
    import matplotlib
    matplotlib.use("Agg")  # Non-interactive backend

    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Image,
        Table, TableStyle, PageBreak, KeepTogether
    )
    from reportlab.lib import colors
    from services.compliance_mapper import map_to_regulations

    buffer = io.BytesIO()

    # ── Watermark callback (drawn on every page) ──────────────────────────
    def _draw_watermark(canvas, doc):
        """Stamp CONFIDENTIAL diagonally across the page in light gray."""
        from reportlab.lib.colors import Color
        canvas.saveState()
        canvas.setFont("Helvetica-Bold", 52)
        canvas.setFillColor(Color(0.75, 0.75, 0.75, alpha=0.18))  # very light gray
        canvas.translate(306, 396)   # centre of letter page (612x792)
        canvas.rotate(45)
        canvas.drawCentredString(0, 0, "CONFIDENTIAL")
        canvas.restoreState()

    doc = SimpleDocTemplate(
        buffer, pagesize=letter,
        topMargin=0.5 * inch, bottomMargin=0.6 * inch,
        leftMargin=0.65 * inch, rightMargin=0.65 * inch
    )
    story = []
    styles = getSampleStyleSheet()
    chart_files = []  # Track temp files for cleanup

    # ── Custom styles ─────────────────────────────────────────────────────
    title_style = ParagraphStyle(
        "RichTitle", parent=styles["Heading1"],
        fontSize=26, textColor=colors.HexColor("#1f2937"),
        spaceAfter=4, fontName="Helvetica-Bold", alignment=TA_CENTER
    )
    subtitle_style = ParagraphStyle(
        "RichSubtitle", parent=styles["Normal"],
        fontSize=10, textColor=colors.HexColor("#6b7280"),
        spaceAfter=16, alignment=TA_CENTER
    )
    section_style = ParagraphStyle(
        "RichSection", parent=styles["Heading2"],
        fontSize=16, textColor=colors.HexColor("#111827"),
        spaceBefore=18, spaceAfter=10, fontName="Helvetica-Bold"
    )
    body_style = ParagraphStyle(
        "RichBody", parent=styles["Normal"],
        fontSize=10, textColor=colors.HexColor("#374151"),
        leading=14, spaceAfter=6
    )
    small_style = ParagraphStyle(
        "SmallNote", parent=styles["Normal"],
        fontSize=8, textColor=colors.HexColor("#9ca3af"),
        leading=11, spaceAfter=4
    )

    # ── Helper to add chart images ────────────────────────────────────────
    def add_chart(path: str, width=None, height=None):
        if not path:
            return
        chart_files.append(path)
        w = width or 6.8 * inch
        h = height or 2.2 * inch
        story.append(Image(path, width=w, height=h))
        story.append(Spacer(1, 0.15 * inch))

    # ══════════════════════════════════════════════════════════════════════
    # PAGE 1 — Header & Overview
    # ══════════════════════════════════════════════════════════════════════

    story.append(Paragraph("FairLens Audit Report", title_style))
    from datetime import datetime
    story.append(Paragraph(
        f"Generated {datetime.now().strftime('%B %d, %Y at %H:%M')}",
        subtitle_style
    ))

    # Severity badge
    severity = results.get("overall_severity", "high")
    badge_path = _chart_severity_badge(severity, results.get("job_id", "N/A"))
    add_chart(badge_path, width=7 * inch, height=1.0 * inch)

    # Fairness score gauge
    fs = results.get("fairness_score", {})
    if fs:
        gauge_path = _chart_fairness_gauge(fs.get("score", 0), fs.get("grade", "N/A"))
        add_chart(gauge_path, width=3.5 * inch, height=2.4 * inch)

    # Dataset info table
    ds = results.get("dataset_info", {})
    story.append(Paragraph("Dataset Overview", section_style))
    info_data = [
        ["Job ID", str(results.get("job_id", "N/A"))],
        ["Total Rows", f"{ds.get('total_rows', 'N/A'):,}" if isinstance(ds.get('total_rows'), int) else str(ds.get('total_rows', 'N/A'))],
        ["Target Column", str(ds.get("target_column", "N/A"))],
        ["Protected Attributes", ", ".join(ds.get("protected_attributes", []))],
        ["Overall Positive Rate", f"{ds.get('positive_rate_overall', 0):.1%}"],
        ["Metrics Passed", f"{results.get('metrics_passed', 0)} / {results.get('metrics_passed', 0) + results.get('metrics_failed', 0)}"],
    ]
    info_table = Table(info_data, colWidths=[2.2 * inch, 4.5 * inch])
    info_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f3f4f6")),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#1f2937")),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e5e7eb")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 0.3 * inch))

    # ══════════════════════════════════════════════════════════════════════
    # PAGE 2 — Metrics & Group Analysis
    # ══════════════════════════════════════════════════════════════════════
    story.append(PageBreak())

    # Metrics bar chart
    metrics = results.get("metrics", {})
    if metrics:
        story.append(Paragraph("Fairness Metrics Analysis", section_style))
        metrics_path = _chart_metrics_bar(metrics)
        add_chart(metrics_path, height=max(2.0, len(metrics) * 0.65) * inch)

        # Detailed metrics table
        met_header = ["Metric", "Value", "Threshold", "Verdict"]
        met_rows = [met_header]
        for key, m in metrics.items():
            verdict = "PASS ✓" if m.get("passed") else "FAIL ✗"
            met_rows.append([
                key.replace("_", " ").title(),
                f"{m.get('value', 0):.3f}",
                str(m.get("threshold", "—")),
                verdict,
            ])
        met_table = Table(met_rows, colWidths=[2.5 * inch, 1.2 * inch, 1.2 * inch, 1.2 * inch])
        met_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d1d5db")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f9fafb")]),
        ]))
        story.append(met_table)
        story.append(Spacer(1, 0.2 * inch))

        # Metric descriptions
        for key, m in metrics.items():
            desc = m.get("description", "")
            if desc:
                story.append(Paragraph(
                    f"<b>{key.replace('_', ' ').title()}:</b> {desc}", small_style
                ))

    # Per-group comparison charts (one per protected attribute)
    per_group = results.get("per_group_stats", {})
    if per_group:
        story.append(PageBreak())
        story.append(Paragraph("Demographic Group Analysis", section_style))
        story.append(Paragraph(
            "Positive outcome rates broken down by each protected attribute group. "
            "Large disparities indicate potential bias.",
            body_style
        ))

        for attr_name, groups in per_group.items():
            group_path = _chart_group_comparison(attr_name, groups)
            if group_path:
                add_chart(group_path, height=3.0 * inch)

                # Summary table for this attribute
                g_header = ["Group", "Count", "Pos. Rate", "TPR", "FPR"]
                g_rows = [g_header]
                for gid, gdata in groups.items():
                    g_rows.append([
                        f"Group {gid}",
                        f"{gdata.get('count', 0):,}",
                        f"{gdata.get('positive_rate', 0):.1%}",
                        f"{gdata.get('tpr', 0):.1%}",
                        f"{gdata.get('fpr', 0):.1%}",
                    ])
                g_table = Table(g_rows, colWidths=[1.2*inch, 1.0*inch, 1.2*inch, 1.0*inch, 1.0*inch])
                g_table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4f46e5")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#c7d2fe")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#eef2ff")]),
                ]))
                story.append(g_table)
                story.append(Spacer(1, 0.25 * inch))

    # ══════════════════════════════════════════════════════════════════════
    # PAGE 3 — SHAP & Remediation
    # ══════════════════════════════════════════════════════════════════════
    story.append(PageBreak())

    # SHAP Feature Importance
    shap_data = results.get("shap", {})
    top_features = shap_data.get("top_features", [])
    if top_features:
        story.append(Paragraph("Feature Importance (SHAP)", section_style))
        story.append(Paragraph(
            "Features driving model predictions. Protected attributes with high importance "
            "indicate the model may be directly using sensitive information.",
            body_style
        ))
        shap_path = _chart_shap_importance(top_features)
        add_chart(shap_path, height=max(2.0, len(top_features) * 0.5) * inch)

        # Protected attribute SHAP callout
        prot_shap = shap_data.get("protected_attr_shap", {})
        if prot_shap:
            story.append(Paragraph("⚠ Protected Attribute Direct Influence:", body_style))
            for attr, val in prot_shap.items():
                flag = " — HIGH RISK" if val > 0.1 else ""
                story.append(Paragraph(
                    f"  • <b>{attr}</b>: SHAP importance = {val:.3f}{flag}",
                    body_style
                ))
            story.append(Spacer(1, 0.15 * inch))

    # Remediation
    remediation = results.get("remediation", {})
    reweighing = remediation.get("reweighing", {})
    metrics_after = reweighing.get("metrics_after", {})

    if metrics_after and metrics:
        story.append(Paragraph("Remediation Analysis", section_style))
        story.append(Paragraph(
            f"Method: <b>{reweighing.get('method', 'reweighing').upper()}</b> | "
            f"Accuracy before: <b>{reweighing.get('accuracy_before', 0):.1%}</b> → "
            f"after: <b>{reweighing.get('accuracy_after', 0):.1%}</b> "
            f"(Δ {reweighing.get('accuracy_delta', 0):+.1%})",
            body_style
        ))
        rem_path = _chart_remediation(metrics, metrics_after)
        if rem_path:
            add_chart(rem_path, height=3.0 * inch)

        # Before/after table
        rem_header = ["Metric", "Before", "After", "Change"]
        rem_rows = [rem_header]
        for key, before in metrics.items():
            after = metrics_after.get(key, {})
            bv = before.get("value", 0)
            av = after.get("value", bv)
            delta = av - bv
            rem_rows.append([
                key.replace("_", " ").title(),
                f"{bv:.3f}",
                f"{av:.3f}",
                f"{delta:+.3f}",
            ])
        rem_table = Table(rem_rows, colWidths=[2.5*inch, 1.2*inch, 1.2*inch, 1.2*inch])
        rem_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d1d5db")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f9fafb")]),
        ]))
        story.append(rem_table)
        story.append(Spacer(1, 0.2 * inch))

    # ══════════════════════════════════════════════════════════════════════
    # PAGE 4 — Compliance & AI Analysis
    # ══════════════════════════════════════════════════════════════════════
    story.append(PageBreak())

    # Compliance mapping
    compliance_violations = map_to_regulations(metrics)
    if compliance_violations:
        story.append(Paragraph("Regulatory Compliance Mapping", section_style))

        comp_header = ["Metric", "Framework", "Article", "Severity"]
        comp_rows = [comp_header]
        for v in compliance_violations:
            comp_rows.append([
                v.get("metric", ""),
                v.get("framework", ""),
                v.get("article", ""),
                v.get("severity", "").upper(),
            ])
        comp_table = Table(comp_rows, colWidths=[1.8*inch, 2.2*inch, 1.5*inch, 1.0*inch])
        comp_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#7c3aed")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#c4b5fd")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f3ff")]),
        ]))
        story.append(comp_table)
        story.append(Spacer(1, 0.3 * inch))

    # AI Analysis
    if explanation:
        story.append(Paragraph("AI Analysis (Gemini)", section_style))
        plain = explanation.get("plain_english", "No AI analysis available.")
        story.append(Paragraph(plain, body_style))
        story.append(Spacer(1, 0.15 * inch))

        findings = explanation.get("findings", [])
        if findings:
            story.append(Paragraph("Key Findings:", body_style))
            for f in findings:
                headline = f.get("headline", "")
                detail = f.get("detail", "")
                sev = f.get("severity", "medium").upper()
                story.append(Paragraph(
                    f"<b>[{sev}] {headline}</b><br/>{detail}",
                    body_style
                ))
                story.append(Spacer(1, 0.08 * inch))

        rec_fix = explanation.get("recommended_fix", "none")
        rec_reason = explanation.get("recommended_fix_reason", "")
        if rec_fix and rec_fix != "none":
            story.append(Spacer(1, 0.1 * inch))
            story.append(Paragraph(
                f"<b>Recommended Action:</b> {rec_fix.replace('_', ' ').title()}<br/>"
                f"{rec_reason}",
                body_style
            ))

    # Fairness Score Breakdown
    breakdown = fs.get("breakdown", {}) if fs else {}
    if breakdown:
        story.append(Spacer(1, 0.2 * inch))
        story.append(Paragraph("Fairness Score Breakdown", section_style))
        bd_header = ["Component", "Contribution"]
        bd_rows = [bd_header]
        for comp, val in breakdown.items():
            bd_rows.append([comp.replace("_", " ").title(), f"{val:.1f}"])
        bd_table = Table(bd_rows, colWidths=[4.0*inch, 2.0*inch])
        bd_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d1d5db")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f9fafb")]),
        ]))
        story.append(bd_table)

    # Footer
    story.append(Spacer(1, 0.4 * inch))
    story.append(Paragraph(
        "This report was generated automatically by FairLens. "
        "It is intended to support — not replace — human review of AI fairness.",
        small_style
    ))

    # ── Build Document (watermark on every page) ──────────────────────────
    doc.build(story, onFirstPage=_draw_watermark, onLaterPages=_draw_watermark)
    pdf_bytes = buffer.getvalue()
    logger.info(f"Rich PDF generated successfully ({len(pdf_bytes):,} bytes)")

    # Cleanup temp chart images
    for f in chart_files:
        try:
            os.unlink(f)
        except Exception:
            pass

    return pdf_bytes


def _generate_minimal_pdf(results: dict, explanation: dict) -> bytes:
    """Absolute minimum PDF generator - just text output."""
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas

        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter

        y = height - 50
        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, y, "FairLens Audit Report")

        y -= 30
        c.setFont("Helvetica", 10)
        c.drawString(50, y, f"Job ID: {results.get('job_id', 'N/A')}")

        y -= 20
        severity = results.get("overall_severity", "unknown").upper()
        c.drawString(50, y, f"Severity: {severity}")

        y -= 30
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, y, "Metrics:")

        y -= 15
        c.setFont("Helvetica", 9)
        metrics = results.get("metrics", {})
        for metric_name, metric_data in metrics.items():
            status = "PASS" if metric_data.get("passed") else "FAIL"
            text = f"{metric_name}: {metric_data.get('value', 'N/A')} [{status}]"
            c.drawString(60, y, text)
            y -= 12

        c.save()
        pdf_bytes = buffer.getvalue()
        logger.info(f"Minimal PDF generated successfully ({len(pdf_bytes):,} bytes)")
        return pdf_bytes
    except Exception as e:
        logger.error(f"Even minimal PDF failed: {e}")
        raise
