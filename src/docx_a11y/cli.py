"""docx-a11y CLI entry point.

Dual-mode interface:
1. Unified twin interface (matching pptx-a11y):
   docx-a11y FILE [--gui] [--format md,html,pdf,json] [--theme THEME]
                  [--output-dir DIR] [--fix] [--out-docx OUT]
2. Subcommands (backward compatibility):
   docx-a11y audit FILE ...
   docx-a11y fix FILE ...
   docx-a11y remediate FILE ...
   docx-a11y rules
"""
import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .audit import audit_file, audit_result_to_json
from .enrich import build_enrichment
from .remediate import (
    _batch_docx_files,
    fix_batch,
    fix_one,
    remediate,
    remediate_from_result,
)
from .report import write_report
from .reports.html import render_html
from .reports.md import render_md
from .reports.pdf import render_pdf
from .reports.theme import available_themes
from .rules import RULES, AuditContext


def _parse_heading_map(s):
    """'0=Heading 1,4=Heading 2' -> {0: 'Heading 1', 4: 'Heading 2'}"""
    out = {}
    if not s:
        return out
    for part in s.split(","):
        part = part.strip()
        if not part:
            continue
        idx, _, style = part.partition("=")
        out[int(idx.strip())] = style.strip()
    return out


def _ctx(args, source_name) -> AuditContext:
    return AuditContext(
        source_name=source_name,
        default_language=getattr(args, "language", "en-US"),
        background_rgb=getattr(args, "background", "FFFFFF"),
        heading_map=_parse_heading_map(getattr(args, "heading_map", None)),
    )


def cmd_audit(args) -> int:
    if getattr(args, "batch", None):
        return _cmd_audit_batch(args)
    ctx = _ctx(args, args.file)
    try:
        result = audit_file(args.file, ctx)
    except FileNotFoundError as e:
        print(f"error: file not found: {e}", file=sys.stderr)
        return 2
    except Exception as e:
        print(f"error: {type(e).__name__}: {e}", file=sys.stderr)
        return 2

    if args.json:
        Path(args.json).write_text(audit_result_to_json(result) + "\n")
        print(f"findings written: {args.json}")
    if args.report:
        enrichment, source = build_enrichment(result, live=getattr(args, "enrich", False))
        write_report(
            result,
            args.report,
            source_path=args.file,
            enrichment=enrichment,
            enrichment_source=source,
        )
        print(f"report written: {args.report} (normative text: {source})")

    s = result["summary"]
    verdict = "PASS" if s["pass"] else "FAIL"
    print(
        f"audit {args.file}: {s['total']} findings "
        f"(critical={s['by_severity']['critical']}, serious={s['by_severity']['serious']}, "
        f"moderate={s['by_severity']['moderate']}) -> {verdict}"
    )
    for f in result["findings"]:
        mark = "fixable" if f["fixable"] else "manual "
        print(
            f"  [{f['severity'].upper():8s}] SC {f['sc']:5s} {mark} @ {f['location']} :: {f['description']}"
        )
    return 0 if s["pass"] else 1


def _cmd_audit_batch(args) -> int:
    results = {}
    failed = 0
    try:
        files = _batch_docx_files(Path(args.batch))
    except NotADirectoryError as e:
        print(f"error: not a directory: {e}", file=sys.stderr)
        return 2
    if not files:
        print(f"error: no .docx files in {args.batch}", file=sys.stderr)
        return 2
    for p in files:
        pctx = _ctx(args, p.name)
        try:
            result = audit_file(p, pctx)
        except Exception as e:
            failed += 1
            results[p.name] = {"error": f"{type(e).__name__}: {e}"}
            print(f"[ERROR] {p.name}: {type(e).__name__}: {e}", file=sys.stderr)
            continue
        s = result["summary"]
        verdict = "PASS" if s["pass"] else "FAIL"
        if not s["pass"]:
            failed += 1
        results[p.name] = result
        print(
            f"[{verdict}] {p.name}: {s['total']} findings "
            f"(critical={s['by_severity']['critical']}, serious={s['by_severity']['serious']}, "
            f"moderate={s['by_severity']['moderate']})"
        )
    if args.json:
        agg = {"directory": str(Path(args.batch)), "files": results}
        Path(args.json).write_text(json.dumps(agg, indent=2, sort_keys=True) + "\n")
        print(f"batch findings written: {args.json}")
    print(f"audit batch {args.batch}: {len(files)} file(s), {failed} failed")
    return 0 if failed == 0 else 1


