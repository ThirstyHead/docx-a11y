"""Tests for the unified CLI twin interface matching pptx-a11y."""
from pathlib import Path
import pytest
from docx_a11y.cli import main

FIX = Path(__file__).resolve().parent / "fixtures"


def test_cli_audit_clean(tmp_path: Path):
    rc = main([str(FIX / "clean.docx"), "--output-dir", str(tmp_path)])
    assert rc == 0


def test_cli_audit_violations(tmp_path: Path):
    rc = main([str(FIX / "violations.docx"), "--output-dir", str(tmp_path)])
    assert rc == 1


def test_cli_missing_file():
    rc = main(["non_existent_file.docx"])
    assert rc == 2


def test_cli_formats_and_reports(tmp_path: Path, capsys):
    out_dir = tmp_path / "reports"
    rc = main([
        str(FIX / "clean.docx"),
        "--format", "md,html,pdf,json",
        "--theme", "ocean",
        "--output-dir", str(out_dir),
    ])
    assert rc == 0
    assert (out_dir / "clean-a11y-report.md").exists()
    assert (out_dir / "clean-a11y-report.html").exists()
    assert (out_dir / "clean-a11y-report.pdf").exists()
    assert (out_dir / "clean-audit.json").exists()


def test_cli_fix_and_integrity(tmp_path: Path, capsys):
    out_dir = tmp_path / "reports"
    fixed_docx = tmp_path / "remediated.docx"
    rc = main([
        str(FIX / "fixable.docx"),
        "--fix",
        "--out-docx", str(fixed_docx),
        "--format", "md,html",
        "--output-dir", str(out_dir),
        "--theme", "forest",
    ])
    captured = capsys.readouterr()
    assert "[Integrity Verified]" in captured.out
    assert fixed_docx.exists()
    assert (out_dir / "fixable-a11y-report.md").exists()
    assert (out_dir / "fixable-a11y-report.html").exists()


def test_cli_rejects_overwriting_input(tmp_path: Path):
    rc = main([
        str(FIX / "clean.docx"),
        "--fix",
        "--out-docx", str(FIX / "clean.docx"),
    ])
    assert rc == 2
