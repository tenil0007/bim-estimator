"""
PDF Report Generator
---------------------
Generates professional construction estimation reports using ReportLab.
Reports include cost summaries, time estimates, Gantt charts, and SHAP insights.
Formatted for L&T management presentation standards.
"""

import io
import os
from datetime import datetime
from pathlib import Path
from typing import Optional
from app.utils import get_logger
from app.config import get_settings

logger = get_logger("report_generator")

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch, mm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        PageBreak, Image, HRFlowable
    )
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False
    logger.warning("ReportLab not installed. PDF generation unavailable.")


# L&T Brand Colors
LT_BLUE = colors.HexColor("#003366")
LT_LIGHT_BLUE = colors.HexColor("#0066CC")
LT_GRAY = colors.HexColor("#F5F5F5")
LT_DARK = colors.HexColor("#1A1A2E")
ACCENT_GREEN = colors.HexColor("#28A745")
ACCENT_RED = colors.HexColor("#DC3545")
ACCENT_ORANGE = colors.HexColor("#FD7E14")


class ReportGenerator:
    """Generates professional PDF reports for BIM cost/time estimation."""

    def __init__(self):
        if not HAS_REPORTLAB:
            raise ImportError("ReportLab is required for PDF generation")

        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def generate_report(
        self,
        project_data: dict,
        cost_data: dict = None,
        time_data: dict = None,
        schedule_data: dict = None,
        shap_data: dict = None,
        config: dict = None,
    ) -> str:
        """
        Generate a complete PDF report.

        Args:
            project_data: Project metadata
            cost_data: Cost prediction results
            time_data: Time prediction results
            schedule_data: Schedule/Gantt data
            shap_data: SHAP explanation data
            config: Report configuration

        Returns:
            Path to the generated PDF file
        """
        config = config or {}
        report_title = config.get("report_title", "BIM Cost & Time Estimation Report")
        company_name = config.get("company_name", "Larsen & Toubro Limited")

        # Output path
        settings = get_settings()
        output_dir = settings.reports_path
        output_dir.mkdir(parents=True, exist_ok=True)

        project_id = project_data.get("project_id", "unknown")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = str(output_dir / f"report_{project_id}_{timestamp}.pdf")

        # Build PDF
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=20 * mm,
            leftMargin=20 * mm,
            topMargin=25 * mm,
            bottomMargin=20 * mm,
        )

        elements = []

        # ─── Cover Page ───
        elements.extend(self._build_cover_page(report_title, company_name, project_data))
        elements.append(PageBreak())

        # ─── Executive Summary ───
        elements.extend(self._build_executive_summary(project_data, cost_data, time_data, schedule_data))
        elements.append(PageBreak())

        # ─── Cost Analysis Section ───
        if cost_data and config.get("include_cost", True):
            elements.extend(self._build_cost_section(cost_data))
            elements.append(PageBreak())

        # ─── Time Analysis Section ───
        if time_data and config.get("include_time", True):
            elements.extend(self._build_time_section(time_data))
            elements.append(PageBreak())

        # ─── Schedule Section ───
        if schedule_data and config.get("include_schedule", True):
            elements.extend(self._build_schedule_section(schedule_data))
            elements.append(PageBreak())

        # ─── SHAP Insights Section ───
        if shap_data and config.get("include_shap", True):
            elements.extend(self._build_shap_section(shap_data))

        # ─── Footer / Disclaimer ───
        elements.extend(self._build_footer())

        # Build PDF
        doc.build(elements)
        logger.info(f"PDF report generated | path={output_path}")

        return output_path

    def _setup_custom_styles(self):
        """Configure custom paragraph styles for the report."""
        self.styles.add(ParagraphStyle(
            name="CoverTitle",
            parent=self.styles["Title"],
            fontSize=28,
            textColor=LT_BLUE,
            spaceAfter=20,
            alignment=TA_CENTER,
        ))
        self.styles.add(ParagraphStyle(
            name="CoverSubtitle",
            parent=self.styles["Normal"],
            fontSize=14,
            textColor=LT_LIGHT_BLUE,
            spaceAfter=10,
            alignment=TA_CENTER,
        ))
        self.styles.add(ParagraphStyle(
            name="SectionTitle",
            parent=self.styles["Heading1"],
            fontSize=18,
            textColor=LT_BLUE,
            spaceBefore=15,
            spaceAfter=10,
            borderWidth=1,
            borderColor=LT_BLUE,
            borderPadding=5,
        ))
        self.styles.add(ParagraphStyle(
            name="SubSection",
            parent=self.styles["Heading2"],
            fontSize=14,
            textColor=LT_DARK,
            spaceBefore=10,
            spaceAfter=8,
        ))
        self.styles.add(ParagraphStyle(
            name="MetricValue",
            parent=self.styles["Normal"],
            fontSize=24,
            textColor=LT_BLUE,
            alignment=TA_CENTER,
            spaceAfter=5,
        ))
        self.styles.add(ParagraphStyle(
            name="MetricLabel",
            parent=self.styles["Normal"],
            fontSize=10,
            textColor=colors.gray,
            alignment=TA_CENTER,
        ))

    def _build_cover_page(self, title: str, company: str, project: dict) -> list:
        """Build the report cover page."""
        elements = []
        elements.append(Spacer(1, 2 * inch))
        elements.append(Paragraph(company.upper(), self.styles["CoverSubtitle"]))
        elements.append(Spacer(1, 0.3 * inch))
        elements.append(HRFlowable(width="80%", thickness=2, color=LT_BLUE))
        elements.append(Spacer(1, 0.3 * inch))
        elements.append(Paragraph(title, self.styles["CoverTitle"]))
        elements.append(Spacer(1, 0.2 * inch))
        elements.append(Paragraph(
            f"Project: {project.get('name', 'BIM Project')}",
            self.styles["CoverSubtitle"]
        ))
        elements.append(Paragraph(
            f"Date: {datetime.now().strftime('%B %d, %Y')}",
            self.styles["CoverSubtitle"]
        ))
        elements.append(Spacer(1, 1 * inch))
        elements.append(Paragraph(
            "AI-Driven BIM Cost & Time Estimation<br/>with Explainable Machine Learning",
            self.styles["CoverSubtitle"]
        ))
        elements.append(Spacer(1, 2 * inch))
        elements.append(Paragraph(
            "<i>CONFIDENTIAL — For Internal Use Only</i>",
            ParagraphStyle("Conf", parent=self.styles["Normal"],
                           fontSize=9, textColor=colors.gray, alignment=TA_CENTER)
        ))
        return elements

    def _build_executive_summary(self, project, cost_data, time_data, schedule_data) -> list:
        """Build executive summary section with key metrics."""
        elements = []
        elements.append(Paragraph("Executive Summary", self.styles["SectionTitle"]))
        elements.append(Spacer(1, 0.2 * inch))

        # Project Info
        proj_info = [
            ["Parameter", "Value"],
            ["Project Name", project.get("name", "N/A")],
            ["IFC File", project.get("ifc_filename", "N/A")],
            ["Total Elements", str(project.get("total_elements", "N/A"))],
            ["Report Generated", datetime.now().strftime("%Y-%m-%d %H:%M")],
        ]

        elements.append(self._create_table(proj_info, "Project Information"))
        elements.append(Spacer(1, 0.3 * inch))

        # Key Metrics Summary
        metrics = [["Metric", "Value", "Unit"]]

        if cost_data:
            total_cost = cost_data.get("total_cost", 0)
            metrics.append(["Total Estimated Cost", f"₹{total_cost:,.2f}", "INR"])
            metrics.append(["Cost Model R²", str(cost_data.get("metrics", {}).get("test_r2", "N/A")), ""])

        if time_data:
            total_hours = time_data.get("total_duration_hours", 0)
            total_days = time_data.get("total_duration_days", 0)
            metrics.append(["Total Labor Hours", f"{total_hours:,.1f}", "hours"])
            metrics.append(["Total Duration", f"{total_days:,.1f}", "days"])

        if schedule_data:
            proj_duration = schedule_data.get("total_duration_days", 0)
            critical = len(schedule_data.get("critical_path", []))
            metrics.append(["Project Schedule", f"{proj_duration:.0f}", "days"])
            metrics.append(["Critical Activities", str(critical), "count"])

        elements.append(self._create_table(metrics, "Key Metrics"))

        return elements

    def _build_cost_section(self, cost_data: dict) -> list:
        """Build cost analysis section."""
        elements = []
        elements.append(Paragraph("Cost Analysis", self.styles["SectionTitle"]))

        # Total cost
        total = cost_data.get("total_cost", 0)
        elements.append(Paragraph(f"Total Estimated Cost: ₹{total:,.2f}", self.styles["SubSection"]))
        elements.append(Spacer(1, 0.2 * inch))

        # Cost by element type
        breakdown = cost_data.get("cost_breakdown", {})
        if breakdown:
            table_data = [["Element Type", "Cost (₹)", "Percentage"]]
            for elem, cost in sorted(breakdown.items(), key=lambda x: x[1], reverse=True):
                pct = (cost / total * 100) if total > 0 else 0
                table_data.append([elem.replace("Ifc", ""), f"₹{cost:,.2f}", f"{pct:.1f}%"])
            elements.append(self._create_table(table_data, "Cost Breakdown by Element Type"))
            elements.append(Spacer(1, 0.2 * inch))

        # Cost by material
        mat_breakdown = cost_data.get("material_breakdown", {})
        if mat_breakdown:
            table_data = [["Material", "Cost (₹)", "Percentage"]]
            for mat, cost in sorted(mat_breakdown.items(), key=lambda x: x[1], reverse=True)[:10]:
                pct = (cost / total * 100) if total > 0 else 0
                table_data.append([mat, f"₹{cost:,.2f}", f"{pct:.1f}%"])
            elements.append(self._create_table(table_data, "Cost Breakdown by Material"))

        # Model metrics
        metrics = cost_data.get("metrics", {})
        if metrics:
            elements.append(Spacer(1, 0.2 * inch))
            elements.append(Paragraph("Model Performance", self.styles["SubSection"]))
            metrics_table = [["Metric", "Value"]]
            for key, val in metrics.items():
                metrics_table.append([key.replace("_", " ").title(), str(val)])
            elements.append(self._create_table(metrics_table, ""))

        return elements

    def _build_time_section(self, time_data: dict) -> list:
        """Build time analysis section."""
        elements = []
        elements.append(Paragraph("Time & Duration Analysis", self.styles["SectionTitle"]))

        total_hours = time_data.get("total_duration_hours", 0)
        total_days = time_data.get("total_duration_days", 0)

        elements.append(Paragraph(
            f"Total Labor Hours: {total_hours:,.1f} hours ({total_days:,.1f} working days)",
            self.styles["SubSection"]
        ))
        elements.append(Spacer(1, 0.2 * inch))

        # Duration by element type
        breakdown = time_data.get("duration_breakdown", {})
        if breakdown:
            table_data = [["Element Type", "Hours", "Days", "Percentage"]]
            for elem, hours in sorted(breakdown.items(), key=lambda x: x[1], reverse=True):
                pct = (hours / total_hours * 100) if total_hours > 0 else 0
                table_data.append([
                    elem.replace("Ifc", ""),
                    f"{hours:,.1f}",
                    f"{hours / 8:,.1f}",
                    f"{pct:.1f}%"
                ])
            elements.append(self._create_table(table_data, "Duration Breakdown by Element Type"))

        return elements

    def _build_schedule_section(self, schedule_data: dict) -> list:
        """Build schedule/Gantt section."""
        elements = []
        elements.append(Paragraph("Project Schedule (CPM Analysis)", self.styles["SectionTitle"]))

        total_days = schedule_data.get("total_duration_days", 0)
        elements.append(Paragraph(
            f"Total Project Duration: {total_days:.0f} days",
            self.styles["SubSection"]
        ))

        # Critical path
        critical_path = schedule_data.get("critical_path", [])
        if critical_path:
            elements.append(Spacer(1, 0.1 * inch))
            elements.append(Paragraph("Critical Path:", self.styles["SubSection"]))
            cp_text = " → ".join(critical_path)
            elements.append(Paragraph(cp_text, self.styles["Normal"]))

        # Schedule table
        gantt = schedule_data.get("gantt_data", [])
        if gantt:
            elements.append(Spacer(1, 0.2 * inch))
            table_data = [["Activity", "Duration", "Start", "End", "Slack", "Critical"]]
            for item in gantt[:30]:  # Limit rows
                table_data.append([
                    item.get("name", "")[:35],
                    f"{item.get('duration', 0):.1f}d",
                    f"Day {item.get('start_day', 0):.0f}",
                    f"Day {item.get('end_day', 0):.0f}",
                    f"{item.get('total_float', 0):.1f}d",
                    "YES" if item.get("is_critical") else "",
                ])
            elements.append(self._create_table(table_data, "Project Schedule"))

        # Summary
        summary = schedule_data.get("summary", {})
        if summary:
            elements.append(Spacer(1, 0.2 * inch))
            sum_table = [["Metric", "Value"]]
            sum_table.append(["Total Activities", str(summary.get("total_activities", 0))])
            sum_table.append(["Critical Activities", str(summary.get("critical_activities", 0))])
            sum_table.append(["Avg Float", f"{summary.get('avg_float_days', 0):.1f} days"])
            sum_table.append(["Total Labor Hours", f"{summary.get('total_labor_hours', 0):,.0f}"])
            elements.append(self._create_table(sum_table, "Schedule Summary"))

        return elements

    def _build_shap_section(self, shap_data: dict) -> list:
        """Build SHAP explainability section."""
        elements = []
        elements.append(Paragraph("AI Explainability (SHAP Analysis)", self.styles["SectionTitle"]))

        elements.append(Paragraph(
            "SHAP (SHapley Additive exPlanations) values indicate how each feature "
            "contributes to the model's predictions. Higher absolute SHAP values indicate "
            "stronger influence on the prediction.",
            self.styles["Normal"]
        ))
        elements.append(Spacer(1, 0.2 * inch))

        # Feature importance table
        importance = shap_data.get("feature_importance", {})
        if importance:
            table_data = [["Feature", "Importance (Mean |SHAP|)", "Direction"]]
            direction = shap_data.get("feature_direction", {})

            for feature, value in list(importance.items())[:15]:
                dir_text = direction.get(feature, "N/A")
                table_data.append([
                    feature.replace("_", " ").title(),
                    f"{value:.4f}",
                    dir_text.title(),
                ])
            elements.append(self._create_table(table_data, "Feature Importance Rankings"))

        # Insert SHAP plot image if available
        plot_path = shap_data.get("summary_plot_path")
        if plot_path and os.path.exists(plot_path):
            elements.append(Spacer(1, 0.2 * inch))
            elements.append(Paragraph("SHAP Summary Plot", self.styles["SubSection"]))
            img = Image(plot_path, width=6 * inch, height=4 * inch)
            elements.append(img)

        return elements

    def _build_footer(self) -> list:
        """Build report footer with disclaimer."""
        elements = []
        elements.append(Spacer(1, 0.5 * inch))
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.gray))
        elements.append(Spacer(1, 0.1 * inch))
        elements.append(Paragraph(
            "<i>This report was generated by the AI-Driven BIM Cost & Time Estimator. "
            "Predictions are based on machine learning models trained on historical data "
            "and should be validated by project engineers before use in contractual documents.</i>",
            ParagraphStyle("Footer", parent=self.styles["Normal"],
                           fontSize=8, textColor=colors.gray)
        ))
        return elements

    def _create_table(self, data: list[list], title: str = "") -> Table:
        """Create a styled table with L&T branding."""
        elements = []

        if title:
            elements.append(Paragraph(title, self.styles["SubSection"]))

        table = Table(data, repeatRows=1)

        style = TableStyle([
            # Header
            ("BACKGROUND", (0, 0), (-1, 0), LT_BLUE),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 10),
            ("ALIGN", (0, 0), (-1, 0), "CENTER"),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
            ("TOPPADDING", (0, 0), (-1, 0), 8),

            # Body
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 1), (-1, -1), 9),
            ("ALIGN", (1, 1), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BOTTOMPADDING", (0, 1), (-1, -1), 5),
            ("TOPPADDING", (0, 1), (-1, -1), 5),

            # Grid
            ("GRID", (0, 0), (-1, -1), 0.5, colors.gray),

            # Alternating row colors
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LT_GRAY]),
        ])

        table.setStyle(style)
        return table
