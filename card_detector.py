"""
module1_vision/card_detector.py
---------------------------------
Detects and classifies playing cards from cropped regions.

Strategy
--------
1. Crop the card region from the normalised screenshot.
2. Extract the rank (top-left corner) and suit (colour + shape) sub-regions.
3. Classify rank via OCR on the corner; classify suit via HSV colour analysis.
4. Return a standard notation string, e.g. "Ah", "Kd", "2c", "Ts".

Suit colour map for GGPoker
---------------------------
  Spades   (♠) — near-black / dark gray
  Clubs    (♣) — dark green
  Hearts   (♥) — red
  Diamonds (♦) — blue  (GGPoker uses blue, not red, for diamonds)
"""

import cv2
import numpy as np
import re
from typing import Optional, List
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


# ── Rank normalisation ────────────────────────────────────────────────────────

RANK_ALIASES = {
    "1": "A", "11": "J", "12": "Q", "13": "K",
    "l": "A", "i": "A",   # common OCR misreads for Ace corner "A"
    "0": "10",
}
VALID_RANKS = {"2","3","4","5","6","7","8","9","10","J","Q","K","A"}


def _normalise_rank(raw: str) -> Optional[str]:
    raw = raw.strip().upper().replace("O", "0").replace(" ", "")
    raw = RANK_ALIASES.get(raw, raw)
    return raw if raw in VALID_RANKS else None


# ── Suit detection via HSV colour ─────────────────────────────────────────────

# Each suit defined as (H_low, H_high, S_low, V_low)
# GGPoker: hearts=red, diamonds=blue, clubs=green, spades=black
SUIT_HSV_RANGES = {
    "h": [(0, 10, 120, 80), (170, 180, 120, 80)],   # red (wraps hue)
    "d": [(100, 130, 120, 80)],                       # blue
    "c": [(45, 85, 80, 60)],                          # green
    "s": [(0, 180, 0, 0)],                            # black — catch-all after others
}


def _detect_suit_from_region(suit_crop: np.ndarray) -> Optional[str]:
    """
    Classify suit by dominant HSV colour in the suit icon region.
    Returns 'h', 'd', 'c', or 's'.
    """
    if suit_crop is None or suit_crop.size == 0:
        return None

    hsv = cv2.cvtColor(suit_crop, cv2.COLOR_BGR2HSV)
    scores = {}

    for suit, ranges in SUIT_HSV_RANGES.items():
        if suit == "s":
            continue  # spades are detected by exclusion
        mask_total = np.zeros(hsv.shape[:2], dtype=np.uint8)
        for (h_lo, h_hi, s_lo, v_lo) in ranges:
            lo = np.array([h_lo, s_lo, v_lo])
            hi = np.array([h_hi, 255, 255])
            mask_total = cv2.bitwise_or(mask_total, cv2.inRange(hsv, lo, hi))
        scores[suit] = int(cv2.countNonZero(mask_total))

    best_suit = max(scores, key=scores.get)
    if scores[best_suit] < 30:
        return "s"  # no strong colour → spades
    return best_suit


# ── Rank OCR ──────────────────────────────────────────────────────────────────

def _ocr_rank_region(rank_crop: np.ndarray) -> Optional[str]:
    """
    Read the rank character from the top-left corner of a card.
    Tries pytesseract first; falls back to easyOCR.
    """
    enhanced = enhance_for_ocr(rank_crop, mode="light_bg")

    # Tesseract — single-char whitelist mode
    if TESSERACT_AVAILABLE:
        config = (
            "--psm 8 --oem 3 "
            "-c tessedit_char_whitelist=A23456789TJQK10"
        )
        try:
            raw = pytesseract.image_to_string(enhanced, config=config)
            rank = _normalise_rank(raw)
            if rank:
                return rank
        except Exception:
            pass

    # easyOCR fallback
    if EASYOCR_AVAILABLE and _easy_reader:
        try:
            results = _easy_reader.readtext(enhanced, detail=0, allowlist="A23456789TJQK10")
            if results:
                rank = _normalise_rank(results[0])
                if rank:
                    return rank
        except Exception:
            pass

    return None


# ── Card sub-region layout within a card bounding box ────────────────────────
# GGPoker card corners occupy roughly the top-left 30% of the card area.

def _split_card_region(card_crop: np.ndarray):
    """Return (rank_crop, suit_crop) from a raw card region."""
    h, w = card_crop.shape[:2]
    rank_crop = card_crop[0:int(h * 0.38), 0:int(w * 0.55)]
    suit_crop = card_crop[int(h * 0.35):int(h * 0.72), 0:int(w * 0.55)]
    return rank_crop, suit_crop


# ── Public API ────────────────────────────────────────────────────────────────

def detect_card(img: np.ndarray, region: list) -> Optional[str]:
    """
    Detect a single card from a [x, y, w, h] region of the normalised image.

    Returns a card string like "Ah", "Kd", "2c", or None if detection fails.
    """
    card_crop = crop_region(img, region)
    if card_crop.size == 0:
        return None

    rank_crop, suit_crop = _split_card_region(card_crop)
    rank = _ocr_rank_region(rank_crop)
    suit = _detect_suit_from_region(suit_crop)

    if rank and suit:
        return f"{rank}{suit}"
    return None


def detect_hole_cards(img: np.ndarray, regions: dict) -> List[Optional[str]]:
    """
    Detect both hero hole cards.

    Parameters
    ----------
    regions : dict  — {"card_1": [x,y,w,h], "card_2": [x,y,w,h]}

    Returns
    -------
    List of two card strings or Nones, e.g. ["Ah", "Kd"]
    """
    return [
        detect_card(img, regions["card_1"]),
        detect_card(img, regions["card_2"]),
    ]


def detect_community_cards(img: np.ndarray, regions: dict) -> List[Optional[str]]:
    """
    Detect up to 5 community cards.
    Returns only cards that are face-up (non-None detections).

    Parameters
    ----------
    regions : dict — keys: flop_1, flop_2, flop_3, turn, river
    """
    keys = ["flop_1", "flop_2", "flop_3", "turn", "river"]
    cards = [detect_card(img, regions[k]) for k in keys if k in regions]
    return [c for c in cards if c is not None]
