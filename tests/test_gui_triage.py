"""Tests for GUI interactive TriageDialog."""
import shutil
from pathlib import Path
from docx_a11y.audit import audit_file
from docx_a11y.gui.triage_dialog import TriageDialog

FIXTURES = Path(__file__).parent / "fixtures"


def test_triage_dialog_flow(qtbot, tmp_path: Path):
    doc_path = tmp_path / "test_triage.docx"
    shutil.copyfile(FIXTURES / "fixable.docx", doc_path)

    audit_res = audit_file(doc_path)
    findings = [
        f for f in audit_res["findings"]
        if f["rule_id"] in ("image-alt-missing", "title-missing")
    ]
    assert len(findings) >= 2

    dialog = TriageDialog(doc_path, findings)
    qtbot.addWidget(dialog)

    # 1. Provide alt text for image
    dialog.txt_input.setText("Quarterly sales chart diagram")
    dialog.apply_current()

    # 2. Provide document title
    dialog.txt_input.setText("Company Financial Report 2026")
    dialog.apply_current()

    # Re-audit: image-alt-missing and title-missing should be resolved
    res2 = audit_file(doc_path)
    rule_ids = {f["rule_id"] for f in res2["findings"]}
    assert "image-alt-missing" not in rule_ids
    assert "title-missing" not in rule_ids


def test_triage_dialog_decorative_and_skip(qtbot, tmp_path: Path):
    doc_path = tmp_path / "test_triage2.docx"
    shutil.copyfile(FIXTURES / "fixable.docx", doc_path)

    audit_res = audit_file(doc_path)
    findings = audit_res["findings"]

    dialog = TriageDialog(doc_path, findings)
    qtbot.addWidget(dialog)

    # Test toggling decorative for image
    dialog.chk_decorative.setChecked(True)
    assert dialog.txt_input.isEnabled() is False
    dialog.apply_current()

    # Test skip for title
    dialog.skip_current()

    res2 = audit_file(doc_path)
    rule_ids = {f["rule_id"] for f in res2["findings"]}
    assert "image-alt-missing" not in rule_ids
    assert "title-missing" in rule_ids
