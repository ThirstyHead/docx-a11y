"""Markdown report generator: audit result JSON -> canonical accessibility report (source of truth)."""
from typing import Any, Dict, List, Optional
from .meta import PRINCIPLES, POUR_INTROS, SC_META, W3C_QUICKREF
from .stats import compute_progress_stats
from .tone import RULE_BARRIER_EXPLANATIONS, WHO_MAP, WORD_ASSISTANT_NOTES, assert_social_model_language
from .. import __version__


def render_md(
    result: Dict[str, Any],
    after_result: Optional[Dict[str, Any]] = None,
    source_path: Optional[str] = None,
) -> str:
    src = source_path or result.get("file", "document.docx")
    summary = result.get("summary", {})
    findings = result.get("findings", [])
    after_summary = after_result.get("summary") if after_result else None
    stats = compute_progress_stats(summary, after_summary)

    lines: List[str] = []
    lines.append(f"# Accessibility Audit Report: {src}")
    lines.append("")
    lines.append(f"- **Document Evaluated:** `{src}`")
    lines.append(f"- **Original File SHA-256:** `{result.get('sha256', 'n/a')}`")
    lines.append("- **Integrity Verification:** Immutable (original document is strictly read-only and never modified in place)")
    lines.append(f"- **Audit Standard:** [WCAG 2.1 Levels A & AA]({W3C_QUICKREF})")
    lines.append(f"- **Evaluated At:** {result.get('audited_at', 'n/a')}")
    lines.append(f"- **Audit Tool:** `{result.get('tool', f'docx-a11y/{__version__}')}`")
    lines.append(f"- **Compliance Status:** **{stats['compliance_verdict']}**")
    lines.append("")

    # Summary Progress Banner
    lines.append("## Executive Summary")
    lines.append("")
    if stats["mode"] == "remediated":
        lines.append(
            f"> **Remediation Progress:** Resolved **{stats['resolved_blocking']}** of "
            f"**{stats['before_blocking']}** blocking accessibility barriers "
            f"(**{stats['improvement_rate_pct']}% improvement**). "
            f"Remaining barriers: **{stats['after_blocking']}**."
        )
        lines.append(">")
        lines.append(
            f"> **Integrity Guarantee:** The original source document was verified untouched and preserved byte-for-byte (SHA-256: `{result.get('sha256')}`)."
        )
    else:
        status_word = "clean and passes" if summary.get("pass") else "contains accessibility barriers that need attention"
        lines.append(
            f"> **Assessment:** This document {status_word}. "
            f"A total of **{summary.get('total', 0)}** items were cataloged "
            f"(**{summary.get('blocking', 0)}** blocking WCAG 2.1 AA conformance)."
        )
    lines.append("")

    # Group findings by Principle (POUR)
    findings_by_principle: Dict[str, List[Dict[str, Any]]] = {"1": [], "2": [], "3": [], "4": []}
    for f in findings:
        sc = f.get("sc", "1.1.1")
        principle_key = sc.split(".")[0]
        if principle_key in findings_by_principle:
            findings_by_principle[principle_key].append(f)

    # Render each POUR section
    for p_key, p_name in PRINCIPLES:
        p_findings = findings_by_principle[p_key]
        lines.append(f"## {p_key}. {p_name}")
        lines.append("")
        lines.append(POUR_INTROS[p_key])
        lines.append("")

        if not p_findings:
            lines.append(f"_No accessibility barriers detected under Principle {p_name}._")
            lines.append("")
            continue

        for idx, f in enumerate(p_findings, start=1):
            sc = f["sc"]
            sc_info = SC_META.get(sc, ("Accessibility Requirement", "A", f"{p_key} {p_name}", W3C_QUICKREF))
            sc_title, sc_level, _, sc_url = sc_info
            rule_id = f.get("rule_id", "custom-rule")
            sev = f.get("severity", "moderate").upper()

            lines.append(f"### {idx}. [{sev}] {f['description']}")
            lines.append("")
            lines.append(f"- **Success Criterion:** [WCAG 2.1 SC {sc}: {sc_title} (Level {sc_level})]({sc_url})")
            lines.append(f"- **Location:** `{f.get('location', 'Unknown')}`")
            lines.append(f"- **Barrier Detected:** {RULE_BARRIER_EXPLANATIONS.get(rule_id, f.get('description'))}")
            lines.append(f"- **Recommended Remediation:** {f.get('fix', 'Inspect and resolve.')}")
            lines.append(f"- **Who Benefits:** {WHO_MAP.get(sc, 'All readers gain improved access.')}")
            lines.append(f"- **Technical Evidence:** `{f.get('evidence', '')}`")

            note = WORD_ASSISTANT_NOTES.get(rule_id)
            if note:
                lines.append(f"- **Word Accessibility Assistant Note:** {note}")

            why_unfixable = f.get("why_unfixable")
            if why_unfixable:
                lines.append(f"- **Why Software Cannot Automatically Fix This:** {why_unfixable}")

            manual_steps = f.get("manual_steps")
            if manual_steps:
                lines.append("- **Human in the Loop Remediation Protocol:**")
                for s_num, step in enumerate(manual_steps, start=1):
                    lines.append(f"  {s_num}. {step}")
            lines.append("")

    report_text = "\n".join(lines) + "\n"
    assert_social_model_language(report_text)
    return report_text
