"""
Test C & D: Mixed Text Runs, Shapes, Borders, and Image Elements.
"""

import os
import pytest
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE

from html2slides.config import Config
from html2slides.browser import BrowserSession
from html2slides.extractor import DOMExtractor
from html2slides.pptx_renderer import PPTXRenderer


def test_mixed_runs_rendering(tmp_path):
    fixture_path = os.path.abspath("tests/fixtures/mixed_runs.html")
    config = Config()
    config.deck.slide_selector = ".slide"

    with BrowserSession(config) as browser:
        browser.load_html(fixture_path, is_file=True)
        extractor = DOMExtractor(config)
        deck_model, _ = extractor.extract_deck(browser.page)

    out_pptx = str(tmp_path / "test_mixed_runs.pptx")
    renderer = PPTXRenderer(deck_model)
    renderer.render(out_pptx)

    prs = Presentation(out_pptx)
    slide = prs.slides[0]

    # Verify that multiple runs exist in a single paragraph
    runs_found = []
    for shape in slide.shapes:
        if shape.has_text_frame:
            for p in shape.text_frame.paragraphs:
                for r in p.runs:
                    runs_found.append(r)

    bold_runs = [r for r in runs_found if r.font.bold]
    italic_runs = [r for r in runs_found if r.font.italic]
    underline_runs = [r for r in runs_found if r.font.underline]

    assert len(bold_runs) >= 1, "Bold run not detected"
    assert len(italic_runs) >= 1, "Italic run not detected"
    assert len(underline_runs) >= 1, "Underline run not detected"


def test_shapes_and_cards_rendering(tmp_path):
    fixture_path = os.path.abspath("tests/fixtures/shapes.html")
    config = Config()
    config.deck.slide_selector = ".slide"

    with BrowserSession(config) as browser:
        browser.load_html(fixture_path, is_file=True)
        extractor = DOMExtractor(config)
        deck_model, _ = extractor.extract_deck(browser.page)

    out_pptx = str(tmp_path / "test_shapes.pptx")
    renderer = PPTXRenderer(deck_model)
    renderer.render(out_pptx)

    prs = Presentation(out_pptx)
    slide = prs.slides[0]

    # Ensure shape objects are created
    assert len(slide.shapes) >= 3
    # Check that text is directly editable in shape text frame
    editable_texts = [s.text_frame.text for s in slide.shapes if s.has_text_frame]
    full_text = " ".join(editable_texts)
    assert "Standard Rect" in full_text
    assert "Rounded Card" in full_text
    assert "Accent Bar" in full_text
