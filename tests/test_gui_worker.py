"""Tests for BatchWorker thread execution and Qt signals."""
from pathlib import Path
from docx_a11y.gui.models import BatchItem
from docx_a11y.gui.worker import BatchWorker

FIXTURES = Path(__file__).parent / "fixtures"


def test_batch_worker_execution(qtbot, tmp_path: Path):
    fixture_path = FIXTURES / "clean.docx"
    item = BatchItem(path=fixture_path)

    worker = BatchWorker(
        items=[item],
        out_dir=tmp_path,
        formats=["md", "json"],
        theme="ocean",
        auto_fix=False,
    )

    started_signals = []
    finished_signals = []
    completed_signals = []

    worker.item_started.connect(lambda idx, tot, name: started_signals.append((idx, tot, name)))
    worker.item_finished.connect(lambda idx, st, cnt, sc: finished_signals.append((idx, st, cnt, sc)))
    worker.all_completed.connect(lambda tot, err: completed_signals.append((tot, err)))

    with qtbot.waitSignal(worker.all_completed, timeout=5000):
        worker.start()

    assert len(started_signals) == 1
    assert started_signals[0][2] == "clean.docx"

    assert len(finished_signals) == 1
    assert item.error_message is None
    assert finished_signals[0][1] == "Completed"

    assert len(completed_signals) == 1
    assert completed_signals[0] == (1, 0)

    # Check reports were written
    assert (tmp_path / "clean-a11y-report.md").exists()
    assert (tmp_path / "clean-audit.json").exists()


def test_batch_worker_all_formats_and_error(tmp_path: Path):
    fixture_clean = FIXTURES / "clean.docx"
    item1 = BatchItem(path=fixture_clean)
    item2 = BatchItem(path=tmp_path / "non_existent.docx")

    worker = BatchWorker(
        items=[item1, item2],
        out_dir=tmp_path,
        formats=["md", "html", "pdf", "json"],
        theme="ocean",
        auto_fix=True,
    )

    # Run directly in test process to ensure branch coverage
    worker.run()

    assert item1.status == "Completed"
    assert (tmp_path / "clean-a11y-report.pdf").exists()
    assert (tmp_path / "clean-a11y-report.html").exists()

    assert item2.status == "Failed"
    assert item2.error_message is not None


def test_batch_worker_cancellation(tmp_path: Path):
    fixture_clean = FIXTURES / "clean.docx"
    item1 = BatchItem(path=fixture_clean)
    worker = BatchWorker(items=[item1], out_dir=tmp_path, formats=["md"])
    worker.request_stop()
    worker.run()
    # When stop requested before loop, item remains Pending
    assert item1.status == "Pending"
