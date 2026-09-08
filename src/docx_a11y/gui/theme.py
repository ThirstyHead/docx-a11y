"""Accessible Qt stylesheet and color tokens for docx-a11y GUI."""

APP_STYLESHEET = """
QMainWindow {
    background-color: #f8fafc;
}

QToolBar {
    background-color: #ffffff;
    border-bottom: 1px solid #e2e8f0;
    padding: 6px;
    spacing: 8px;
}

QPushButton {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 6px 14px;
    font-size: 13px;
    font-weight: 500;
    color: #0f172a;
}

QPushButton:hover {
    background-color: #f1f5f9;
    border-color: #94a3b8;
}

QPushButton:disabled {
    background-color: #f8fafc;
    border-color: #e2e8f0;
    color: #94a3b8;
}

QPushButton#btn_primary {
    background-color: #2563eb;
    border: 1px solid #1d4ed8;
    color: #ffffff;
    font-weight: 600;
}

QPushButton#btn_primary:hover {
    background-color: #1d4ed8;
}

QPushButton#btn_primary:disabled {
    background-color: #93c5fd;
    border-color: #93c5fd;
    color: #ffffff;
}

QTableWidget {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    gridline-color: #f1f5f9;
    selection-background-color: #eff6ff;
    selection-color: #1e3a8a;
}

QHeaderView::section {
    background-color: #f8fafc;
    border: none;
    border-bottom: 1px solid #cbd5e1;
    padding: 6px 8px;
    font-weight: 600;
    color: #334155;
}

QGroupBox {
    font-weight: 600;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    margin-top: 10px;
    padding-top: 14px;
    color: #1e293b;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
}

QProgressBar {
    border: 1px solid #cbd5e1;
    border-radius: 4px;
    text-align: center;
    background-color: #e2e8f0;
    font-weight: 600;
}

QProgressBar::chunk {
    background-color: #2563eb;
    border-radius: 3px;
}
"""
