"""docx-a11y CLI entry point."""
import argparse
import sys
from pathlib import Path
from engine_a11y.criteria_config import (
    apply_criteria_config,
    generate_criteria_template,
    load_criteria_config,
)
from engine_a11y.findings import summarize
from engine_a11y.profile import get_docx_profile
from .audit import audit_file, audit_result_to_json
from .remediate import remediate_document
from .reports.html import render_html
from .reports.md import render_md
from .reports.pdf import render_pdf
from .reports.theme import available_themes
from .triage import run_interactive_triage


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="docx-a11y",
        description="Audit and remediate Word documents against WCAG 2.2 AA standards.",
    )
    parser.add_argument("file", nargs="?", default=None, help="Path to Word .docx file")
    parser.add_argument("--gui", action="store_true", help="Launch graphical user interface")
    parser.add_argument(
        "--format",
        default="md",
        help="Report formats (comma-separated): md, html, pdf, json (default: md)",
    )
    parser.add_argument(
        "--theme",
        default="light",
        help=f"SMACSS theme for HTML/PDF reports: {[t['name'] for t in available_themes()]}",
    )
    parser.add_argument("--output-dir", default=".", help="Directory to save generated reports")
    parser.add_argument("--fix", action="store_true", help="Perform deterministic remediation")
    parser.add_argument("--triage", action="store_true", help="Launch interactive human-in-the-loop triage session")
    parser.add_argument("--out-docx", help="Output path for remediated .docx file")
    parser.add_argument(
        "--criteria",
        help="Path to criteria configuration checklist ([x]/[ ]) or YAML for what-if testing",
    )
    parser.add_argument(
        "--init-criteria",
        nargs="?",
        const="a11y-criteria.txt",
        help="Generate default criteria checklist file ([x]/[ ]) and exit",
    )

    args = parser.parse_args(argv)

    if args.init_criteria:
        out_criteria = Path(args.init_criteria)
        generate_criteria_template(out_criteria)
        print(f"Generated criteria checklist at: {out_criteria}")
        sys.exit(0)

    if args.gui:
        try:
            from .gui.app import main as gui_main  # type: ignore[import-not-found]

            gui_main()
            sys.exit(0)
        except (ImportError, ModuleNotFoundError) as e:
            print(f"Error: GUI dependencies not installed. Run 'pip install docx-a11y[gui]'. ({e})", file=sys.stderr)
            sys.exit(1)

    if not args.file:
        parser.error("the following arguments are required: file (or specify --gui, --init-criteria)")

    input_path = Path(args.file)
    if not input_path.exists():
        print(f"Error: File '{input_path}' not found.", file=sys.stderr)
        sys.exit(1)

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = input_path.stem

    # Interactive triage mode
    if args.triage:
        triaged_docx = Path(args.out_docx) if args.out_docx else out_dir / f"{stem}-triaged.docx"
        run_interactive_triage(input_path, triaged_docx)
        input_path = triaged_docx
        stem = input_path.stem

    # 1. Audit original file
    audit_before = audit_file(input_path)
    audit_after = None

    excluded_sc = set()
    if args.criteria:
        criteria_path = Path(args.criteria)
        if not criteria_path.exists():
            print(f"Error: Criteria config '{criteria_path}' not found.", file=sys.stderr)
            sys.exit(1)
        _, excluded_sc = load_criteria_config(criteria_path)
        apply_criteria_config(audit_before.get("findings", []), excluded_sc)
        audit_before["summary"] = summarize(audit_before.get("findings", []))

    # 2. Remediate if requested
    if args.fix:
        fixed_docx = Path(args.out_docx) if args.out_docx else out_dir / f"{stem}-remediated.docx"
        if fixed_docx.resolve() == input_path.resolve():
            sys.exit("Error: --out-docx cannot match input document. docx-a11y strictly guarantees that original files remain untouched and immutable.")
        fixes = remediate_document(input_path, fixed_docx)
        print(f"[Integrity Verified] Original file preserved unchanged (SHA-256: {fixes.get('original_sha256')})")
        print(f"Remediation saved to: {fixed_docx}")
        print(f"Fixes applied: {fixes}")
        audit_after = audit_file(fixed_docx)
        if excluded_sc:
            apply_criteria_config(audit_after.get("findings", []), excluded_sc)
            audit_after["summary"] = summarize(audit_after.get("findings", []))

    # 3. Render canonical Markdown report (Source of Truth)
    formats = [f.strip().lower() for f in args.format.split(",")]
    md_text = render_md(
        audit_before,
        after_result=audit_after,
        source_path=str(input_path),
        excluded_sc=excluded_sc,
    )

    if "md" in formats:
        md_file = out_dir / f"{stem}-a11y-report.md"
        md_file.write_text(md_text, encoding="utf-8")
        print(f"Markdown report: {md_file}")

    if "json" in formats:
        json_file = out_dir / f"{stem}-audit.json"
        json_file.write_text(audit_result_to_json(audit_before), encoding="utf-8")
        print(f"JSON audit: {json_file}")

    if "html" in formats:
        html_doc = render_html(md_text, theme=args.theme)
        html_file = out_dir / f"{stem}-a11y-report.html"
        html_file.write_text(html_doc, encoding="utf-8")
        print(f"Accessible HTML report: {html_file}")

    if "pdf" in formats:
        html_doc = render_html(md_text, theme=args.theme)
        pdf_file = out_dir / f"{stem}-a11y-report.pdf"
        render_pdf(html_doc, out_path=pdf_file)
        print(f"Accessible PDF report: {pdf_file}")

    # Exit code reflects compliance status (0 = compliant, 1 = action required)
    final_summary = (audit_after or audit_before)["summary"]
    sys.exit(0 if final_summary.get("pass", False) else 1)


if __name__ == "__main__":
    main()
