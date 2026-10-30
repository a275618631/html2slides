"""
Test Enterprise 6-Slide Regression Fixture (deck_sample.html).
"""

import os
import pytest
from pptx import Presentation
from pptx.util import Inches

from html2slides.config import Config
from html2slides.browser import BrowserSession
from html2slides.extractor import DOMExtractor
from html2slides.pptx_renderer import PPTXRenderer
from html2slides.validator import PresentationValidator


def test_enterprise_6slide_regression(tmp_path):
    fixture_path = os.path.abspath("examples/enterprise_ai_deck/deck_sample.html")
    assert os.path.exists(fixture_path), f"Enterprise HTML fixture not found at {fixture_path}"

    config = Config()
    config.deck.slide_selector = ".slide-container"
    config.deck.width_in = 13.333
    config.deck.height_in = 7.5

    # 1. Extraction
    with BrowserSession(config) as browser:
        browser.load_html(fixture_path, is_file=True)
        extractor = DOMExtractor(config)
        deck_model, warnings = extractor.extract_deck(browser.page)

    assert len(deck_model.slides) == 6, f"Expected 6 slides, got {len(deck_model.slides)}"

    # 2. Rendering
    out_pptx = str(tmp_path / "enterprise_regression.pptx")
    renderer = PPTXRenderer(deck_model)
    renderer.render(out_pptx)

    # 3. PPTX Validation
    validator = PresentationValidator(out_pptx, deck_model)
    report = validator.validate(warnings)

    assert report["status"] == "PASS"
    assert report["slides"] == 6
    assert report["shape_elements"] > 10
    assert report["text_elements"] + report["shape_elements"] > 20

    # 4. Content Verification
    prs = Presentation(out_pptx)
    assert len(prs.slides) == 6
    assert abs(prs.slide_width.inches - 13.333) < 0.01
    assert abs(prs.slide_height.inches - 7.5) < 0.01

    all_slide_texts = []
    for s in prs.slides:
        slide_text = " ".join(shape.text_frame.text for shape in s.shapes if shape.has_text_frame)
        all_slide_texts.append(slide_text)

    # Slide 1 Content Check
    assert "Manufacturing Systems" in all_slide_texts[0] or "FOUNDATION" in all_slide_texts[0]
    # Slide 2 Content Check
    assert "REDUNDANCY" in all_slide_texts[1] or "Failover" in all_slide_texts[1]
    # Slide 3 Content Check
    assert "PRODUCTION DECISION" in all_slide_texts[2] or "DETERMINISTIC" in all_slide_texts[2]
    # Slide 4 Content Check
    assert "99.8%" in all_slide_texts[3] or "Physical" in all_slide_texts[3]
    # Slide 5 Content Check
    assert "Data Path" in all_slide_texts[4] or "Control Path" in all_slide_texts[4]
    # Slide 6 Content Check
    assert "Architecture Thinking" in all_slide_texts[5] or "Context" in all_slide_texts[5]
