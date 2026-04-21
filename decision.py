"""
module2_engine/decision.py
----------------------------
Main decision engine. Takes a GameState dict from Module 1
and returns a structured recommendation.

Decision hierarchy
------------------
1. Short stack (< 20bb) → Push/fold Nash
2. Pre-flop (no board)  → GTO RFI chart
3. Post-flop            → Pot odds vs equity
4. 3-bet spot           → 3-bet range check
"""

from typing import Optional
from gto_charts import hand_to_str, hand_position_action, get_3bet_range, is_in_range
from push_fold import should_push, should_call_push
from equity import calc_equity_preflop, calc_equity_postflop, pot_odds_decision


# ── Stack depth helper ────────────────────────────────────────────────────────

def effective_bb(hero_stack: Optional[float],
                 villain_stack: Optional[float],
                 big_blind: float = 100.0) -> Optional[float]:
    """
    Calculate effective stack in big blinds.
    Uses the smaller of the two stacks.
    """
    if hero_stack is None or villain_stack is None:
        return None
    eff = min(hero_stack, villain_stack)
    return eff / big_blind


# ── Steal / 3-bet detection ───────────────────────────────────────────────────

STEAL_POSITIONS = {"CO", "BTN", "SB"}

def is_steal_spot(position: str, street: str) -> bool:
    return position.upper() in STEAL_POSITIONS and street == "preflop"

def is_3bet_spot(position: str, villain_position: str) -> bool:
    return position.upper() in {"BB", "SB", "BTN", "CO"}


# ── Main decision function ────────────────────────────────────────────────────

def make_decision(game_state: dict, big_blind: float = 100.0, num_opponents: int = 1) -> dict:
    """
    Core decision engine.

    Parameters
    ----------
    game_state : dict from module1_vision parser
    big_blind  : chip value of 1 BB (default 100)

    Returns
    -------
    dict with:
        action       : "FOLD" | "CALL" | "RAISE" | "PUSH" | "CHECK"
        equity       : float % or None
        pot_odds     : float % or None
        reasoning    : str explanation
        confidence   : "high" | "medium" | "low"
        decision_type: "push_fold" | "gto_preflop" | "pot_odds" | "steal" | "unknown"
    """
    hole_cards     = game_state.get("hole_cards", [None, None])
    community      = game_state.get("community_cards", [])
    pot            = game_state.get("pot")
    hero_stack     = game_state.get("hero_stack")
    villain_stack  = game_state.get("villain_stack")
    position       = game_state.get("position", "unknown")
    street         = game_state.get("street", "preflop")

    hand_str = hand_to_str(hole_cards)

    result = {
        "action": "FOLD",
        "equity": None,
        "pot_odds": None,
        "edge": None,
        "reasoning": "Insufficient data to make decision.",
        "confidence": "low",
        "decision_type": "unknown",
        "hand": hand_str,
        "position": position,
        "street": street,
    }

    # ── Guard: need at least hole cards ──────────────────────────────────────
    if not hand_str:
        result["reasoning"] = "Could not parse hole cards from screenshot."
        return result

    # ── Calculate effective stack depth ──────────────────────────────────────
    eff_bb = effective_bb(hero_stack, villain_stack, big_blind)

    # ── 1. Short stack: push/fold mode ───────────────────────────────────────
    if eff_bb is not None and eff_bb <= 20 and street == "preflop":
        pf = should_push(hand_str, position, eff_bb)
        equity = calc_equity_preflop(hole_cards, num_opponents=num_opponents, simulations=2000)

        result.update({
            "action": pf["action"],
            "equity": round(equity * 100, 1) if equity else None,
            "confidence": "high",
            "decision_type": "push_fold",
            "reasoning": (
                f"{hand_str} at {position} with {eff_bb:.1f}bb → "
                f"Nash push/fold: {pf['action']}. "
                f"{'Hand is in push range.' if pf['in_push_range'] else 'Hand is outside push range — fold.'}"
            ),
        })
        return result

    # ── 2. Pre-flop: GTO chart ────────────────────────────────────────────────
    if street == "preflop":
        gto = hand_position_action(hand_str, position)
        equity = calc_equity_preflop(hole_cards, num_opponents=num_opponents, simulations=2000)

        # Steal spot modifier
        if is_steal_spot(position, street):
            decision_type = "steal"
            reasoning = (
                f"{hand_str} in steal position {position}: "
                f"GTO recommends {gto['action']}. "
                f"{gto['range_description']}."
            )
        else:
            decision_type = "gto_preflop"
            reasoning = (
                f"{hand_str} from {position}: "
                f"GTO RFI range → {gto['action']}. "
                f"{gto['range_description']}."
            )

        result.update({
            "action": gto["action"],
            "equity": round(equity * 100, 1) if equity else None,
            "confidence": "high",
            "decision_type": decision_type,
            "reasoning": reasoning,
        })
        return result

    # ── 3. Post-flop: pot odds vs equity ─────────────────────────────────────
    if street in ("flop", "turn", "river") and len(community) >= 3:
        equity = calc_equity_postflop(hole_cards, community, num_opponents=num_opponents)

        if equity is None:
            result.update({
                "reasoning": "Could not calculate post-flop equity (library missing?).",
                "confidence": "low",
            })
            return result

        # Estimate call amount from pot (if villain bet ~67% pot as default)
        # In production this comes from bet sizing detection (future Module 1 addition)
        call_amount = (pot * 0.67) if pot else None

        if call_amount and pot:
            odds_result = pot_odds_decision(equity, call_amount, pot)
            action = odds_result["decision"]
            pot_odds_pct = odds_result["pot_odds"]
            edge = odds_result["edge"]
            reasoning = (
                f"{hand_str} on {street} — "
                f"Equity: {equity*100:.1f}% vs Pot odds: {pot_odds_pct:.1f}% → "
                f"{action}. Edge: {edge:+.1f}%."
            )
        else:
            # No pot data — pure equity-based decision
            action = "CALL" if equity > 0.45 else "FOLD"
            pot_odds_pct = None
            edge = None
            reasoning = (
                f"{hand_str} on {street} — "
                f"Equity: {equity*100:.1f}% → "
                f"{'Strong enough to continue.' if action == 'CALL' else 'Insufficient equity — fold.'}"
            )

        result.update({
            "action": action,
            "equity": round(equity * 100, 1),
            "pot_odds": pot_odds_pct,
            "edge": edge,
            "confidence": "high" if pot else "medium",
            "decision_type": "pot_odds",
            "reasoning": reasoning,
        })
        return result

    # ── Fallback ──────────────────────────────────────────────────────────────
    result["reasoning"] = (
        f"Could not determine decision context for {hand_str} on street={street}."
    )
    return result


# ── Formatted output for UI ───────────────────────────────────────────────────

def format_recommendation(decision: dict) -> str:
    """
    Format decision dict into a clean single-line recommendation for the UI.

    Example: "Recommended Action: RAISE | Equity: 67.3% | Edge: +12.1%"
    """
    action   = decision.get("action", "UNKNOWN")
    equity   = decision.get("equity")
    pot_odds = decision.get("pot_odds")
    edge     = decision.get("edge")

    parts = [f"Recommended Action: {action}"]

    if equity is not None:
        parts.append(f"Equity: {equity}%")
    if pot_odds is not None:
        parts.append(f"Pot Odds: {pot_odds}%")
    if edge is not None:
        sign = "+" if edge >= 0 else ""
        parts.append(f"Edge: {sign}{edge}%")

    return " | ".join(parts)
