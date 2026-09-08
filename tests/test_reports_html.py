"""Tests for HTML5 report generation and SMACSS theme engine."""
from pathlib import Path
import pytest
from docx_a11y.reports.html import render_html
from docx_a11y.reports.theme import available_themes, theme_css


def test_theme_inventory():
    manifests = available_themes()
    names = [t["name"] for t in manifests]
    for required in ("light", "dark", "ocean", "forest", "high-contrast", "print"):
        assert required in names


def test_theme_css_assembly():
    css = theme_css("ocean")
    assert "docx-a11y theme: ocean" in css
    assert "--bg:" in css
    assert "--accent:" in css
    assert ".layout" in css
    assert ".finding" in css


def test_custom_user_theme(tmp_path: Path):
    user_theme_dir = tmp_path / "themes" / "custom"
    user_theme_dir.mkdir(parents=True)
    (user_theme_dir / "theme.json").write_text(
        '{"name": "custom", "label": "Custom Brand", "mode": "light"}'
    )
    (user_theme_dir / "tokens.css").write_text(":root { --bg: #ffffff; --fg: #111111; }")
    (user_theme_dir / "overrides.css").write_text(".custom-override { display: block; }")

    themes = available_themes(config_dir=tmp_path)
    assert any(t["name"] == "custom" for t in themes)

    css = theme_css("custom", config_dir=tmp_path)
    assert "--bg: #ffffff;" in css
    assert ".custom-override" in css


def test_html_accessibility_elements():
    md = "# Accessibility Audit Report: doc.docx\n\n## Executive Summary\nAll good.\n\n## 1. Perceivable\n\n### 1. [CRITICAL] Missing alt\n"
    html = render_html(md, theme="forest")
    assert '<!doctype html>' in html
    assert '<html lang="en">' in html
    assert '<a class="skip" href="#main">Skip to main content</a>' in html
    assert '<nav class="toc" aria-label="Table of contents">' in html
    assert '<main id="main" class="report"' in html
    assert '<section class="finding">' in html
