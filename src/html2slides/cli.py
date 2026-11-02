"""
Command Line Interface (CLI) for html2slides.
"""

import os
import sys
import argparse
from typing import Optional

from .config import Config, DeckConfig, FontConfig, SelectorOverride, SecurityConfig, GoogleSlidesConfig
from .browser import BrowserSession
from .extractor import DOMExtractor
from .pptx_renderer import PPTXRenderer
from .validator import PresentationValidator
from .google_slides import GoogleSlidesUploader, GOOGLE_API_AVAILABLE


def print_pass(msg: str):
    print(f"\033[92mPASS\033[0m  {msg}")


def print_warn(msg: str):
    print(f"\033[93mWARN\033[0m  {msg}")


def print_fail(msg: str):
    print(f"\033[91mFAIL\033[0m  {msg}")


def main():
    parser = argparse.ArgumentParser(
        prog="html2slides",
        description="Universal Editable HTML to PowerPoint (PPTX) and Google Slides Converter."
    )
    parser.add_argument("input", help="Path to input HTML slide deck file.")
    parser.add_argument("-o", "--output", help="Path to output PPTX file (default: output/<input_name>.pptx).")
    parser.add_argument("--config", help="Path to html2slides.toml configuration file.")
    parser.add_argument("--slide-selector", help="CSS selector for slide containers (e.g. '.slide-container').")
    parser.add_argument("--font", help="Default or override font family (e.g. 'Noto Sans TC').")
    parser.add_argument("--font-mode", choices=["preserve", "override", "map"], help="Font resolution mode.")
    parser.add_argument("--google-slides", action="store_true", help="Convert generated PPTX to native Google Slides via Drive API.")
    parser.add_argument("--drive-folder-id", help="Google Drive destination folder ID.")
    parser.add_argument("--strict", action="store_true", help="Treat any warning as fatal failure.")
    parser.add_argument("--allow-network", action="store_true", help="Allow loading remote network resources.")
    parser.add_argument("--allow-javascript", action="store_true", help="Allow executing scripts in HTML.")
    parser.add_argument("--report", action="store_true", default=True, help="Generate conversion_report.json (default: True).")

    args = parser.parse_args()

    input_path = os.path.abspath(args.input)
    if not os.path.exists(input_path):
        print_fail(f"Input HTML file not found: {input_path}")
        sys.exit(1)

    # 1. Load Configuration
    config = Config.load(args.config)

    # CLI Overrides
    if args.slide_selector:
        config.deck.slide_selector = args.slide_selector
    if args.font:
        config.fonts.default = args.font
    if args.font_mode:
        config.fonts.mode = args.font_mode
    if args.allow_network:
        config.security.allow_network = True
    if args.allow_javascript:
        config.security.allow_javascript = True
    if args.drive_folder_id:
        config.google_slides.drive_folder_id = args.drive_folder_id

    # Determine Output Paths
    input_stem = os.path.splitext(os.path.basename(input_path))[0]
    out_dir = os.path.abspath("output")
    os.makedirs(out_dir, exist_ok=True)
    
    if args.output:
        output_pptx = os.path.abspath(args.output)
    else:
        output_pptx = os.path.join(out_dir, f"{input_stem}.pptx")

    all_warnings = []

    # 2. Browser Layout & DOM Extraction (Playwright)
    try:
        with BrowserSession(config) as browser:
            sec_warnings = browser.load_html(input_path, is_file=True)
            all_warnings.extend(sec_warnings)
            print_pass("HTML parsed and sanitized")

            extractor = DOMExtractor(config)
            deck_model, extract_warnings = extractor.extract_deck(browser.page)
            all_warnings.extend(extract_warnings)
            
            slide_count = len(deck_model.slides)
            if slide_count == 0:
                print_fail("No slides detected matching selector.")
                sys.exit(1)
            print_pass(f"{slide_count} slides detected")
    except Exception as e:
        print_fail(f"Browser extraction failed: {e}")
        sys.exit(1)

    # Count intermediate elements
    total_text = sum(1 for s in deck_model.slides for el in s.elements if el.__class__.__name__ == "TextElement" or (hasattr(el, "paragraphs") and el.paragraphs))
    total_shapes = sum(1 for s in deck_model.slides for el in s.elements if el.__class__.__name__ == "ShapeElement")
    total_images = sum(1 for s in deck_model.slides for el in s.elements if el.__class__.__name__ == "ImageElement")

    print_pass(f"{total_text} editable text objects")
    print_pass(f"{total_shapes} editable shapes")
    print_pass(f"{total_images} images")

    # 3. PPTX Rendering (python-pptx)
    try:
        renderer = PPTXRenderer(deck_model)
        renderer.render(output_pptx)
        print_pass(f"PPTX generated: {output_pptx}")
    except Exception as e:
        print_fail(f"PPTX rendering failed: {e}")
        sys.exit(1)

    # 4. PPTX Validation
    validator = PresentationValidator(output_pptx, deck_model)
    report_data = validator.validate(all_warnings)
    print_pass("PPTX validation")

    # Print any warnings
    for w in all_warnings:
        print_warn(w)

    # 5. Optional Google Slides Conversion
    if args.google_slides:
        if not GOOGLE_API_AVAILABLE:
            print_fail("Google Slides dependencies not installed.")
        else:
            uploader = GoogleSlidesUploader()
            pres_id, view_url, err = uploader.upload_and_convert(
                pptx_path=output_pptx,
                presentation_name=input_stem,
                drive_folder_id=config.google_slides.drive_folder_id
            )
            if err:
                print_fail(f"Google Slides conversion failed: {err}")
                report_data["google_slides"] = {"status": "FAIL", "error": err}
            else:
                print_pass("Google Slides converted")
                print(f"URL   {view_url}")
                url_file = os.path.join(out_dir, f"{input_stem}_google_slides_url.txt")
                with open(url_file, "w", encoding="utf-8") as f:
                    f.write(view_url + "\n")
                
                # Validate Google Slides readback
                gs_val = uploader.validate_google_slides(pres_id)
                report_data["google_slides"] = gs_val
                if gs_val.get("status") == "PASS":
                    print_pass(f"Google Slides validated ({gs_val.get('slide_count')} slides, {gs_val.get('shape_elements')} editable shapes)")

    # 6. Save conversion report
    if args.report:
        report_path = os.path.join(out_dir, "conversion_report.json")
        validator.save_report(report_path, report_data)
        print_pass(f"Report saved: {report_path}")

    # Strict check
    if args.strict and all_warnings:
        print_fail(f"Strict mode enabled: {len(all_warnings)} warnings encountered.")
        sys.exit(1)


if __name__ == "__main__":
    main()
