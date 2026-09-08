"""Theme loader and SMACSS layer assembler with user theme support."""
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

BUNDLED_DIR = Path(__file__).parent / "themes"
BUNDLED_THEMES = ["light", "dark", "high-contrast", "ocean", "forest", "print"]
DEFAULT_USER_CONFIG_DIR = Path.home() / ".config" / "docx-a11y"


def _load_manifest(path: Path) -> Dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    for req in ("name", "label", "mode"):
        if req not in data:
            raise ValueError(f"Theme manifest {path} missing required field '{req}'")
    data.setdefault("default", False)
    return data


def available_themes(config_dir: Optional[str | Path] = None) -> List[Dict[str, Any]]:
    """Return all theme manifests. User themes override bundled themes with identical names."""
    themes: list[dict[str, Any]] = []
    seen: set[str] = set()

    # 1. User themes
    user_cfg = Path(config_dir) if config_dir else DEFAULT_USER_CONFIG_DIR
    user_theme_dir = user_cfg / "themes"
    if user_theme_dir.is_dir():
        for d in sorted(user_theme_dir.iterdir()):
            manifest = d / "theme.json"
            if d.is_dir() and manifest.exists():
                m_data = _load_manifest(manifest)
                themes.append(m_data)
                seen.add(m_data["name"])

    # 2. Bundled themes
    for name in BUNDLED_THEMES:
        if name in seen:
            continue
        manifest = BUNDLED_DIR / name / "theme.json"
        if manifest.exists():
            themes.append(_load_manifest(manifest))
    return themes


def theme_css(name: str = "light", config_dir: Optional[str | Path] = None) -> str:
    """Assemble the complete SMACSS stylesheet for a named theme."""
    target_dir: Optional[Path] = None

    user_cfg = Path(config_dir) if config_dir else DEFAULT_USER_CONFIG_DIR
    candidate = user_cfg / "themes" / name
    if candidate.is_dir() and (candidate / "tokens.css").exists():
        target_dir = candidate

    if not target_dir:
        candidate = BUNDLED_DIR / name
        if candidate.is_dir() and (candidate / "tokens.css").exists():
            target_dir = candidate

    if not target_dir:
        raise KeyError(
            f"Theme '{name}' not found. Available: {[t['name'] for t in available_themes(config_dir)]}"
        )

    parts = [f"/* docx-a11y theme: {name} */\n"]
    # 1. Tokens
    parts.append((target_dir / "tokens.css").read_text(encoding="utf-8").rstrip() + "\n")
    # 2. Objects
    parts.append((BUNDLED_DIR / "_layout" / "objects.css").read_text(encoding="utf-8").rstrip() + "\n")
    # 3. Units
    parts.append((BUNDLED_DIR / "_layout" / "units.css").read_text(encoding="utf-8").rstrip() + "\n")
    # 4. Overrides
    overrides = target_dir / "overrides.css"
    if overrides.exists():
        parts.append(overrides.read_text(encoding="utf-8").rstrip() + "\n")

    return "\n".join(parts)
