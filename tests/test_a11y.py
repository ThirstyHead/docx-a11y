"""End-to-end tests for docx-a11y.

Fixtures are committed under tests/fixtures/ (build once via tests/make_fixtures.py).
"""
import json
import shutil
from pathlib import Path

import pytest

from docx_a11y.audit import audit_file
from docx_a11y.cli import main
from docx_a11y.contrast import contrast_ratio, hex_to_rgb
from docx_a11y.remediate import remediate
from docx_a11y.rules import AuditContext

FIX = Path(__file__).resolve().parent / "fixtures"

HEADING_MAP_BREAD = "0=Heading 1,4=Heading 2,9=Heading 2"
HEADING_MAP_FIXABLE = "0=Heading 1,3=Heading 2,4=Heading 2"


def _ids(result):
    return {f["rule_id"] for f in result["findings"]}


# ---------------------------------------------------------------------------
# contrast math
# ---------------------------------------------------------------------------

def test_contrast_black_on_white():
    assert contrast_ratio(hex_to_rgb("000000"), hex_to_rgb("FFFFFF")) == pytest.approx(21.0, abs=0.05)


def test_contrast_e8e8e8_on_white_fails():
    r = contrast_ratio(hex_to_rgb("E8E8E8"), hex_to_rgb("FFFFFF"))
    assert r < 4.5
    assert r == pytest.approx(1.23, abs=0.05)


def test_contrast_red_on_white_fails_45():
    r = contrast_ratio(hex_to_rgb("FF0000"), hex_to_rgb("FFFFFF"))
    assert r == pytest.approx(4.0, abs=0.05)
    assert r < 4.5


# ---------------------------------------------------------------------------
# audit: clean
# ---------------------------------------------------------------------------

def test_clean_passes():
    res = audit_file(FIX / "clean.docx")
    assert res["summary"]["pass"] is True
    assert res["summary"]["total"] == 0


# ---------------------------------------------------------------------------
# audit: fixable fixture
# ---------------------------------------------------------------------------

def test_fixable_finds_all_six():
    res = audit_file(FIX / "fixable.docx")
    ids = _ids(res)
    assert ids == {
        "image-alt-missing",
        "headings-none",
        "table-header-missing",
        "title-missing",
        "color-contrast",
        "language-missing",
    }
    assert res["summary"]["pass"] is False
    assert res["summary"]["blocking"] == 3  # 1 critical + 2 serious
    # all findings fixable
    assert all(f["fixable"] for f in res["findings"])


def test_fixable_severities():
    res = audit_file(FIX / "fixable.docx")
    sev = {f["rule_id"]: f["severity"] for f in res["findings"]}
    assert sev["image-alt-missing"] == "critical"
    assert sev["headings-none"] == "serious"
    assert sev["table-header-missing"] == "serious"


def test_fixable_remediate_then_pass():
    res = audit_file(FIX / "fixable.docx")
    (FIX.parent / "tmp").mkdir(exist_ok=True)
    out = FIX.parent / "tmp" / "fixable_fixed.docx"
    ctx = AuditContext(source_name="fixable.docx",
                       heading_map={0: "Heading 1", 3: "Heading 2", 4: "Heading 2"})
    rr = remediate(FIX / "fixable.docx", _tmp_json(res), out, ctx)
    assert rr.ok, rr.skipped
    assert len(rr.applied) == 6
    reaudit = audit_file(out)
    assert reaudit["summary"]["pass"] is True
    assert reaudit["summary"]["total"] == 0
    # source untouched
    src_reaudit = audit_file(FIX / "fixable.docx")
    assert src_reaudit["summary"]["total"] == 6


# ---------------------------------------------------------------------------
# remediate_from_result (in-memory)
# ---------------------------------------------------------------------------

def test_remediate_from_result_matches_file_variant():
    from docx_a11y.remediate import remediate, remediate_from_result
    res = audit_file(FIX / "fixable.docx")
    ctx = AuditContext(source_name="fixable.docx",
                       heading_map={0: "Heading 1", 3: "Heading 2", 4: "Heading 2"})
    out_a = FIX.parent / "tmp" / "fixable_fromresult_a.docx"
    out_b = FIX.parent / "tmp" / "fixable_fromresult_b.docx"
    rr_a = remediate(FIX / "fixable.docx", _tmp_json(res), out_a, ctx)
    rr_b = remediate_from_result(FIX / "fixable.docx", res, out_b, ctx)
    assert rr_a.applied == rr_b.applied
    assert rr_a.skipped == rr_b.skipped
    reaudit = audit_file(out_b)
    assert reaudit["summary"]["pass"] is True
    assert reaudit["summary"]["total"] == 0


