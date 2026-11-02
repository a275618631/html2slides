"""
Configuration loading and validation for html2slides using TOML.
"""

import os
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

# Python 3.11+ built-in tomllib
try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None


@dataclass
class DeckConfig:
    slide_selector: str = ".slide-container"
    width_in: float = 13.333
    height_in: float = 7.5


@dataclass
class FontConfig:
    mode: str = "preserve"  # "preserve", "override", "map"
    default: str = "Noto Sans TC"
    map: Dict[str, str] = field(default_factory=dict)


@dataclass
class SelectorOverride:
    selector: str
    font_family: Optional[str] = None
    font_size_pt: Optional[float] = None
    font_weight: Optional[int] = None
    color: Optional[str] = None
    text_align: Optional[str] = None
    background_color: Optional[str] = None


@dataclass
class SecurityConfig:
    allow_network: bool = False
    allow_javascript: bool = False


@dataclass
class GoogleSlidesConfig:
    drive_folder_id: Optional[str] = None


@dataclass
class Config:
    deck: DeckConfig = field(default_factory=DeckConfig)
    fonts: FontConfig = field(default_factory=FontConfig)
    overrides: List[SelectorOverride] = field(default_factory=list)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    google_slides: GoogleSlidesConfig = field(default_factory=GoogleSlidesConfig)

    @classmethod
    def load(cls, config_path: Optional[str] = None) -> "Config":
        """Load configuration from a file or return defaults."""
        if not config_path or not os.path.exists(config_path):
            return cls()

        if tomllib is None:
            print("WARN: tomllib not found, using default configuration.", file=sys.stderr)
            return cls()

        try:
            with open(config_path, "rb") as f:
                data = tomllib.load(f)
        except Exception as e:
            print(f"WARN: Failed to parse config file {config_path}: {e}. Using defaults.", file=sys.stderr)
            return cls()

        deck_data = data.get("deck", {})
        deck = DeckConfig(
            slide_selector=deck_data.get("slide_selector", ".slide-container"),
            width_in=float(deck_data.get("width_in", 13.333)),
            height_in=float(deck_data.get("height_in", 7.5)),
        )

        font_data = data.get("fonts", {})
        font_map = font_data.get("map", {})
        fonts = FontConfig(
            mode=font_data.get("mode", "preserve"),
            default=font_data.get("default", "Noto Sans TC"),
            map=font_map,
        )

        overrides = []
        for ov_data in data.get("overrides", []):
            if "selector" in ov_data:
                overrides.append(
                    SelectorOverride(
                        selector=ov_data["selector"],
                        font_family=ov_data.get("font_family"),
                        font_size_pt=float(ov_data["font_size_pt"]) if "font_size_pt" in ov_data else None,
                        font_weight=int(ov_data["font_weight"]) if "font_weight" in ov_data else None,
                        color=ov_data.get("color"),
                        text_align=ov_data.get("text_align"),
                        background_color=ov_data.get("background_color"),
                    )
                )

        sec_data = data.get("security", {})
        security = SecurityConfig(
            allow_network=bool(sec_data.get("allow_network", False)),
            allow_javascript=bool(sec_data.get("allow_javascript", False)),
        )

        gs_data = data.get("google_slides", {})
        google_slides = GoogleSlidesConfig(
            drive_folder_id=gs_data.get("drive_folder_id"),
        )

        return cls(
            deck=deck,
            fonts=fonts,
            overrides=overrides,
            security=security,
            google_slides=google_slides,
        )
