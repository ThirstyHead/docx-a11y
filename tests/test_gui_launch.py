"""Tests for GUI entry point launch and CLI --gui integration."""
import sys
import pytest
from docx_a11y.cli import main
from docx_a11y.gui.app import create_app


def test_create_app_initialization(qtbot):
    app = create_app()
    assert app.applicationName() == "docx-a11y"
    assert app.organizationName() == "ThirstyHead"


def test_cli_gui_flag_triggers_gui(monkeypatch):
    called = []

    def mock_gui_main():
        called.append(True)

    monkeypatch.setattr("docx_a11y.gui.app.main", mock_gui_main)
    monkeypatch.setattr(sys, "argv", ["docx-a11y", "--gui"])

    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 0
    assert called == [True]
