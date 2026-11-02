"""
Intermediate Representation Data Model for Slides, Elements, and Formatting.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict, Any


@dataclass
class TextRun:
    """Represents a formatted inline text run."""
    text: str
    font_family: str = "Noto Sans TC"
    font_size_pt: float = 14.0
    font_weight: int = 400
    bold: bool = False
    italic: bool = False
    underline: bool = False
    color_rgb: Tuple[int, int, int] = (30, 41, 59)
    opacity: float = 1.0


@dataclass
class Paragraph:
    """Represents a paragraph of text runs with alignment and spacing."""
    runs: List[TextRun] = field(default_factory=list)
    alignment: str = "left"  # "left", "center", "right", "justify"
    line_spacing_pt: Optional[float] = None
    space_before_pt: float = 0.0
    space_after_pt: float = 0.0

    @property
    def plain_text(self) -> str:
        return "".join(run.text for run in self.runs)


@dataclass
class Padding:
    """Padding around content in inches."""
    top_in: float = 0.0
    right_in: float = 0.0
    bottom_in: float = 0.0
    left_in: float = 0.0


@dataclass
class Element:
    """Base element located on a slide with absolute inches coordinates."""
    id: str
    x_in: float
    y_in: float
    width_in: float
    height_in: float
    z_index: int = 0
    dom_order: int = 0
    opacity: float = 1.0
    rotation: float = 0.0


@dataclass
class ShapeElement(Element):
    """Shape element (Rectangle, Rounded Rectangle, Oval) optionally containing text."""
    shape_type: str = "rectangle"  # "rectangle", "rounded_rectangle", "ellipse"
    fill_color_rgb: Optional[Tuple[int, int, int]] = None
    fill_opacity: float = 1.0
    border_color_rgb: Optional[Tuple[int, int, int]] = None
    border_width_pt: float = 0.0
    border_radius_pt: float = 0.0
    border_style: str = "solid"  # "solid", "dashed", "dotted"
    paragraphs: List[Paragraph] = field(default_factory=list)
    vertical_align: str = "top"  # "top", "middle", "bottom"
    padding: Padding = field(default_factory=Padding)
    # Left accent border support (common in modern cards / takeaways)
    accent_bar_left: Optional[Dict[str, Any]] = None  # e.g. {"color_rgb": (0,82,155), "width_in": 0.05}


@dataclass
class TextElement(Element):
    """Pure Text Box element containing paragraphs."""
    paragraphs: List[Paragraph] = field(default_factory=list)
    vertical_align: str = "top"  # "top", "middle", "bottom"
    padding: Padding = field(default_factory=Padding)
    background_color_rgb: Optional[Tuple[int, int, int]] = None
    border_color_rgb: Optional[Tuple[int, int, int]] = None
    border_width_pt: float = 0.0


@dataclass
class ImageElement(Element):
    """Image element with raw bytes, path or data URI."""
    src: str = ""
    image_bytes: Optional[bytes] = None
    mime_type: str = "image/png"
    alt_text: str = ""


@dataclass
class LineElement(Element):
    """Line element with coordinates and stroke."""
    x2_in: float = 0.0
    y2_in: float = 0.0
    stroke_color_rgb: Tuple[int, int, int] = (203, 213, 225)
    stroke_width_pt: float = 1.0
    stroke_style: str = "solid"  # "solid", "dashed"


@dataclass
class SlideModel:
    """Slide container with background and ordered elements."""
    index: int
    title: str = ""
    background_color_rgb: Optional[Tuple[int, int, int]] = (248, 250, 252)
    elements: List[Element] = field(default_factory=list)

    def sort_elements(self):
        """Sort elements by z_index ascending, then by dom_order ascending."""
        self.elements.sort(key=lambda el: (el.z_index, el.dom_order))


@dataclass
class DeckModel:
    """Entire slide deck with target dimensions in inches."""
    width_in: float = 13.333
    height_in: float = 7.5
    slides: List[SlideModel] = field(default_factory=list)
