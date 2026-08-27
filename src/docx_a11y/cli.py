"""docx-a11y CLI.

Usage:
  docx-a11y audit FILE [--json out.json] [--report out.md]
              [--language en-US] [--background FFFFFF]
              [--heading-map '0=Heading 1,4=Heading 2']
  docx-a11y remediate FILE --findings audit.json --out FILE_fixed.docx
              [--language en-US] [--background FFFFFF]
              [--heading-map '0=Heading 1,4=Heading 2']
  docx-a11y rules

Exit codes (audit): 0 = pass (no blocking findings), 1 = fail, 2 = usage/IO error.
"""
import argparse
import sys
from pathlib import Path

from . import __version__
from .audit import audit_file, audit_result_to_json
from .remediate import remediate
from .report import write_report
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
        default_language=args.language,
        background_rgb=args.background,
        heading_map=_parse_heading_map(getattr(args, "heading_map", None)),
    )


def cmd_audit(args) -> int:
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
        write_report(result, args.report, source_path=args.file)
        print(f"report written: {args.report}")

    s = result["summary"]
    verdict = "PASS" if s["pass"] else "FAIL"
    print(f"audit {args.file}: {s['total']} findings "
          f"(critical={s['by_severity']['critical']}, serious={s['by_severity']['serious']}, "
          f"moderate={s['by_severity']['moderate']}) -> {verdict}")
    for f in result["findings"]:
        mark = "fixable" if f["fixable"] else "manual "
        print(f"  [{f['severity'].upper():8s}] SC {f['sc']:5s} {mark} @ {f['location']} :: {f['description']}")
    return 0 if s["pass"] else 1


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


def cmd_rules(_args) -> int:
    print(f"{'rule_id':28s} {'sc':6s} {'severity':9s} fixable-rules")
    for r in RULES:
        print(f"{r.rule_id:28s} {r.sc:6s} {r.severity:9s} {'yes' if _has_fix(r) else 'no '}")
    return 0


def _has_fix(r):
    import inspect
    src = inspect.getsource(r.fix)
    return "return True" in src or "return fixed" in src or "return len(" in src


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="docx-a11y",
                                description="Audit and remediate Word .docx files for WCAG 2.1 AA.")
    p.add_argument("--version", action="version", version=f"docx-a11y {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("audit", help="audit a .docx for WCAG violations")
    a.add_argument("file")
    a.add_argument("--json", help="write findings JSON")
    a.add_argument("--report", help="write markdown report")
    a.add_argument("--language", default="en-US", help="default language code (default en-US)")
    a.add_argument("--background", default="FFFFFF", help="assumed background RGB for contrast math")
    a.add_argument("--heading-map", help="deterministic structure: '0=Heading 1,4=Heading 2'")
    a.set_defaults(func=cmd_audit)

    r = sub.add_parser("remediate", help="apply deterministic fixes from an audit JSON")
    r.add_argument("file")
    r.add_argument("--findings", required=True, help="audit JSON produced by `docx-a11y audit --json`")
    r.add_argument("--out", required=True, help="output .docx (source is never modified)")
    r.add_argument("--language", default="en-US")
    r.add_argument("--background", default="FFFFFF")
    r.add_argument("--heading-map", help="deterministic structure: '0=Heading 1,4=Heading 2'")
    r.set_defaults(func=cmd_remediate)

    rl = sub.add_parser("rules", help="list audit rules")
    rl.set_defaults(func=cmd_rules)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())