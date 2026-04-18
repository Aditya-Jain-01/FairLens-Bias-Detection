"""
FairLens â€” PDF Report Generator

Renders the Jinja2 HTML template and converts it to PDF using WeasyPrint.
All CSS must be inline â€” WeasyPrint does not support external stylesheets.
"""

import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Path to the templates directory (relative to this file: services/ â†’ templates/)
_TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


def _build_shap_svg(top_features: list) -> str:
    """
    Build an inline SVG horizontal bar chart for SHAP feature importance.
    WeasyPrint renders inline SVG â€” no external image files.
    """
    if not top_features:
        return ""

    chart_width = 500
    bar_height = 28
    gap = 10
    label_width = 160
    bar_max_width = chart_width - label_width - 60  # room for value label
    total_height = len(top_features) * (bar_height + gap) + 40

    # Colour mapping
    color_map = {"positive": "#22c55e", "negative": "#ef4444", "mixed": "#f59e0b"}
    default_color = "#6366f1"

    max_importance = max(f["importance"] for f in top_features) or 1.0

    bars = []
    for i, feat in enumerate(top_features):
        y = 30 + i * (bar_height + gap)
        bar_w = (feat["importance"] / max_importance) * bar_max_width
        color = color_map.get(feat.get("direction", ""), default_color)
        pct = f"{feat['importance']:.1%}"

        bars.append(
            f'<text x="{label_width - 8}" y="{y + bar_height // 2 + 5}" '
            f'text-anchor="end" font-family="Georgia, serif" font-size="11" fill="#374151">'
            f'{feat["feature"]}</text>'
        )
        bars.append(
            f'<rect x="{label_width}" y="{y}" width="{bar_w:.1f}" height="{bar_height}" '
            f'rx="4" fill="{color}" opacity="0.85"/>'
        )
        bars.append(
            f'<text x="{label_width + bar_w + 6}" y="{y + bar_height // 2 + 5}" '
            f'font-family="Georgia, serif" font-size="11" fill="#6b7280">{pct}</text>'
        )

    bars_str = "\n    ".join(bars)

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{chart_width}" height="{total_height}" viewBox="0 0 {chart_width} {total_height}">
  <text x="0" y="18" font-family="Georgia, serif" font-size="13" font-weight="bold" fill="#111827">Top Feature Importances (SHAP)</text>
  {bars_str}
