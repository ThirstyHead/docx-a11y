# docx-a11y

Audit and remediate Microsoft Word `.docx` files against **WCAG 2.1 AA** — standalone, deterministic, no AI in the loop.

`docx-a11y` is a rule-based linter over the OOXML parts python-docx exposes. It reports every violation with a WCAG success-criterion mapping, then applies the fixes it can do deterministically and writes a new file (the source is never modified). Re-run the audit to verify a PASS.

## Quickstart

```bash
python3 -m venv .venv
.venv/bin/pip install -e .          # or: pip install docx-a11y

# 1. audit (exit 0 = pass, 1 = fail, 2 = error)
docx-a11y audit recipe.docx --json findings.json --report report.md
#    reports can embed official WCAG normative text (see "Report enrichment")

# 2. remediate (needs the audit JSON; provide a heading map for deterministic structure)
docx-a11y remediate recipe.docx --findings findings.json \
    --out recipe_fixed.docx --heading-map '0=Heading 1,4=Heading 2'

# 3. re-verify
docx-a11y audit recipe_fixed.docx
```

Use the venv entry point on machines where the console script isn't on PATH:

```bash
.venv/bin/docx-a11y audit recipe.docx
```

### Audit options

| Flag | Default | Meaning |
|---|---|---|
| `--json OUT` | — | write machine-readable findings (stable key order, sorted findings) |
| `--report OUT` | — | write a markdown report |
| `--language CODE` | `en-US` | default language used when fixing SC 3.1.1 |
| `--background RRGGBB` | `FFFFFF` | assumed page background for contrast math |
| `--heading-map 'i=Heading N'` | — | deterministic structure: paragraph index → heading style |

`remediate` accepts the same `--language`, `--background`, `--heading-map` flags.

## Rules

| rule_id | SC | severity | deterministic fix |
|---|---|---|---|
| `title-missing` | 2.4.2 (by convention) | moderate | yes — dc:title from first H1 or filename stem |
| `language-missing` | 3.1.1 | moderate | yes — `w:lang` in docDefaults |
| `heading-level-skipped` | 1.3.1 | serious | yes — re-level to next valid heading |
| `headings-none` | 1.3.1 | serious | yes, **with** `--heading-map`; otherwise manual |
| `multiple-h1` | 1.3.1 | moderate | no — manual (keep one H1) |
| `image-alt-missing` | 1.1.1 | critical | placeholder only — inserts `[ALT-NOT-PROVIDED: …]`; real alt text is human content |
| `table-header-missing` | 1.3.1 | serious | yes — `w:tblHeader` on first row |
| `merged-cell` | 1.3.1 | moderate | no — manual (unmerge) |
| `color-contrast` | 1.4.3 | moderate | yes — removes failing `w:color` override |

Severity order: critical → serious (blocking) → moderate → minor. The audit **passes** when there are no critical/serious findings; moderate findings are advisory.

## Determinism & safety

- **Same input file + same version → identical findings JSON.** Findings are sorted by severity then location; JSON keys are sorted.
- **Remediation only mutates a copy.** The source `.docx` is never touched; output goes to `--out`.
- **Only deterministic fixes run automatically.** Anything requiring human judgment (real alt text, heading choices without a map, unmerging cells) is reported as `fixable: false` / skipped, never guessed.
- **A broken rule cannot kill the audit** — it is captured as an internal finding.

## Scope

- WCAG 2.1 AA. Keyboard/navigation criteria (2.x) do not apply to `.docx` content; SC 2.4.2 (Page Titled) is applied by convention to document title metadata.
- Contrast assumes a flat background (`--background`); page-level backgrounds/gradients are out of scope.
- Contrast uses the `wcag-contrast-ratio` library when present, with an equivalent W3C fallback, so the package still runs with only python-docx-ng.

## Tests

```bash
.venv/bin/pip install -e ".[dev]"
.venv/bin/python -m pytest tests/ -q
```

Fixtures are committed under `tests/fixtures/`. To regenerate them (after a python-docx change):

```bash
.venv/bin/python tests/make_fixtures.py
```

`tests/fixtures/no-knead-bread.docx` is a real-world recipe document used to reproduce the original manual audit run end-to-end.

## Project layout

```
src/docx_a11y/
  audit.py        run rules, collect findings (JSON-safe)
  remediate.py    apply deterministic fixes from an audit JSON
  rules.py        rule registry (check + fix per rule)
  contrast.py     WCAG relative-luminance contrast math
  report.py       findings JSON -> markdown
  findings.py     Finding data model + summary
  cli.py          docx-a11y audit | remediate | rules
tests/
  fixtures/       committed .docx golden files
  make_fixtures.py  regenerate fixtures
  test_a11y.py    end-to-end tests
```

## License

MIT