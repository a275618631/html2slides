"""
DOM extraction logic to inspect computed styles, layout bounding boxes, and construct DeckModel.
"""

import os
import json
from typing import List, Dict, Any, Tuple, Optional
from playwright.sync_api import Page

from .model import (
    DeckModel, SlideModel, Element, ShapeElement, TextElement,
    ImageElement, LineElement, Paragraph, TextRun, Padding
)
from .config import Config
from .units import px_to_inch, px_to_pt, parse_color, parse_px
from .font_utils import resolve_font, check_font_availability


JS_EXTRACTOR_SCRIPT = """
(slideSelector) => {
    let slideElements = Array.from(document.querySelectorAll(slideSelector));
    if (slideElements.length === 0) {
        // Fallback: look for common slide classes or body
        slideElements = Array.from(document.querySelectorAll('.slide, .slide-container, section.slide, .page'));
    }
    if (slideElements.length === 0) {
        slideElements = [document.body];
    }

    const results = [];

    slideElements.forEach((slideEl, slideIndex) => {
        const slideRect = slideEl.getBoundingClientRect();
        const slideStyle = window.getComputedStyle(slideEl);
        
        const slideData = {
            index: slideIndex + 1,
            width_px: slideRect.width || 1333,
            height_px: slideRect.height || 750,
            bg_color: slideStyle.backgroundColor,
            elements: []
        };

        let domOrder = 0;

        function getZIndex(style) {
            const z = parseInt(style.zIndex, 10);
            return isNaN(z) ? 0 : z;
        }

        function isVisible(rect, style) {
            if (style.display === 'none' || style.visibility === 'hidden' || parseFloat(style.opacity) === 0) {
                return false;
            }
            if (rect.width <= 0.5 || rect.height <= 0.5) {
                return false;
            }
            return true;
        }

        // Helper to extract text runs from an element
        function extractTextRuns(el) {
            const runs = [];
            
            function walkNodes(node) {
                if (node.nodeType === Node.TEXT_NODE) {
                    const text = node.textContent;
                    if (text && text.trim().length > 0) {
                        const parentEl = node.parentElement;
                        const pStyle = window.getComputedStyle(parentEl);
                        runs.push({
                            text: text,
                            fontFamily: pStyle.fontFamily,
                            fontSizePx: parseFloat(pStyle.fontSize) || 16,
                            fontWeight: parseInt(pStyle.fontWeight, 10) || 400,
                            fontStyle: pStyle.fontStyle,
                            color: pStyle.color,
                            textDecoration: pStyle.textDecorationLine || pStyle.textDecoration,
                            whiteSpace: pStyle.whiteSpace
                        });
                    }
                } else if (node.nodeType === Node.ELEMENT_NODE) {
                    const elStyle = window.getComputedStyle(node);
                    if (elStyle.display !== 'none' && elStyle.visibility !== 'hidden') {
                        node.childNodes.forEach(walkNodes);
                    }
                }
            }

            walkNodes(el);
            return runs;
        }

        // Helper to extract paragraphs from a block element
        function extractParagraphs(containerEl) {
            const blockTags = ['P', 'H1', 'H2', 'H3', 'H4', 'H5', 'H6', 'DIV', 'LI', 'SECTION', 'HEADER'];
            const directBlocks = Array.from(containerEl.children).filter(child => {
                const s = window.getComputedStyle(child);
                return (blockTags.includes(child.tagName) || s.display === 'block' || s.display === 'flex') && isVisible(child.getBoundingClientRect(), s);
            });

            // If no distinct block children, treat container itself as one paragraph
            if (directBlocks.length === 0 || directBlocks.length === 1 && directBlocks[0].innerText === containerEl.innerText) {
                const cStyle = window.getComputedStyle(containerEl);
                const runs = extractTextRuns(containerEl);
                if (runs.length === 0) return [];
                return [{
                    runs: runs,
                    textAlign: cStyle.textAlign || 'left',
                    lineHeightPx: parseFloat(cStyle.lineHeight) || null
                }];
            }

            const paragraphs = [];
            directBlocks.forEach(block => {
                const bStyle = window.getComputedStyle(block);
                const runs = extractTextRuns(block);
                if (runs.length > 0) {
                    paragraphs.push({
                        runs: runs,
                        textAlign: bStyle.textAlign || 'left',
                        lineHeightPx: parseFloat(bStyle.lineHeight) || null
                    });
                }
            });

            return paragraphs;
        }

        // Traverse elements inside slide
        const allElements = slideEl.querySelectorAll('*');
        const processedElements = new Set();

        allElements.forEach(el => {
            if (['SCRIPT', 'STYLE', 'LINK', 'META', 'BR', 'WBR'].includes(el.tagName)) {
                return;
            }

            const rect = el.getBoundingClientRect();
            const style = window.getComputedStyle(el);

            if (!isVisible(rect, style)) {
                return;
            }

            domOrder++;
            const relX = rect.left - slideRect.left;
            const relY = rect.top - slideRect.top;
            const relW = rect.width;
            const relH = rect.height;

            // 1. Image Element (IMG)
            if (el.tagName === 'IMG') {
                slideData.elements.push({
                    type: 'image',
                    id: el.id || `img_${domOrder}`,
                    x_px: relX,
                    y_px: relY,
                    w_px: relW,
                    h_px: relH,
                    z_index: getZIndex(style),
                    dom_order: domOrder,
                    opacity: parseFloat(style.opacity) || 1.0,
                    src: el.currentSrc || el.src || '',
                    alt: el.alt || ''
                });
                processedElements.add(el);
                return;
            }

            // 2. SVG Element
            if (el.tagName === 'svg' || el.tagName === 'SVG') {
                slideData.elements.push({
                    type: 'svg',
                    id: el.id || `svg_${domOrder}`,
                    x_px: relX,
                    y_px: relY,
                    w_px: relW,
                    h_px: relH,
                    z_index: getZIndex(style),
                    dom_order: domOrder,
                    opacity: parseFloat(style.opacity) || 1.0,
                    outer_html: el.outerHTML
                });
                processedElements.add(el);
                return;
            }

            // Check background and borders
            const bg = style.backgroundColor;
            const hasBg = bg && bg !== 'transparent' && bg !== 'rgba(0, 0, 0, 0)';
            
            const bTopW = parseFloat(style.borderTopWidth) || 0;
            const bRightW = parseFloat(style.borderRightWidth) || 0;
            const bBottomW = parseFloat(style.borderBottomWidth) || 0;
            const bLeftW = parseFloat(style.borderLeftWidth) || 0;
            const maxBorderW = Math.max(bTopW, bRightW, bBottomW, bLeftW);
            const borderRadiusPx = parseFloat(style.borderRadius) || 0;

            // Check if it is a container shape/card (has background, border, or rounded corners)
            const isCardShape = hasBg || (maxBorderW > 0.5) || (borderRadiusPx > 0);

            // Check if this is a leaf text element or a dedicated text container
            const hasDirectText = Array.from(el.childNodes).some(n => n.nodeType === Node.TEXT_NODE && n.textContent.trim().length > 0);
            const childElements = Array.from(el.children).filter(c => !['SCRIPT', 'STYLE', 'BR'].includes(c.tagName));

            if (isCardShape) {
                // Determine shape type
                let shapeType = 'rectangle';
                if (borderRadiusPx >= Math.min(relW, relH) / 2 && Math.abs(relW - relH) < 5) {
                    shapeType = 'ellipse';
                } else if (borderRadiusPx > 2) {
                    shapeType = 'rounded_rectangle';
                }

                // Check for single accent border (e.g. border-left accent bar in takeaway bars)
                let accentBar = null;
                if (bLeftW >= 2 && bTopW <= 0.5 && bRightW <= 0.5 && bBottomW <= 0.5) {
                    accentBar = {
                        side: 'left',
                        color: style.borderLeftColor,
                        width_px: bLeftW
                    };
                }

                // Extract paragraphs if this shape directly manages its own text or is a self-contained card
                let paragraphs = [];
                // If the element has children with their own sub-cards, don't extract child card text into parent
                const childCards = childElements.filter(c => {
                    const cs = window.getComputedStyle(c);
                    const cbg = cs.backgroundColor;
                    const cHasBg = cbg && cbg !== 'transparent' && cbg !== 'rgba(0, 0, 0, 0)';
                    const cbw = Math.max(parseFloat(cs.borderTopWidth)||0, parseFloat(cs.borderLeftWidth)||0);
                    return cHasBg || cbw > 0.5 || (parseFloat(cs.borderRadius)||0) > 2;
                });

                if (childCards.length === 0) {
                    paragraphs = extractParagraphs(el);
                    // Mark direct children as processed to avoid double rendering
                    childElements.forEach(c => processedElements.add(c));
                }

                slideData.elements.push({
                    type: 'shape',
                    id: el.id || `shape_${domOrder}`,
                    x_px: relX,
                    y_px: relY,
                    w_px: relW,
                    h_px: relH,
                    z_index: getZIndex(style),
                    dom_order: domOrder,
                    opacity: parseFloat(style.opacity) || 1.0,
                    shape_type: shapeType,
                    bg_color: hasBg ? bg : null,
                    border_color: style.borderTopColor || style.borderColor,
                    border_width_px: (bTopW > 0 && bRightW > 0 && bBottomW > 0 && bLeftW > 0) ? bTopW : 0,
                    border_radius_px: borderRadiusPx,
                    border_style: style.borderTopStyle || 'solid',
                    accent_bar: accentBar,
                    padding_top_px: parseFloat(style.paddingTop) || 0,
                    padding_right_px: parseFloat(style.paddingRight) || 0,
                    padding_bottom_px: parseFloat(style.paddingBottom) || 0,
                    padding_left_px: parseFloat(style.paddingLeft) || 0,
                    paragraphs: paragraphs,
                    vertical_align: (style.alignItems === 'center' || style.justifyContent === 'center') ? 'middle' : 'top'
                });
                processedElements.add(el);
            } else if (!processedElements.has(el)) {
                // If element contains text and no processed parent already swallowed it
                if (hasDirectText || (childElements.length === 0 && el.innerText && el.innerText.trim().length > 0)) {
                    const paragraphs = extractParagraphs(el);
                    if (paragraphs.length > 0) {
                        slideData.elements.push({
                            type: 'text',
                            id: el.id || `txt_${domOrder}`,
                            x_px: relX,
                            y_px: relY,
                            w_px: relW,
                            h_px: relH,
                            z_index: getZIndex(style),
                            dom_order: domOrder,
                            opacity: parseFloat(style.opacity) || 1.0,
                            padding_top_px: parseFloat(style.paddingTop) || 0,
                            padding_right_px: parseFloat(style.paddingRight) || 0,
                            padding_bottom_px: parseFloat(style.paddingBottom) || 0,
                            padding_left_px: parseFloat(style.paddingLeft) || 0,
                            paragraphs: paragraphs,
                            vertical_align: (style.alignItems === 'center' || style.justifyContent === 'center') ? 'middle' : 'top'
                        });
                        processedElements.add(el);
                    }
                }
            }
        });

        results.push(slideData);
    });

    return results;
}
"""


