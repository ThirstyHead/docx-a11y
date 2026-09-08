"""WCAG relative-luminance contrast math adhering strictly to W3C specifications."""
from typing import Optional, Tuple


def hex_to_rgb(hexstr: str) -> Optional[Tuple[int, int, int]]:
    """Parse '#RRGGBB' or 'RRGGBB' into (r, g, b) ints, or None if malformed."""
    if hexstr is None:
        return None
    s = hexstr.strip().lstrip("#")
    if len(s) == 3:
        s = "".join(c * 2 for c in s)
    if len(s) != 6:
        return None
    try:
        return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))
    except ValueError:
        return None


def relative_luminance(rgb: Tuple[int, int, int]) -> float:
    """Return W3C relative luminance (0.0..1.0) of an (r, g, b) tuple (0..255)."""
    chans = []
    for c in rgb:
        cs = c / 255.0
        chans.append(cs / 12.92 if cs <= 0.04045 else ((cs + 0.055) / 1.055) ** 2.4)
    return 0.2126 * chans[0] + 0.7152 * chans[1] + 0.0722 * chans[2]


def contrast_ratio(fg: Tuple[int, int, int], bg: Tuple[int, int, int]) -> float:
    """Return WCAG contrast ratio (1.0..21.0) between two (r, g, b) tuples."""
    l1, l2 = relative_luminance(fg), relative_luminance(bg)
    if l1 < l2:
        l1, l2 = l2, l1
    return (l1 + 0.05) / (l2 + 0.05)


THRESHOLD_NORMAL = 4.5  # WCAG 1.4.3 AA
THRESHOLD_LARGE = 3.0   # WCAG 1.4.3 AA large text


def is_contrast_acceptable(fg_hex: str, bg_hex: str, is_large: bool = False) -> bool:
    """Check whether fg_hex meets WCAG AA contrast threshold against bg_hex."""
    fg = hex_to_rgb(fg_hex)
    bg = hex_to_rgb(bg_hex)
    if fg is None or bg is None:
        return False
    threshold = THRESHOLD_LARGE if is_large else THRESHOLD_NORMAL
    return contrast_ratio(fg, bg) >= threshold


def adjust_color_for_contrast(fg_hex: str, bg_hex: str, target_ratio: float = 4.5) -> str:
    """Deterministically scale luminosity of fg_hex to achieve target_ratio against bg_hex.

    If bg is light (relative luminance >= 0.5), darkens fg.
    If bg is dark (relative luminance < 0.5), brightens fg.
    Returns the adjusted 6-character hex color (e.g. 'E50000').
    """
    fg = hex_to_rgb(fg_hex)
    bg = hex_to_rgb(bg_hex)
    if fg is None or bg is None:
        return "000000"

    current_ratio = contrast_ratio(fg, bg)
    if current_ratio >= target_ratio:
        return fg_hex.strip().lstrip("#").upper()

    bg_lum = relative_luminance(bg)

    if bg_lum >= 0.5:
        # Darken fg towards black
        for step in range(99, -1, -1):
            factor = step / 100.0
            candidate = (int(fg[0] * factor), int(fg[1] * factor), int(fg[2] * factor))
            if contrast_ratio(candidate, bg) >= target_ratio:
                return f"{candidate[0]:02X}{candidate[1]:02X}{candidate[2]:02X}"
        return "000000"
    else:
        # Lighten fg towards white
        for step in range(1, 101):
            factor = step / 100.0
            candidate = (
                int(fg[0] + (255 - fg[0]) * factor),
                int(fg[1] + (255 - fg[1]) * factor),
                int(fg[2] + (255 - fg[2]) * factor),
            )
            if contrast_ratio(candidate, bg) >= target_ratio:
                return f"{candidate[0]:02X}{candidate[1]:02X}{candidate[2]:02X}"
        return "FFFFFF"
