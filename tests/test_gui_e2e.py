"""End-to-end integration test for GUI batch processing workflow."""
from pathlib import Path
from docx_a11y.gui.main_window import MainWindow

FIXTURES = Path(__file__).parent / "fixtures"


def test_gui_batch_e2e_processing(qtbot, tmp_path: Path):
    win = MainWindow()
    qtbot.addWidget(win)

    # Configure output directory
    win.txt_out_dir.setText(str(tmp_path))

    # Add two documents
    clean_p = FIXTURES / "clean.docx"
    viol_p = FIXTURES / "violations.docx"
    win.add_file_paths([clean_p, viol_p])

    assert win.table.rowCount() == 2
    assert win.btn_start.isEnabled() is True

    # Configure formats: md, html, json (skip pdf in fast e2e to keep test snappy)
    win.chk_md.setChecked(True)
    win.chk_html.setChecked(True)
    win.chk_pdf.setChecked(False)
    win.chk_json.setChecked(True)
    win.cmb_theme.setCurrentText("ocean")
    win.chk_autofix.setChecked(True)

    # Trigger processing and block until worker signals completion
    win.start_processing()
    assert win.worker is not None

    with qtbot.waitSignal(win.worker.all_completed, timeout=10000):
        pass

    # Verify queue states
    item_clean = win.queue.items[0]
    item_viol = win.queue.items[1]

    assert item_clean.status == "Completed"
    assert item_viol.status == "Completed"
    assert item_clean.score is not None and item_clean.score >= 90.0

    # Verify files generated on disk
    assert (tmp_path / "clean-a11y-report.md").exists()
    assert (tmp_path / "clean-a11y-report.html").exists()
    assert (tmp_path / "clean-audit.json").exists()
    assert (tmp_path / "clean-remediated.docx").exists()

    assert (tmp_path / "violations-a11y-report.md").exists()
    assert (tmp_path / "violations-a11y-report.html").exists()
    assert (tmp_path / "violations-audit.json").exists()
    assert (tmp_path / "violations-remediated.docx").exists()

    # Verify UI table updated
    item0_status = win.table.item(0, 2)
    item1_status = win.table.item(1, 2)
    assert item0_status is not None and item0_status.text() == "Completed"
    assert item1_status is not None and item1_status.text() == "Completed"
    assert win.btn_start.isEnabled() is True
    assert win.btn_stop.isEnabled() is False
