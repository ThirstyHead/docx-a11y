"""Application entry point for docx-a11y GUI."""
import sys
from PySide6.QtWidgets import QApplication

try:
    from .main_window import MainWindow
except ImportError:
    from docx_a11y.gui.main_window import MainWindow


def create_app(argv=None) -> QApplication:
    app = QApplication.instance()
    if not app or not isinstance(app, QApplication):
        app = QApplication(argv or sys.argv)
    app.setApplicationName("docx-a11y")
    app.setOrganizationName("ThirstyHead")
    return app


def main():
    app = create_app()
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