def _tmp_json(result):
    (FIX.parent / "tmp").mkdir(exist_ok=True)
    p = FIX.parent / "tmp" / "audit.json"
    p.write_text(json.dumps(result, indent=2, sort_keys=True))
    return p


# ---------------------------------------------------------------------------
# audit + remediate: violations fixture (mixed fixable/manual)
# ---------------------------------------------------------------------------

def test_violations_finds_manual_and_fixable():
    res = audit_file(FIX / "violations.docx")
    ids = _ids(res)
    assert "heading-level-skipped" in ids
    assert "multiple-h1" in ids
    assert "merged-cell" in ids
    assert "table-header-missing" in ids
    manual = {f["rule_id"] for f in res["findings"] if not f["fixable"]}
    assert manual == {"multiple-h1", "merged-cell"}


def test_violations_remediate_leaves_manual():
    res = audit_file(FIX / "violations.docx")
    out = FIX.parent / "tmp" / "viol_fixed.docx"
    rr = remediate(FIX / "violations.docx", _tmp_json(res), out)
    assert rr.ok
    reaudit = audit_file(out)
    # blocking (heading skip, table header) resolved
    assert reaudit["summary"]["blocking"] == 0
    # manual findings remain
    ids = _ids(reaudit)
    assert "multiple-h1" in ids
    assert "merged-cell" in ids
    # heading skip is gone (H3 re-leveled to H2)
    assert "heading-level-skipped" not in ids


# ---------------------------------------------------------------------------
# real-world fixture: no-knead-bread
# ---------------------------------------------------------------------------

def test_bread_reproduce_original_audit():
    res = audit_file(FIX / "no-knead-bread.docx")
    ids = _ids(res)
    assert ids == {
        "image-alt-missing",
        "headings-none",
        "title-missing",
        "color-contrast",
    }
    # the E8E8E8 run
    cc = [f for f in res["findings"] if f["rule_id"] == "color-contrast"]
    assert "E8E8E8" in cc[0]["evidence"]


def test_bread_remediate_then_pass():
    res = audit_file(FIX / "no-knead-bread.docx")
    out = FIX.parent / "tmp" / "bread_fixed.docx"
    ctx = AuditContext(source_name="no-knead-bread.docx",
                       heading_map={0: "Heading 1", 4: "Heading 2", 9: "Heading 2"})
    rr = remediate(FIX / "no-knead-bread.docx", _tmp_json(res), out, ctx)
    assert rr.ok
    reaudit = audit_file(out)
    assert reaudit["summary"]["pass"] is True
    assert reaudit["summary"]["total"] == 0


# ---------------------------------------------------------------------------
# idempotency: remediating a clean doc changes nothing
# ---------------------------------------------------------------------------

def test_remediate_clean_is_noop():
    res = audit_file(FIX / "clean.docx")
    out = FIX.parent / "tmp" / "clean_fixed.docx"
    rr = remediate(FIX / "clean.docx", _tmp_json(res), out)
    assert rr.ok
    reaudit = audit_file(out)
    assert reaudit["summary"]["pass"] is True
    assert reaudit["summary"]["total"] == 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def test_cli_audit_exit_codes(tmp_path, capsys):
    rc = main(["audit", str(FIX / "clean.docx")])
    assert rc == 0
    capsys.readouterr()
    rc = main(["audit", str(FIX / "violations.docx")])
    assert rc == 1
    capsys.readouterr()
    rc = main(["audit", str(tmp_path / "nope.docx")])
    assert rc == 2


def test_cli_audit_writes_json_and_report(tmp_path, capsys):
    j = tmp_path / "a.json"
    r = tmp_path / "a.md"
    rc = main(["audit", str(FIX / "fixable.docx"), "--json", str(j), "--report", str(r)])
    assert rc == 1
    data = json.loads(j.read_text())
    assert data["summary"]["total"] == 6
    md = r.read_text()
    assert "Accessibility Audit Report" in md
    assert "SC 1.1.1" in md


def test_cli_rules(capsys):
    rc = main(["rules"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "image-alt-missing" in out
    assert "title-missing" in out
