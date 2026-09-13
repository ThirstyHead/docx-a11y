"""Structural + accessibility + tone validator for the docx-a11y site.

Run: .venv/bin/python -m pytest tests/test_site.py -v
"""
from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path

import pytest

# WCAG Contrast Formula
def hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))

def contrast_ratio(fg: tuple[int, int, int], bg: tuple[int, int, int]) -> float:
    def lum(c: int) -> float:
        c = c / 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    
    def get_luminance(rgb: tuple[int, int, int]) -> float:
        r, g, b = rgb
        return 0.2126 * lum(r) + 0.7152 * lum(g) + 0.0722 * lum(b)

    L1 = get_luminance(fg)
    L2 = get_luminance(bg)
    
    brightest = max(L1, L2)
    darkest = min(L1, L2)
    return (brightest + 0.05) / (darkest + 0.05)

REPO = Path(__file__).resolve().parents[1]
SITE = REPO / "docs"

# Project Configuration
PAGES = ["index.html", "install.html", "usage.html", "power-user.html", "about.html"]
ORIGIN = "https://thirstyhead.com/docx-a11y"
BANNED = ("suffer from", "suffers from", "handicapped", "normal user")
SKIP_LINK_ID = "main"

class _Collector(HTMLParser):
    SKIP_TAGS = {"img", "script", "iframe", "object", "embed"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.html_lang = None
        self.h1_count = 0
        self.heading_levels: list[int] = []
        self.landmarks = set()
        self.main_id = None
        self.bad_skip = False
        self.first_anchor = True
        self.forbidden: list[str] = []
        self.links: list[str] = []
        self.anchor_texts: list[str] = []
        self._anchor_depth = 0
        self._anchor_text: list[str] = []
        self.fragment_ids: set[str] = set()

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "html":
            self.html_lang = a.get("lang")
        if tag in self.SKIP_TAGS:
            self.forbidden.append(tag)
        if tag in ("header", "nav", "main", "footer"):
            self.landmarks.add(tag)
        if tag == "main" and a.get("id"):
            self.main_id = a.get("id")
        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            lvl = int(tag[1])
            self.heading_levels.append(lvl)
            if lvl == 1:
                self.h1_count += 1
        if "id" in a and a["id"]:
            self.fragment_ids.add(a["id"])
        if tag == "a":
            self._anchor_depth += 1
            self._anchor_text.append("")
            self.links.append(a.get("href", ""))
            if self.first_anchor:
                self.first_anchor = False
                if a.get("href", "") != f"#{SKIP_LINK_ID}":
                    self.bad_skip = True

    def handle_data(self, data):
        if self._anchor_depth:
            self._anchor_text[-1] += data

    def handle_endtag(self, tag):
        if tag == "a" and self._anchor_depth:
            self._anchor_depth -= 1
            self.anchor_texts.append(self._anchor_text.pop())

def _parse(page: Path) -> _Collector:
    c = _Collector()
    c.feed(page.read_text(encoding="utf-8"))
    return c

def _text_of(page: Path) -> str:
    raw = page.read_text(encoding="utf-8")
    raw = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", raw, flags=re.S | re.I)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", raw))

@pytest.mark.parametrize("page", PAGES)
def test_single_h1(page):
    assert _parse(SITE / page).h1_count == 1, f"{page}: need exactly one <h1>"

@pytest.mark.parametrize("page", PAGES)
def test_heading_levels_do_not_skip(page):
    levels = _parse(SITE / page).heading_levels
    for prev, cur in zip(levels, levels[1:]):
        assert cur <= prev + 1, f"{page}: heading jumps h{prev} -> h{cur}"

@pytest.mark.parametrize("page", PAGES)
def test_html_lang(page):
    assert _parse(SITE / page).html_lang == "en", f"{page}: <html lang=\"en\"> required"

@pytest.mark.parametrize("page", PAGES)
def test_landmarks_present(page):
    lm = _parse(SITE / page).landmarks
    for need in ("header", "nav", "main", "footer"):
        assert need in lm, f"{page}: missing <{need}> landmark"

@pytest.mark.parametrize("page", PAGES)
def test_skip_link_and_main_id(page):
    c = _parse(SITE / page)
    assert not c.bad_skip, f"{page}: first <a> must be the skip link href=\"#{SKIP_LINK_ID}\""
    assert c.main_id == SKIP_LINK_ID, f"{page}: <main id=\"{SKIP_LINK_ID}\"> required"

