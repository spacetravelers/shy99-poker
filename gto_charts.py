"""
module2_engine/gto_charts.py
------------------------------
Pre-flop GTO range charts for Full Ring (9-handed).

Positions: UTG, UTG1, UTG2, MP, HJ, CO, BTN, SB, BB

Chart format
------------
Each position has:
  - RFI (Raise First In): hands to open when folded to
  - vs_3bet: hands to call/4bet when facing a 3-bet
  - steal: CO/BTN/SB steal ranges (wider)

Hand notation
-------------
"AKs" = suited, "AKo" = offsuit, "AK" = both
Pairs: "AA", "KK", ... "22"

Stack depth adjustments
-----------------------
< 20bb  → push/fold only (see push_fold.py)
20-40bb → tighter opens, more shove/fold
40bb+   → full GTO ranges below
"""

from typing import Optional

# ── Hand rank lookup ──────────────────────────────────────────────────────────

RANKS = ["2", "3", "4", "5", "6", "7", "8", "9", "T", "J", "Q", "K", "A"]
RANK_VAL = {r: i for i, r in enumerate(RANKS)}


def hand_to_str(hole_cards: list) -> Optional[str]:
    """
    Convert ["Ah", "Kd"] → "AKo" or "AKs".
    Returns None if cards are missing.
    """
    if not hole_cards or len(hole_cards) < 2:
        return None
    if None in hole_cards:
        return None

    c1, c2 = hole_cards[0], hole_cards[1]
    r1, s1 = c1[:-1], c1[-1]
    r2, s2 = c2[:-1], c2[-1]

    # Normalise rank (10 → T)
    r1 = "T" if r1 == "10" else r1
    r2 = "T" if r2 == "10" else r2

    # Higher rank first
    if RANK_VAL.get(r1, 0) < RANK_VAL.get(r2, 0):
        r1, r2 = r2, r1
        s1, s2 = s2, s1

    if r1 == r2:
        return r1 + r2  # pair

    suited = "s" if s1 == s2 else "o"
    return r1 + r2 + suited


# ── Full Ring RFI ranges (40bb+) ──────────────────────────────────────────────
# Source: GTO Wizard / solver approximations for 9-handed cash

