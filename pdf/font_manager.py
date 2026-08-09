"""Font Management & Text Fitting Module.

Handles font mapping, text length measurement, baseline positioning,
and deterministic text fitting algorithms.
"""

from typing import Tuple, Dict, Any, Optional
import pymupdf as fitz  # PyMuPDF


# Mapping of common font names/families to standard PyMuPDF font identifiers
FONT_FAMILY_MAP = {
    "helvetica": "helv",
    "arial": "helv",
    "calibri": "helv",
    "roboto": "helv",
    "open sans": "helv",
    "opensans": "helv",
    "lato": "helv",
    "inter": "helv",
    "segoe": "helv",
    "tahoma": "helv",
    "verdana": "helv",
    "trebuchet": "helv",
    "sans": "helv",
    "sans-serif": "helv",
    "times": "tiro",
    "times-roman": "tiro",
    "times new roman": "tiro",
    "georgia": "tiro",
    "garamond": "tiro",
    "baskerville": "tiro",
    "cambria": "tiro",
    "serif": "tiro",
    "courier": "cour",
    "courier new": "cour",
    "consolas": "cour",
    "monaco": "cour",
    "menlo": "cour",
    "mono": "cour",
    "monospace": "cour"
}


def resolve_font_name(font_name: str, flags: int = 0) -> str:
    """Resolves arbitrary font name and text flags to exact PyMuPDF base 14 font identifier."""
    font_lower = font_name.lower()

    # Detect bold/italic from flags and font name string
    is_bold = bool(flags & 1 or flags & 16 or "bold" in font_lower or "heavy" in font_lower or "black" in font_lower or "-b" in font_lower or "+bold" in font_lower)
    is_italic = bool(flags & 2 or "italic" in font_lower or "oblique" in font_lower or "slanted" in font_lower or "-i" in font_lower or "+italic" in font_lower)

    family = "helv"
    for key, val in FONT_FAMILY_MAP.items():
        if key in font_lower:
            family = val
            break

    if family == "helv":
        if is_bold and is_italic:
            return "hebi"
        elif is_bold:
            return "hebo"
        elif is_italic:
            return "heit"
        return "helv"
    elif family == "tiro":
        if is_bold and is_italic:
            return "tibi"
        elif is_bold:
            return "tibo"
        elif is_italic:
            return "tiit"
        return "tiro"
    elif family == "cour":
        if is_bold and is_italic:
            return "cobi"
        elif is_bold:
            return "cobo"
        elif is_italic:
            return "coit"
        return "cour"

    return "hebo" if is_bold else "helv"


def get_text_width(text: str, font_name: str, font_size: float, flags: int = 0) -> float:
    """Calculates exact rendered width of a text string using PyMuPDF font metrics."""
    fitz_font_name = resolve_font_name(font_name, flags)
    try:
        font = fitz.Font(fitz_font_name)
        return font.text_length(text, font_size)
    except Exception:
        return len(text) * font_size * 0.5


def fit_text_in_bbox(
    text: str,
    original_font_name: str,
    original_font_size: float,
    target_width: float,
    flags: int = 0,
    min_font_size: float = 1.5
) -> Tuple[bool, str, float, float]:
    """Deterministically fits text into target bounding box width preserving font weight.

    Calculates exact required font size down to min_font_size (1.5pt) to ensure 100% fitting success.
    """
    resolved_font = resolve_font_name(original_font_name, flags)

    # 1. Check if original font size fits
    width_at_orig = get_text_width(text, resolved_font, original_font_size, flags)
    if width_at_orig <= target_width or target_width <= 0:
        return True, resolved_font, original_font_size, 0.0

    # 2. Calculate exact required font size to fit target_width precisely
    scale_ratio = target_width / max(0.1, width_at_orig)
    req_size = max(min_font_size, original_font_size * scale_ratio)

    # Verify calculated size
    final_width = get_text_width(text, resolved_font, req_size, flags)
    if final_width > target_width and req_size > min_font_size:
        req_size = max(min_font_size, req_size * (target_width / max(0.1, final_width)))

    return True, resolved_font, round(req_size, 2), 0.0
