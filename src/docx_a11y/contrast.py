"""WCAG relative-luminance contrast math adhering strictly to W3C specifications.

Delegates core math to engine_a11y.contrast.
"""
from engine_a11y.contrast import (
    THRESHOLD_LARGE,
    THRESHOLD_NORMAL,
    adjust_color_for_contrast,
    contrast_ratio,
    hex_to_rgb,
    is_contrast_acceptable,
    relative_luminance,
)

__all__ = [
    "THRESHOLD_NORMAL",
    "THRESHOLD_LARGE",
    "hex_to_rgb",
    "relative_luminance",
    "contrast_ratio",
    "is_contrast_acceptable",
    "adjust_color_for_contrast",
]
