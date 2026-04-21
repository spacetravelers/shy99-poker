"""
module2_engine/equity.py
--------------------------
Hand equity calculation using the `treys` library.

Supports:
  - Pre-flop equity (Monte Carlo simulation)
  - Post-flop equity (exact enumeration up to river)
  - Pot odds vs equity decision
"""

from typing import List, Optional, Tuple
try:
    from treys import Card, Evaluator, Deck
    TREYS_AVAILABLE = True
except ImportError:
    TREYS_AVAILABLE = False

import random


evaluator = Evaluator() if TREYS_AVAILABLE else None


# ── Card string conversion ────────────────────────────────────────────────────
# Our parser outputs "Ah", "Kd", "2c" etc.
# treys expects the same format but needs Card.new()

def to_treys(card_str: str) -> int:
    """Convert "Ah" -> treys int. Returns None on failure."""
    if not TREYS_AVAILABLE or not card_str:
        return None
    try:
        # treys uses uppercase rank + lowercase suit
        rank = card_str[:-1].upper()
        suit = card_str[-1].lower()
        # treys uses 'T' for 10
        if rank == "10":
            rank = "T"
        return Card.new(rank + suit)
    except Exception:
        return None


def to_treys_list(cards: List[str]) -> List[int]:
    """Convert a list of card strings to treys ints, skipping Nones."""
    result = []
    for c in cards:
        t = to_treys(c)
        if t is not None:
            result.append(t)
    return result


# ── Equity calculation ────────────────────────────────────────────────────────

def calc_equity_preflop(
    hole_cards: List[str],
    num_opponents: int = 1,
    simulations: int = 5000,
) -> Optional[float]:
    """
    Monte Carlo equity estimate for pre-flop.

    Parameters
    ----------
    hole_cards    : ["Ah", "Kd"]
    num_opponents : number of villains (1–8)
    simulations   : number of random runouts

    Returns
    -------
    equity as float 0.0–1.0, or None on error
    """
    if not TREYS_AVAILABLE:
        return None

    hero = to_treys_list(hole_cards)
    if len(hero) != 2:
        return None

    wins = 0
    ties = 0

    for _ in range(simulations):
        deck = Deck()
        # Remove known cards
        deck.cards = [c for c in deck.cards if c not in hero]
        random.shuffle(deck.cards)

        # Deal opponent hands
        opponents = []
        try:
            for _ in range(num_opponents):
                opp = deck.draw(2)
                opponents.append(opp)
            board = deck.draw(5)
        except Exception:
            continue

        hero_score = evaluator.evaluate(board, hero)
        opp_scores = [evaluator.evaluate(board, opp) for opp in opponents]

        best_opp = min(opp_scores)  # lower = better in treys
        if hero_score < best_opp:
            wins += 1
        elif hero_score == best_opp:
            ties += 1

    total = simulations
    return (wins + ties * 0.5) / total if total > 0 else None


def calc_equity_postflop(
    hole_cards: List[str],
    community_cards: List[str],
    num_opponents: int = 1,
    simulations: int = 3000,
) -> Optional[float]:
    """
    Monte Carlo equity for flop/turn (enumerates remaining board cards).

    Returns equity as float 0.0–1.0.
    """
    if not TREYS_AVAILABLE:
        return None

    hero = to_treys_list(hole_cards)
    board_known = to_treys_list(community_cards)

    if len(hero) != 2:
        return None

    cards_to_deal = 5 - len(board_known)  # 2 on flop, 1 on turn, 0 on river
    wins = 0
    ties = 0

    for _ in range(simulations):
        deck = Deck()
        known = hero + board_known
        deck.cards = [c for c in deck.cards if c not in known]
        random.shuffle(deck.cards)

        try:
            opponents = []
            for _ in range(num_opponents):
                opp = deck.draw(2)
                opponents.append(opp)
            runout = board_known + deck.draw(cards_to_deal)
        except Exception:
            continue

        hero_score = evaluator.evaluate(runout, hero)
        opp_scores = [evaluator.evaluate(runout, opp) for opp in opponents]
        best_opp = min(opp_scores)

        if hero_score < best_opp:
            wins += 1
        elif hero_score == best_opp:
            ties += 1

    total = simulations
    return (wins + ties * 0.5) / total if total > 0 else None


# ── Pot odds ──────────────────────────────────────────────────────────────────

def calc_pot_odds(call_amount: float, pot_size: float) -> Optional[float]:
    """
    Pot odds = call / (pot + call)

    Returns float 0.0–1.0 representing the equity needed to break even.
    """
    if call_amount is None or pot_size is None:
        return None
    total = pot_size + call_amount
    if total <= 0:
        return None
    return call_amount / total


def pot_odds_decision(
    equity: float,
    call_amount: float,
    pot_size: float,
) -> dict:
    """
    Compare equity vs pot odds to recommend call/fold.

    Returns dict with decision, equity, pot_odds, edge.
    """
    pot_odds = calc_pot_odds(call_amount, pot_size)
    if pot_odds is None:
        return {"decision": "UNKNOWN", "reason": "Missing pot/call data"}

    edge = equity - pot_odds
    decision = "CALL" if equity >= pot_odds else "FOLD"

    return {
        "decision": decision,
        "equity": round(equity * 100, 1),
        "pot_odds": round(pot_odds * 100, 1),
        "edge": round(edge * 100, 1),
        "reason": (
            f"Equity {equity*100:.1f}% {'>' if equity >= pot_odds else '<'} "
            f"Pot odds {pot_odds*100:.1f}% → {decision}"
        ),
    }
