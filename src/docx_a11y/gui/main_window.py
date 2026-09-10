"""Main dashboard window for docx-a11y desktop application with Before/After storytelling."""
import os
from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)
from engine_a11y.gui import ReportViewerDialog
from engine_a11y.gui.theme import APP_STYLESHEET

from ..audit import audit_file
from ..reports.theme import available_themes
from .models import BatchItem, BatchQueue
from .triage_dialog import TriageDialog
from .worker import BatchWorker


class MainWindow(QMainWindow):
    """Main dashboard featuring Before/After storytelling remediation for Word documents."""

    worker_completed_signal = Signal(int, int)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("docx-a11y: Word WCAG Accessibility Remediation")
        self.resize(1080, 720)
        self.setStyleSheet(APP_STYLESHEET)
        self.setAcceptDrops(True)

        self.queue = BatchQueue()
        self.worker: Optional[BatchWorker] = None

        self._init_ui()

    def _init_ui(self):
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(14, 14, 14, 14)

        # 1. Non-Technical Guide Banner
        self.guide_banner = QLabel(
            "💡 <b>How it works:</b> "
            "1. Add Word documents on the left (<b>Before</b>)  ➔  "
            "2. Click <b>Fix & Audit</b> in the center  ➔  "
            "3. Open your remediated documents and reports on the right (<b>After</b>). "
            "<i>Your original files are safe and never modified.</i>"
        )
        self.guide_banner.setObjectName("guide_banner")
        self.guide_banner.setWordWrap(True)
        main_layout.addWidget(self.guide_banner)

        # 2. Main Splitter: Before (Left) vs After (Right)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        # --- LEFT PANE: Before ---
        self.pane_before = QGroupBox("1. Before: Original Documents")
        self.pane_before.setObjectName("pane_before")
        before_layout = QVBoxLayout(self.pane_before)
        before_layout.setSpacing(8)

        before_sub = QLabel("Select Word (.docx) documents needing accessibility remediation. Original files remain safe and unmodified.")
        before_sub.setObjectName("pane_subtitle")
        before_sub.setWordWrap(True)
        before_layout.addWidget(before_sub)

        # Left Toolbar
        tb_layout = QHBoxLayout()
        self.btn_add_files = QPushButton("📄 Add Files...")
        self.btn_add_files.clicked.connect(self.select_files)
        self.btn_add_folder = QPushButton("📁 Add Folder...")
        self.btn_add_folder.clicked.connect(self.select_folder)
        self.btn_clear = QPushButton("🗑️ Clear")
        self.btn_clear.clicked.connect(self.clear_files)
        self.btn_triage = QPushButton("🔍 Triage")
        self.btn_triage.clicked.connect(self.open_triage)

        tb_layout.addWidget(self.btn_add_files)
        tb_layout.addWidget(self.btn_add_folder)
        tb_layout.addWidget(self.btn_clear)
        tb_layout.addWidget(self.btn_triage)
        before_layout.addLayout(tb_layout)

        # Before Table
        self.table_before = QTableWidget(0, 5)
        self.table_before.setHorizontalHeaderLabels(["File Name", "Paragraphs", "Status", "Findings", "Score"])
        h_header = self.table_before.horizontalHeader()
        h_header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        h_header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        h_header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        h_header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        h_header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table_before.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table_before.setAlternatingRowColors(True)
        before_layout.addWidget(self.table_before, stretch=1)

        # Backward compatibility alias
        self.table = self.table_before

        splitter.addWidget(self.pane_before)

        # --- CENTER BRIDGE: Fix & Audit Flow ---
        self.center_bridge = QFrame()
        self.center_bridge.setObjectName("center_bridge")
        self.center_bridge.setFixedWidth(190)
        bridge_layout = QVBoxLayout(self.center_bridge)
        bridge_layout.setContentsMargins(10, 20, 10, 20)
        bridge_layout.setSpacing(12)
        bridge_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        arrow_label = QLabel("➔")
        arrow_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        arrow_label.setStyleSheet("font-size: 26px; color: #64748b; font-weight: bold;")
        bridge_layout.addWidget(arrow_label)

        self.btn_remediate_bridge = QPushButton("✨ Fix & Audit ➔")
        self.btn_remediate_bridge.setObjectName("btn_remediate_primary")
        self.btn_remediate_bridge.setEnabled(False)
        self.btn_remediate_bridge.clicked.connect(self.start_processing)
        bridge_layout.addWidget(self.btn_remediate_bridge)

        # Backward compatibility alias
        self.btn_start = self.btn_remediate_bridge

        self.btn_stop = QPushButton("Cancel")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.stop_processing)
        bridge_layout.addWidget(self.btn_stop)

        self.chk_autofix = QCheckBox("Auto-fix barriers")
        self.chk_autofix.setChecked(True)
        self.chk_autofix.toggled.connect(self._update_start_button_text)
        bridge_layout.addWidget(self.chk_autofix)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        bridge_layout.addWidget(self.progress_bar)

        self.lbl_status = QLabel("Ready")
        self.lbl_status.setWordWrap(True)
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_status.setStyleSheet("font-size: 11px; color: #475569;")
        bridge_layout.addWidget(self.lbl_status)

        bridge_layout.addStretch()
        splitter.addWidget(self.center_bridge)

        # --- RIGHT PANE: After ---
        self.pane_after = QGroupBox("2. After: Remediated Files & Reports")
        self.pane_after.setObjectName("pane_after")
        after_layout = QVBoxLayout(self.pane_after)
        after_layout.setSpacing(8)

        after_sub = QLabel("Remediated documents and audit reports are saved to your output folder. Double-click any item to open.")
        after_sub.setObjectName("pane_subtitle")
        after_sub.setWordWrap(True)
        after_layout.addWidget(after_sub)

        # After Tree
        self.tree_after = QTreeWidget()
        self.tree_after.setHeaderLabels(["Generated Item", "Details"])
        tree_header = self.tree_after.header()
        tree_header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        tree_header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.tree_after.setAlternatingRowColors(True)
        self.tree_after.itemDoubleClicked.connect(self._on_after_item_double_clicked)
        after_layout.addWidget(self.tree_after, stretch=1)

        # After Action Toolbar
        after_btn_layout = QHBoxLayout()
        self.btn_open_output_folder = QPushButton("📂 Open Output Folder")
        self.btn_open_output_folder.clicked.connect(self.open_output_folder)

        self.btn_view_report = QPushButton("🔍 View Report In-App")
        self.btn_view_report.clicked.connect(self.view_selected_report)

        after_btn_layout.addWidget(self.btn_open_output_folder)
        after_btn_layout.addWidget(self.btn_view_report)
        after_btn_layout.addStretch()
        after_layout.addLayout(after_btn_layout)

        splitter.addWidget(self.pane_after)
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 0)
        splitter.setStretchFactor(2, 4)

        main_layout.addWidget(splitter, stretch=1)

        # 3. Settings Box
        settings_group = QGroupBox("Configuration & Output Settings")
        settings_layout = QVBoxLayout(settings_group)
        settings_layout.setSpacing(8)

        out_dir_layout = QHBoxLayout()
        out_dir_layout.addWidget(QLabel("Output Directory:"))
        docs_dir = Path.home() / "Documents"
        default_out = (docs_dir if docs_dir.is_dir() else Path.home()) / "docx-a11y-output"
        self.txt_out_dir = QLineEdit(str(default_out))
        self.btn_browse_out = QPushButton("Browse...")
        self.btn_browse_out.clicked.connect(self.browse_output_dir)
        out_dir_layout.addWidget(self.txt_out_dir, stretch=1)
        out_dir_layout.addWidget(self.btn_browse_out)
        settings_layout.addLayout(out_dir_layout)

        options_layout = QHBoxLayout()
        options_layout.addWidget(QLabel("Report Formats:"))
        self.chk_md = QCheckBox("Markdown (.md)")
        self.chk_md.setChecked(True)
        self.chk_html = QCheckBox("HTML (.html)")
        self.chk_html.setChecked(True)
        self.chk_pdf = QCheckBox("PDF (.pdf)")
        self.chk_pdf.setChecked(True)
        self.chk_json = QCheckBox("JSON (.json)")
        self.chk_json.setChecked(True)

        options_layout.addWidget(self.chk_md)
        options_layout.addWidget(self.chk_html)
        options_layout.addWidget(self.chk_pdf)
        options_layout.addWidget(self.chk_json)
        options_layout.addSpacing(20)

        options_layout.addWidget(QLabel("Theme:"))
        self.cmb_theme = QComboBox()
        for t in available_themes():
            self.cmb_theme.addItem(t["name"])
        self.cmb_theme.setCurrentText("ocean")
        options_layout.addWidget(self.cmb_theme)
        options_layout.addStretch()

        settings_layout.addLayout(options_layout)
        main_layout.addWidget(settings_group)

    # Drag and Drop handlers
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        for url in event.mimeData().urls():
            p = Path(url.toLocalFile())
            if p.is_dir():
                self.queue.add_directory(p)
            elif p.suffix.lower() == ".docx":
                self.queue.add_file(p)
        self._refresh_table()

    # User Actions
    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Document Folder")
        if folder:
            added = self.queue.add_directory(folder)
            self._refresh_table()
            self.lbl_status.setText(f"Added {added} documents from {Path(folder).name}")

    def select_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select Word Documents", "", "Word Documents (*.docx)"
        )
        if files:
            self.add_file_paths([Path(f) for f in files])

    def add_file_paths(self, paths: List[Path | str]):
        added = 0
        for p in paths:
            if self.queue.add_file(p):
                added += 1
        self._refresh_table()
        self.lbl_status.setText(f"Loaded {len(self.queue)} document(s).")

    def clear_files(self):
        self.queue.clear()
        self._refresh_table()
        self.tree_after.clear()
        self.lbl_status.setText("Queue cleared.")

    def browse_output_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Output Directory", self.txt_out_dir.text())
        if dir_path:
            self.txt_out_dir.setText(dir_path)

    def open_triage(self):
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.information(self, "Select Document", "Please select a document from the table to triage.")
            return

        idx = selected_rows[0].row()
        item = self.queue.items[idx]
        audit_res = audit_file(item.path)
        findings = audit_res.get("findings", [])

        dialog = TriageDialog(item.path, findings, parent=self)
        dialog.exec()
        self.lbl_status.setText(f"Triage session finished for {item.path.name}.")

    def _refresh_table(self):
        self.table_before.setRowCount(len(self.queue.items))
        for row, item in enumerate(self.queue.items):
            self.table_before.setItem(row, 0, QTableWidgetItem(item.path.name))
            self.table_before.setItem(row, 1, QTableWidgetItem(str(item.paragraph_count) if item.paragraph_count else "-"))
            self.table_before.setItem(row, 2, QTableWidgetItem(item.status))
            self.table_before.setItem(row, 3, QTableWidgetItem(str(item.findings_count) if item.findings_count else "-"))
            self.table_before.setItem(row, 4, QTableWidgetItem(f"{item.score:.1f}%" if item.score is not None else "-"))

        has_items = len(self.queue.items) > 0
        self.btn_start.setEnabled(has_items)

    def _update_start_button_text(self):
        if self.chk_autofix.isChecked():
            self.btn_remediate_bridge.setText("✨ Fix & Audit ➔")
        else:
            self.btn_remediate_bridge.setText("🔍 Audit Only ➔")

    def start_processing(self):
        if not self.queue.items:
            return

        out_dir = Path(self.txt_out_dir.text()).expanduser().resolve()
        try:
            out_dir.mkdir(parents=True, exist_ok=True)
            test_file = out_dir / ".test_write"
            test_file.touch()
            test_file.unlink()
        except Exception as e:
            QMessageBox.critical(
                self,
                "Output Directory Error",
                f"Cannot write to output directory:\n{out_dir}\n\nError: {e}\n\nPlease choose a writable directory.",
            )
            return

        formats = []
        if self.chk_md.isChecked():
            formats.append("md")
        if self.chk_html.isChecked():
            formats.append("html")
        if self.chk_pdf.isChecked():
            formats.append("pdf")
        if self.chk_json.isChecked():
            formats.append("json")

        if not formats:
            QMessageBox.warning(self, "No Formats Selected", "Please select at least one report output format.")
            return

        theme = self.cmb_theme.currentText()
        auto_fix = self.chk_autofix.isChecked()

        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.btn_add_folder.setEnabled(False)
        self.btn_add_files.setEnabled(False)
        self.btn_clear.setEnabled(False)
        self.progress_bar.setMaximum(len(self.queue.items))
        self.progress_bar.setValue(0)

        self.worker = BatchWorker(
            items=self.queue.items,
            out_dir=out_dir,
            formats=formats,
            theme=theme,
            auto_fix=auto_fix,
        )
        self.worker.item_started.connect(self._on_item_started)
        self.worker.item_progress.connect(self._on_item_progress)
        self.worker.item_finished.connect(self._on_item_finished)
        self.worker.error_occurred.connect(self._on_error_occurred)
        self.worker.all_completed.connect(self._on_all_completed)
        self.worker.start()

    def stop_processing(self):
        if self.worker:
            self.worker.request_stop()
            self.lbl_status.setText("Cancelling after current file finishes...")
            self.btn_stop.setEnabled(False)

    def _on_error_occurred(self, idx: int, error_msg: str):
        self.lbl_status.setText(f"Error: {error_msg}")
        if os.environ.get("QT_QPA_PLATFORM") != "offscreen":
            QMessageBox.warning(self, "Processing Issue", error_msg)

    def _on_item_started(self, idx: int, total: int, file_name: str):
        self.lbl_status.setText(f"Processing [{idx + 1}/{total}]: {file_name}")
        self.table_before.setItem(idx, 2, QTableWidgetItem("Auditing..."))

    def _on_item_progress(self, idx: int, step_name: str):
        self.lbl_status.setText(f"[{idx + 1}/{len(self.queue.items)}] {step_name}")

    def _on_item_finished(self, idx: int, status: str, findings: int, score: float):
        item = self.queue.items[idx]
        self.table_before.setItem(idx, 1, QTableWidgetItem(str(item.paragraph_count)))
        self.table_before.setItem(idx, 2, QTableWidgetItem(status))
        self.table_before.setItem(idx, 3, QTableWidgetItem(str(findings)))
        self.table_before.setItem(idx, 4, QTableWidgetItem(f"{score:.1f}%"))
        self.progress_bar.setValue(idx + 1)
        self._populate_after_tree_for_item(item)

    def _populate_after_tree_for_item(self, item: BatchItem):
        doc_node = QTreeWidgetItem([f"📄 {item.path.name}", f"Score: {item.score:.1f}%" if item.score is not None else item.status])
        doc_node.setData(0, Qt.ItemDataRole.UserRole, str(item.path))

        out_dir = Path(self.txt_out_dir.text()).expanduser().resolve()
        stem = item.path.stem

        # Check for fixed docx
        fixed_docx = out_dir / f"{stem}.fixed.docx"
        if fixed_docx.exists():
            fixed_node = QTreeWidgetItem(["✨ Fixed DOCX: " + fixed_docx.name, "Remediated Document"])
            fixed_node.setData(0, Qt.ItemDataRole.UserRole, str(fixed_docx))
            doc_node.addChild(fixed_node)

        # Reports
        md_report = out_dir / f"{stem}-a11y-report.md"
        if md_report.exists():
            md_node = QTreeWidgetItem(["📊 Audit Report: " + md_report.name, "Markdown (Double-click to view)"])
            md_node.setData(0, Qt.ItemDataRole.UserRole, str(md_report))
            md_node.setData(1, Qt.ItemDataRole.UserRole, item.score)
            doc_node.addChild(md_node)

        html_report = out_dir / f"{stem}.html"
        if html_report.exists():
            html_node = QTreeWidgetItem(["🌐 HTML Report: " + html_report.name, "Web Report"])
            html_node.setData(0, Qt.ItemDataRole.UserRole, str(html_report))
            doc_node.addChild(html_node)

        pdf_report = out_dir / f"{stem}-a11y-report.pdf"
        if pdf_report.exists():
            pdf_node = QTreeWidgetItem(["📑 PDF Report: " + pdf_report.name, "Printable Report"])
            pdf_node.setData(0, Qt.ItemDataRole.UserRole, str(pdf_report))
            doc_node.addChild(pdf_node)

        self.tree_after.addTopLevelItem(doc_node)
        doc_node.setExpanded(True)

    def _on_all_completed(self, processed: int, errors: int):
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.btn_add_folder.setEnabled(True)
        self.btn_add_files.setEnabled(True)
        self.btn_clear.setEnabled(True)
        self.lbl_status.setText(f"Completed! Processed {processed} document(s) ({errors} errors).")
        self.worker_completed_signal.emit(processed, errors)

        if os.environ.get("QT_QPA_PLATFORM") != "offscreen":
            QMessageBox.information(
                self,
                "Batch Complete",
                f"Processing finished!\nSuccessfully processed: {processed}\n\nRemediated documents and reports are ready in the 'After' pane.",
            )

    def _on_after_item_double_clicked(self, item: QTreeWidgetItem, column: int):
        path_str = item.data(0, Qt.ItemDataRole.UserRole)
        if not path_str:
            return
        path = Path(path_str)
        if not path.exists():
            return

        if path.suffix.lower() == ".md":
            score = item.data(1, Qt.ItemDataRole.UserRole)
            dialog = ReportViewerDialog(report_path=path, score=score, parent=self)
            dialog.exec()
        else:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def open_output_folder(self):
        out_dir = Path(self.txt_out_dir.text()).expanduser().resolve()
        if out_dir.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(out_dir)))

    def view_selected_report(self):
        item = self.tree_after.currentItem()
        if not item:
            QMessageBox.information(self, "Select Item", "Please select a report in the After pane to view.")
            return

        path_str = item.data(0, Qt.ItemDataRole.UserRole)
        if not path_str and item.childCount() > 0:
            child = item.child(0)
            if child is not None:
                path_str = child.data(0, Qt.ItemDataRole.UserRole)
                item = child

        if path_str:
            path = Path(path_str)
            if path.suffix.lower() == ".md":
                score = item.data(1, Qt.ItemDataRole.UserRole)
                dialog = ReportViewerDialog(report_path=path, score=score, parent=self)
                dialog.exec()
            else:
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
