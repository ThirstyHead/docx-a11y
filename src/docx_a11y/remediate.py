"""Remediation engine: apply deterministic fixes from an audit result.

Safety model:
  - Works on a fresh in-memory Document copy of the source; never mutates the source file.
  - Only fixes flagged fixable=true are attempted, in deterministic order
    (structure before metadata, so the title rule can pick up a new H1).
  - Every fix has a precondition; failures are recorded, never exceptions.
  - Output is a new file; the original is untouched.
"""
from dataclasses import dataclass, field
from pathlib import Path

from docx import Document

from .audit import load_result
from .findings import Finding
from .rules import RULES_BY_ID, RULES, AuditContext

# Deterministic application order (structure first, metadata last).
APPLY_ORDER = [
    "HeadingsNone",          # applies heading map if provided
    "HeadingSkipped",
    "ImageAltMissing",
    "TableHeaderMissing",
    "ColorContrast",
    "TitleMissing",          # after headings so dc:title can use the first H1
    "LanguageMissing",
]


@dataclass
class RemediationResult:
    output_path: str
    applied: list = field(default_factory=list)    # [rule_id, location]
    skipped: list = field(default_factory=list)    # [rule_id, location, reason]

    @property
    def ok(self):
        return not self.skipped

    def to_dict(self):
        return {"output_path": self.output_path, "applied": self.applied,
                "skipped": self.skipped, "ok": self.ok}


def apply_fixes(doc, result: dict, rr: RemediationResult, ctx: AuditContext) -> None:
    """Apply deterministic fixes for `result`'s fixable findings onto an in-memory
    Document. Populates rr.applied / rr.skipped. Never raises for rule failures."""
    findings = [Finding(**f) for f in result["findings"] if f.get("fixable")]
    # group by rule class name (derived from rule_id)
    by_rule = {}
    for f in findings:
        rcls = _class_for(f.rule_id)
        by_rule.setdefault(rcls, []).append(f)

    for rcls in APPLY_ORDER:
        rule = _rule_for_class(rcls)
        if rule is None:
            continue
        rule_findings = by_rule.get(rcls, [])
        # Rules whose fix() handles ALL of its findings in one shot (whole-doc mutations).
        bulk = rcls in ("HeadingsNone", "TitleMissing")
        if bulk and rule_findings:
            f0 = rule_findings[0]
            reason = None
            try:
                ok = rule.fix(doc, f0, ctx)
            except Exception as exc:
                ok = False
                reason = f"{type(exc).__name__}: {exc}"
            if ok:
                rr.applied.extend([rcls, f.location] for f in rule_findings)
            else:
                rr.skipped.extend([rcls, f.location, reason or "fix returned False"]
                                   for f in rule_findings)
            continue
        for f in rule_findings:
            reason = None
            try:
                ok = rule.fix(doc, f, ctx)
            except Exception as exc:
                ok = False
                reason = f"{type(exc).__name__}: {exc}"
            if ok:
                rr.applied.append([rcls, f.location])
            else:
                rr.skipped.append([rcls, f.location, reason or "fix returned False"])


def remediate(src_path, result_path, out_path, ctx=None) -> RemediationResult:
    src, out = Path(src_path), Path(out_path)
    res = load_result(result_path)
    doc = Document(str(src))
    if ctx is None:
        ctx = AuditContext(source_name=src.name)
    if not ctx.source_name:
        ctx.source_name = src.name

    rr = RemediationResult(output_path=str(out))
    apply_fixes(doc, res, rr, ctx)
    doc.save(str(out))
    return rr


def _class_for(rule_id):
    # rule_ids: title-missing, language-missing, heading-level-skipped, headings-none,
    #           multiple-h1, image-alt-missing, table-header-missing, merged-cell, color-contrast
    mapping = {
        "title-missing": "TitleMissing",
        "language-missing": "LanguageMissing",
        "heading-level-skipped": "HeadingSkipped",
        "headings-none": "HeadingsNone",
        "multiple-h1": "MultipleH1",
        "image-alt-missing": "ImageAltMissing",
        "table-header-missing": "TableHeaderMissing",
        "merged-cell": "MergedCell",
        "color-contrast": "ColorContrast",
    }
    return mapping.get(rule_id, rule_id)


def _rule_for_class(rcls):
    for r in RULES:
        if type(r).__name__ == rcls:
            return r
    return None