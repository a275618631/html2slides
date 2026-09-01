"""
Font strategy, font family resolution, availability validation, and OpenXML East Asian / CJK typeface utilities.
"""

import os
import sys
import re
from typing import Dict, Optional, Tuple, Set
from pptx.oxml import parse_xml
from pptx.oxml.ns import nsdecls, qn

from .config import FontConfig

# Common standard fonts available across platforms
STANDARD_FONTS = {
    "Arial", "Helvetica", "Calibri", "Segoe UI", "Aptos", "Times New Roman",
    "Georgia", "Verdana", "Tahoma", "Trebuchet MS", "Courier New",
    "Noto Sans TC", "Noto Sans SC", "Noto Sans", "Microsoft JhengHei",
    "PingFang TC", "PingFang SC", "Heiti TC", "SimSun", "PMingLiU", "DFKai-SB"
}

# CJK Unicode range regex
CJK_REGEX = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff\u3040-\u30ff\u31f0-\u31ff\uac00-\ud7af]")


def contains_cjk(text: str) -> bool:
    """Check if string contains any CJK / East Asian characters."""
    if not text:
        return False
    return bool(CJK_REGEX.search(text))


def clean_font_name(name: str) -> str:
    """Clean quote characters and whitespace from font family name."""
    s = name.strip()
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        s = s[1:-1].strip()
    return s


def resolve_font(
    css_font_family: Optional[str],
    font_config: FontConfig
) -> Tuple[str, Optional[str]]:
    """
    Resolve target font name based on CSS computed font-family and FontConfig mode.
    Returns (resolved_font_name, warning_message_or_None).
    """
    # 1. Override mode: unconditionally use configured default font
    if font_config.mode == "override":
        return (font_config.default, None)

    # If no font family specified in CSS, fallback to default
    if not css_font_family:
        return (font_config.default, None)

    # Parse comma-separated font fallback list
    candidates = [clean_font_name(f) for f in css_font_family.split(",") if clean_font_name(f)]
    
    # 2. Map mode or Preserve with Map lookup
    for candidate in candidates:
        if candidate in font_config.map:
            return (font_config.map[candidate], None)

    # Filter out generic CSS font families
    generic_families = {"sans-serif", "serif", "monospace", "cursive", "fantasy", "system-ui"}
    valid_candidates = [c for c in candidates if c.lower() not in generic_families]

    # In preserve mode, return first valid candidate or default
    if valid_candidates:
        chosen = valid_candidates[0]
        # Ignore system prefixes like -apple-system, BlinkMacSystemFont if no map matched
        if chosen in ("-apple-system", "BlinkMacSystemFont"):
            return (font_config.default, None)
        return (chosen, None)

    return (font_config.default, None)


def check_font_availability(font_name: str) -> Tuple[bool, Optional[str]]:
    """
    Check if a font is generally available or known.
    Returns (is_available, warning_message_if_not).
    """
    # For common fonts and known Google Fonts, consider available
    if font_name in STANDARD_FONTS:
        return (True, None)

    # On macOS, check /Library/Fonts or /System/Library/Fonts
    if sys.platform == "darwin":
        font_dirs = ["/Library/Fonts", "/System/Library/Fonts", os.path.expanduser("~/Library/Fonts")]
        for d in font_dirs:
            if os.path.exists(d):
                for f in os.listdir(d):
                    if font_name.lower().replace(" ", "") in f.lower().replace(" ", ""):
                        return (True, None)

    # If font availability cannot be confirmed, return warning
    warning = f"Font '{font_name}' may not be natively installed. PowerPoint will use its fallback substitution."
    return (False, warning)


def apply_run_font(run, font_name: str, text: str = "") -> None:
    """
    Apply typography and OpenXML typeface tags (Latin, East Asian, Complex Script)
    to a python-pptx Run without monkey-patching python-pptx.
    """
    run.font.name = font_name

    # Set underlying OpenXML element attributes for East Asian and Latin scripts
    rPr = run._r.get_or_add_rPr()

    # Set a:latin
    latin_elem = rPr.find(qn("a:latin"))
    if latin_elem is None:
        latin_elem = parse_xml(f'<a:latin {nsdecls("a")} typeface="{font_name}"/>')
        rPr.append(latin_elem)
    else:
        latin_elem.set("typeface", font_name)

    # Set a:ea (East Asian / CJK)
    ea_elem = rPr.find(qn("a:ea"))
    if ea_elem is None:
        ea_elem = parse_xml(f'<a:ea {nsdecls("a")} typeface="{font_name}"/>')
        rPr.append(ea_elem)
    else:
        ea_elem.set("typeface", font_name)

    # Set a:cs (Complex Script)
    cs_elem = rPr.find(qn("a:cs"))
    if cs_elem is None:
        cs_elem = parse_xml(f'<a:cs {nsdecls("a")} typeface="{font_name}"/>')
        rPr.append(cs_elem)
    else:
        cs_elem.set("typeface", font_name)
