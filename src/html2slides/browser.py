"""
Playwright browser automation and page lifecycle management for layout computation.
"""

import os
import sys
from typing import Optional, List
from playwright.sync_api import sync_playwright, Browser, Page, Playwright

from .config import Config, SelectorOverride
from .security import sanitize_html


class BrowserSession:
    """Manages Playwright browser lifecycle, page rendering, and resource blocking."""

    def __init__(self, config: Config):
        self.config = config
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._page: Optional[Page] = None

    def __enter__(self) -> "BrowserSession":
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def start(self):
        """Start Playwright and launch Chromium (with fallback to system Chrome)."""
        self._playwright = sync_playwright().start()

        launch_args = [
            "--disable-web-security",
            "--allow-file-access-from-files",
            "--font-render-hinting=none",
        ]

        # 1. Try launching bundled Chromium
        try:
            self._browser = self._playwright.chromium.launch(
                headless=True,
                args=launch_args
            )
        except Exception as e:
            # 2. Fallback to system Google Chrome channel
            try:
                self._browser = self._playwright.chromium.launch(
                    channel="chrome",
                    headless=True,
                    args=launch_args
                )
            except Exception:
                # 3. Fallback to explicit macOS Chrome binary path
                mac_chrome = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
                if sys.platform == "darwin" and os.path.exists(mac_chrome):
                    self._browser = self._playwright.chromium.launch(
                        executable_path=mac_chrome,
                        headless=True,
                        args=launch_args
                    )
                else:
                    raise RuntimeError(f"Failed to launch browser: {e}. Please run 'playwright install chromium'.")

        context = self._browser.new_context(
            viewport={"width": 1920, "height": 1080},
            device_scale_factor=1.0,
        )
        self._page = context.new_page()

        # Network blocking if allow_network is False
        if not self.config.security.allow_network:
            def route_handler(route):
                url = route.request.url.lower()
                if url.startswith("file:") or url.startswith("data:") or url.startswith("about:"):
                    route.continue_()
                else:
                    route.abort()

            self._page.route("**/*", route_handler)

    def load_html(self, html_path_or_content: str, is_file: bool = True) -> List[str]:
        """
        Load HTML file or string into page, sanitize content, apply CSS overrides,
        and wait for fonts and images to be fully rendered.
        """
        if not self._page:
            raise RuntimeError("Browser session not started.")

        warnings: List[str] = []

        if is_file:
            if not os.path.exists(html_path_or_content):
                raise FileNotFoundError(f"HTML file not found: {html_path_or_content}")
            with open(html_path_or_content, "r", encoding="utf-8", errors="replace") as f:
                raw_html = f.read()
            base_dir = os.path.abspath(os.path.dirname(html_path_or_content))
        else:
            raw_html = html_path_or_content
            base_dir = os.getcwd()

        # Sanitize HTML
        clean_html, sec_warnings = sanitize_html(
            raw_html,
            allow_network=self.config.security.allow_network,
            allow_javascript=self.config.security.allow_javascript,
        )
        warnings.extend(sec_warnings)

        # Build custom CSS overrides
        override_css = self._build_override_css(self.config.overrides)

        # Inject base tag to resolve relative paths correctly
        if "<head>" in clean_html:
            clean_html = clean_html.replace("<head>", f'<head><base href="file://{base_dir}/"><style>{override_css}</style>')
        else:
            clean_html = f'<base href="file://{base_dir}/"><style>{override_css}</style>' + clean_html

        self._page.set_content(clean_html, wait_until="load")

        # Wait for web fonts and images
        try:
            self._page.evaluate("() => document.fonts.ready")
        except Exception:
            pass

        # Wait for all images to complete loading
        try:
            self._page.evaluate("""
                () => Promise.all(
                    Array.from(document.images)
                        .filter(img => !img.complete)
                        .map(img => new Promise(resolve => {
                            img.onload = img.onerror = resolve;
                        }))
                )
            """)
        except Exception:
            pass

        return warnings

    def _build_override_css(self, overrides: List[SelectorOverride]) -> str:
        """Convert SelectorOverrides into injected CSS rules with !important."""
        rules = []
        for ov in overrides:
            declarations = []
            if ov.font_family:
                declarations.append(f'font-family: "{ov.font_family}" !important;')
            if ov.font_size_pt is not None:
                declarations.append(f'font-size: {ov.font_size_pt * 96.0 / 72.0}px !important;')
            if ov.font_weight is not None:
                declarations.append(f'font-weight: {ov.font_weight} !important;')
            if ov.color:
                declarations.append(f'color: {ov.color} !important;')
            if ov.text_align:
                declarations.append(f'text-align: {ov.text_align} !important;')
            if ov.background_color:
                declarations.append(f'background-color: {ov.background_color} !important;')

            if declarations:
                rules.append(f"{ov.selector} {{ {' '.join(declarations)} }}")
        return "\n".join(rules)

    @property
    def page(self) -> Page:
        if not self._page:
            raise RuntimeError("Browser session not active.")
        return self._page

    def close(self):
        """Close browser and Playwright."""
        if self._page:
            try:
                self._page.close()
            except Exception:
                pass
            self._page = None
        if self._browser:
            try:
                self._browser.close()
            except Exception:
                pass
            self._browser = None
        if self._playwright:
            try:
                self._playwright.stop()
            except Exception:
                pass
            self._playwright = None
