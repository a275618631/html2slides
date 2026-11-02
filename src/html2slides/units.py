"""
Units, coordinate mapping, and CSS color conversion utilities.
"""

import re
from typing import Tuple, Optional

# Standard CSS Color Name Mapping
CSS_COLOR_NAMES = {
    "white": (255, 255, 255),
    "black": (0, 0, 0),
    "transparent": (0, 0, 0),  # Handled with alpha=0.0
    "red": (255, 0, 0),
    "green": (0, 128, 0),
    "blue": (0, 0, 255),
    "yellow": (255, 255, 0),
    "gray": (128, 128, 128),
    "grey": (128, 128, 128),
    "silver": (192, 192, 192),
    "lightgray": (211, 211, 211),
    "darkgray": (169, 169, 169),
    "navy": (0, 0, 128),
    "orange": (255, 165, 0),
    "purple": (128, 0, 128),
    "teal": (0, 128, 128),
    "amber": (194, 65, 12),
}


def px_to_inch(px: float, html_dimension: float, ppt_dimension: float) -> float:
    """
    Convert HTML coordinate/size in px to PowerPoint dimension in inches,
    scaled proportionally to the slide canvas.
    """
    if html_dimension <= 0:
        return 0.0
    return (px / html_dimension) * ppt_dimension


def px_to_pt(px: float) -> float:
    """
    Convert CSS computed font-size / border in px to typography points (pt).
    Standard CSS formula: 1pt = 1/72 inch, 1px = 1/96 inch -> pt = px * 72 / 96 = px * 0.75
    """
    return px * 72.0 / 96.0


def pt_to_px(pt: float) -> float:
    """Convert typography points to CSS pixels."""
    return pt * 96.0 / 72.0


def parse_color(color_str: Optional[str]) -> Tuple[Optional[Tuple[int, int, int]], float]:
    """
    Parse a CSS color string (hex, rgb, rgba, named color) into an RGB tuple (0-255) and alpha (0.0-1.0).
    Returns (None, 0.0) for transparent / none / invalid colors.
    """
    if not color_str:
        return (None, 0.0)

    s = color_str.strip().lower()

    if s in ("transparent", "none", "rgba(0, 0, 0, 0)", "rgba(0,0,0,0)"):
        return (None, 0.0)

    if s in CSS_COLOR_NAMES:
        return (CSS_COLOR_NAMES[s], 1.0)

    # Hex: #RGB or #RRGGBB or #RRGGBBAA
    if s.startswith("#"):
        hex_val = s[1:]
        if len(hex_val) == 3:
            r = int(hex_val[0] * 2, 16)
            g = int(hex_val[1] * 2, 16)
            b = int(hex_val[2] * 2, 16)
            return ((r, g, b), 1.0)
        elif len(hex_val) == 4:
            r = int(hex_val[0] * 2, 16)
            g = int(hex_val[1] * 2, 16)
            b = int(hex_val[2] * 2, 16)
            a = int(hex_val[3] * 2, 16) / 255.0
            return ((r, g, b), a)
        elif len(hex_val) == 6:
            r = int(hex_val[0:2], 16)
            g = int(hex_val[2:4], 16)
            b = int(hex_val[4:6], 16)
            return ((r, g, b), 1.0)
        elif len(hex_val) == 8:
            r = int(hex_val[0:2], 16)
            g = int(hex_val[2:4], 16)
            b = int(hex_val[4:6], 16)
            a = int(hex_val[6:8], 16) / 255.0
            return ((r, g, b), a)

    # rgb(...) or rgba(...)
    rgb_match = re.match(r"rgba?\s*\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)(?:\s*,\s*([\d.]+))?\s*\)", s)
    if rgb_match:
        r = max(0, min(255, int(float(rgb_match.group(1)))))
        g = max(0, min(255, int(float(rgb_match.group(2)))))
        b = max(0, min(255, int(float(rgb_match.group(3)))))
        a = 1.0
        if rgb_match.group(4) is not None:
            a = max(0.0, min(1.0, float(rgb_match.group(4))))
        if a <= 0.01:
            return (None, 0.0)
        return ((r, g, b), a)

    return (None, 0.0)


def parse_px(value_str: Optional[str]) -> float:
    """Parse numeric pixel string like '14px', '2.5px', or '0' into float."""
    if not value_str:
        return 0.0
    s = value_str.strip().lower()
    if s.endswith("px"):
        s = s[:-2].strip()
    try:
        return float(s)
    except ValueError:
        return 0.0
