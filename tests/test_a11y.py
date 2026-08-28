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
# fix_one (audit -> remediate -> verify)
# ---------------------------------------------------------------------------

def test_fix_one_clean_doc_is_noop_pass():
    from docx_a11y.remediate import fix_one
    out = FIX.parent / "tmp" / "clean_fixed_one.docx"
    fr = fix_one(FIX / "clean.docx", out)
    assert fr["status"] == "pass"
    assert fr["reaudit"]["summary"]["total"] == 0
    assert Path(out).exists()


def test_fix_one_fixable_doc_passes_after_fix():
    from docx_a11y.remediate import fix_one
    out = FIX.parent / "tmp" / "fixable_fixed_one.docx"
    ctx = AuditContext(source_name="fixable.docx",
                       heading_map={0: "Heading 1", 3: "Heading 2", 4: "Heading 2"})
    fr = fix_one(FIX / "fixable.docx", out, ctx)
    assert fr["status"] == "pass"
    assert fr["findings_before"] == 6
    assert fr["reaudit"]["summary"]["total"] == 0
    assert fr["remediation"]["ok"] is True
    # source untouched
    assert audit_file(FIX / "fixable.docx")["summary"]["total"] == 6


def test_fix_one_residual_manual_only_passes():
    """violations.docx: blocking findings (heading skip, table header) are fixable
    without a map; manual findings (multiple-h1, merged-cell) are moderate
    (non-blocking), so the doc still PASSES after fix."""
    from docx_a11y.remediate import fix_one
    out = FIX.parent / "tmp" / "viol_fixed_one.docx"
    fr = fix_one(FIX / "violations.docx", out)
    assert fr["status"] == "pass"
    assert fr["reaudit"]["summary"]["blocking"] == 0
    # manual findings remain but are non-blocking
    ids = {f["rule_id"] for f in fr["reaudit"]["findings"]}
    assert "multiple-h1" in ids and "merged-cell" in ids


def test_fix_one_unfixable_blocking_reports_fail():
    from docx_a11y.remediate import fix_one
    out = FIX.parent / "tmp" / "fixable_nomap_one.docx"
    # NO heading map -> headings-none (serious) cannot be fixed -> still blocking
    fr = fix_one(FIX / "fixable.docx", out)
    assert fr["status"] == "fail"
    assert fr["reaudit"]["summary"]["blocking"] >= 1
    assert any(f["rule_id"] == "headings-none" for f in fr["reaudit"]["findings"])


def test_fix_one_error_returns_error_status():
    from docx_a11y.remediate import fix_one
    fr = fix_one(FIX / "does-not-exist.docx", FIX.parent / "tmp" / "x.docx")
    assert fr["status"] == "error"
    assert fr["error"]


# ---------------------------------------------------------------------------
# fix_batch (directory mode)
# ---------------------------------------------------------------------------

def _make_batch_dir(tmp_path):
    d = tmp_path / "docs"
    d.mkdir()
    shutil.copy(FIX / "clean.docx", d / "a-clean.docx")
    shutil.copy(FIX / "fixable.docx", d / "b-fixable.docx")
    shutil.copy(FIX / "violations.docx", d / "c-violations.docx")
    (d / "lock~$temp.docx").write_bytes(b"junk")   # must be skipped
    (d / "notes.txt").write_text("not a docx")      # must be ignored
    return d


def test_fix_batch_processes_all_and_aggregates(tmp_path):
    from docx_a11y.remediate import fix_batch
    d = _make_batch_dir(tmp_path)
    ctx = AuditContext(source_name="",
                       heading_map={0: "Heading 1", 3: "Heading 2", 4: "Heading 2"})
    res = fix_batch(d, ctx)
    names = [e["file"] for e in res["entries"]]
    assert names == ["a-clean.docx", "b-fixable.docx", "c-violations.docx"]
    assert res["summary"]["total"] == 3
    # clean passes (0 findings); fixable passes with the map (6 findings all fixed);
    # violations passes WITHOUT needing the map — its blocking findings
    # (heading-level-skipped, table-header-missing) are fixable as-is, and the
    # manual findings (multiple-h1, merged-cell) are moderate (non-blocking).
    assert res["summary"]["pass"] == 3
    assert res["summary"]["fail"] == 0
    assert res["summary"]["error"] == 0
    # outputs all exist, sources untouched
    for e in res["entries"]:
        assert Path(e["output_path"]).exists()
    assert audit_file(FIX / "fixable.docx")["summary"]["total"] == 6


