"""Tests for GUI MainWindow layout, table binding, and controls."""
from pathlib import Path
from PySide6.QtCore import Qt
from docx_a11y.gui.main_window import MainWindow

FIXTURES = Path(__file__).parent / "fixtures"


def test_main_window_initial_state(qtbot):
    win = MainWindow()
    qtbot.addWidget(win)

    assert win.windowTitle() == "docx-a11y: Word WCAG Accessibility Remediation"
    assert win.table.columnCount() == 5
    assert win.table.rowCount() == 0
    assert win.btn_start.isEnabled() is False
    assert win.btn_stop.isEnabled() is False


def test_main_window_add_files_and_clear(qtbot):
    win = MainWindow()
    qtbot.addWidget(win)

    win.add_file_paths([FIXTURES / "clean.docx", FIXTURES / "violations.docx"])
    assert win.table.rowCount() == 2
    assert win.btn_start.isEnabled() is True

    # Clear table
    win.clear_files()
    assert win.table.rowCount() == 0
    assert win.btn_start.isEnabled() is False


def test_main_window_worker_callbacks(qtbot, tmp_path: Path):
    win = MainWindow()
    qtbot.addWidget(win)

    win.add_file_paths([FIXTURES / "clean.docx"])
    win._on_item_started(0, 1, "clean.docx")
    assert "clean.docx" in win.lbl_status.text()

    win._on_item_progress(0, "Analyzing paragraphs...")
    assert "Analyzing paragraphs" in win.lbl_status.text()

    win._on_item_finished(0, "Completed", 0, 100.0)
    assert win.progress_bar.value() == 1

    win._on_all_completed(1, 0)
    assert "Completed" in win.lbl_status.text()


def test_main_window_two_pane_story_components(qtbot):
    win = MainWindow()
    qtbot.addWidget(win)

    # Before pane
    assert hasattr(win, "pane_before")
    assert win.pane_before.objectName() == "pane_before"
    assert win.table_before == win.table

    # Center bridge
    assert hasattr(win, "center_bridge")
    assert win.center_bridge.objectName() == "center_bridge"
    assert hasattr(win, "btn_remediate_bridge")
    assert win.btn_start == win.btn_remediate_bridge

    # After pane
    assert hasattr(win, "pane_after")
    assert win.pane_after.objectName() == "pane_after"
    assert hasattr(win, "tree_after")
    assert hasattr(win, "btn_open_output_folder")
    assert hasattr(win, "btn_view_report")
    assert hasattr(win, "guide_banner")


def test_main_window_after_tree_population_and_view(qtbot, tmp_path: Path):
    win = MainWindow()
    qtbot.addWidget(win)

    win.txt_out_dir.setText(str(tmp_path))

    # Create dummy output files
    fixed_docx = tmp_path / "clean.fixed.docx"
    fixed_docx.write_text("dummy fixed docx content", encoding="utf-8")
    md_report = tmp_path / "clean-a11y-report.md"
    md_report.write_text("# Clean Report\nScore: 100%", encoding="utf-8")

    from docx_a11y.gui.models import BatchItem
    item = BatchItem(path=FIXTURES / "clean.docx")
    item.score = 100.0
    item.status = "Remediated"

    win._populate_after_tree_for_item(item)

    assert win.tree_after.topLevelItemCount() == 1
    doc_node = win.tree_after.topLevelItem(0)
    assert doc_node is not None
    assert "clean.docx" in doc_node.text(0)

    # Children: fixed docx and md report
    assert doc_node.childCount() == 2
    child_texts = [c.text(0) for i in range(doc_node.childCount()) if (c := doc_node.child(i)) is not None]
    assert any("Fixed DOCX" in t for t in child_texts)
    assert any("Audit Report" in t for t in child_texts)

