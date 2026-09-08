"""Verify that example documents demonstrate 'before' and 'after' states."""
from pathlib import Path
from docx_a11y.audit import audit_file

EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "examples"


def test_example_after_clean_document():
    """Verify that 'No Knead Bread.docx' represents what good looks like (0 barriers)."""
    clean_path = EXAMPLES_DIR / "No Knead Bread.docx"
    assert clean_path.exists(), "examples/No Knead Bread.docx must exist"
    
    result = audit_file(clean_path)
    assert result["summary"]["total"] == 0
    assert result["summary"]["blocking"] == 0
    assert result["summary"]["pass"] is True
    assert len(result["findings"]) == 0


def test_example_before_test_document_contains_all_barriers():
    """Verify that 'No Knead Bread-test.docx' contains each core accessibility barrier."""
    test_path = EXAMPLES_DIR / "No Knead Bread-test.docx"
    assert test_path.exists(), "examples/No Knead Bread-test.docx must exist"
    
    result = audit_file(test_path)
    assert result["summary"]["pass"] is False
    assert result["summary"]["total"] >= 8
    
    rule_ids = {f["rule_id"] for f in result["findings"]}
    expected_rules = {
        "image-alt-missing",
        "heading-level-skipped",
        "multiple-h1",
        "table-header-missing",
        "merged-cell",
        "title-missing",
        "language-missing",
        "color-contrast",
    }
    missing_rules = expected_rules - rule_ids
    assert not missing_rules, f"Missing expected barrier rules in test document: {missing_rules}"
