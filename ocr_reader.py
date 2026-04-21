"""
module1_vision/ocr_reader.py
-------------------------------
Reads numeric values (pot size, stack sizes) from the screenshot.

GGPoker-specific challenges handled
-------------------------------------
- Stack values may include commas: "12,450"
- Abbreviated values: "12.4K", "1.2M"
- Font colours vary (gold/white for hero stack, white for villain)
- Shadows and glow effects under the text
- BB (big blind) amounts sometimes appear alongside chip counts

Strategy
--------
Use easyOCR for coloured/styled text (better with complex backgrounds).
Fall back to pytesseract with aggressive preprocessing for cleaner regions.
"""

import re
import cv2
import numpy as np
from typing import Optional
from preprocessor import crop_region, enhance_for_ocr

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

try:
    import easyocr
    _easy_reader = easyocr.Reader(["en"], gpu=False, verbose=False)
    EASYOCR_AVAILABLE = True
except Exception:
    EASYOCR_AVAILABLE = False
    _easy_reader = None


# ── Value parsing ─────────────────────────────────────────────────────────────

_CHIP_PATTERN = re.compile(
    r"([\d,]+\.?\d*)\s*([KkMm]?)",
    re.IGNORECASE
)

def _parse_chip_value(raw: str) -> Optional[float]:
    """
    Parse a raw OCR string into a chip count float.

    Handles: "12,450", "12.4K", "1.2M", "1200BB" (strips BB suffix).
    Returns None if parsing fails.
    """
    if not raw:
        return None

    # Strip common noise characters and suffixes
    cleaned = raw.strip().replace(" ", "").replace("$", "")
    cleaned = re.sub(r"BB$", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"[^0-9.,KkMm]", "", cleaned)

    match = _CHIP_PATTERN.search(cleaned)
    if not match:
        return None

    num_str, suffix = match.group(1), match.group(2).upper()
    try:
        value = float(num_str.replace(",", ""))
    except ValueError:
        return None

    if suffix == "K":
        value *= 1_000
    elif suffix == "M":
        value *= 1_000_000

    return value


# ── OCR engines ───────────────────────────────────────────────────────────────

def _ocr_with_tesseract(img: np.ndarray, mode: str = "dark_bg") -> str:
    """Run pytesseract in numeric/symbol mode."""
    enhanced = enhance_for_ocr(img, mode=mode)
    config = "--psm 7 --oem 3 -c tessedit_char_whitelist=0123456789,.KkMmBb"
    try:
        return pytesseract.image_to_string(enhanced, config=config)
    except Exception:
        return ""


def _ocr_with_easyocr(img: np.ndarray) -> str:
    """Run easyOCR on a colour crop (better for styled fonts)."""
    if not EASYOCR_AVAILABLE or _easy_reader is None:
        return ""
    colour_crop = enhance_for_ocr(img, mode="colour")
    try:
        results = _easy_reader.readtext(colour_crop, detail=0)
        return " ".join(results)
    except Exception:
        return ""


def _read_value(img: np.ndarray, region: list, prefer_easyocr: bool = False) -> Optional[float]:
    """
    Crop region and attempt OCR with both engines.

    Returns the parsed chip value or None.
    """
    crop = crop_region(img, region)
    if crop.size == 0:
        return None

    raw_results = []

    if prefer_easyocr:
        raw_results.append(_ocr_with_easyocr(crop))
        if TESSERACT_AVAILABLE:
            raw_results.append(_ocr_with_tesseract(crop))
    else:
        if TESSERACT_AVAILABLE:
            raw_results.append(_ocr_with_tesseract(crop))
        raw_results.append(_ocr_with_easyocr(crop))

    for raw in raw_results:
        value = _parse_chip_value(raw)
        if value is not None and value > 0:
            return value

    return None


# ── Public API ────────────────────────────────────────────────────────────────

def read_pot(img: np.ndarray, region: list) -> Optional[float]:
    """
    Read the pot size from the given region.

    GGPoker pot text is typically white on dark semi-transparent background
    — tesseract with dark_bg preprocessing works well here.
    """
    return _read_value(img, region, prefer_easyocr=False)


def read_stack(img: np.ndarray, region: list, is_hero: bool = True) -> Optional[float]:
    """
    Read a player stack size.

    Hero stack is often rendered in gold/yellow (GGPoker theme), so easyOCR
    handles colour variance better. Villain stack is plain white — either works.
    """
    return _read_value(img, region, prefer_easyocr=is_hero)


def read_all_values(img: np.ndarray, regions_cfg: dict) -> dict:
    """
    Read pot + both stacks in one call.

    Parameters
    ----------
    regions_cfg : dict  — the 'pot' and 'stacks' sections from regions.json

    Returns
    -------
    dict with keys: pot, hero_stack, villain_stack (each float or None)
    """
    return {
        "pot":           read_pot(img,   regions_cfg["pot"]["region"]),
        "hero_stack":    read_stack(img, regions_cfg["stacks"]["hero"],    is_hero=True),
        "villain_stack": read_stack(img, regions_cfg["stacks"]["villain"], is_hero=False),
    }
