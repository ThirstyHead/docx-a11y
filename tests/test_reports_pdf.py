"""Tests for accessible tagged PDF report generator."""
from pathlib import Path
import pikepdf
from docx_a11y.reports.html import render_html
from docx_a11y.reports.pdf import render_pdf


def test_pdf_generation_and_tags(tmp_path: Path):
    md = (
        "# Accessibility Audit Report: doc.docx\n\n"
        "## Executive Summary\n\n"
        "> Summary text.\n\n"
        "## 1. Perceivable\n\n"
        "### 1. [CRITICAL] Image missing alt\n\n"
        "Detailed explanation.\n"
    )
    html = render_html(md, theme="print")
    pdf_out = tmp_path / "test_report.pdf"
    res_path = render_pdf(html, out_path=pdf_out, lang="en", title="Accessibility Audit Report")

    assert res_path.exists()
    assert res_path.stat().st_size > 500

    with pikepdf.open(pdf_out) as pdf:
        assert len(pdf.pages) >= 1
        assert str(pdf.Root.Lang) == "en"
        assert pdf.Root[pikepdf.Name("/MarkInfo")][pikepdf.Name("/Marked")] == pikepdf.Boolean(True)
        with pdf.open_metadata() as meta:
            assert meta["dc:title"] == "Accessibility Audit Report"
            assert "docx-a11y" in meta["pdf:Producer"]