def test_fix_batch_exit_mapping(tmp_path):
    from docx_a11y.remediate import fix_batch
    d = _make_batch_dir(tmp_path)
    res = fix_batch(d)   # no heading map: b-fixable fails (headings-none unfixable, serious)
    assert res["summary"]["pass"] == 2   # a-clean (no findings) + c-violations (blockings fixable w/o map)
    assert res["summary"]["fail"] == 1   # b-fixable: headings-none still blocking after fix
    assert res["summary"]["error"] == 0


def test_fix_batch_error_exit_mapping(tmp_path):
    from docx_a11y.remediate import fix_batch
    d = tmp_path / "bad"
    d.mkdir()
    (d / "corrupt.docx").write_bytes(b"not a zip at all")
    res = fix_batch(d)
    assert res["summary"]["error"] == 1
    assert res["entries"][0]["status"] == "error"


def test_fix_batch_forwards_all_ctx_knobs(tmp_path):
    """Every ctx knob must reach the per-file audit, not just the ones
    previously hand-forwarded (language/background/heading_map).

    A document with NO default language in docDefaults is flagged by the
    language rule and the fix must write the ctx's default_language (fr-CA)
    — proving caller knobs are forwarded via dataclasses.replace instead of
    silently reset to the module default (en-US).
    """
    import zipfile
    from docx import Document
    from docx.oxml.ns import qn
    from docx_a11y.remediate import fix_batch

    d = tmp_path / "lang"
    d.mkdir()
    src = d / "lang.docx"
    doc = Document()
    doc.add_paragraph("doc with no default language")
    # strip w:lang from docDefaults in-memory so the rule flags it as missing
    for lang in doc.styles.element.iter(qn("w:lang")):
        lang.getparent().remove(lang)
    doc.save(str(src))

    ctx = AuditContext(source_name="",
                       default_language="fr-CA",
                       background_rgb="FFFFFF",
                       large_text_size_pt=1.0,
                       large_text_bold_pt=2.0)
    res = fix_batch(d, ctx)
    e = res["entries"][0]
    assert e["status"] != "error"
    # the language rule flagged the missing default and the fix ran
    assert e["remediation"] is not None
    assert any(a[0] == "LanguageMissing" for a in e["remediation"]["applied"])
    # the fix must have written fr-CA (not the en-US module default)
    z = zipfile.ZipFile(e["output_path"])
    styles = z.read("word/styles.xml").decode()
    assert 'w:val="fr-CA"' in styles


def test_fix_batch_non_dir_raises(tmp_path):
    from docx_a11y.remediate import fix_batch
    with pytest.raises(NotADirectoryError):
        fix_batch(tmp_path / "no-such-dir")


def test_fix_batch_skips_own_outputs(tmp_path):
    """Running fix_batch twice in the same dir must not re-process the
    .fixed.docx outputs from the first run."""
    from docx_a11y.remediate import fix_batch
    d = _make_batch_dir(tmp_path)
    first = fix_batch(d)
    assert first["summary"]["total"] == 3
    second = fix_batch(d)
    assert second["summary"]["total"] == 3
    assert [e["file"] for e in second["entries"]] == \
        [e["file"] for e in first["entries"]]


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


# ---------------------------------------------------------------------------
# CLI: fix
# ---------------------------------------------------------------------------

