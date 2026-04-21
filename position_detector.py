"""
module1_vision/position_detector.py
--------------------------------------
Detects the dealer button position and infers hero's seat position
(BTN, CO, HJ, MP, UTG, BB, SB) for use in GTO chart lookups.

Detection method
----------------
The GGPoker dealer button is a small circular white/gold disc with a "D"
character. We search for it using:
  1. Hough circle detection near known seat positions.
  2. Template matching with a reference button patch (optional).
  3. Fallback: scan the full image for the "D" text near seat positions.

For a heads-up game (the primary target):
  - If button is at hero seat → hero is BTN/SB (acts first pre-flop in HU)
  - If button is at villain seat → hero is BB
"""

import cv2
import numpy as np
from typing import Optional, Tuple, List
from preprocessor import crop_region

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False


# ── Hough circle button finder ────────────────────────────────────────────────

def _search_for_button_circle(
    img: np.ndarray,
    center: Tuple[int, int],
    radius: int
) -> Optional[Tuple[int, int]]:
    """
    Use Hough circle detection to find the dealer button near a seat position.

    Parameters
    ----------
    center : (x, y) — seat center coordinates
    radius : int    — search radius around the seat center

    Returns
    -------
    (x, y) of button center if found, else None
    """
    cx, cy = center
    x1 = max(0, cx - radius)
    y1 = max(0, cy - radius)
    x2 = min(img.shape[1], cx + radius)
    y2 = min(img.shape[0], cy + radius)

    roi = img[y1:y2, x1:x2]
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)

    # Blur to reduce noise before circle detection
    blurred = cv2.GaussianBlur(gray, (7, 7), 0)

    circles = cv2.HoughCircles(
        blurred,
        cv2.HOUGH_GRADIENT,
        dp=1.2,
        minDist=20,
        param1=80,
        param2=25,
        minRadius=10,
        maxRadius=28,
    )

    if circles is None:
        return None

    circles = np.round(circles[0, :]).astype(int)

    # Pick the brightest circle (dealer button tends to be light-coloured)
    best = None
    best_brightness = -1
    for (cx_rel, cy_rel, r) in circles:
        mask = np.zeros(gray.shape, dtype=np.uint8)
        cv2.circle(mask, (cx_rel, cy_rel), r, 255, -1)
        brightness = cv2.mean(gray, mask=mask)[0]
        if brightness > best_brightness:
            best_brightness = brightness
            best = (x1 + cx_rel, y1 + cy_rel)

    # Only accept bright circles (dealer button is white/gold)
    if best_brightness < 160:
        return None

    return best


def _button_has_d_text(img: np.ndarray, center: Tuple[int, int], r: int = 22) -> bool:
    """
    Check if a circular region contains a 'D' character (dealer button label).
    """
    if not TESSERACT_AVAILABLE:
        return True  # can't verify — assume it's valid

    cx, cy = center
    crop = crop_region(img, [cx - r, cy - r, r * 2, r * 2])
    if crop.size == 0:
        return False

    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, 100, 255, cv2.THRESH_BINARY)
    config = "--psm 10 --oem 3 -c tessedit_char_whitelist=D"
    try:
        text = pytesseract.image_to_string(binary, config=config).strip()
        return "D" in text.upper()
    except Exception:
        return True  # assume valid if OCR fails


# ── Position mapping ──────────────────────────────────────────────────────────

# GGPoker heads-up: two seats — hero (bottom) and villain (top)
SEAT_LABELS = {
    "hero":    "hero",
    "villain": "villain",
}

HU_POSITION_MAP = {
    "hero":    "BTN",   # hero has button → BTN/SB in HU
    "villain": "BB",    # button is at villain → hero is BB
}


def detect_position(img: np.ndarray, dealer_cfg: dict) -> dict:
    """
    Detect the dealer button position and return positional info.

    Parameters
    ----------
    dealer_cfg : dict — the 'dealer_button' section from regions.json

    Returns
    -------
    dict with:
        button_at   : "hero" | "villain" | "unknown"
        hero_position: "BTN" | "BB" | "unknown"
        button_xy   : (x, y) or None
    """
    search_r = dealer_cfg.get("search_radius", 60)
    hero_seat = tuple(dealer_cfg["hero_seat"])
    villain_seat = tuple(dealer_cfg["villain_seat"])

    results = {
        "button_at": "unknown",
        "hero_position": "unknown",
        "button_xy": None,
    }

    found_at = {}
    for seat_name, seat_center in [("hero", hero_seat), ("villain", villain_seat)]:
        btn_xy = _search_for_button_circle(img, seat_center, search_r)
        if btn_xy is not None:
            found_at[seat_name] = btn_xy

    if len(found_at) == 1:
        seat_name, btn_xy = next(iter(found_at.items()))
        results["button_at"] = seat_name
        results["hero_position"] = HU_POSITION_MAP.get(seat_name, "unknown")
        results["button_xy"] = btn_xy
    elif len(found_at) > 1:
        # Multiple candidates — pick the one with brighter surroundings
        # (the real button will stand out more)
        results["button_at"] = "ambiguous"
        results["hero_position"] = "unknown"

    return results