def cmd_remediate(args) -> int:
    ctx = _ctx(args, args.file)
    try:
        rr = remediate(args.file, args.findings, args.out, ctx)
    except FileNotFoundError as e:
        print(f"error: file not found: {e}", file=sys.stderr)
        return 2
    except Exception as e:
        print(f"error: {type(e).__name__}: {e}", file=sys.stderr)
        return 2
    print(f"remediated {args.file} -> {args.out}")
    print(f"  applied: {len(rr.applied)}, skipped(manual): {len(rr.skipped)}")
    for a in rr.applied:
        print(f"  [applied ] {a[0]} @ {a[1]}")
    for s in rr.skipped:
        reason = s[2] if len(s) > 2 else ""
        print(f"  [skipped] {s[0]} @ {s[1]}" + (f" — {reason}" if reason else ""))
    print("re-verify: docx-a11y audit " + Path(args.out).name)
    return 0 if rr.ok else 1


def cmd_fix(args) -> int:
    if getattr(args, "batch", None):
        return _cmd_fix_batch(args)
    if not args.file:
        print("error: FILE required (or use --batch DIR)", file=sys.stderr)
        return 2
    ctx = _ctx(args, args.file)
    out = args.out or str(Path(args.file).with_name(Path(args.file).name + ".fixed.docx"))
    fr = fix_one(args.file, out, ctx)
    if fr["status"] == "error":
        print(f"error: {fr['error']}", file=sys.stderr)
        return 2

    if args.json:
        Path(args.json).write_text(json.dumps(fr, indent=2, sort_keys=True) + "\n")
        print(f"fix result written: {args.json}")

    before = fr["findings_before"]
    after_total = fr["reaudit"]["summary"]["total"]
    if fr["remediation"]:
        m = fr["remediation"]
        print(f"fix {args.file} -> {fr['output_path']}")
        print(f"  applied: {len(m['applied'])}, skipped(manual): {len(m['skipped'])}")
        for s in m["skipped"]:
            reason = s[2] if len(s) > 2 else ""
            print(f"  [skipped] {s[0]} @ {s[1]}" + (f" — {reason}" if reason else ""))
    else:
        print(f"fix {args.file} -> {fr['output_path']} (clean: 0 findings, copied)")

    verdict = "PASS" if fr["status"] == "pass" else "FAIL (blocking findings remain)"
    print(f"  findings: {before} -> {after_total} => {verdict}")
    if fr["status"] != "pass":
        for f in fr["reaudit"]["findings"]:
            if f["severity"] in ("critical", "serious"):
                print(
                    f"  [BLOCKING] {f['rule_id']} SC {f['sc']} @ {f['location']} :: {f['description']}"
                )

    if args.report:
        enrichment, source = build_enrichment(fr["reaudit"], live=getattr(args, "enrich", False))
        write_report(
            fr["reaudit"],
            args.report,
            remediation=fr["remediation"],
            source_path=args.file,
            enrichment=enrichment,
            enrichment_source=source,
        )
        print(f"report written: {args.report} (normative text: {source})")
    return 0 if fr["status"] == "pass" else 1


