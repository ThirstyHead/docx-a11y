"""Accessible HTML5 report generator derived strictly from Markdown."""
import html as _html
import re
from typing import Optional
import markdown
from .theme import theme_css

_MD_EXTENSIONS = ["tables", "fenced_code", "toc", "sane_lists"]
_H2_RE = re.compile(r'<h2 id="([^"]+)"[^>]*>(.*?)</h2>')


def _wrap_summary_banner(body: str) -> str:
    m = re.search(r'(<h2 id="executive-summary"[^>]*>.*?</h2>)(.*?)(?=<h2 )', body, re.DOTALL)
    if not m:
        return body
    inner = m.group(2).strip("\n")
    wrapped = f'{m.group(1)}\n<div class="summary-banner">\n{inner}\n</div>\n'
    return body[:m.start()] + wrapped + body[m.end():]


def _wrap_findings(body: str) -> str:
    pattern = re.compile(r'(<h3 [^>]*>.*?</h3>.*?)(?=<h3 |<h2 |$)', re.DOTALL)
    return pattern.sub(r'<section class="finding">\n\1\n</section>\n', body)


def _build_toc_nav(body: str) -> str:
    items = [f'    <li><a href="#{hid}">{text}</a></li>' for hid, text in _H2_RE.findall(body)]
    if not items:
        return ""
    return (
        '<nav class="toc" aria-label="Table of contents">\n'
        "  <h2>Contents</h2>\n"
        "  <ul>\n" + "\n".join(items) + "\n  </ul>\n"
        "</nav>\n"
    )


def _extract_title(md_text: str) -> str:
    for line in md_text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return "Accessibility Audit Report"


def render_html(
    md_text: str,
    theme: str = "light",
    lang: str = "en",
    config_dir: Optional[str] = None,
) -> str:
    """Render canonical Markdown into an accessible, self-contained HTML5 document."""
    raw_body = markdown.markdown(md_text, extensions=_MD_EXTENSIONS)
    body = _wrap_summary_banner(raw_body)
    body = _wrap_findings(body)
    toc = _build_toc_nav(body)
    title = _html.escape(_extract_title(md_text))
    css = theme_css(theme, config_dir=config_dir)

    return (
        "<!doctype html>\n"
        f'<html lang="{lang}">\n'
        "<head>\n"
        '  <meta charset="utf-8">\n'
        '  <meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"  <title>{title}</title>\n"
        f"  <style>\n{css}\n  </style>\n"
        "</head>\n"
        "<body>\n"
        '  <a class="skip" href="#main">Skip to main content</a>\n'
        '  <div class="layout">\n'
        f"    {toc}\n"
        '    <main id="main" class="report" tabindex="-1">\n'
        f"      {body}\n"
        "    </main>\n"
        "  </div>\n"
        "</body>\n"
        "</html>\n"
    )
