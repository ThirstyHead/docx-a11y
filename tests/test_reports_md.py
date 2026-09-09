"""Tests for Markdown report engine adhering to WCAG 2.1 & Social Model."""
import pytest
from docx_a11y.reports.md import render_md
from docx_a11y.reports.tone import assert_social_model_language


def test_social_model_language_guard():
    with pytest.raises(ValueError, match="Prohibited language detected"):
        assert_social_model_language("Screen reader users suffer from missing titles.")

    assert_social_model_language(
        "The document lacks a title, preventing screen reader users from navigating by landmark."
    )


def test_markdown_pour_structure():
    sample_audit = {
        "file": "doc.docx",
        "audited_at": "2026-09-08T12:00:00Z",
        "tool": "docx-a11y/0.2.0",
        "sha256": "abcdef1234567890",
        "summary": {
            "total": 1,
            "blocking": 1,
            "pass": False,
            "by_severity": {"critical": 1, "serious": 0, "moderate": 0, "minor": 0},
        },
        "findings": [
            {
                "rule_id": "image-alt-missing",
                "sc": "1.1.1",
                "severity": "critical",
                "location": "paragraph[2]",
                "description": "Image has no alt text.",
                "evidence": "drawing",
                "fixable": False,
                "fix": "Add alt text.",
            }
        ],
    }
    md = render_md(sample_audit)
    assert "## 1. Perceivable" in md
    assert "## 2. Operable" in md
    assert "## 3. Understandable" in md
    assert "## 4. Robust" in md
    assert "https://www.w3.org/WAI/WCAG21/Understanding/non-text-content.html" in md
    assert "Who Benefits:" in md
    assert "Barrier Detected:" in md
    assert "Immutable (original document is strictly read-only" in md
    assert "abcdef1234567890" in md


def test_markdown_remediation_progress():
    before = {
        "file": "doc.docx",
        "sha256": "1111222233334444",
        "summary": {"total": 4, "blocking": 2, "pass": False},
        "findings": [],
    }
    after = {
        "file": "doc.docx",
        "summary": {"total": 2, "blocking": 0, "pass": True},
        "findings": [],
    }
    md = render_md(before, after_result=after)
    assert "Remediation Progress:" in md
    assert "Resolved **2** of **2** blocking accessibility barriers" in md
    assert "100.0% improvement" in md
    assert "1111222233334444" in md


def test_word_assistant_discrepancy_notes():
    audit_data = {
        "file": "test-sample.docx",
        "audited_at": "2026-09-08T12:00:00Z",
        "sha256": "abcdef123456",
        "summary": {"total": 3, "blocking": 2, "pass": False},
        "findings": [
            {
                "rule_id": "headings-none",
                "sc": "1.3.1",
                "severity": "serious",
                "location": "document body",
                "description": "No headings.",
                "evidence": "0 headings",
                "fixable": False,
                "fix": "Add headings.",
            },
            {
                "rule_id": "table-header-missing",
                "sc": "1.3.1",
                "severity": "serious",
                "location": "table[0]",
                "description": "Missing header.",
                "evidence": "0 tblHeader",
                "fixable": True,
                "fix": "Add tblHeader.",
            },
            {
                "rule_id": "merged-cell",
                "sc": "1.3.1",
                "severity": "moderate",
                "location": "table[0] row[1] cell[0]",
                "description": "Merged cell.",
                "evidence": "vMerge",
                "fixable": False,
                "fix": "Unmerge.",
            },
        ],
    }
    md = render_md(audit_data)
    assert "- **Word Accessibility Assistant Note:** Microsoft Word's built-in Accessibility Assistant suppresses the 'No headings in document' warning" in md
    assert "- **Word Accessibility Assistant Note:** Microsoft Word's built-in Accessibility Assistant primarily inspects table header repetition across page breaks" in md
    assert "- **Word Accessibility Assistant Note:** Microsoft Word's built-in Accessibility Assistant checks for split cells or nested tables but routinely overlooks" in md