def _cmd_fix_batch(args) -> int:
    if getattr(args, "report", None):
        print(
            "warning: --report is not supported in batch mode; use --json (one aggregated file)",
            file=sys.stderr,
        )
    ctx = _ctx(args, "")
    try:
        res = fix_batch(args.batch, ctx)
    except NotADirectoryError as e:
        print(f"error: not a directory: {e}", file=sys.stderr)
        return 2
    if not res["entries"]:
        print(f"error: no .docx files in {args.batch}", file=sys.stderr)
        return 2
    s = res["summary"]
    for e in res["entries"]:
        mark = {"pass": "PASS", "fail": "FAIL", "error": "ERROR"}[e["status"]]
        after = e["reaudit"]["summary"]["total"] if e["reaudit"] else "?"
        extra = f" :: {e['error']}" if e["status"] == "error" else ""
        print(f"[{mark}] {e['file']}: {e['findings_before']} -> {after}{extra}")
    failed = s["fail"] + s["error"]
    print(
        f"fix batch {args.batch}: {s['total']} file(s) — "
        f"pass={s['pass']} fail={s['fail']} error={s['error']} "
        f"(findings {s['findings_before']} -> {s['findings_after']})"
    )
    if args.json:
        Path(args.json).write_text(json.dumps(res, indent=2, sort_keys=True) + "\n")
        print(f"batch result written: {args.json}")
    print(f"{failed} file(s) failed")
    if s["error"]:
        return 2
    return 0 if s["fail"] == 0 else 1


def cmd_rules(_args) -> int:
    print(f"{'rule_id':28s} {'sc':6s} {'severity':9s} fixable-rules")
    for r in RULES:
        print(f"{r.rule_id:28s} {r.sc:6s} {r.severity:9s} {'yes' if _has_fix(r) else 'no '}")
    return 0


def _has_fix(r):
    import inspect

    src = inspect.getsource(r.fix)
    return "return True" in src or "return fixed" in src or "return len(" in src


