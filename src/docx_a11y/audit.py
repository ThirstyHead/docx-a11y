"""Audit engine: run all rules against a .docx and collect findings."""
import hashlib
import json
import time
from pathlib import Path

from docx import Document

from . import __version__
from .findings import Finding, findings_sorted, summarize
from .rules import RULES, AuditContext


def audit_file(path, ctx=None) -> dict:
    """Audit a .docx file. Returns a result dict (JSON-safe).

    Result shape:
    {
      "file": str,
      "audited_at": iso8601,
      "tool": "docx-a11y/0.2.0",
      "sha256": "...",
      "findings": [ {rule_id, sc, severity, location, description, evidence, fixable, fix}, ... ],
      "summary": {total, by_severity, blocking, pass}
    }
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)
    file_bytes = path.read_bytes()
    file_sha256 = hashlib.sha256(file_bytes).hexdigest()
    doc = Document(str(path))
    if ctx is None:
        ctx = AuditContext(source_name=path.name)
    findings = []
    for rule in RULES:
        try:
            findings.extend(rule.check(doc, ctx))
        except Exception as exc:  # a broken rule must not kill the whole audit
            findings.append(Finding(f"{rule.rule_id}__error", rule.sc, "moderate",
                                    "internal",
                                    f"Rule {rule.rule_id} raised: {exc}",
                                    repr(exc), False, "Fix the rule; treat as manual review."))
    return {
        "file": path.name,
        "audited_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "tool": f"docx-a11y/{__version__}",
        "sha256": file_sha256,
        "findings": [f.to_dict() for f in findings_sorted(findings)],
        "summary": summarize(findings_sorted(findings)),
    }


def audit_result_to_json(result: dict) -> str:
    return json.dumps(result, indent=2, sort_keys=True)


def load_result(path) -> dict:
    return json.loads(Path(path).read_text())