"""Main dashboard window for docx-a11y desktop application."""
from pathlib import Path
from typing import List, Optional
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from ..audit import audit_file
from ..reports.theme import available_themes
from .models import BatchItem, BatchQueue
from .theme import APP_STYLESHEET
from .triage_dialog import TriageDialog
from .worker import BatchWorker


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("docx-a11y: Word WCAG Accessibility Remediation")
        self.resize(960, 680)
        self.setStyleSheet(APP_STYLESHEET)
        self.setAcceptDrops(True)

        self.queue = BatchQueue()
        self.worker: Optional[BatchWorker] = None

        self._init_ui()

    def _init_ui(self):
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(16, 16, 16, 16)

        # 1. Top Action Toolbar
        toolbar_layout = QHBoxLayout()
        self.btn_add_folder = QPushButton("📁 Add Folder...")
        self.btn_add_folder.clicked.connect(self.select_folder)

        self.btn_add_files = QPushButton("📄 Add Files...")
        self.btn_add_files.clicked.connect(self.select_files)

        self.btn_clear = QPushButton("🗑️ Clear List")
        self.btn_clear.clicked.connect(self.clear_files)

        self.btn_triage = QPushButton("🔍 Interactive Triage")
        self.btn_triage.clicked.connect(self.open_triage)

        toolbar_layout.addWidget(self.btn_add_folder)
        toolbar_layout.addWidget(self.btn_add_files)
        toolbar_layout.addWidget(self.btn_clear)
        toolbar_layout.addWidget(self.btn_triage)
        toolbar_layout.addStretch()

        main_layout.addLayout(toolbar_layout)

        # 2. Batch Queue Table
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["File Name", "Paragraphs", "Status", "Findings", "Score"])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)

        main_layout.addWidget(self.table, stretch=1)

        # 3. Settings Box
        settings_group = QGroupBox("Configuration & Output Settings")
        settings_layout = QVBoxLayout(settings_group)
        settings_layout.setSpacing(10)

        # Output directory selector
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

        # Options row: formats, theme, auto-fix
        options_layout = QHBoxLayout()

        # Format checkboxes
        options_layout.addWidget(QLabel("Formats:"))
        self.chk_md = QCheckBox("Markdown")
        self.chk_md.setChecked(True)
        self.chk_html = QCheckBox("HTML")
        self.chk_html.setChecked(True)
        self.chk_pdf = QCheckBox("PDF")
        self.chk_pdf.setChecked(True)
        self.chk_json = QCheckBox("JSON")
        self.chk_json.setChecked(True)

        options_layout.addWidget(self.chk_md)
        options_layout.addWidget(self.chk_html)
        options_layout.addWidget(self.chk_pdf)
        options_layout.addWidget(self.chk_json)
        options_layout.addSpacing(20)

        # Theme dropdown
        options_layout.addWidget(QLabel("Theme:"))
        self.cmb_theme = QComboBox()
        for t in available_themes():
            self.cmb_theme.addItem(t["name"])
        self.cmb_theme.setCurrentText("ocean")
        options_layout.addWidget(self.cmb_theme)
        options_layout.addSpacing(20)

        # Auto-fix checkbox
        self.chk_autofix = QCheckBox("Apply Deterministic Auto-Fixes")
        self.chk_autofix.setChecked(True)
        self.chk_autofix.toggled.connect(self._update_start_button_text)
        options_layout.addWidget(self.chk_autofix)

        options_layout.addStretch()
        settings_layout.addLayout(options_layout)

        main_layout.addWidget(settings_group)

        # 4. Progress and Execution Bar
        progress_layout = QHBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.lbl_status = QLabel("Ready. Add Word documents or folders to begin.")

        self.btn_start = QPushButton("Start Remediation")
        self.btn_start.setObjectName("btn_primary")
        self.btn_start.setEnabled(False)
        self.btn_start.clicked.connect(self.start_processing)

        self.btn_stop = QPushButton("Cancel")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.stop_processing)

        progress_layout.addWidget(self.btn_start)
        progress_layout.addWidget(self.btn_stop)
        progress_layout.addWidget(self.progress_bar, stretch=1)

        main_layout.addLayout(progress_layout)
        main_layout.addWidget(self.lbl_status)

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
        self.table.setRowCount(len(self.queue.items))
        for row, item in enumerate(self.queue.items):
            self.table.setItem(row, 0, QTableWidgetItem(item.path.name))
            self.table.setItem(row, 1, QTableWidgetItem(str(item.paragraph_count) if item.paragraph_count else "-"))
            self.table.setItem(row, 2, QTableWidgetItem(item.status))
            self.table.setItem(row, 3, QTableWidgetItem(str(item.findings_count) if item.findings_count else "-"))
            self.table.setItem(row, 4, QTableWidgetItem(f"{item.score:.1f}%" if item.score is not None else "-"))

        has_items = len(self.queue.items) > 0
        self.btn_start.setEnabled(has_items)

    def _update_start_button_text(self):
        if self.chk_autofix.isChecked():
            self.btn_start.setText("Start Remediation")
        else:
            self.btn_start.setText("Start Audit")

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
        QMessageBox.warning(self, "Processing Issue", error_msg)

    def _on_item_started(self, idx: int, total: int, file_name: str):
        self.lbl_status.setText(f"Processing [{idx + 1}/{total}]: {file_name}")
        self.table.setItem(idx, 2, QTableWidgetItem("Auditing..."))

    def _on_item_progress(self, idx: int, step_name: str):
        self.lbl_status.setText(f"[{idx + 1}/{len(self.queue.items)}] {step_name}")

    def _on_item_finished(self, idx: int, status: str, findings: int, score: float):
        item = self.queue.items[idx]
        self.table.setItem(idx, 1, QTableWidgetItem(str(item.paragraph_count)))
        self.table.setItem(idx, 2, QTableWidgetItem(status))
        self.table.setItem(idx, 3, QTableWidgetItem(str(findings)))
        self.table.setItem(idx, 4, QTableWidgetItem(f"{score:.1f}%"))
        self.progress_bar.setValue(idx + 1)

    def _on_all_completed(self, processed: int, errors: int):
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.btn_add_folder.setEnabled(True)
        self.btn_add_files.setEnabled(True)
        self.btn_clear.setEnabled(True)
        self.lbl_status.setText(f"Completed! Processed {processed} document(s) ({errors} errors).")
