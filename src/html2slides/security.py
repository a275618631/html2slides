"""
Security sanitization for input HTML content.
"""

import re
from typing import Tuple, List
from bs4 import BeautifulSoup


def sanitize_html(
    html_content: str,
    allow_network: bool = False,
    allow_javascript: bool = False
) -> Tuple[str, List[str]]:
    """
    Sanitize HTML string by stripping unsafe tags, scripts, and event handlers.
    Returns the sanitized HTML and a list of security warnings.
    """
    warnings: List[str] = []
    soup = BeautifulSoup(html_content, "html.parser")

    # 1. Remove <script> tags unless explicitly allowed
    if not allow_javascript:
        scripts = soup.find_all("script")
        if scripts:
            warnings.append(f"Security: Removed {len(scripts)} <script> tags from HTML.")
            for s in scripts:
                s.decompose()

    # 2. Strip inline event handlers (onclick, onload, onerror, etc.)
    event_attrs = [
        "onclick", "onload", "onerror", "onmouseover", "onmouseout",
        "onkeydown", "onkeyup", "onkeypress", "onsubmit", "onchange"
    ]
    cleaned_events_count = 0
    for tag in soup.find_all(True):
        for attr in event_attrs:
            if tag.has_attr(attr):
                del tag[attr]
                cleaned_events_count += 1
        
        # Check href / src for javascript: URI
        for attr in ("href", "src"):
            if tag.has_attr(attr):
                val = str(tag[attr]).strip().lower()
                if val.startswith("javascript:"):
                    tag[attr] = "#"
                    warnings.append(f"Security: Removed 'javascript:' URI in {tag.name}.")

        # Check for remote URLs when network is disallowed
        if not allow_network:
            for attr in ("src", "href"):
                if tag.has_attr(attr):
                    val = str(tag[attr]).strip()
                    if val.startswith("http://") or val.startswith("https://"):
                        warnings.append(f"Security: Blocked remote resource URL '{val}' (use --allow-network to enable).")
                        # For images, replace with placeholder or empty
                        if tag.name == "img":
                            tag[attr] = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='100' height='100'><rect width='100' height='100' fill='%23eee'/></svg>"

    if cleaned_events_count > 0:
        warnings.append(f"Security: Stripped {cleaned_events_count} inline JavaScript event handlers.")

    return str(soup), warnings
