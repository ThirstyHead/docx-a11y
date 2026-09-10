"""Packaging infrastructure and collision prevention tests for docx-a11y."""
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

def test_packaging_entrypoints_exist():
    gui_entry = REPO_ROOT / "packaging" / "entrypoints" / "gui_main.py"
    cli_entry = REPO_ROOT / "packaging" / "entrypoints" / "cli_main.py"
    assert gui_entry.exists(), "packaging/entrypoints/gui_main.py must exist"
    assert cli_entry.exists(), "packaging/entrypoints/cli_main.py must exist"
    assert "docx_a11y.gui.app" in gui_entry.read_text(encoding="utf-8")
    assert "docx_a11y.cli" in cli_entry.read_text(encoding="utf-8")

def test_packaging_specs_exist_and_avoid_collision():
    gui_spec = REPO_ROOT / "packaging" / "specs" / "docx-a11y-gui.spec"
    cli_spec = REPO_ROOT / "packaging" / "specs" / "docx-a11y-cli.spec"
    assert gui_spec.exists(), "docx-a11y-gui.spec must exist"
    assert cli_spec.exists(), "docx-a11y-cli.spec must exist"

    gui_spec_content = gui_spec.read_text(encoding="utf-8")
    cli_spec_content = cli_spec.read_text(encoding="utf-8")

    # GUI COLLECT block must output to 'docx-a11y-gui' to avoid collision with CLI single-file binary 'docx-a11y'
    assert "name='docx-a11y-gui'" in gui_spec_content, (
        "COLLECT block in docx-a11y-gui.spec must use name='docx-a11y-gui' to avoid directory collision"
    )

    # CLI spec must produce standalone binary 'docx-a11y' and exclude GUI libraries
    assert "name='docx-a11y'" in cli_spec_content
    assert "'PySide6'" in cli_spec_content

def test_inno_setup_script_targets_gui_bundle():
    iss_file = REPO_ROOT / "packaging" / "windows" / "docx-a11y.iss"
    assert iss_file.exists(), "docx-a11y.iss must exist"
    iss_content = iss_file.read_text(encoding="utf-8")

    # Must source files from docx-a11y-gui directory bundle
    assert r"dist\docx-a11y-gui\*" in iss_content

def test_appimage_script_targets_gui_bundle():
    appimage_script = REPO_ROOT / "packaging" / "linux" / "build_appimage.sh"
    assert appimage_script.exists(), "build_appimage.sh must exist"
    script_content = appimage_script.read_text(encoding="utf-8")

    # Must stage files from docx-a11y-gui directory bundle
    assert "docx-a11y-gui" in script_content
    assert "APPIMAGE_EXTRACT_AND_RUN=1" in script_content

def test_icons_generated():
    icons_dir = REPO_ROOT / "packaging" / "icons"
    if not (icons_dir / "docx-a11y.png").exists():
        import subprocess
        import sys
        script = REPO_ROOT / "packaging" / "scripts" / "generate_icons.py"
        subprocess.run([sys.executable, str(script)], check=True)
    assert (icons_dir / "docx-a11y.png").exists()
    assert (icons_dir / "docx-a11y.ico").exists()
    assert (icons_dir / "docx-a11y.icns").exists()


def test_packaging_uses_shared_engine():
    gen_script = (REPO_ROOT / "packaging" / "scripts" / "generate_icons.py").read_text(encoding="utf-8")
    assert "engine_a11y.packaging.icons" in gen_script
    gui_spec = (REPO_ROOT / "packaging" / "specs" / "docx-a11y-gui.spec").read_text(encoding="utf-8")
    assert "engine_a11y.packaging.specs" in gui_spec

