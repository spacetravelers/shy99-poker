"""
module1_vision/parser.py
--------------------------
Orchestrates the full image parsing pipeline for Module 1.

Usage
-----
    from module1_vision.parser import parse_screenshot

    game_state = parse_screenshot("screenshot.png")
    print(game_state)
    # {
    #   "hole_cards": ["Ah", "Kd"],
    #   "community_cards": ["2c", "7h", "Js"],
    #   "pot": 1250.0,
    #   "hero_stack": 8450.0,
    #   "villain_stack": 6200.0,
    #   "position": "BTN",
    #   "street": "flop",
    #   "parse_warnings": []
    # }
"""

import json
import os
from typing import Optional
import numpy as np

from preprocessor import load_image, normalise_resolution
from card_detector import detect_hole_cards, detect_community_cards
from ocr_reader import read_all_values
from position_detector import detect_position


# ── Config loader ─────────────────────────────────────────────────────────────

_DEFAULT_CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config", "regions.json")


def load_regions(config_path: str = _DEFAULT_CONFIG_PATH) -> dict:
    with open(config_path, "r") as f:
        return json.load(f)


# ── Street inference ──────────────────────────────────────────────────────────

def _infer_street(community_cards: list) -> str:
    n = len(community_cards)
    if n == 0: return "preflop"
    if n == 3: return "flop"
    if n == 4: return "turn"
    if n == 5: return "river"
    return "unknown"


# ── Main pipeline ─────────────────────────────────────────────────────────────

def parse_screenshot(
    image_path: str,
    config_path: str = _DEFAULT_CONFIG_PATH,
    override_regions: Optional[dict] = None,
) -> dict:
    """
    Parse a GGPoker screenshot and return a structured GameState dict.

    Parameters
    ----------
    image_path     : str  — path to the screenshot file
    config_path    : str  — path to regions.json (defaults to config/regions.json)
    override_regions: dict — optional manual region overrides (takes precedence)

    Returns
    -------
    dict with keys:
        hole_cards, community_cards, pot, hero_stack, villain_stack,
        position, street, parse_warnings, raw_image_shape
    """
    warnings = []

    # 1. Load and normalise
    img_raw = load_image(image_path)
    img, sx, sy = normalise_resolution(img_raw)

    # 2. Load region config
    regions = load_regions(config_path)
    if override_regions:
        _deep_merge(regions, override_regions)

    # 3. Detect cards
    hole_cards = detect_hole_cards(img, regions["hole_cards"])
    community_cards = detect_community_cards(img, regions["community_cards"])

    if None in hole_cards:
        warnings.append(f"Hole card detection partially failed: {hole_cards}")
    if not hole_cards[0] and not hole_cards[1]:
        warnings.append("Could not detect either hole card — check bounding boxes.")

    # 4. Read numeric values
    values = read_all_values(img, regions)

    if values["pot"] is None:
        warnings.append("Pot size OCR failed.")
    if values["hero_stack"] is None:
        warnings.append("Hero stack OCR failed.")
    if values["villain_stack"] is None:
        warnings.append("Villain stack OCR failed.")

    # 5. Detect position
    pos_result = detect_position(img, regions["dealer_button"])
    if pos_result["hero_position"] == "unknown":
        warnings.append("Dealer button not detected — position unknown.")

    # 6. Infer street
    street = _infer_street(community_cards)

    game_state = {
        "hole_cards":      hole_cards,
        "community_cards": community_cards,
        "pot":             values["pot"],
        "hero_stack":      values["hero_stack"],
        "villain_stack":   values["villain_stack"],
        "position":        pos_result["hero_position"],
        "street":          street,
        "parse_warnings":  warnings,
        "raw_image_shape": img_raw.shape,
        "_debug": {
            "scale_x":        round(sx, 4),
            "scale_y":        round(sy, 4),
            "dealer_button":  pos_result,
        },
    }

    return game_state


def _deep_merge(base: dict, override: dict):
    """Recursively merge override into base dict in-place."""
    for k, v in override.items():
        if k in base and isinstance(base[k], dict) and isinstance(v, dict):
            _deep_merge(base[k], v)
        else:
            base[k] = v
