# docx-a11y

Audit and remediate Microsoft Word `.docx` documents against **WCAG 2.1 AA** standards — standalone, deterministic, and headless.

`docx-a11y` evaluates WordprocessingML / OOXML structures to uncover digital accessibility barriers across all four POUR principles (**Perceivable**, **Operable**, **Understandable**, **Robust**). It applies non-destructive, deterministic remediations and compiles comprehensive audit reports in **Markdown** (the single source of truth), **accessible HTML5** (styled via SMACSS), and **accessible tagged PDF**.

Part of the document accessibility trio alongside [pptx-a11y](https://github.com/ThirstyHead/pptx-a11y) and [pdf-a11y](https://github.com/ThirstyHead/pdf-a11y).

---

## Key Features

- **POUR Structure (WCAG 2.1 AA):** Every finding and recommendation is categorized under Perceivable, Operable, Understandable, or Robust, linking to canonical W3C Understanding documentation.
- **Social Model of Disability:** Language focuses strictly on document deficiencies and environmental barriers rather than personal limitations. Unit-tested language guards prevent ableist or medical-model phrasing.
- **Single Source of Truth:** Reports are authored as CommonMark Markdown, then compiled into accessible HTML5 and accessible tagged PDF with zero semantic or textual discrepancies.
- **SMACSS Theme Engine:** Build-free, text-based CSS theme architecture with 6 bundled palettes (`light`, `dark`, `ocean`, `forest`, `high-contrast`, `print`). Supports custom user themes in `~/.config/docx-a11y/themes/`.
- **Contrast Rigor (WCAG 1.4.3):** Evaluates run-level text contrast against page backgrounds (4.5:1 for normal text, 3:1 for large text). Automatically scales luminance to pass thresholds while preserving the author's color hue and brand accents.
- **Interactive & Batch GUI:** Native cross-platform desktop application for bulk directory remediation, file drag-and-drop, real-time progress, and interactive barrier triage.
- **Tagged Accessible PDF:** Exports multi-page PDFs carrying `/Lang`, `/Title`, `/MarkInfo /Marked true`, and validated tag trees.
- **Deterministic & Structural Remediation:** Auto-remediates document title metadata, language tags, table header repetition (`w:tblHeader`) and anti-split (`w:cantSplit`), heading skips, and contrast overrides.
- **Interactive Triage:** Guided human-in-the-loop triage workflow for author-intent barriers: descriptive image alt text, decorative image markers, and document titles.
- **Strict Document Immutability:** Original files are never modified in-place; all remediations produce cryptographically verified new artifacts with SHA-256 provenance.

---

## Installation

### 1. Desktop GUI Application (Pre-built Installers)

Pre-built desktop installers with bundled dependencies (including PySide6/Qt) are available on the [GitHub Releases](https://github.com/ThirstyHead/docx-a11y/releases) page:

- **macOS (`.dmg`)**:
  1. Download `docx-a11y-v<version>-macos.dmg` (e.g. `docx-a11y-v0.5.0-macos.dmg`).
  2. Double-click to mount the disk image.
  3. Drag `docx-a11y.app` into `/Applications`.
  4. Launch `docx-a11y` from Spotlight, Launchpad, or the Applications folder.
  > **Note (macOS Gatekeeper)**: Because `docx-a11y` is an open-source binary distributed outside the Mac App Store without paid Apple Developer notarization, macOS blocks first launch with *“Apple could not verify docx-a11y is free of malware”*.
  > - **GUI bypass**: Right-click (or Control-click) `docx-a11y.app` in `/Applications`, select **Open**, and click **Open**. Alternatively, go to **System Settings > Privacy & Security**, scroll down to the **Security** section, and click **Open Anyway**.
  > - **Terminal bypass**: Run `xattr -cr /Applications/docx-a11y.app` (or `xattr -d com.apple.quarantine ~/Downloads/docx-a11y-*-macos.dmg` before opening the DMG).
- **Windows (`.exe`)**:
  1. Download `docx-a11y-setup-v<version>.exe` (e.g. `docx-a11y-setup-v0.5.0.exe`).
  2. Run the installer wizard to install into `Program Files` and create Start Menu / Desktop shortcuts.
- **Linux (`.AppImage`)**:
  1. Download `docx-a11y-v<version>-x86_64.AppImage` (e.g. `docx-a11y-v0.5.0-x86_64.AppImage`).
  2. Make it executable: `chmod +x docx-a11y-v*-x86_64.AppImage`.
  3. Run directly: `./docx-a11y-v*-x86_64.AppImage`.

### 2. Standalone Headless CLI Binary (No Python Required)

Single-file headless CLI executables are available on [GitHub Releases](https://github.com/ThirstyHead/docx-a11y/releases) for agentic workflows, CI/CD pipelines, and terminal environments:

```bash
# Example: Download macOS Apple Silicon standalone CLI binary
curl -LO https://github.com/ThirstyHead/docx-a11y/releases/latest/download/docx-a11y-cli-macos-arm64
chmod +x docx-a11y-cli-macos-arm64
sudo mv docx-a11y-cli-macos-arm64 /usr/local/bin/docx-a11y

# Verify installation
docx-a11y --help
```

### 3. Ephemeral Execution via `uvx`

Run `docx-a11y` instantly in any environment without managing Python virtual environments:

```bash
# Run headless CLI audit & remediation
uvx docx-a11y document.docx --fix --format md,html,pdf,json

# Launch desktop GUI ephemerally
uvx --with "docx-a11y[gui]" docx-a11y-gui
```

### 4. Python Package via `pip` or `venv`

Requires **Python >= 3.10**.

#### Development Virtual Environment (`venv`)

```bash
# Clone and enter repository
git clone https://github.com/ThirstyHead/docx-a11y.git
cd docx-a11y

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\Activate.ps1

# Install with all dependencies
pip install -e ".[all]"
> **Important Installation Tips:**
> - **Execute from the repository root:** Ensure your working directory is `docx-a11y/` where `pyproject.toml` lives.
> - **Quote the extras string (`".[gui]"`):** In macOS `zsh`, unquoted brackets `docx-a11y[gui]` or `.[gui]` are interpreted as shell globbing patterns. Always wrap the target in double quotes (`".[gui]"`).
> - **Developer & Test Suite:** To install development, linting, and automated test dependencies alongside the GUI, use `pip install -e ".[all]"`.

---

### Alternative: CLI-Only via `pipx`

For isolated headless server use or CI/CD pipelines without GUI dependencies:

```bash
pipx install .
docx-a11y --help
```

---

## Quickstart

### Example Test Documents

Two sample documents based on an artisanal bread baking recipe are provided in `examples/` for evaluating both the CLI and GUI:

- **`examples/No Knead Bread.docx` (Clean Reference):**
  A fully accessible document featuring hierarchical headings, declared table headers, descriptive image alt text, and document title metadata. Audits cleanly with **0 findings (100% WCAG 2.1 AA compliance)**.

- **`examples/No Knead Bread-test.docx` (Accessibility Barriers):**
  Intentionally includes digital accessibility barriers checked by `docx-a11y`: missing title metadata, missing language attribute, skipped heading levels, undeclared table headers, merged cells, missing image alt text, and low contrast colors.

```bash
# Test the clean document (passes cleanly, exits 0):
docx-a11y "examples/No Knead Bread.docx" --format md,html,pdf,json --output-dir ./reports-clean

# Test the barrier document (detects barriers, exits 1):
docx-a11y "examples/No Knead Bread-test.docx" --format md,html,pdf,json --output-dir ./reports-barriers
```

Or drag both files directly into the desktop GUI (`docx-a11y --gui` or `docx-a11y-gui`) to test batch analysis, progress tracking, and interactive triage!

---

### 1. Audit a Document

Audit a document and generate all report formats (`.md`, `.html`, `.pdf`, `.json`):

```bash
docx-a11y document.docx --format md,html,pdf,json --output-dir ./reports
```

### 2. Remediate Violations

Apply deterministic fixes (adds missing title metadata, marks table header rows with repeat and cantSplit, tags document language, heals heading skips, and adjusts contrast):

```bash
docx-a11y document.docx --fix --output-dir ./remediated
```
This saves `document-remediated.docx` alongside before-and-after audit reports highlighting remediation progress.

### 3. Interactive Triage

Launch interactive terminal triage to provide author-intent alt text, mark images as decorative, or set document titles:

```bash
docx-a11y document.docx --triage --out-docx ./triaged.docx
```

### 4. Choose a Theme

Select one of the built-in accessible SMACSS themes for HTML and PDF output:

```bash
docx-a11y document.docx --format html,pdf --theme ocean --output-dir ./reports
```

Available bundled themes:
- `light`: Clean corporate theme (default).
- `dark`: High-legibility charcoal dark mode.
- `ocean`: Marine blue palette.
- `forest`: Botanical green palette.
- `high-contrast`: Maximum contrast pure black and yellow/cyan accents.
- `print`: Theme-independent black-on-white stylesheet relying on text-weight cues.

---

## Custom Branding & User Themes

You can define custom, human-editable themes without touching Python code. Place them in `~/.config/docx-a11y/themes/<theme-name>/`:

```
~/.config/docx-a11y/themes/brand/
├── theme.json
└── tokens.css
```

### `theme.json`
```json
{
  "name": "brand",
  "label": "Acme Brand Theme",
  "mode": "light",
  "default": false
}
```

### `tokens.css` (10 required CSS variables)
```css
:root {
  --bg: #ffffff;
  --fg: #1a1a1a;
  --muted: #cccccc;
  --accent: #0055aa;
  --link: #004488;
  --code-bg: #f5f5f5;
  --sev-critical: #b30000;
  --sev-serious: #cc5500;
  --sev-moderate: #886600;
  --sev-minor: #444444;
}
```

User themes automatically take precedence over bundled themes with matching names.

---

## WCAG 2.1 Coverage

| Rule ID | WCAG 2.1 SC | Level | Principle | Description | Auto-Fixable? |
|---|---|---|---|---|---|
| `image-alt-missing` | **1.1.1** Non-text Content | A | Perceivable | Visual asset lacks alt text or decorative flag | Triage / Manual |
| `table-header-missing` | **1.3.1** Info & Relationships | A | Perceivable | Table lacks designated header row (`w:tblHeader`) | Yes (`tblHeader` + `cantSplit`) |
| `heading-level-skipped` | **1.3.1** Info & Relationships | A | Perceivable | Heading level skips hierarchy (e.g. H1 -> H3) | Yes (re-level) |
| `headings-none` | **1.3.1** Info & Relationships | A | Perceivable | Document lacks semantic Heading styles | Yes (map or auto-promote) |
| `multiple-h1` | **1.3.1** Info & Relationships | A | Perceivable | Document contains multiple Heading 1 elements | Manual / Normalizable |
| `merged-cell` | **1.3.1** Info & Relationships | A | Perceivable | Merged cells (`gridSpan`/`vMerge`) break table structure | Manual / Unmergable |
| `color-contrast` | **1.4.3** Contrast (Minimum) | AA | Perceivable | Text color fails 4.5:1 contrast against page background | Yes (scales luminance) |
| `title-missing` | **2.4.2** Page Titled | A | Operable | Document core metadata missing title | Yes |
| `language-missing` | **3.1.1** Language of Page | A | Understandable | Default document language missing from `w:docDefaults` | Yes |

---

## Graphical Desktop Application (GUI)

For content creators, editors, and accessibility auditors remediating bulk Word documents without writing terminal commands:

```bash
# Launch via CLI flag:
docx-a11y --gui

# Or standalone launcher:
docx-a11y-gui
```

### GUI Features:
- **Bulk Directory Ingestion:** Scan and remediate directories of `.docx` files simultaneously.
- **Drag and Drop:** Drag individual `.docx` files or folders directly into the queue.
- **Visual Barrier Triage:** Resolve missing alt text, decorative image designations, and document titles interactively.
- **Multi-Format Reporting:** Export Markdown, HTML, tagged PDF, and audit JSON in any of the 6 SMACSS themes.
- **Threaded Execution:** Audit and remediation run in background threads, keeping the interface fluid.

---

## CLI Reference

```
usage: docx-a11y [-h] [--gui] [--format FORMAT] [--theme THEME] [--output-dir OUTPUT_DIR]
                 [--fix] [--triage] [--out-docx OUT_DOCX] [file]

Audit and remediate Microsoft Word .docx files against WCAG 2.1 AA standards.

positional arguments:
  file                  Path to Word .docx file (or specify --gui)

options:
  -h, --help            show this help message and exit
  --gui                 Launch graphical user interface
  --format FORMAT       Report formats (comma-separated): md, html, pdf, json (default: md)
  --theme THEME         SMACSS theme for HTML/PDF reports: ['light', 'dark', 'ocean', 'forest', 'high-contrast', 'print']
  --output-dir OUTPUT_DIR
                        Directory to save generated reports (default: .)
  --fix                 Perform deterministic remediation
  --triage              Launch interactive human-in-the-loop triage session
  --out-docx OUT_DOCX   Output path for remediated .docx file
```

### Exit Codes
- `0`: Document passes all blocking WCAG 2.1 AA checks.
- `1`: Document contains unresolved blocking accessibility barriers.
- `2`: Input file error / invalid argument.

---

## Programmatic Python API

```python
from pathlib import Path
from docx_a11y.audit import audit_file
from docx_a11y.remediate import remediate_document

# 1. Audit a document
result = audit_file(Path("document.docx"))
print(f"Total findings: {result['summary']['total']}")
print(f"Blocking findings: {result['summary']['blocking']}")

# 2. Remediate deterministically (original file stays untouched)
if result['summary']['blocking'] > 0:
    fixes = remediate_document(Path("document.docx"), Path("document-remediated.docx"))
    print(f"Applied fixes: {fixes}")
```

---

## Running Tests

```bash
pytest --cov=docx_a11y tests/
```

---

## License

MIT License. See [LICENSE](LICENSE) for details.
