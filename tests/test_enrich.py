"""Tests for wcag-mcp report enrichment (offline cache + live stdio path)."""
import json
from pathlib import Path

import pytest

from docx_a11y.audit import audit_file
from docx_a11y.cli import main
from docx_a11y.enrich import (BUNDLED_CACHE, Cache, build_enrichment,
                              find_server, get_criterion_text,
                              parse_criterion)
from docx_a11y.report import render_report

FIX = Path(__file__).resolve().parent / "fixtures"
ALL_SCS = ["1.1.1", "1.3.1", "1.4.3", "2.4.2", "3.1.1"]


# ---------------------------------------------------------------------------
# bundled cache
# ---------------------------------------------------------------------------

def test_bundled_cache_present_with_all_scs():
    assert BUNDLED_CACHE.exists()
    data = json.loads(BUNDLED_CACHE.read_text())
    for sc in ALL_SCS:
        assert sc in data, f"missing {sc} in bundled cache"
        assert len(data[sc]) > 500, f"cache entry {sc} suspiciously short"
        assert data[sc].startswith(f"# {sc} ")


def test_get_criterion_text_offline():
    for sc in ALL_SCS:
        t = get_criterion_text(sc, live=False)
        assert t and t.startswith(f"# {sc} ")


def test_get_criterion_text_unknown_sc():
    assert get_criterion_text("9.9.9", live=False) is None


def test_parse_criterion_fields():
    p = parse_criterion(get_criterion_text("1.1.1", live=False))
    assert p["num"] == "1.1.1"
    assert p["handle"] == "Non-text Content"
    assert p["level"] == "A"
    assert "Perceivable" in p["principle"]
    assert "Text Alternatives" in p["guideline"]
    assert p["in_brief"]
    assert p["description"]
    assert p["intent"]


def test_parse_criterion_handles_2_4_2_convention():
    p = parse_criterion(get_criterion_text("2.4.2", live=False))
    assert p["num"] == "2.4.2"
    assert p["level"] == "A"


def test_parse_criterion_empty():
    p = parse_criterion("")
    assert p["num"] == ""
    assert p["raw_len"] == 0


# ---------------------------------------------------------------------------
# build_enrichment
# ---------------------------------------------------------------------------

def test_build_enrichment_offline():
    res = audit_file(FIX / "fixable.docx")
    enrichment, source = build_enrichment(res, live=False)
    assert source == "bundled sc_cache.json (offline)"
    # fixable.docx findings touch: 1.1.1, 1.3.1, 1.4.3, 2.4.2, 3.1.1
    assert set(enrichment.keys()) == {"1.1.1", "1.3.1", "1.4.3", "2.4.2", "3.1.1"}
    assert enrichment["1.4.3"]["level"] == "AA"


def test_build_enrichment_clean_doc_is_empty():
    res = audit_file(FIX / "clean.docx")
    enrichment, _ = build_enrichment(res, live=False)
    assert enrichment == {}


def test_enrichment_deterministic():
    res = audit_file(FIX / "no-knead-bread.docx")
    e1, _ = build_enrichment(res, live=False)
    e2, _ = build_enrichment(res, live=False)
    assert e1 == e2


# ---------------------------------------------------------------------------
# report rendering with enrichment
# ---------------------------------------------------------------------------

def test_report_includes_normative_blocks():
    res = audit_file(FIX / "no-knead-bread.docx")
    enrichment, source = build_enrichment(res, live=False)
    md = render_report(res, source_path="no-knead-bread.docx",
                       enrichment=enrichment, enrichment_source=source)
    assert "**Normative text source:** bundled sc_cache.json (offline)" in md
    # each distinct SC present gets a details block
    assert md.count("<details><summary>Normative text") == 4
    assert "Normative text — SC 1.1.1" in md
    assert "Normative text — SC 1.4.3" in md
    # normative content present
    assert "All non-text content that is presented to the user" in md
    # blocks are closed
    assert md.count("</details>") == 4


def test_report_without_enrichment_has_no_blocks():
    res = audit_file(FIX / "no-knead-bread.docx")
    md = render_report(res, source_path="no-knead-bread.docx")
    assert "<details>" not in md
    assert "Normative text source" not in md


def test_report_deterministic_with_enrichment():
    res = audit_file(FIX / "violations.docx")
    enrichment, source = build_enrichment(res, live=False)
    kw = dict(source_path="violations.docx", enrichment=enrichment,
              enrichment_source=source)
    assert render_report(res, **kw) == render_report(res, **kw)


# ---------------------------------------------------------------------------
# live stdio path (integration; skipped when server not installed)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(find_server() is None,
                    reason="wcag-guidelines-mcp not installed locally")
def test_live_fetch_matches_cache_shape():
    text = get_criterion_text("1.1.1", live=True)
    assert text is not None
    assert text.startswith("# 1.1.1 Non-text Content")
    p = parse_criterion(text)
    assert p["level"] == "A"
    assert p["description"]


@pytest.mark.skipif(find_server() is None,
                    reason="wcag-guidelines-mcp not installed locally")
def test_build_enrichment_live():
    res = audit_file(FIX / "fixable.docx")
    enrichment, source = build_enrichment(res, live=True)
    assert "live stdio" in source
    assert "1.1.1" in enrichment
    assert enrichment["1.1.1"]["handle"] == "Non-text Content"


# ---------------------------------------------------------------------------
# CLI integration
# ---------------------------------------------------------------------------

def test_cli_report_with_enrichment(tmp_path, capsys):
    r = tmp_path / "a.md"
    rc = main(["audit", str(FIX / "no-knead-bread.docx"), "--report", str(r)])
    assert rc == 1  # fails on violations but report still written
    out = capsys.readouterr().out
    assert "normative text: bundled sc_cache.json (offline)" in out
    md = r.read_text()
    assert "Normative text — SC 1.1.1" in md