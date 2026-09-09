"""Canonical Markdown report renderer.

Delegates to engine_a11y.reports.md with docx document profile.
"""
from typing import Any, Dict, Optional, Set
from engine_a11y.profile import get_docx_profile
from engine_a11y.reports.md import render_md as _engine_render_md


def render_md(
    audit_data: Dict[str, Any],
    after_result: Optional[Dict[str, Any]] = None,
    source_path: Optional[str] = None,
    profile: Optional[Any] = None,
    excluded_sc: Optional[Set[str]] = None,
) -> str:
    """Render canonical Markdown report using engine-a11y with docx profile."""
    active_profile = profile or get_docx_profile()
    return _engine_render_md(
        result=audit_data,
        after_result=after_result,
        source_path=source_path,
        profile=active_profile,
        excluded_sc=excluded_sc,
    )


__all__ = ["render_md"]
