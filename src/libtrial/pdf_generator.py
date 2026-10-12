"""PDF investigation report generator for LibTrial using ReportLab."""

import io
from datetime import datetime, timezone
from typing import List, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from libtrial.models import (
    CandidateEvaluation,
    CompatibilityVerdict,
    ProjectProfile,
    TrialOutcome,
    TrialResult,
)


def _clean_license(lic: Optional[str]) -> str:
    """Extracts a concise license name from potentially long legal boilerplate."""
    if not lic:
        return "Not stated"
    lic_upper = lic.upper()
    if "MIT" in lic_upper:
        return "MIT License"
    if "APACHE" in lic_upper:
        return "Apache 2.0"
    if "BSD" in lic_upper:
        return "BSD License"
    if "GPL" in lic_upper:
        return "GPL License"
    if "MPL" in lic_upper or "MOZILLA" in lic_upper:
        return "MPL 2.0"
    first = lic.split("\n")[0].strip()
    if len(first) > 30:
        return first[:27] + "..."
    return first or "Not stated"


def generate_pdf_report(
    profile: ProjectProfile,
    requirement: str,
    evaluations: List[CandidateEvaluation],
    selected_candidate_name: Optional[str] = None,
    trial_result: Optional[TrialResult] = None,
) -> bytes:
    """Generates an auditable, beautifully formatted PDF report."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()

    # Custom typography
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#0F172A"),
        spaceAfter=4,
    )
    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#64748B"),
        spaceAfter=12,
    )
    h2_style = ParagraphStyle(
        "Heading2_Custom",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#1E293B"),
        spaceBefore=10,
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "Body_Custom",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#334155"),
    )
    bold_label_style = ParagraphStyle(
        "BoldLabel",
        parent=body_style,
        fontName="Helvetica-Bold",
        textColor=colors.HexColor("#0F172A"),
    )
    code_style = ParagraphStyle(
        "CodeText",
        parent=body_style,
        fontName="Courier",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#1E293B"),
    )
    table_cell = ParagraphStyle(
        "TableCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#334155"),
    )
    table_cell_bold = ParagraphStyle(
        "TableCellBold",
        parent=table_cell,
        fontName="Helvetica-Bold",
        textColor=colors.HexColor("#0F172A"),
    )

    elements = []

    # Title Banner
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    elements.append(Paragraph("LibTrial — Evidence-Backed Investigation Report", title_style))
    elements.append(
        Paragraph(
            f"Automated Python Library Evaluation & Sandbox Trial Audit &nbsp;|&nbsp; <i>Generated: {now_str}</i>",
            subtitle_style,
        )
    )
    elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0284C7"), spaceAfter=10))

    # Section 1: Requirement & Project Summary
    elements.append(Paragraph("1. Target Requirement & Project Profile", h2_style))
    
    fw_str = ", ".join(profile.detected_frameworks) if profile.detected_frameworks else "None detected"
    proj_summary_data = [
        [Paragraph("Project Name", bold_label_style), Paragraph(profile.project_name, table_cell),
         Paragraph("Target Python", bold_label_style), Paragraph(profile.python_version, code_style)],
        [Paragraph("Total Python Files", bold_label_style), Paragraph(str(profile.total_python_files), table_cell),
         Paragraph("Frameworks", bold_label_style), Paragraph(fw_str, table_cell)],
        [Paragraph("Requirement", bold_label_style), Paragraph(requirement or "(None provided)", table_cell),
         Paragraph("Dependencies", bold_label_style), Paragraph(f"{len(profile.declared_dependencies)} declared", table_cell)],
    ]
    t_proj = Table(proj_summary_data, colWidths=[1.3 * inch, 2.2 * inch, 1.2 * inch, 2.8 * inch])
    t_proj.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(t_proj)
    elements.append(Spacer(1, 10))

    # Section 2: Candidate Evaluation & Verified Registry Facts
    elements.append(Paragraph("2. Candidate Packages & PyPI Registry Verification", h2_style))
    
    cand_header = [
        Paragraph("Package", table_cell_bold),
        Paragraph("PyPI Status", table_cell_bold),
        Paragraph("Version", table_cell_bold),
        Paragraph("Requires-Python", table_cell_bold),
        Paragraph("License", table_cell_bold),
        Paragraph("Dependencies", table_cell_bold),
        Paragraph("Compatibility Verdict", table_cell_bold),
    ]
    cand_table_data = [cand_header]

    for ev in evaluations:
        sug = ev.suggestion
        meta = ev.pypi_metadata
        compat = ev.compatibility

        if meta and meta.is_found:
            status_txt = "<font color='#16A34A'><b>Verified</b></font>"
            ver_txt = f"v{meta.version}"
            req_py = meta.requires_python or "Not stated"
            lic_txt = _clean_license(meta.license)
            deps_cnt = f"{len(meta.requires_dist)} pkgs"
        else:
            status_txt = "<font color='#DC2626'><b>Not Found</b></font>"
            ver_txt = "N/A"
            req_py = "N/A"
            lic_txt = "N/A"
            deps_cnt = "N/A"

        # Verdict text
        if compat.verdict == CompatibilityVerdict.COMPATIBLE_WITH_AVAILABLE_EVIDENCE:
            verdict_html = f"<font color='#16A34A'><b>{compat.verdict.value}</b></font>"
        elif compat.verdict == CompatibilityVerdict.POTENTIAL_CONFLICT:
            verdict_html = f"<font color='#D97706'><b>{compat.verdict.value}</b></font>"
        else:
            verdict_html = f"<font color='#2563EB'><b>{compat.verdict.value}</b></font>"

        cand_table_data.append([
            Paragraph(sug.name, code_style),
            Paragraph(status_txt, table_cell),
            Paragraph(ver_txt, code_style),
            Paragraph(req_py, code_style),
            Paragraph(lic_txt, table_cell),
            Paragraph(deps_cnt, table_cell),
            Paragraph(verdict_html, table_cell),
        ])

    t_cands = Table(cand_table_data, colWidths=[1.1 * inch, 0.9 * inch, 0.7 * inch, 1.2 * inch, 1.0 * inch, 0.8 * inch, 1.8 * inch])
    t_cands.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F1F5F9")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    elements.append(t_cands)
    elements.append(Spacer(1, 10))

    # Section 3: Model Hypotheses (Segregated)
    elements.append(Paragraph("3. Gemma 4 Candidate Hypotheses (AI Suggestions — Unverified Facts)", h2_style))
    hypo_rows = [
        [Paragraph("Candidate", table_cell_bold),
         Paragraph("Expected Import", table_cell_bold),
         Paragraph("Proposed Capability", table_cell_bold),
         Paragraph("Fit Rationale", table_cell_bold)]
    ]
    for ev in evaluations:
        sug = ev.suggestion
        hypo_rows.append([
            Paragraph(sug.name, code_style),
            Paragraph(sug.import_name or "unknown", code_style),
            Paragraph(sug.capability or "N/A", table_cell),
            Paragraph(sug.fit_rationale or "N/A", table_cell),
        ])
    t_hypo = Table(hypo_rows, colWidths=[1.1 * inch, 1.1 * inch, 2.5 * inch, 2.8 * inch])
    t_hypo.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F8FAFC")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(t_hypo)
    elements.append(Spacer(1, 10))

    # Section 4: Isolated Container Trial
    elements.append(Paragraph("4. Isolated Container Integration Trial", h2_style))
    if trial_result and selected_candidate_name:
        if trial_result.outcome == TrialOutcome.PASS:
            res_badge = "<font color='#16A34A'><b>PASS</b></font>"
        elif trial_result.outcome == TrialOutcome.FAIL:
            res_badge = "<font color='#DC2626'><b>FAIL</b></font>"
        elif trial_result.outcome == TrialOutcome.NOT_RUN:
            res_badge = "<font color='#D97706'><b>NOT RUN</b></font>"
        else:
            res_badge = "<font color='#D97706'><b>INCONCLUSIVE</b></font>"

        exit_code_str = str(trial_result.exit_code) if trial_result.exit_code is not None else "N/A"
        time_str = f"{trial_result.execution_time_seconds:.2f}s" if trial_result.execution_time_seconds else "N/A"
        sandbox_str = "Ephemeral Docker Container (--network none)" if trial_result.docker_available else "Skipped (Host environment protected)"

        trial_data = [
            [Paragraph("Trial Candidate", bold_label_style), Paragraph(selected_candidate_name, code_style),
             Paragraph("Outcome", bold_label_style), Paragraph(res_badge, table_cell)],
            [Paragraph("Exit Code", bold_label_style), Paragraph(exit_code_str, code_style),
             Paragraph("Runtime", bold_label_style), Paragraph(time_str, table_cell)],
            [Paragraph("Isolation Boundary", bold_label_style), Paragraph(sandbox_str, table_cell),
             Paragraph("Host Execution", bold_label_style), Paragraph("<font color='#16A34A'><b>Zero Host Code Run</b></font>", table_cell)],
        ]
        t_trial = Table(trial_data, colWidths=[1.3 * inch, 2.2 * inch, 1.2 * inch, 2.8 * inch])
        t_trial.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        elements.append(t_trial)

        if trial_result.reasons:
            reasons_txt = "<b>Findings:</b> " + "; ".join(trial_result.reasons)
            elements.append(Spacer(1, 4))
            elements.append(Paragraph(reasons_txt, body_style))
    else:
        elements.append(Paragraph("<i>No candidate trial was executed.</i>", body_style))

    elements.append(Spacer(1, 10))

    # Section 5: Boundaries & Disclaimers
    elements.append(Paragraph("5. Safety Boundaries & Audit Limitations", h2_style))
    disc_text = (
        "• <b>Hypothesis Separation:</b> Model suggestions represent initial unverified hypotheses; "
        "only registry data from PyPI and container execution status represent empirical facts.<br/>"
        "• <b>Dependency Completeness:</b> PyPI metadata only reflects declared direct dependencies; "
        "transitive sub-dependencies are not fully SAT-solved.<br/>"
        "• <b>Host Safety:</b> All trial probes are executed within disposable, network-isolated "
        "Docker containers or aborted if Docker is absent. No candidate code was executed on the host system."
    )
    elements.append(Paragraph(disc_text, body_style))
    elements.append(Spacer(1, 12))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#94A3B8"), spaceAfter=6))
    elements.append(Paragraph("LibTrial &copy; 2026 &middot; Evidence-Backed Package Evaluation &middot; MIT License", subtitle_style))

    doc.build(elements)
    buf.seek(0)
    return buf.getvalue()
