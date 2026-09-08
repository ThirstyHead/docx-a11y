"""Tests for document immutability and SHA-256 integrity verification."""
import hashlib
from pathlib import Path
import pytest
from docx_a11y.audit import audit_file
from docx_a11y.remediate import fix_one, remediate_document, remediate

FIX = Path(__file__).resolve().parent / "fixtures"


def test_audit_file_includes_sha256():
    res = audit_file(FIX / "fixable.docx")
    assert "sha256" in res
    assert len(res["sha256"]) == 64
    expected_sha = hashlib.sha256((FIX / "fixable.docx").read_bytes()).hexdigest()
    assert res["sha256"] == expected_sha


def test_remediate_rejects_in_place_overwrite():
    with pytest.raises(ValueError, match="strictly guarantees that original files remain untouched"):
        remediate(FIX / "fixable.docx", FIX / "fixable.docx", FIX / "fixable.docx")


def test_remediate_document_rejects_in_place_overwrite():
    with pytest.raises(ValueError, match="strictly guarantees that original files remain untouched"):
        remediate_document(FIX / "fixable.docx", FIX / "fixable.docx")


def test_fix_one_rejects_same_output():
    res = fix_one(FIX / "fixable.docx", out_path=FIX / "fixable.docx")
    assert res["status"] == "error"
    assert "source must remain immutable" in res["error"]


def test_input_file_integrity_preserved(tmp_path: Path):
    # Copy fixture to tmp_path to test
    src = tmp_path / "target.docx"
    src.write_bytes((FIX / "fixable.docx").read_bytes())
    sha_before = hashlib.sha256(src.read_bytes()).hexdigest()

    out = tmp_path / "target-remediated.docx"
    res = remediate_document(src, out)

    sha_after = hashlib.sha256(src.read_bytes()).hexdigest()
    assert sha_before == sha_after, "Original document was modified!"
    assert res["original_sha256"] == sha_before
    assert res["original_file_immutable"] is True
    assert out.exists()