RFI_RANGES = {
    "UTG": {
        "open": [
            "AA","KK","QQ","JJ","TT","99","88",
            "AKs","AQs","AJs","ATs","A9s","A8s","A5s",
            "AKo","AQo","AJo","ATo",
            "KQs","KJs","KTs","K9s",
            "KQo","KJo",
            "QJs","QTs","Q9s",
            "JTs","J9s",
            "T9s","T8s",
            "98s","97s",
            "87s","86s",
            "76s","75s",
            "65s","54s",
        ],
        "description": "UTG — tightest range, ~14% of hands"
    },
    "UTG1": {
        "open": [
            "AA","KK","QQ","JJ","TT","99","88","77",
            "AKs","AQs","AJs","ATs","A9s","A8s","A7s","A5s","A4s",
            "AKo","AQo","AJo","ATo","A9o",
            "KQs","KJs","KTs","K9s","K8s",
            "KQo","KJo","KTo",
            "QJs","QTs","Q9s","Q8s",
            "JTs","J9s","J8s",
            "T9s","T8s","T7s",
            "98s","97s","96s",
            "87s","86s","85s",
            "76s","75s",
            "65s","64s","54s",
        ],
        "description": "UTG+1 — ~16% of hands"
    },
    "UTG2": {
        "open": [
            "AA","KK","QQ","JJ","TT","99","88","77","66",
            "AKs","AQs","AJs","ATs","A9s","A8s","A7s","A6s","A5s","A4s","A3s",
            "AKo","AQo","AJo","ATo","A9o","A8o",
            "KQs","KJs","KTs","K9s","K8s","K7s",
            "KQo","KJo","KTo","K9o",
            "QJs","QTs","Q9s","Q8s","Q7s",
            "QJo","QTo",
            "JTs","J9s","J8s","J7s",
            "JTo",
            "T9s","T8s","T7s",
            "98s","97s","96s",
            "87s","86s","85s",
            "76s","75s","74s",
            "65s","64s","63s",
            "54s","53s","43s",
        ],
        "description": "UTG+2 — ~18% of hands"
    },
    "MP": {
        "open": [
            "AA","KK","QQ","JJ","TT","99","88","77","66","55",
            "AKs","AQs","AJs","ATs","A9s","A8s","A7s","A6s","A5s","A4s","A3s","A2s",
            "AKo","AQo","AJo","ATo","A9o","A8o","A7o",
            "KQs","KJs","KTs","K9s","K8s","K7s","K6s",
            "KQo","KJo","KTo","K9o",
            "QJs","QTs","Q9s","Q8s","Q7s",
            "QJo","QTo","Q9o",
            "JTs","J9s","J8s","J7s","J6s",
            "JTo","J9o",
            "T9s","T8s","T7s","T6s",
            "T9o",
            "98s","97s","96s","95s",
            "87s","86s","85s","84s",
            "76s","75s","74s",
            "65s","64s","63s",
            "54s","53s","52s",
            "43s","42s","32s",
        ],
        "description": "MP — ~22% of hands"
    },
    "HJ": {
        "open": [
            "AA","KK","QQ","JJ","TT","99","88","77","66","55","44",
            "AKs","AQs","AJs","ATs","A9s","A8s","A7s","A6s","A5s","A4s","A3s","A2s",
            "AKo","AQo","AJo","ATo","A9o","A8o","A7o","A6o",
            "KQs","KJs","KTs","K9s","K8s","K7s","K6s","K5s",
            "KQo","KJo","KTo","K9o","K8o",
            "QJs","QTs","Q9s","Q8s","Q7s","Q6s",
            "QJo","QTo","Q9o","Q8o",
            "JTs","J9s","J8s","J7s","J6s","J5s",
            "JTo","J9o","J8o",
            "T9s","T8s","T7s","T6s","T5s",
            "T9o","T8o",
            "98s","97s","96s","95s","94s",
            "87s","86s","85s","84s",
            "76s","75s","74s","73s",
            "65s","64s","63s","62s",
            "54s","53s","52s",
            "43s","42s","32s",
        ],
        "description": "HJ (Hijack) — ~26% of hands"
    },
    "CO": {
        "open": [
            "AA","KK","QQ","JJ","TT","99","88","77","66","55","44","33","22",
            "AKs","AQs","AJs","ATs","A9s","A8s","A7s","A6s","A5s","A4s","A3s","A2s",
            "AKo","AQo","AJo","ATo","A9o","A8o","A7o","A6o","A5o","A4o",
            "KQs","KJs","KTs","K9s","K8s","K7s","K6s","K5s","K4s","K3s","K2s",
            "KQo","KJo","KTo","K9o","K8o","K7o",
            "QJs","QTs","Q9s","Q8s","Q7s","Q6s","Q5s","Q4s",
            "QJo","QTo","Q9o","Q8o","Q7o",
            "JTs","J9s","J8s","J7s","J6s","J5s","J4s",
            "JTo","J9o","J8o","J7o",
            "T9s","T8s","T7s","T6s","T5s","T4s",
            "T9o","T8o","T7o",
            "98s","97s","96s","95s","94s","93s",
            "98o","97o",
            "87s","86s","85s","84s","83s",
            "87o","86o",
            "76s","75s","74s","73s","72s",
            "76o","75o",
            "65s","64s","63s","62s",
            "65o",
            "54s","53s","52s",
            "43s","42s","32s",
        ],
        "description": "CO (Cutoff) — ~34% of hands"
    },
    "BTN": {
        "open": [
            "AA","KK","QQ","JJ","TT","99","88","77","66","55","44","33","22",
            "AKs","AQs","AJs","ATs","A9s","A8s","A7s","A6s","A5s","A4s","A3s","A2s",
            "AKo","AQo","AJo","ATo","A9o","A8o","A7o","A6o","A5o","A4o","A3o","A2o",
            "KQs","KJs","KTs","K9s","K8s","K7s","K6s","K5s","K4s","K3s","K2s",
            "KQo","KJo","KTo","K9o","K8o","K7o","K6o","K5o",
            "QJs","QTs","Q9s","Q8s","Q7s","Q6s","Q5s","Q4s","Q3s","Q2s",
            "QJo","QTo","Q9o","Q8o","Q7o","Q6o",
            "JTs","J9s","J8s","J7s","J6s","J5s","J4s","J3s","J2s",
            "JTo","J9o","J8o","J7o","J6o",
            "T9s","T8s","T7s","T6s","T5s","T4s","T3s","T2s",
            "T9o","T8o","T7o","T6o",
            "98s","97s","96s","95s","94s","93s","92s",
            "98o","97o","96o",
            "87s","86s","85s","84s","83s","82s",
            "87o","86o","85o",
            "76s","75s","74s","73s","72s",
            "76o","75o","74o",
            "65s","64s","63s","62s",
            "65o","64o",
            "54s","53s","52s",
            "54o","53o",
            "43s","42s","32s",
            "43o",
        ],
        "description": "BTN (Button) — ~46% of hands"
    },
    "SB": {
        "open": [
            "AA","KK","QQ","JJ","TT","99","88","77","66","55","44","33","22",
            "AKs","AQs","AJs","ATs","A9s","A8s","A7s","A6s","A5s","A4s","A3s","A2s",
            "AKo","AQo","AJo","ATo","A9o","A8o","A7o","A6o","A5o","A4o","A3o","A2o",
            "KQs","KJs","KTs","K9s","K8s","K7s","K6s","K5s","K4s","K3s","K2s",
            "KQo","KJo","KTo","K9o","K8o","K7o","K6o","K5o","K4o",
            "QJs","QTs","Q9s","Q8s","Q7s","Q6s","Q5s","Q4s","Q3s","Q2s",
            "QJo","QTo","Q9o","Q8o","Q7o","Q6o","Q5o",
            "JTs","J9s","J8s","J7s","J6s","J5s","J4s","J3s","J2s",
            "JTo","J9o","J8o","J7o","J6o","J5o",
            "T9s","T8s","T7s","T6s","T5s","T4s","T3s","T2s",
            "T9o","T8o","T7o","T6o","T5o",
            "98s","97s","96s","95s","94s","93s","92s",
            "98o","97o","96o","95o",
            "87s","86s","85s","84s","83s","82s",
            "87o","86o","85o","84o",
            "76s","75s","74s","73s","72s",
            "76o","75o","74o","73o",
            "65s","64s","63s","62s",
            "65o","64o","63o",
            "54s","53s","52s","54o","53o",
            "43s","42s","32s","43o",
        ],
        "description": "SB (Small Blind) — ~52% vs BB"
    },
    "BB": {
        "open": [],  # BB never RFI; uses defend ranges instead
        "defend_vs_open": [
            "AA","KK","QQ","JJ","TT","99","88","77","66","55","44","33","22",
            "AKs","AQs","AJs","ATs","A9s","A8s","A7s","A6s","A5s","A4s","A3s","A2s",
            "AKo","AQo","AJo","ATo","A9o","A8o","A7o",
            "KQs","KJs","KTs","K9s","K8s","K7s","K6s","K5s","K4s","K3s","K2s",
            "KQo","KJo","KTo","K9o","K8o",
            "QJs","QTs","Q9s","Q8s","Q7s","Q6s","Q5s","Q4s","Q3s",
            "QJo","QTo","Q9o","Q8o",
            "JTs","J9s","J8s","J7s","J6s","J5s","J4s",
            "JTo","J9o","J8o","J7o",
            "T9s","T8s","T7s","T6s","T5s","T4s",
            "T9o","T8o","T7o",
            "98s","97s","96s","95s","94s",
            "98o","97o","96o",
            "87s","86s","85s","84s",
            "87o","86o",
            "76s","75s","74s","73s",
            "65s","64s","63s",
            "54s","53s","43s",
        ],
        "description": "BB — defends ~45% vs BTN open"
    },
}