def test_cli_fix_single_file_pass(capsys, tmp_path):
    out = tmp_path / "fixable.fixed.docx"
    rc = main(["fix", str(FIX / "fixable.docx"), "--out", str(out),
               "--heading-map", "0=Heading 1,3=Heading 2,4=Heading 2"])
    assert rc == 0
    out_text = capsys.readouterr().out
    assert "6 -> 0" in out_text          # "6 findings before, 0 after"
    assert "PASS" in out_text
    assert out.exists()


def test_cli_fix_single_file_fail(capsys, tmp_path):
    rc = main(["fix", str(FIX / "fixable.docx"),
               "--out", str(tmp_path / "x.docx")])   # no heading map
    assert rc == 1
    out_text = capsys.readouterr().out
    assert "FAIL" in out_text
    assert "headings-none" in out_text


def test_cli_fix_missing_file_exit_2(capsys):
    rc = main(["fix", str(Path(FIX) / "nope.docx")])
    assert rc == 2
    assert "error" in capsys.readouterr().err


def test_cli_fix_writes_json_and_report(capsys, tmp_path):
    j, r = tmp_path / "f.json", tmp_path / "f.md"
    rc = main(["fix", str(FIX / "fixable.docx"),
               "--out", str(tmp_path / "x.docx"),
               "--heading-map", "0=Heading 1,3=Heading 2,4=Heading 2",
               "--json", str(j), "--report", str(r)])
    assert rc == 0
    capsys.readouterr()
    data = json.loads(j.read_text())
    assert data["status"] == "pass"
    assert data["findings_before"] == 6
    md = r.read_text()
    assert "Remediation" in md            # report includes applied/skipped
    assert "Re-verify" in md


# ---------------------------------------------------------------------------
# CLI: batch
# ---------------------------------------------------------------------------

def test_cli_fix_batch_exit_0_all_pass(capsys, tmp_path):
    d = _make_batch_dir(tmp_path)
    rc = main(["fix", "--batch", str(d),
               "--heading-map", "0=Heading 1,3=Heading 2,4=Heading 2"])
    # all three pass with the map (b-fixable fixable; c-violations manual-only blockings fixed)
    assert rc == 0
    out_text = capsys.readouterr().out
    assert "3 file(s)" in out_text
    assert "PASS" in out_text


def test_cli_fix_batch_exit_1_partial_fail(capsys, tmp_path):
    d = _make_batch_dir(tmp_path)
    rc = main(["fix", "--batch", str(d)])   # no map -> b-fixable fails
    assert rc == 1
    out_text = capsys.readouterr().out
    assert "[FAIL]" in out_text and "b-fixable.docx" in out_text
    assert "1 file(s) failed" in out_text or "failed: 1" in out_text  # match final wording


def test_cli_fix_batch_json(capsys, tmp_path):
    d = _make_batch_dir(tmp_path)
    j = tmp_path / "batch.json"
    rc = main(["fix", "--batch", str(d),
               "--heading-map", "0=Heading 1,3=Heading 2,4=Heading 2",
               "--json", str(j)])
    assert rc == 0
    capsys.readouterr()
    data = json.loads(j.read_text())
    assert data["summary"]["total"] == 3
    assert all(e["status"] == "pass" for e in data["entries"])


def test_cli_fix_batch_bad_dir_exit_2(capsys, tmp_path):
    rc = main(["fix", "--batch", str(tmp_path / "no-such-dir")])
    assert rc == 2


def test_cli_audit_batch(capsys, tmp_path):
    d = _make_batch_dir(tmp_path)
    rc = main(["audit", "--batch", str(d)])
    assert rc == 1   # at least one doc fails its audit
    out_text = capsys.readouterr().out
    assert "3 file(s)" in out_text
    assert "[PASS] a-clean.docx" in out_text


# ---------------------------------------------------------------------------
# CLI: rules
# ---------------------------------------------------------------------------

def test_cli_rules(capsys):
    rc = main(["rules"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "image-alt-missing" in out
    assert "title-missing" in out
