"""
trainer/engine.py
------------------
Pure logic layer for the GTO Scenario Trainer.
No GUI imports — fully testable in isolation.

Responsibilities
----------------
- Load scenarios from JSON
- Deal random hole cards
- Evaluate user action against GTO strategy
- Track session statistics
"""

import json
import random
import os
from typing import Optional

# ── Constants ─────────────────────────────────────────────────────────────────

RANKS  = ["2", "3", "4", "5", "6", "7", "8", "9", "T", "J", "Q", "K", "A"]
SUITS  = ["h", "d", "c", "s"]
SUIT_SYMBOLS = {"h": "♥", "d": "♦", "c": "♣", "s": "♠"}
SUIT_COLORS  = {"h": "#e74c3c", "d": "#3498db", "c": "#2ecc71", "s": "#ecf0f1"}

RANK_VAL = {r: i for i, r in enumerate(RANKS)}

VALID_ACTIONS = {"FOLD", "CALL", "RAISE"}

DEFAULT_SCENARIOS_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "data", "gto_scenarios.json"
)


# ── Data layer ────────────────────────────────────────────────────────────────

def load_scenarios(path: str = DEFAULT_SCENARIOS_PATH) -> list:
    """Load GTO scenario list from a JSON file."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_scenario_by_id(scenarios: list, scenario_id: str) -> Optional[dict]:
    for s in scenarios:
        if s["id"] == scenario_id:
            return s
    return None


# ── Card utilities ────────────────────────────────────────────────────────────

def deal_random_hand() -> tuple:
    """
    Deal two distinct random cards.
    Returns ((rank1, suit1), (rank2, suit2))
    """
    deck = [(r, s) for r in RANKS for s in SUITS]
    c1, c2 = random.sample(deck, 2)
    return c1, c2


def cards_to_hand_str(c1: tuple, c2: tuple) -> str:
    """
    Convert two card tuples to hand notation like 'AKo', 'QJs', 'TT'.
    Always returns higher rank first.
    """
    r1, s1 = c1
    r2, s2 = c2

    if RANK_VAL[r1] < RANK_VAL[r2]:
        r1, r2 = r2, r1
        s1, s2 = s2, s1

    if r1 == r2:
        return r1 + r2

    suited = "s" if s1 == s2 else "o"
    return r1 + r2 + suited


def card_display(rank: str, suit: str) -> dict:
    """Return display info for a single card."""
    return {
        "rank":   rank,
        "suit":   suit,
        "symbol": SUIT_SYMBOLS[suit],
        "color":  SUIT_COLORS[suit],
        "label":  rank + SUIT_SYMBOLS[suit],
    }


# ── GTO lookup ────────────────────────────────────────────────────────────────

def lookup_gto(scenario: dict, hand_str: str) -> dict:
    """
    Look up GTO strategy for a hand in a scenario.

    Returns the strategy dict, e.g.:
        {"RAISE": 100}
        {"RAISE": 50, "FOLD": 50}
        {"FOLD": 100}

    Falls back to {"FOLD": 100} if hand not in scenario.
    """
    return scenario["strategy"].get(hand_str, {"FOLD": 100})


def primary_action(strategy: dict) -> str:
    """Return the action with the highest frequency."""
    return max(strategy, key=strategy.get)


def is_mixed_strategy(strategy: dict) -> bool:
    """Return True if the GTO strategy involves multiple actions."""
    return len(strategy) > 1


# ── Evaluation ────────────────────────────────────────────────────────────────

def evaluate_action(user_action: str, strategy: dict) -> dict:
    """
    Compare user action against GTO strategy.

    Returns
    -------
    dict with:
        correct        : bool
        grade          : "correct" | "mixed" | "incorrect"
        gto_primary    : str — best GTO action
        gto_frequency  : int — frequency of best action
        user_frequency : int — GTO frequency of user's action (0 if not in range)
        ev_loss        : str — qualitative EV loss description
    """
    user_action = user_action.upper()
    gto_primary = primary_action(strategy)
    gto_freq    = strategy.get(gto_primary, 0)
    user_freq   = strategy.get(user_action, 0)
    mixed       = is_mixed_strategy(strategy)

    if user_action == gto_primary:
        grade   = "correct"
        correct = True
    elif mixed and user_freq > 0:
        grade   = "mixed"
        correct = True   # acceptable — part of GTO range
    else:
        grade   = "incorrect"
        correct = False

    # Qualitative EV loss
    if grade == "correct":
        ev_loss = "No EV loss."
    elif grade == "mixed":
        ev_loss = f"Slight EV loss — GTO plays {gto_primary} {gto_freq}% here."
    else:
        diff = 100 - user_freq
        if diff >= 80:
            ev_loss = "Significant EV loss."
        elif diff >= 40:
            ev_loss = "Moderate EV loss."
        else:
            ev_loss = "Minor EV loss."

    return {
        "correct":       correct,
        "grade":         grade,
        "gto_primary":   gto_primary,
        "gto_frequency": gto_freq,
        "user_frequency": user_freq,
        "ev_loss":       ev_loss,
        "strategy":      strategy,
    }


def build_feedback_message(
    hand_str:   str,
    scenario:   dict,
    user_action: str,
    evaluation: dict,
) -> str:
    """
    Build the detailed feedback string shown to the user.
    """
    pos     = scenario.get("hero_position", scenario.get("position","?"))
    stack   = scenario["stack_bb"]
    strat   = evaluation["strategy"]
    grade   = evaluation["grade"]
    primary = evaluation["gto_primary"]

    # Strategy description
    strat_parts = [f"{action} {freq}%" for action, freq in sorted(strat.items(), key=lambda x: -x[1])]
    strat_str = " / ".join(strat_parts)

    if grade == "correct":
        verdict = "✓  Correct!"
    elif grade == "mixed":
        verdict = "~ Acceptable (mixed strategy)"
    else:
        verdict = "✗  Incorrect"

    lines = [
        verdict,
        f"",
        f"Hand:      {hand_str}",
        f"Position:  {pos}  |  Stack: {stack}bb",
        f"",
        f"GTO play:  {strat_str}",
        f"Your play: {user_action}",
        f"",
        f"{evaluation['ev_loss']}",
    ]
    return "\n".join(lines)


# ── Session tracker ───────────────────────────────────────────────────────────

class TrainerSession:
    """Tracks statistics across a training session."""

    def __init__(self):
        self.reset()

    def reset(self):
        self.hands_played  = 0
        self.correct       = 0
        self.mixed         = 0
        self.incorrect     = 0
        self.history       = []

    def record(self, hand_str: str, scenario_id: str, user_action: str, evaluation: dict):
        self.hands_played += 1
        grade = evaluation["grade"]
        if grade == "correct":
            self.correct += 1
        elif grade == "mixed":
            self.mixed += 1
        else:
            self.incorrect += 1

        self.history.append({
            "hand":        hand_str,
            "scenario_id": scenario_id,
            "action":      user_action,
            "grade":       grade,
        })

    @property
    def accuracy(self) -> float:
        if self.hands_played == 0:
            return 0.0
        return round((self.correct + self.mixed) / self.hands_played * 100, 1)

    def summary(self) -> str:
        return (
            f"Hands: {self.hands_played}  |  "
            f"✓ {self.correct}  ~{self.mixed}  ✗ {self.incorrect}  |  "
            f"Accuracy: {self.accuracy}%"
        )


# ── Table game-state builder (for Streamlit trainer) ──────────────────────────

POSITIONS_9MAX = ["UTG", "UTG1", "UTG2", "MP", "HJ", "CO", "BTN", "SB", "BB"]
POSITIONS_6MAX = ["UTG", "HJ", "CO", "BTN", "SB", "BB"]


def _table_layout(hero_pos: str) -> list:
    """Return the seat-order list for this hero position."""
    if hero_pos in ["UTG1", "UTG2", "MP"]:
        return POSITIONS_9MAX
    if hero_pos in POSITIONS_6MAX:
        return POSITIONS_6MAX
    return POSITIONS_9MAX


def scenario_game_state(scenario: dict) -> dict:
    """
    Build a full game-state dict from a scenario for the Streamlit trainer.

    Parses prior_action to reconstruct what each seat did, the pot size,
    and how much hero has to call.

    Returns
    -------
    dict with keys:
        seats            : list of seat dicts
        hero_idx         : int
        positions        : list[str]
        pot_bb           : float
        to_call_bb       : float
        suggest_raise_bb : float
        hero_pos         : str
        stack_bb         : float
    """
    hero_pos  = scenario.get("position", scenario.get("hero_position", "BTN"))
    stack_bb  = float(scenario.get("stack_bb", 40))
    prior_str = scenario.get("prior_action", "Folds to you")
    prior_low = prior_str.lower()

    positions = _table_layout(hero_pos)
    if hero_pos not in positions:
        positions = POSITIONS_9MAX
    hero_idx = positions.index(hero_pos)

    SB_AMT     = 0.5
    BB_AMT     = 1.0
    OPEN_SIZE  = 2.5   # standard open raise in bb

    # ── Detect whether someone raised before hero ──────────────────
    raiser_pos = None
    for pos in positions:
        if f"{pos.lower()} raise" in prior_low:
            raiser_pos = pos
            break

    has_raise = raiser_pos is not None

    # ── Pot starts with both blinds posted ──────────────────────────
    pot_bb = SB_AMT + BB_AMT
    if has_raise:
        pot_bb += OPEN_SIZE   # raiser's bet adds to pot

    # ── Build seat list ─────────────────────────────────────────────
    seats = []
    for i, pos in enumerate(positions):
        action    = None
        bet_bb    = 0.0

        if pos == "SB":
            bet_bb = SB_AMT
            if has_raise and "sb fold" in prior_low:
                action = "FOLD"   # SB folded after the open
            else:
                action = "POST"
        elif pos == "BB":
            bet_bb = BB_AMT
            if pos == hero_pos:
                action = None     # hero decides
            else:
                action = "POST"
        elif pos == hero_pos:
            action = None         # hero decides
        elif pos == raiser_pos:
            bet_bb = OPEN_SIZE
            action = "RAISE"
        elif i < hero_idx:
            action = "FOLD"
        # i > hero_idx → not yet acted (action stays None)

        hero_post  = (BB_AMT if hero_pos == "BB"
                      else SB_AMT if hero_pos == "SB"
                      else 0.0)
        remaining  = stack_bb - (bet_bb if pos != hero_pos else hero_post)

        seats.append({
            "position":    pos,
            "starting_bb": stack_bb,
            "remaining_bb": max(remaining, 0.0),
            "bet_bb":      bet_bb,
            "action":      action,
            "is_hero":     pos == hero_pos,
        })

    # ── Hero's cost to call ─────────────────────────────────────────
    hero_already  = (BB_AMT if hero_pos == "BB"
                     else SB_AMT if hero_pos == "SB"
                     else 0.0)
    to_call_bb    = max(OPEN_SIZE - hero_already, 0.0) if has_raise else 0.0

    # ── Default raise suggestion ────────────────────────────────────
    suggest_raise = round(OPEN_SIZE * 3.0, 1) if has_raise else 2.5

    return {
        "seats":            seats,
        "hero_idx":         hero_idx,
        "positions":        positions,
        "pot_bb":           round(pot_bb, 1),
        "to_call_bb":       round(to_call_bb, 1),
        "suggest_raise_bb": suggest_raise,
        "hero_pos":         hero_pos,
        "stack_bb":         stack_bb,
    }