def _build_subcommand_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="docx-a11y",
        description="Audit and remediate Word .docx files for WCAG 2.1 AA.",
    )
    p.add_argument("--version", action="version", version=f"docx-a11y {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("audit", help="audit a .docx for WCAG violations")
    a.add_argument("file", nargs="?", help=".docx to audit (omit when using --batch)")
    a.add_argument("--batch", help="audit every .docx in a directory (non-recursive)")
    a.add_argument("--json", help="write findings JSON")
    a.add_argument("--report", help="write markdown report")
    a.add_argument("--language", default="en-US", help="default language code (default en-US)")
    a.add_argument("--background", default="FFFFFF", help="assumed background RGB for contrast math")
    a.add_argument("--heading-map", help="deterministic structure: '0=Heading 1,4=Heading 2'")
    a.add_argument(
        "--enrich",
        action="store_true",
        help="fetch normative text live from wcag-guidelines-mcp (default: offline cache)",
    )
    a.set_defaults(func=cmd_audit)

    r = sub.add_parser("remediate", help="apply deterministic fixes from an audit JSON")
    r.add_argument("file")
    r.add_argument("--findings", required=True, help="audit JSON produced by `docx-a11y audit --json`")
    r.add_argument("--out", required=True, help="output .docx (source is never modified)")
    r.add_argument("--language", default="en-US")
    r.add_argument("--background", default="FFFFFF")
    r.add_argument("--heading-map", help="deterministic structure: '0=Heading 1,4=Heading 2'")
    r.set_defaults(func=cmd_remediate)

    fx = sub.add_parser("fix", help="audit + remediate + verify in one step (source untouched)")
    fx.add_argument("file", nargs="?", help=".docx to fix (omit when using --batch)")
    fx.add_argument(
        "--batch",
        help="process every .docx in a directory instead of one file (non-recursive)",
    )
    fx.add_argument("--out", help="output .docx (default: <file>.fixed.docx)")
    fx.add_argument("--json", help="write full fix result JSON (before/after/remediation)")
    fx.add_argument("--report", help="write markdown report (re-audit + remediation section)")
    fx.add_argument("--language", default="en-US")
    fx.add_argument("--background", default="FFFFFF")
    fx.add_argument("--heading-map", help="deterministic structure: '0=Heading 1,4=Heading 2'")
    fx.add_argument(
        "--enrich",
        action="store_true",
        help="fetch normative text live from wcag-guidelines-mcp for --report",
    )
    fx.set_defaults(func=cmd_fix)

    rl = sub.add_parser("rules", help="list audit rules")
    rl.set_defaults(func=cmd_rules)
    return p


def _build_unified_parser() -> argparse.ArgumentParser:
    themes = [t["name"] for t in available_themes()]
    p = argparse.ArgumentParser(
        prog="docx-a11y",
        description="Audit and remediate Word .docx files against WCAG 2.1 AA standards.",
    )
    p.add_argument("file", nargs="?", default=None, help="Path to Word .docx file or directory")
    p.add_argument("--gui", action="store_true", help="Launch graphical user interface")
    p.add_argument(
        "--format",
        default="md",
        help="Report formats (comma-separated): md, html, pdf, json (default: md)",
    )
    p.add_argument(
        "--theme",
        default="light",
        help=f"SMACSS theme for HTML/PDF reports: {themes}",
    )
    p.add_argument("--output-dir", default=".", help="Directory to save generated reports")
    p.add_argument("--fix", action="store_true", help="Perform deterministic remediation")
    p.add_argument("--out-docx", help="Output path for remediated .docx file")
    p.add_argument("--out", help=argparse.SUPPRESS)
    p.add_argument("--batch", help="Batch process every .docx in a directory (non-recursive)")
    p.add_argument("--language", default="en-US", help="Default language code (default: en-US)")
    p.add_argument("--background", default="FFFFFF", help="Assumed background RGB for contrast math")
    p.add_argument("--heading-map", help="Deterministic structure: '0=Heading 1,4=Heading 2'")
    p.add_argument("--enrich", action="store_true", help="Fetch normative text live from wcag-guidelines-mcp")
    p.add_argument("--version", action="version", version=f"docx-a11y {__version__}")
    return p


def run_unified(args, parser: argparse.ArgumentParser) -> int:
    if args.gui:
        try:
            from .gui.app import main as gui_main  # type: ignore[import-not-found]

            gui_main()
            return 0
        except (ImportError, ModuleNotFoundError) as e:
            print(
                f"Error: GUI dependencies not installed. Run 'pip install docx-a11y[gui]'. ({e})",
                file=sys.stderr,
            )
            return 1

    if not args.file and not args.batch:
        parser.error("the following arguments are required: file (or specify --gui)")

    target = Path(args.batch or args.file)
    if target.is_dir():
        args.batch = str(target)
        if args.fix:
            return _cmd_fix_batch(args)
        return _cmd_audit_batch(args)

    input_path = target
    if not input_path.exists():
        print(f"Error: File '{input_path}' not found.", file=sys.stderr)
        return 2

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = input_path.stem

    ctx = _ctx(args, input_path.name)

    # 1. Audit original file
    audit_before = audit_file(input_path, ctx)
    audit_after = None

    # 2. Remediate if requested
    out_target = args.out_docx or args.out
    if args.fix:
        fixed_docx = Path(out_target) if out_target else out_dir / f"{stem}-remediated.docx"
        if fixed_docx.resolve() == input_path.resolve():
            print(
                "Error: --out-docx cannot match input document. "
                "docx-a11y strictly guarantees that original files remain untouched and immutable.",
                file=sys.stderr,
            )
            return 2
        rr = remediate_from_result(input_path, audit_before, fixed_docx, ctx)
        print(
            f"[Integrity Verified] Original file preserved unchanged (SHA-256: {audit_before.get('sha256')})"
        )
        print(f"Remediation saved to: {fixed_docx}")
        print(f"Fixes applied: {len(rr.applied)} applied, {len(rr.skipped)} skipped")
        audit_after = audit_file(fixed_docx, ctx)

    # 3. Render reports
    formats = [f.strip().lower() for f in args.format.split(",")]
    md_text = render_md(audit_before, after_result=audit_after, source_path=str(input_path))

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

    final_summary = (audit_after or audit_before)["summary"]
    return 0 if final_summary["pass"] else 1


def main(argv=None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    subcommands = {"audit", "remediate", "fix", "rules"}
    if argv and argv[0] in subcommands:
        p = _build_subcommand_parser()
        args = p.parse_args(argv)
        return args.func(args)

    p = _build_unified_parser()
    args = p.parse_args(argv)
    return run_unified(args, p)


if __name__ == "__main__":
    sys.exit(main())