</svg>"""


def _build_remediation_rows(remediation: dict) -> list:
    """
    Build a list of dicts for the before/after metrics table.
    """
    reweighing = remediation.get("reweighing", {})
    metrics_after = reweighing.get("metrics_after", {})
    return metrics_after


def generate_pdf_report(results: dict, explanation: dict) -> bytes:
    """
    Render the Jinja2 HTML template and convert to PDF bytes.

    Args:
        results:     Parsed results.json dict.
        explanation: Parsed explanation.json dict (Gemini output).

    Returns:
        PDF content as bytes.
    """
    from jinja2 import Environment, FileSystemLoader, select_autoescape

    # Build SHAP SVG
    shap_svg = _build_shap_svg(
        results.get("shap", {}).get("top_features", [])
    )

    # Severity badge colour
    severity_colors = {
        "high": "#dc2626",
        "medium": "#d97706",
        "low": "#16a34a",
        "none": "#6b7280",
        "critical": "#7c3aed",
    }
    severity = results.get("overall_severity", "high").lower()
    severity_color = severity_colors.get(severity, "#dc2626")

    # Metric pass/fail badge colours
    def metric_badge(passed: bool) -> dict:
        return {
            "label": "PASS" if passed else "FAIL",
            "color": "#16a34a" if passed else "#dc2626",
            "bg": "#dcfce7" if passed else "#fee2e2",
        }

    # Enrich metrics with badge info
    metrics_enriched = {}
    for name, m in results.get("metrics", {}).items():
        metrics_enriched[name] = {**m, "badge": metric_badge(m.get("passed", False))}

    # Remediation before/after table
    reweighing = results.get("remediation", {}).get("reweighing", {})
    metrics_after = reweighing.get("metrics_after", {})
    remediation_rows = []
    for name, before in results.get("metrics", {}).items():
        after = metrics_after.get(name, {})
        remediation_rows.append({
            "name": name.replace("_", " ").title(),
            "before_value": before.get("value", "â€”"),
            "before_passed": before.get("passed", False),
            "after_value": after.get("value", "â€”"),
            "after_passed": after.get("passed", False),
            "threshold": before.get("threshold", "â€”"),
        })

    # Jinja2 environment
    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATES_DIR)),
        autoescape=select_autoescape(["html"]),
    )
    template = env.get_template("report.html")

    html_string = template.render(
        results=results,
        explanation=explanation,
        shap_svg=shap_svg,
        severity_color=severity_color,
        metrics_enriched=metrics_enriched,
        remediation_rows=remediation_rows,
        accuracy_before=reweighing.get("accuracy_before", 0),
        accuracy_after=reweighing.get("accuracy_after", 0),
        accuracy_delta=reweighing.get("accuracy_delta", 0),
    )

    logger.info("Rendering PDF from HTML templateâ€¦")
    try:
        from weasyprint import HTML as WeasyHTML
        pdf_bytes = WeasyHTML(string=html_string, base_url=str(_TEMPLATES_DIR)).write_pdf()
        logger.info(f"PDF rendered successfully ({len(pdf_bytes):,} bytes)")
        return pdf_bytes
    except Exception as e:
        logger.warning(f"WeasyPrint failed: {e}. Generating fallback PDF with reportlab...")
        # Fallback: use reportlab to create a simple text-based PDF
        try:
            return _generate_reportlab_fallback(results, explanation)
        except Exception as fallback_err:
            logger.error(f"Fallback PDF generation also failed: {fallback_err}")
            # Last resort: return a simple text PDF using reportlab
            return _generate_minimal_pdf(results, explanation)


def _generate_reportlab_fallback(results: dict, explanation: dict) -> bytes:
    """Fallback PDF generator using reportlab (simpler than WeasyPrint, no GTK deps)."""
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
        from reportlab.lib import colors
        from io import BytesIO

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
        story = []
        styles = getSampleStyleSheet()
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1f2937'),
            spaceAfter=0.3*inch,
            fontName='Helvetica-Bold'
        )
        story.append(Paragraph("FairLens Audit Report", title_style))
        
        # Job ID
        story.append(Paragraph(f"<b>Job ID:</b> {results.get('job_id', 'N/A')}", styles['Normal']))
        story.append(Spacer(1, 0.2*inch))
        
        # Overall Severity
        severity = results.get('overall_severity', 'unknown').upper()
        story.append(Paragraph(f"<b>Overall Severity:</b> {severity}", styles['Normal']))
        story.append(Spacer(1, 0.3*inch))
        
        # Metrics Summary
        story.append(Paragraph("Fairness Metrics:", styles['Heading2']))
        metrics = results.get('metrics', {})
        for metric_name, metric_data in metrics.items():
            status = "âœ“ PASS" if metric_data.get('passed') else "âœ— FAIL"
            story.append(Paragraph(
                f"â€¢ <b>{metric_name.replace('_', ' ').title()}:</b> {metric_data.get('value', 'N/A')} [{status}]",
                styles['Normal']
            ))
        
        story.append(Spacer(1, 0.2*inch))
        
        # Explanation
        if explanation:
            story.append(Paragraph("AI Analysis:", styles['Heading2']))
            story.append(Paragraph(explanation.get('plain_english', 'No analysis available'), styles['Normal']))
        
        doc.build(story)
        pdf_bytes = buffer.getvalue()
        logger.info(f"Reportlab PDF generated successfully ({len(pdf_bytes):,} bytes)")
        return pdf_bytes
    except ImportError:
        raise

def _generate_minimal_pdf(results: dict, explanation: dict) -> bytes:
    """Absolute minimum PDF generator - just text output."""
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        from io import BytesIO
        
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter
        
        y = height - 50
        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, y, "FairLens Audit Report")
        
        y -= 30
        c.setFont("Helvetica", 10)
        c.drawString(50, y, f"Job ID: {results.get('job_id', 'N/A')}")
        
        y -= 20
        severity = results.get('overall_severity', 'unknown').upper()
        c.drawString(50, y, f"Severity: {severity}")
        
        y -= 30
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, y, "Metrics:")
        
        y -= 15
        c.setFont("Helvetica", 9)
        metrics = results.get('metrics', {})
        for metric_name, metric_data in metrics.items():
            status = "PASS" if metric_data.get('passed') else "FAIL"
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