# ── 3-bet ranges ──────────────────────────────────────────────────────────────

THREEBET_RANGES = {
    "BTN_vs_CO": ["AA","KK","QQ","JJ","TT","AKs","AQs","AJs","ATs","A5s","A4s","KQs","AKo","AQo"],
    "BB_vs_BTN": ["AA","KK","QQ","JJ","TT","99","AKs","AQs","AJs","ATs","A5s","A4s","A3s","KQs","KJs","QJs","AKo","AQo","AJo"],
    "SB_vs_BTN": ["AA","KK","QQ","JJ","TT","AKs","AQs","AJs","A5s","A4s","KQs","AKo","AQo"],
    "default":   ["AA","KK","QQ","JJ","AKs","AQs","AKo"],
}

# ── Public API ────────────────────────────────────────────────────────────────

def get_rfi_range(position: str) -> list:
    """Return the open-raise range for a position."""
    pos = position.upper()
    data = RFI_RANGES.get(pos, {})
    return data.get("open", [])


def get_defend_range(position: str) -> list:
    """Return BB defend range."""
    pos = position.upper()
    if pos == "BB":
        return RFI_RANGES["BB"].get("defend_vs_open", [])
    return []


def get_3bet_range(hero_pos: str, villain_pos: str) -> list:
    """Return 3-bet range for a given position matchup."""
    key = f"{hero_pos.upper()}_vs_{villain_pos.upper()}"
    return THREEBET_RANGES.get(key, THREEBET_RANGES["default"])


def is_in_range(hand_str: str, range_list: list) -> bool:
    """Check if a hand string like 'AKo' is in a range list."""
    if not hand_str:
        return False
    return hand_str in range_list


def hand_position_action(hand_str: str, position: str) -> dict:
    """
    Given a hand and position, return the GTO recommended pre-flop action.

    Returns dict with: action, in_rfi_range, in_3bet_range, range_pct
    """
    rfi = get_rfi_range(position)
    in_rfi = is_in_range(hand_str, rfi)

    pos_data = RFI_RANGES.get(position.upper(), {})
    total_combos = 1326  # total possible hold'em starting hands
    range_size = len(rfi)

    return {
        "action": "RAISE" if in_rfi else "FOLD",
        "in_rfi_range": in_rfi,
        "range_description": pos_data.get("description", ""),
        "range_size": range_size,
    }
