"""Markdown report generator: audit result JSON -> accessibility-audit-report.md.

Deterministic: same input JSON -> byte-identical output.
"""
import json
from pathlib import Path

from .audit import audit_result_to_json

SC_NAMES = {
    "1.1.1": ("Non-text Content", "A", "1 Perceivable / 1.1 Text Alternatives"),
    "1.3.1": ("Info and Relationships", "A", "1 Perceivable / 1.3 Adaptable"),
    "1.4.3": ("Contrast (Minimum)", "AA", "1 Perceivable / 1.4 Distinguishable"),
    "2.4.2": ("Page Titled", "A", "2 Operable / 2.4 Navigable (applied by convention to document title metadata)"),
    "3.1.1": ("Language of Page", "A", "3 Understandable / 3.1 Readable"),
}

RULE_NOTES = {
    "title-missing": "Set dc:title from the first Heading 1 or the filename stem.",
    "language-missing": "Set w:lang in docDefaults (default en-US).",
    "heading-level-skipped": "Reassign the offending paragraph to the next-lower valid level.",
    "headings-none": "Structure is presentation-only. Deterministic fix: pass --heading-map "
                     "'<paragraph_index>=<Heading N>' entries; otherwise apply native heading styles in Word.",
    "multiple-h1": "Keep one H1 for the document title; demote the rest to H2 (manual).",
    "image-alt-missing": "Alt text is human content. The auto-fix inserts an [ALT-NOT-PROVIDED: ...] "
                         "marker so the location stays tracked; replace it with a real description.",
    "table-header-missing": "Mark the first row as a header row (w:tblHeader); ensure every column "
                            "has a header cell.",
    "merged-cell": "Unmerge cells and repeat values unless the data genuinely spans (manual).",
    "color-contrast": "Remove the hardcoded w:color override so text inherits the default color, "
                      "or pick a color meeting 4.5:1 (3:1 large text).",
}


def render_report(result: dict, remediation=None, source_path=None) -> str:
    src = source_path or result.get("file", "document.docx")
    summary = result["summary"]
    findings = result["findings"]
    L = []
    L.append(f"# Accessibility Audit Report — {src}")
    L.append("")
    L.append(f"- **File:** {src}")
    L.append(f"- **Audited:** {result.get('audited_at', 'n/a')}")
    L.append(f"- **Tool:** {result.get('tool', 'docx-a11y')}")
    L.append("- **Standard:** WCAG 2.1 AA")
    L.append("- **Verdict:** " + ("PASS" if summary["pass"] else "FAIL (blocking violations)"))
    L.append(f"- **Findings:** {summary['total']} "
             f"(critical={summary['by_severity']['critical']}, "
             f"serious={summary['by_severity']['serious']}, "
             f"moderate={summary['by_severity']['moderate']}, "
             f"minor={summary['by_severity']['minor']})")
    L.append("")
    L.append("## Scope note")
    L.append("")
    L.append("Keyboard/navigation criteria (2.x) do not apply to .docx content; 2.4.2 is applied "
             "by convention to document title metadata.")
    L.append("")

    if findings:
        L.append("## Findings")
        L.append("")
        for n, f in enumerate(findings, 1):
            name, level, guide = SC_NAMES.get(f["sc"], ("", f["sc"], ""))
            L.append(f"### {n}. {f['severity'].upper()} — SC {f['sc']} {name} (Level {level})")
            L.append(f"- **Rule:** `{f['rule_id']}`")
            L.append(f"- **Guideline:** {guide}")
            L.append(f"- **Location:** {f['location']}")
            L.append(f"- **Description:** {f['description']}")
            if f.get("evidence"):
                L.append(f"- **Evidence:** `{f['evidence']}`")
            L.append(f"- **Action:** {'Programmatically fixable' if f['fixable'] else 'Manual review required'}")
            if f.get("fix"):
                L.append(f"- **Fix:** {f['fix']}")
            L.append("")
    else:
        L.append("## Findings")
        L.append("")
        L.append("None. All rules passed.")
        L.append("")

    if remediation is not None:
        rr = remediation if isinstance(remediation, dict) else {}
        L.append("## Remediation")
        L.append("")
        if rr.get("output_path"):
            L.append(f"- **Output:** {rr['output_path']}")
        applied = rr.get("applied", [])
        skipped = rr.get("skipped", [])
        L.append(f"- **Applied fixes:** {len(applied)}")
        for a in applied:
            L.append(f"  - `{a[0]}` @ {a[1]}")
        L.append(f"- **Skipped (manual):** {len(skipped)}")
        for s in skipped:
            reason = s[2] if len(s) > 2 else ""
            L.append(f"  - `{s[0]}` @ {s[1]}" + (f" — {reason}" if reason else ""))
        L.append("")

    manual = [f for f in findings if not f["fixable"]]
    if manual:
        L.append("## Residual manual work")
        L.append("")
        for f in manual:
            L.append(f"- **{f['rule_id']}** @ {f['location']}: {f.get('fix', f['description'])}")
        L.append("")

    L.append("## Re-verify")
    L.append("")
    L.append("```bash")
    L.append(f"docx-a11y audit {Path(src).stem}_remediated.docx --json reaudit.json")
    L.append("```")
    L.append("")
    return "\n".join(L)


def write_report(result: dict, path, remediation=None, source_path=None):
    text = render_report(result, remediation, source_path)
    Path(path).write_text(text)
    return path