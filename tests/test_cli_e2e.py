"""End-to-end integration test exercising the full CLI across all report formats."""
import subprocess
import sys
from pathlib import Path
import pytest
from docx_a11y.cli import main

FIXTURES = Path(__file__).parent / "fixtures"


def test_cli_subprocess_multi_format(tmp_path: Path):
    cmd = [
        sys.executable,
        "-m",
        "docx_a11y.cli",
        str(FIXTURES / "clean.docx"),
        "--format",
        "md,html,pdf,json",
        "--output-dir",
        str(tmp_path),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0, f"CLI failed: {res.stderr}"

    assert (tmp_path / "clean-a11y-report.md").exists()
    assert (tmp_path / "clean-a11y-report.html").exists()
    assert (tmp_path / "clean-a11y-report.pdf").exists()
    assert (tmp_path / "clean-audit.json").exists()


def test_cli_direct_invocation(tmp_path: Path, monkeypatch):
    args = [
        "docx-a11y",
        str(FIXTURES / "violations.docx"),
        "--fix",
        "--format",
        "md,html,pdf,json",
        "--output-dir",
        str(tmp_path),
    ]
    monkeypatch.setattr(sys, "argv", args)
    with pytest.raises(SystemExit) as excinfo:
        main()
    assert excinfo.value.code == 0

    assert (tmp_path / "violations-remediated.docx").exists()
    assert (tmp_path / "violations-a11y-report.md").exists()
    assert (tmp_path / "violations-a11y-report.html").exists()
    assert (tmp_path / "violations-a11y-report.pdf").exists()

    md_content = (tmp_path / "violations-a11y-report.md").read_text(encoding="utf-8")
    assert "Remediation Progress" in md_content


def test_cli_triage_invocation(tmp_path: Path, monkeypatch):
    args = [
        "docx-a11y",
        str(FIXTURES / "violations.docx"),
        "--triage",
        "--format",
        "md,json",
        "--output-dir",
        str(tmp_path),
    ]
    monkeypatch.setattr(sys, "argv", args)
    # Mock builtins.input to skip prompts
    monkeypatch.setattr("builtins.input", lambda prompt: "s")
    with pytest.raises(SystemExit):
        main()

    assert (tmp_path / "violations-triaged.docx").exists()
    assert (tmp_path / "violations-triaged-a11y-report.md").exists()
