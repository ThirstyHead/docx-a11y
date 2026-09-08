# SMACSS Theme Architecture Contract

Assembly order for `theme_css(name)`:
1. **Tokens:** `<theme>/tokens.css` (10 required CSS custom properties)
2. **Objects:** `_layout/objects.css` (layout grids, container, skip links)
3. **Units:** `_layout/units.css` (card units, banners, tables, TOC, severity tags)
4. **Overrides:** `<theme>/overrides.css` (optional theme-specific flourishes)

## Required Token Vocabulary (10 tokens):
`--bg`, `--fg`, `--muted`, `--accent`, `--link`, `--code-bg`,
`--sev-critical`, `--sev-serious`, `--sev-moderate`, `--sev-minor`

## Contrast Gate (WCAG 1.4.3 AA):
`--fg` vs `--bg` and every `--sev-*` vs `--bg` must be >= 4.5:1.
