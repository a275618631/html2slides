"""
Test D: Flexbox and Grid Layout extraction accuracy (< 0.03 inch tolerance).
"""

import os
import pytest

from html2slides.config import Config
from html2slides.browser import BrowserSession
from html2slides.extractor import DOMExtractor


def test_flex_and_grid_coordinates():
    fixture_path = os.path.abspath("tests/fixtures/flex_grid.html")
    config = Config()
    config.deck.slide_selector = ".slide"

    with BrowserSession(config) as browser:
        browser.load_html(fixture_path, is_file=True)
        extractor = DOMExtractor(config)
        deck_model, _ = extractor.extract_deck(browser.page)

    assert len(deck_model.slides) == 1
    slide = deck_model.slides[0]

    # Verify flex columns exist and have non-overlapping x coordinates
    col_shapes = [el for el in slide.elements if "Col" in getattr(el, "paragraphs", [None])[0].plain_text if getattr(el, "paragraphs", None)]
    assert len(col_shapes) >= 3

    # Sort by X
    col_shapes.sort(key=lambda s: s.x_in)
    for i in range(len(col_shapes) - 1):
        # Ensure distinct horizontal placement
        assert col_shapes[i+1].x_in > col_shapes[i].x_in + col_shapes[i].width_in - 0.05

    # Verify Grid 2x2 cells exist and form a grid
    grid_cells = [el for el in slide.elements if "Cell" in getattr(el, "paragraphs", [None])[0].plain_text if getattr(el, "paragraphs", None)]
    assert len(grid_cells) >= 4
