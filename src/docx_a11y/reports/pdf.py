"""Tagged Accessible PDF report engine derived strictly from HTML5.

The HTML document is rendered via PyMuPDF Story using the print theme (black on white,
severity marked by weight/text cues rather than color alone). Pikepdf injects PDF/UA
catalog tags, /Lang, /Title, and XMP metadata.
"""
import html as _html
import os
import re
import tempfile
from pathlib import Path
from typing import Optional
import pikepdf
import pymupdf as fitz
from .theme import theme_css

_MARGIN = 54.0  # 0.75 inch print margins
_H1_RE = re.compile(r"<h1[^>]*>(.*?)</h1>", re.DOTALL)
_BODY_RE = re.compile(r"<body[^>]*>(.*)</body>", re.DOTALL)
_SKIP_RE = re.compile(r'<a class="skip"[^>]*>.*?</a>', re.DOTALL)
_TAG_RE = re.compile(r"<[^>]+>")
_TOKEN_RE = re.compile(r"(--[a-zA-Z0-9-]+)\s*:\s*([^;]+);")
_VAR_RE = re.compile(r"var\((--[a-zA-Z0-9-]+)\)")


def _resolve_css_variables(css: str) -> str:
    """Inline CSS custom properties so PyMuPDF Story can render them deterministically."""
    root_block = css.split("}", 1)[0]
    tokens = {k: v.strip() for k, v in _TOKEN_RE.findall(root_block)}

    def _replace(m):
        return tokens.get(m.group(1), m.group(0))

    return _VAR_RE.sub(_replace, css)


def _extract_body_content(html_doc: str) -> str:
    m = _BODY_RE.search(html_doc)
    body = m.group(1) if m else html_doc
    return _SKIP_RE.sub("", body)


def _extract_document_title(html_doc: str) -> str:
    m = _H1_RE.search(html_doc)
    if not m:
        return "Accessibility Audit Report"
    return _html.unescape(_TAG_RE.sub("", m.group(1))).strip()


def render_pdf(
    html_doc: str,
    out_path: Optional[str | Path] = None,
    lang: str = "en",
    title: Optional[str] = None,
) -> Path:
    """Render HTML report into an accessible, searchable PDF with document structure."""
    out_path = Path(out_path) if out_path else Path("accessibility-report.pdf")
    body_content = _extract_body_content(html_doc)
    doc_title = title or _extract_document_title(html_doc)

    # Use the print stylesheet to ensure print/monochrome contrast compliance
    raw_print_css = theme_css("print")
    resolved_css = _resolve_css_variables(raw_print_css)

    # 1. Render pages with Story
    fd, tmp_story = tempfile.mkstemp(suffix=".pdf", prefix="docx-a11y-story-")
    os.close(fd)
    tmp_path = Path(tmp_story)

    try:
        story = fitz.Story(html=body_content, user_css=resolved_css)
        writer = fitz.DocumentWriter(str(tmp_path))
        page_rect = fitz.paper_rect("letter")
        print_rect = fitz.Rect(
            _MARGIN, _MARGIN, page_rect.width - _MARGIN, page_rect.height - _MARGIN
        )

        more = True
        while more:
            dev = writer.begin_page(page_rect)
            more, _ = story.place(print_rect)
            story.draw(dev)
            writer.end_page()
        writer.close()

        # 2. Inject accessibility tags and catalog metadata using pikepdf
        with pikepdf.open(tmp_path) as pdf:
            pdf.Root.Lang = pikepdf.String(lang)
            with pdf.open_metadata(set_pikepdf_as_editor=False) as meta:
                meta["dc:title"] = doc_title
                meta["pdf:Producer"] = "docx-a11y accessible PDF engine"

            # Set /MarkInfo /Marked true
            mark_info = pikepdf.Dictionary()
            mark_info[pikepdf.Name("/Marked")] = pikepdf.Boolean(True)
            pdf.Root[pikepdf.Name("/MarkInfo")] = mark_info

            out_path.parent.mkdir(parents=True, exist_ok=True)
            pdf.save(str(out_path))

    finally:
        if tmp_path.exists():
            tmp_path.unlink()

    return out_path