class DOMExtractor:
    """Extracts raw slide DOM layout and constructs the high-level DeckModel."""

    def __init__(self, config: Config):
        self.config = config

    def extract_deck(self, page: Page) -> Tuple[DeckModel, List[str]]:
        """
        Execute DOM extraction script in browser page, transform into DeckModel,
        and collect warning messages.
        """
        warnings: List[str] = []
        raw_slides_data = page.evaluate(JS_EXTRACTOR_SCRIPT, self.config.deck.slide_selector)

        target_w_in = self.config.deck.width_in
        target_h_in = self.config.deck.height_in

        deck = DeckModel(width_in=target_w_in, height_in=target_h_in)

        for s_idx, s_data in enumerate(raw_slides_data):
            html_w = float(s_data.get("width_px", 1333))
            html_h = float(s_data.get("height_px", 750))
            
            bg_rgb, _ = parse_color(s_data.get("bg_color"))
            if bg_rgb is None:
                bg_rgb = (248, 250, 252)  # Default clean slide background

            slide = SlideModel(
                index=s_idx + 1,
                background_color_rgb=bg_rgb,
            )

            for el_data in s_data.get("elements", []):
                el_type = el_data.get("type")
                x_in = px_to_inch(float(el_data.get("x_px", 0)), html_w, target_w_in)
                y_in = px_to_inch(float(el_data.get("y_px", 0)), html_h, target_h_in)
                w_in = px_to_inch(float(el_data.get("w_px", 0)), html_w, target_w_in)
                h_in = px_to_inch(float(el_data.get("h_px", 0)), html_h, target_h_in)

                z_idx = int(el_data.get("z_index", 0))
                dom_ord = int(el_data.get("dom_order", 0))
                opac = float(el_data.get("opacity", 1.0))

                pad = Padding(
                    top_in=px_to_inch(float(el_data.get("padding_top_px", 0)), html_h, target_h_in),
                    right_in=px_to_inch(float(el_data.get("padding_right_px", 0)), html_w, target_w_in),
                    bottom_in=px_to_inch(float(el_data.get("padding_bottom_px", 0)), html_h, target_h_in),
                    left_in=px_to_inch(float(el_data.get("padding_left_px", 0)), html_w, target_w_in),
                )

                # Process paragraphs and text runs
                paragraphs: List[Paragraph] = []
                for p_data in el_data.get("paragraphs", []):
                    runs: List[TextRun] = []
                    for r_data in p_data.get("runs", []):
                        raw_font = r_data.get("fontFamily", "")
                        resolved_font, font_warn = resolve_font(raw_font, self.config.fonts)
                        if font_warn and font_warn not in warnings:
                            warnings.append(font_warn)

                        # Check availability
                        is_avail, avail_warn = check_font_availability(resolved_font)
                        if avail_warn and avail_warn not in warnings:
                            warnings.append(avail_warn)

                        f_size_pt = px_to_pt(float(r_data.get("fontSizePx", 16)))
                        f_weight = int(r_data.get("fontWeight", 400))
                        is_bold = f_weight >= 600 or "bold" in str(r_data.get("fontWeight", "")).lower()
                        is_italic = "italic" in str(r_data.get("fontStyle", "")).lower()
                        is_underline = "underline" in str(r_data.get("textDecoration", "")).lower()
                        
                        col_rgb, col_a = parse_color(r_data.get("color"))
                        if col_rgb is None:
                            col_rgb = (30, 41, 59)

                        runs.append(
                            TextRun(
                                text=r_data.get("text", ""),
                                font_family=resolved_font,
                                font_size_pt=f_size_pt,
                                font_weight=f_weight,
                                bold=is_bold,
                                italic=is_italic,
                                underline=is_underline,
                                color_rgb=col_rgb,
                                opacity=col_a,
                            )
                        )

                    align_str = p_data.get("textAlign", "left").lower()
                    if align_str not in ("left", "center", "right", "justify"):
                        align_str = "left"

                    line_h_px = p_data.get("lineHeightPx")
                    line_h_pt = px_to_pt(float(line_h_px)) if line_h_px else None

                    paragraphs.append(
                        Paragraph(
                            runs=runs,
                            alignment=align_str,
                            line_spacing_pt=line_h_pt,
                        )
                    )

                if el_type == "shape":
                    fill_rgb, fill_a = parse_color(el_data.get("bg_color"))
                    border_rgb, _ = parse_color(el_data.get("border_color"))
                    border_w_pt = px_to_pt(float(el_data.get("border_width_px", 0)))
                    border_r_pt = px_to_pt(float(el_data.get("border_radius_px", 0)))

                    accent_bar_info = None
                    if el_data.get("accent_bar"):
                        ab = el_data["accent_bar"]
                        ab_col, _ = parse_color(ab.get("color"))
                        if ab_col:
                            accent_bar_info = {
                                "color_rgb": ab_col,
                                "width_in": px_to_inch(float(ab.get("width_px", 4)), html_w, target_w_in),
                            }

                    slide.elements.append(
                        ShapeElement(
                            id=el_data.get("id", ""),
                            x_in=x_in,
                            y_in=y_in,
                            width_in=w_in,
                            height_in=h_in,
                            z_index=z_idx,
                            dom_order=dom_ord,
                            opacity=opac,
                            shape_type=el_data.get("shape_type", "rectangle"),
                            fill_color_rgb=fill_rgb,
                            fill_opacity=fill_a,
                            border_color_rgb=border_rgb,
                            border_width_pt=border_w_pt,
                            border_radius_pt=border_r_pt,
                            border_style=el_data.get("border_style", "solid"),
                            paragraphs=paragraphs,
                            vertical_align=el_data.get("vertical_align", "top"),
                            padding=pad,
                            accent_bar_left=accent_bar_info,
                        )
                    )

                elif el_type == "text":
                    slide.elements.append(
                        TextElement(
                            id=el_data.get("id", ""),
                            x_in=x_in,
                            y_in=y_in,
                            width_in=w_in,
                            height_in=h_in,
                            z_index=z_idx,
                            dom_order=dom_ord,
                            opacity=opac,
                            paragraphs=paragraphs,
                            vertical_align=el_data.get("vertical_align", "top"),
                            padding=pad,
                        )
                    )

                elif el_type == "image":
                    slide.elements.append(
                        ImageElement(
                            id=el_data.get("id", ""),
                            x_in=x_in,
                            y_in=y_in,
                            width_in=w_in,
                            height_in=h_in,
                            z_index=z_idx,
                            dom_order=dom_ord,
                            opacity=opac,
                            src=el_data.get("src", ""),
                            alt_text=el_data.get("alt", ""),
                        )
                    )

                elif el_type == "svg":
                    warnings.append(f"SVG element '{el_data.get('id')}' detected: SVG preserved as static image, internal vector paths are not individually editable.")

            # Sort slide elements by z-index and DOM order
            slide.sort_elements()
            deck.slides.append(slide)

        return (deck, warnings)
