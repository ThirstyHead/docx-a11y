"""Tests for GUI batch queue and models."""
from pathlib import Path
from docx_a11y.gui.models import BatchItem, BatchQueue


def test_batch_item_creation(tmp_path: Path):
    p = tmp_path / "document.docx"
    p.touch()
    item = BatchItem(path=p)
    assert item.path == p
    assert item.status == "Pending"
    assert item.paragraph_count == 0
    assert item.findings_count == 0


def test_batch_queue_add_and_deduplicate(tmp_path: Path):
    p1 = tmp_path / "doc1.docx"
    p2 = tmp_path / "doc2.docx"
    p1.touch()
    p2.touch()

    queue = BatchQueue()
    assert queue.add_file(p1) is not None
    assert len(queue) == 1

    # Adding duplicate should return None and not increase count
    assert queue.add_file(p1) is None
    assert len(queue) == 1

    # Adding non-docx file should return None
    txt = tmp_path / "notes.txt"
    txt.touch()
    assert queue.add_file(txt) is None
    assert len(queue) == 1

    assert queue.add_file(p2) is not None
    assert len(queue) == 2


def test_batch_queue_add_directory(tmp_path: Path):
    sub = tmp_path / "documents"
    sub.mkdir()
    (sub / "a.docx").touch()
    (sub / "b.docx").touch()
    (sub / "~$lock.docx").touch()  # Lock file should be skipped
    (sub / "report.pdf").touch()

    queue = BatchQueue()
    added = queue.add_directory(sub)
    assert added == 2
    assert len(queue) == 2

    # Clear queue
    queue.clear()
    assert len(queue) == 0