@pytest.mark.parametrize("page", PAGES)
def test_no_forbidden_elements(page):
    found = _parse(SITE / page).forbidden
    allowed = {"script"}
    forbidden = [f for f in found if f not in allowed]
    assert not forbidden, f"{page}: text-only, no-JS site found {sorted(set(forbidden))}"

@pytest.mark.parametrize("page", PAGES)
def test_internal_links_resolve(page):
    here = (SITE / page).parent
    for href in _parse(SITE / page).links:
        if not href or href.startswith("#"):
            continue
        if href.startswith(("http://", "https://", "mailto:")):
            continue
        if "://" in href or href.startswith("/"):
            pytest.fail(f"{page}: link '{href}' must be relative (subpath deploy)")
        target = (here / href.split("#", 1)[0]).resolve()
        assert target.exists(), f"{page}: broken relative link '{href}'"

@pytest.mark.parametrize("page", PAGES)
def test_fragment_targets_exist(page):
    c = _parse(SITE / page)
    for href in c.links:
        if href.startswith("#") and len(href) > 1:
            assert href[1:] in c.fragment_ids, f"{page}: no id='{href[1:]}' for link {href}"

@pytest.mark.parametrize("page", PAGES)
def test_external_links_https_only(page):
    for href in _parse(SITE / page).links:
        if href.startswith("http"):
            assert href.startswith("https://"), f"{page}: non-https external link {href}"
        if "javascript:" in href.lower():
            pytest.fail(f"{page}: javascript: href")

@pytest.mark.parametrize("page", PAGES)
def test_every_anchor_has_text(page):
    c = _parse(SITE / page)
    for i, text in enumerate(c.anchor_texts):
        assert text.strip(), f"{page}: anchor #{i} has no accessible text"

@pytest.mark.parametrize("page", PAGES)
def test_no_banned_phrases(page):
    text = _text_of(SITE / page).lower()
    hits = [b for b in BANNED if b in text]
    assert not hits, f"{page}: banned phrase(s) {hits} (use barrier-first language)"

@pytest.mark.parametrize("page", PAGES)
def test_canonical_url(page):
    raw = (SITE / page).read_text(encoding="utf-8")
    m = re.search(r'rel="canonical"\s+href="([^"]+)"', raw)
    assert m, f"{page}: missing <link rel=\"canonical\">"
    assert m.group(1).startswith(ORIGIN), f"{page}: canonical must start with {ORIGIN}"

def _resolve_tokens(theme: str) -> dict[str, str]:
    css = (SITE / "css" / "base.css").read_text(encoding="utf-8")
    
    all_vars = {}
    matches = re.findall(r"(--[a-z-]+)\s*:\s*([^;}\n]+)", css)
    for name, val in matches:
        all_vars[name.strip()] = val.strip()

    if theme == "light":
        root_match = re.search(r":root\s*\{([^}]*)\}", css)
        if root_match:
            all_vars = dict(re.findall(r"(--[a-z-]+)\s*:\s*([^;}\n]+)", root_match.group(1)))
            all_vars = {k.strip(): v.strip() for k, v in all_vars.items()}

    def resolve(val):
        if val.startswith("var("):
            var_match = re.search(r"var\((--[a-z-]+)\)", val)
            if var_match:
                var_name = var_match.group(1)
                resolved_val = all_vars.get(var_name)
                if resolved_val:
                    return resolve(resolved_val)
        return val

    resolved = {}
    for name, val in all_vars.items():
        res = resolve(val)
        if res.startswith("#"):
            resolved[name] = res
    return resolved

@pytest.mark.parametrize("theme", ["light", "dark"])
def test_text_contrast_aa(theme):
    t = _resolve_tokens(theme)
    pairs = [
        ("--sys-color-text-main", "--sys-color-bg-primary"),
        ("--sys-color-text-muted", "--sys-color-bg-primary"),
        ("--sys-color-accent", "--sys-color-bg-primary"),
    ]
    for fg, bg in pairs:
        assert fg in t and bg in t, f"{theme}: missing token {fg} or {bg}"
        ratio = contrast_ratio(hex_to_rgb(t[fg]), hex_to_rgb(t[bg]))
        assert ratio >= 4.5, f"{theme}: {fg} on {bg} is {ratio:.2f}:1 (< 4.5:1 AA)"
