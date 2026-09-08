"""Tests for interactive CLI triage mode."""
import shutil
from pathlib import Path
from docx_a11y.audit import audit_file
from docx_a11y.triage import run_interactive_triage

FIXTURES = Path(__file__).parent / "fixtures"


def test_interactive_triage_sets_alt_text_and_titles(tmp_path: Path):
    in_doc = tmp_path / "triage_input.docx"
    shutil.copyfile(FIXTURES / "fixable.docx", in_doc)
    out_doc = tmp_path / "triage_output.docx"

    # Simulate user answering alt text and title prompts
    inputs = [
        "Company sales chart showing steady Q3 increase",  # for image-alt-missing
        "Quarterly Performance Report",                     # for title-missing
    ]
    logs = []

    def mock_input(prompt):
        return inputs.pop(0)

    def mock_print(*args):
        logs.append(" ".join(str(a) for a in args))

    count = run_interactive_triage(
        in_path=in_doc,
        out_path=out_doc,
        input_func=mock_input,
        print_func=mock_print,
    )

    assert count == 2
    assert out_doc.exists()

    # Re-audit: image-alt-missing and title-missing should now be resolved
    res = audit_file(out_doc)
    rule_ids = {f["rule_id"] for f in res["findings"]}
    assert "image-alt-missing" not in rule_ids
    assert "title-missing" not in rule_ids


def test_interactive_triage_marks_decorative(tmp_path: Path):
    in_doc = tmp_path / "triage_dec_input.docx"
    shutil.copyfile(FIXTURES / "fixable.docx", in_doc)
    out_doc = tmp_path / "triage_dec_output.docx"

    inputs = [
        "d",  # mark image decorative
        "s",  # skip title
    ]

    count = run_interactive_triage(
        in_path=in_doc,
        out_path=out_doc,
        input_func=lambda p: inputs.pop(0),
        print_func=lambda *a: None,
    )

    assert count == 1
    res = audit_file(out_doc)
    rule_ids = {f["rule_id"] for f in res["findings"]}
    assert "image-alt-missing" not in rule_ids
    assert "title-missing" in rule_ids
