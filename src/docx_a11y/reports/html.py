"""Accessible HTML5 report generator derived strictly from Markdown.

Delegates to engine_a11y.reports.html.
"""
from engine_a11y.reports.html import render_html

__all__ = ["render_html"]
