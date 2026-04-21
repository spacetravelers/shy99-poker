"""
app.py
-------
Module 3 — Streamlit UI for the GGPoker Analyzer.

Run with:
    streamlit run app.py
"""

import math
import random
import streamlit as st
import streamlit.components.v1 as components
from PIL import Image
import tempfile
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from parser import parse_screenshot
from decision import make_decision, format_recommendation
from gto_charts import RFI_RANGES, THREEBET_RANGES
from trainer.engine import (
    load_scenarios,
    deal_random_hand,
    cards_to_hand_str,
    lookup_gto,
    evaluate_action,
    build_feedback_message,
    scenario_game_state,
)

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(page_title="SHY99", page_icon="♠", layout="wide")

# ── CSS ───────────────────────────────────────────────────────────────────────

st.markdown("""<style>
    /* ── Global ── */
    .stApp { background-color: #0f1923; }
    section[data-testid="stSidebar"] { background-color: #0b131c; }
    section[data-testid="stSidebar"] * { color: #c8d6e5 !important; }
    h1,h2,h3,p,label { color: #ecf0f1; }
    hr { border-color: #2d3d50 !important; }

    /* ── Tabs ── */
    .stTabs [data-baseweb="tab-list"] {
        background: #0b131c; border-radius: 10px; padding: 4px; gap: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        background: transparent; color: #7f8c8d;
        border-radius: 8px; font-weight: 600; font-size: 14px;
    }
    .stTabs [aria-selected="true"] {
        background: #1e2d40 !important; color: #ecf0f1 !important;
    }

    /* ── Action box ── */
    .action-box {
        padding: 28px 32px; border-radius: 14px; text-align: center;
        margin: 16px 0; box-shadow: 0 4px 24px rgba(0,0,0,0.4);
    }
    .action-RAISE { background:#0d2b0d; border:2px solid #2ecc71; }
    .action-CALL  { background:#0d1f30; border:2px solid #3498db; }
    .action-FOLD  { background:#2b0d0d; border:2px solid #e74c3c; }
    .action-PUSH  { background:#1e0d2b; border:2px solid #9b59b6; }
    .action-CHECK { background:#1f1e0d; border:2px solid #f1c40f; }
    .action-label {
        font-size: 52px; font-weight: 800; letter-spacing: 6px;
        margin: 0; text-shadow: 0 2px 8px rgba(0,0,0,0.5);
    }
    .action-RAISE .action-label { color: #2ecc71; }
    .action-CALL  .action-label { color: #3498db; }
    .action-FOLD  .action-label { color: #e74c3c; }
    .action-PUSH  .action-label { color: #9b59b6; }
    .action-CHECK .action-label { color: #f1c40f; }

    /* ── Stats ── */
    .stat-label { font-size: 12px; color: #7f8c8d; margin-bottom: 2px; }
    .stat-value { font-size: 24px; font-weight: 700; }

    /* ── Reasoning ── */
    .reasoning-box {
        background: #111827; border-left: 3px solid #3498db;
        padding: 14px 18px; border-radius: 8px; font-size: 13px;
        color: #95a5a6; margin-top: 12px; line-height: 1.6;
    }

    /* ── Inline card chip (results panel) ── */
    .card-chip {
        display: inline-block; padding: 4px 10px; border-radius: 6px;
        background: #1e2d40; border: 1px solid #2d3d50;
        font-family: monospace; font-size: 15px; font-weight: 700; margin: 2px;
    }
    .card-chip.heart   { color: #e74c3c; border-color: #7f1d1d; }
    .card-chip.diamond { color: #3498db; border-color: #1e3a5f; }
    .card-chip.club    { color: #2ecc71; border-color: #14532d; }
    .card-chip.spade   { color: #ecf0f1; border-color: #2d3d50; }

    /* ── Poker table seats ── */
    .seat { position:absolute; width:80px; text-align:center; z-index:2; border-radius:10px; padding:5px 3px; }
    .hero-seat { background:#0a1f0e; border:2px solid #2ecc71; }
    .opp-seat  { background:#111827; border:1px solid #2d3d50; }
    .sh  { font-size:9px;  color:#7f8c8d; font-weight:700; letter-spacing:1px; text-transform:uppercase; }
    .sp  { font-size:11px; color:#f1c40f; font-weight:800; }
    .sc  { font-size:12px; font-weight:700; margin:2px 0; line-height:1.3; }
    .ss  { font-size:11px; color:#ecf0f1;  font-weight:600; }
    .tc  { font-size:13px; font-weight:700; }
    .pot-label    { color:#f1c40f; font-weight:700; font-size:14px; margin-top:6px; }
    .street-label { color:#7f8c8d; font-size:10px; letter-spacing:3px; margin-bottom:4px; }
    .comm-cards   { margin:5px 0; }
    .preflop-label { color:#2d3d50; font-size:11px; letter-spacing:2px; margin:6px 0; }

    /* ── Warning ── */
    .warning-box {
        background:#1f1700; border:1px solid #554400; border-radius:8px;
        padding:10px 14px; font-size:13px; color:#d4a017; margin-top:8px;
    }

    /* ── GTO range pills ── */
    .range-pill {
        display:inline-block; background:#1e2d40; border-radius:4px;
        padding:2px 6px; font-size:11px; font-family:monospace;
        color:#ecf0f1; margin:1px;
    }

    /* ── Trainer action buttons ── */
    div[data-testid="column"]:nth-child(1) div[data-testid="stButton"] button {
        background:#7f1d1d; border:1px solid #e74c3c; color:#ecf0f1;
        font-weight:700; font-size:14px; letter-spacing:1px;
    }
    div[data-testid="column"]:nth-child(1) div[data-testid="stButton"] button:hover {
        background:#991b1b; border-color:#f87171;
    }
    div[data-testid="column"]:nth-child(2) div[data-testid="stButton"] button {
        background:#1e3a5f; border:1px solid #3498db; color:#ecf0f1;
        font-weight:700; font-size:14px; letter-spacing:1px;
    }
    div[data-testid="column"]:nth-child(2) div[data-testid="stButton"] button:hover {
        background:#1e4976; border-color:#60aef5;
    }
    div[data-testid="column"]:nth-child(3) div[data-testid="stButton"] button {
        background:#14532d; border:1px solid #2ecc71; color:#ecf0f1;
        font-weight:700; font-size:14px; letter-spacing:1px;
    }
    div[data-testid="column"]:nth-child(3) div[data-testid="stButton"] button:hover {
        background:#166534; border-color:#4ade80;
    }
</style>""", unsafe_allow_html=True)


# ── Trainer scenarios (cached) ────────────────────────────────────────────────

@st.cache_data
def _load_trainer_scenarios() -> list:
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "data", "gto_scenarios.json")
    return load_scenarios(path)

TRAINER_SCENARIOS = _load_trainer_scenarios()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _chip_pile_svg(amount_bb: float, cx: float, cy: float, r: int = 12) -> str:
    """
    Casino-style TOP-VIEW chip pile in SVG.
    Multiple overlapping circles with ring pattern — looks like real poker chips.
    """
    if amount_bb <= 0:
        return ""

    # Colour by denomination (main, edge, highlight)
    if amount_bb >= 100:
        main, edge, hi = "#8e44ad", "#5b2c6f", "#d2b4de"   # purple  500bb
    elif amount_bb >= 25:
        main, edge, hi = "#1c2833", "#0b0b0b", "#717d7e"   # black   100bb
    elif amount_bb >= 10:
        main, edge, hi = "#1a5276", "#0e2f44", "#5dade2"   # blue     25bb
    elif amount_bb >= 5:
        main, edge, hi = "#1d6a39", "#0e3d21", "#52be80"   # green    10bb
    elif amount_bb >= 2:
        main, edge, hi = "#a93226", "#641e16", "#ec7063"   # red       5bb
    else:
        main, edge, hi = "#626567", "#2c3e50", "#aab7b8"   # grey      1bb

    n = min(5, max(1, int(math.log2(max(amount_bb, 1) + 1))))

    # Slightly offset positions for depth illusion (shadow chips behind)
    offsets = [(3, 4), (-3, 3), (2, -3), (-2, -4), (4, 1)]
    parts = []

    # Draw shadow chips (back to front)
    for i in range(n - 1, 0, -1):
        ox, oy = offsets[(i - 1) % len(offsets)]
        px, py = cx + ox * 0.7, cy + oy * 0.7
        op = 0.35 + i * 0.08
        parts.append(
            f'<circle cx="{px:.1f}" cy="{py:.1f}" r="{r}" '
            f'fill="{main}" stroke="{edge}" stroke-width="1.2" opacity="{op:.2f}"/>'
        )

    # Top chip — full detail
    parts += [
        # Main disc
        f'<circle cx="{cx:.0f}" cy="{cy:.0f}" r="{r}" fill="{main}" stroke="{edge}" stroke-width="1.8"/>',
        # Outer ring stripe
        f'<circle cx="{cx:.0f}" cy="{cy:.0f}" r="{int(r * 0.88)}" fill="none" stroke="{hi}" stroke-width="1.4" opacity="0.55"/>',
        # Dashed inset (classic casino pattern)
        f'<circle cx="{cx:.0f}" cy="{cy:.0f}" r="{int(r * 0.62)}" fill="none" stroke="{hi}" stroke-width="2" stroke-dasharray="3 2.5" opacity="0.45"/>',
        # Centre dot
        f'<circle cx="{cx:.0f}" cy="{cy:.0f}" r="2.5" fill="{hi}" opacity="0.5"/>',
        # Specular highlight (top-left)
        f'<ellipse cx="{cx - r*0.28:.1f}" cy="{cy - r*0.3:.1f}" rx="{r*0.28:.1f}" ry="{r*0.18:.1f}" fill="white" opacity="0.18" transform="rotate(-30,{cx},{cy})"/>',
    ]

    # Amount label
    label = f"{int(amount_bb)}bb" if amount_bb == int(amount_bb) else f"{amount_bb:.1f}bb"
    parts.append(
        f'<text x="{cx:.0f}" y="{cy + r + 13:.0f}" text-anchor="middle" '
        f'font-size="10" font-weight="800" fill="#f1c40f" font-family="Arial" '
        f'filter="url(#txt_shd)">{label}</text>'
    )
    return "\n".join(parts)


def _player_avatar_svg(cx: float, cy: float, is_hero: bool,
                       folded: bool = False, pos_label: str = "") -> str:
    """Poker player silhouette avatar for the SVG table layer."""
    if is_hero:
        ring, fill, bg, glow = "#2ecc71", "#27ae60", "#071a0e", "rgba(46,204,113,0.35)"
    elif folded:
        ring, fill, bg, glow = "#2d3d50", "#3a4a5a", "#0a0e14", "none"
    else:
        ring, fill, bg, glow = "#3498db", "#2980b9", "#071627", "rgba(52,152,219,0.3)"

    op = 'opacity="0.3"' if folded else ''
    glow_circle = (
        f'<circle cx="{cx:.0f}" cy="{cy:.0f}" r="21" fill="{glow}"/>'
        if not folded else ""
    )
    return (
        f'<g {op}>'
        + glow_circle +
        # Outer ring
        f'<circle cx="{cx:.0f}" cy="{cy:.0f}" r="18" '
        f'fill="{bg}" stroke="{ring}" stroke-width="1.8"/>'
        # Head
        f'<circle cx="{cx:.0f}" cy="{cy - 7:.0f}" r="6.5" fill="{fill}"/>'
        # Shoulders
        f'<path d="M {cx - 12:.0f} {cy + 10:.0f} '
        f'Q {cx:.0f} {cy + 1:.0f} {cx + 12:.0f} {cy + 10:.0f}" '
        f'fill="{fill}"/>'
        # Star for hero
        + (f'<text x="{cx:.0f}" y="{cy + 22:.0f}" text-anchor="middle" '
           f'font-size="9" fill="#f1c40f" font-weight="700">★</text>' if is_hero else '') +
        f'</g>'
    )


def _card_chip(card_str: str) -> str:
    """Styled inline card chip for the results panel."""
    if not card_str:
        return '<span class="card-chip">?</span>'
    suit = card_str[-1].lower()
    cls  = {"h": "heart", "d": "diamond", "c": "club", "s": "spade"}.get(suit, "")
    sym  = {"h": "♥", "d": "♦", "c": "♣", "s": "♠"}.get(suit, suit)
    return f'<span class="card-chip {cls}">{card_str[:-1]}{sym}</span>'


def _tc(card_str: str) -> str:
    """Tiny colored card for the poker table SVG overlay."""
    if not card_str:
        return '<span class="tc" style="color:#555">?</span>'
    suit  = card_str[-1].lower()
    color = {"h": "#e74c3c", "d": "#3498db", "c": "#2ecc71", "s": "#ecf0f1"}.get(suit, "#ecf0f1")
    sym   = {"h": "♥", "d": "♦", "c": "♣", "s": "♠"}.get(suit, suit)
    return f'<span class="tc" style="color:{color}">{card_str[:-1]}{sym}</span>'


# ── Post-flop board dealer ─────────────────────────────────────────────────────
_ALL_RANKS = "23456789TJQKA"
_ALL_SUITS = "shdc"

def _deal_board(hole_cards: tuple, n_cards: int) -> list:
    """Deal n_cards community cards, excluding hero's hole cards."""
    exclude = {r + s for r, s in hole_cards}
    deck = [r + s for r in _ALL_RANKS for s in _ALL_SUITS if r + s not in exclude]
    random.shuffle(deck)
    return deck[:n_cards]


def _board_cards_svg(cards: list, cx: float, cy: float, street: str = "") -> str:
    """Render 3-5 community cards as large SVG playing cards centered on the felt."""
    if not cards:
        return ""
    CW, CH, GAP = 44, 62, 6          # bigger cards
    n          = len(cards)
    total_w    = n * CW + (n - 1) * GAP
    x0         = cx - total_w / 2
    y0         = cy - CH / 2 - 8     # slightly above centre
    SUIT_SYM   = {"s": "♠", "h": "♥", "d": "♦", "c": "♣"}
    SUIT_COL   = {"s": "#0d1117", "h": "#c0392b", "d": "#c0392b", "c": "#0d1117"}
    STREET_COL = {"flop": "#27ae60", "turn": "#f39c12", "river": "#e74c3c"}
    parts = []
    # Street label above cards
    if street and street != "preflop":
        sc = STREET_COL.get(street, "#7f8c8d")
        lx = cx
        ly = y0 - 10
        parts.append(
            f'<rect x="{lx-22:.1f}" y="{ly-11:.1f}" width="44" height="14" '
            f'rx="4" fill="{sc}"/>'
        )
        parts.append(
            f'<text x="{lx:.1f}" y="{ly:.1f}" font-family="Arial,sans-serif" '
            f'font-size="9" font-weight="900" fill="#fff" text-anchor="middle" '
            f'letter-spacing="1">{street.upper()}</text>'
        )
    for i, card in enumerate(cards):
        if not card or len(card) < 2:
            continue
        suit  = card[-1].lower()
        rank  = card[:-1]
        cx_c  = x0 + i * (CW + GAP)
        col   = SUIT_COL.get(suit, "#0d1117")
        sym   = SUIT_SYM.get(suit, "?")
        # Drop shadow
        parts.append(
            f'<rect x="{cx_c+2:.1f}" y="{y0+3:.1f}" width="{CW}" height="{CH}" '
            f'rx="5" fill="rgba(0,0,0,0.6)"/>'
        )
        # Card face (bright cream)
        parts.append(
            f'<rect x="{cx_c:.1f}" y="{y0:.1f}" width="{CW}" height="{CH}" '
            f'rx="5" fill="#faf5e8" stroke="#d4be80" stroke-width="1.2"/>'
        )
        # Rank top-left
        parts.append(
            f'<text x="{cx_c+4:.1f}" y="{y0+15:.1f}" font-family="Arial,sans-serif" '
            f'font-size="14" font-weight="900" fill="{col}">{rank}</text>'
        )
        # Small suit below top-left rank (real card corner style)
        parts.append(
            f'<text x="{cx_c+5:.1f}" y="{y0+26:.1f}" font-family="Arial,sans-serif" '
            f'font-size="10" fill="{col}">{sym}</text>'
        )
        # Suit centre large
        parts.append(
            f'<text x="{cx_c+CW/2:.1f}" y="{y0+42:.1f}" font-family="Arial,sans-serif" '
            f'font-size="22" fill="{col}" text-anchor="middle">{sym}</text>'
        )
        # Small suit above bottom-right rank
        parts.append(
            f'<text x="{cx_c+CW-5:.1f}" y="{y0+CH-17:.1f}" font-family="Arial,sans-serif" '
            f'font-size="10" fill="{col}" text-anchor="end">{sym}</text>'
        )
        # Rank bottom-right (flipped)
        parts.append(
            f'<text x="{cx_c+CW-4:.1f}" y="{y0+CH-5:.1f}" font-family="Arial,sans-serif" '
            f'font-size="14" font-weight="900" fill="{col}" text-anchor="end">{rank}</text>'
        )
    return "\n".join(parts)


def render_poker_table(game_state: dict, num_opponents: int, decision: dict) -> str:
    """
    Renders an HTML/SVG poker table with avatars, chip stacks, community
    cards and pot chips. Hero always sits at the bottom.
    """
    hero_pos   = game_state.get("position", "?")
    hero_stack = game_state.get("hero_stack")
    vill_stack = game_state.get("villain_stack")
    pot        = game_state.get("pot")
    big_blind  = game_state.get("big_blind", 100)
    hole       = game_state.get("hole_cards", [None, None])
    comm       = game_state.get("community_cards", [])
    street     = game_state.get("street", "preflop")
    action     = decision.get("action", "?")

    W, H   = 620, 410
    cx, cy = W / 2, H / 2 - 10
    rx_t, ry_t = 235, 132
    rx_s, ry_s = 274, 155
    sw     = 82

    action_colors = {
        "RAISE": "#2ecc71", "CALL": "#3498db", "FOLD": "#e74c3c",
        "PUSH":  "#9b59b6", "CHECK": "#f1c40f",
    }
    hero_border = action_colors.get(action, "#3498db")
    total = max(num_opponents + 1, 2)

    def seat_xy(i: int):
        deg = 270 + i * (360 / total)
        rad = math.radians(deg)
        return cx + rx_s * math.cos(rad), cy - ry_s * math.sin(rad)

    # ── SVG layer: felt + avatars + pot chips ──────────────────────────────────
    svg_inner = []

    # Pot chip pile in centre (convert raw chips → bb for the visual)
    if pot and big_blind:
        pot_bb = pot / big_blind
        svg_inner.append(_chip_pile_svg(pot_bb, cx, cy - 18, r=13))

    # Avatars
    hx, hy = seat_xy(0)
    svg_inner.append(_player_avatar_svg(hx, hy - 58, is_hero=True, folded=False))
    opp_stacks = [vill_stack if i == 0 else None for i in range(num_opponents)]
    for i in range(num_opponents):
        ox, oy = seat_xy(i + 1)
        svg_inner.append(_player_avatar_svg(ox, oy - 48, is_hero=False, folded=False))

    # ── HTML seat boxes ────────────────────────────────────────────────────────
    seats = []
    cards_html = (" ".join(_tc(c) for c in hole) if any(hole)
                  else '<span style="color:#3a4a5a">?? ??</span>')
    hero_stk_s = f"{int(hero_stack):,}" if hero_stack else "—"

    # Stack chip pile next to hero seat
    if hero_stack and big_blind:
        hstk_bb = hero_stack / big_blind
        svg_inner.append(_chip_pile_svg(hstk_bb, hx + sw // 2 + 24, hy, r=8))

    seats.append(
        f'<div class="seat hero-seat" '
        f'style="left:{hx - sw//2:.0f}px; top:{hy - 44:.0f}px; border-color:{hero_border};">'
        f'<div class="sp">{hero_pos}</div>'
        f'<div class="sh">HERO</div>'
        f'<div class="sc">{cards_html}</div>'
        f'<div class="ss">{hero_stk_s}</div>'
        f'</div>'
    )

    for i in range(num_opponents):
        ox, oy  = seat_xy(i + 1)
        stk_s   = f"{int(opp_stacks[i]):,}" if opp_stacks[i] else "—"
        label   = f"OPP {i + 1}"
        if opp_stacks[i] and big_blind:
            ostk_bb = opp_stacks[i] / big_blind
            svg_inner.append(_chip_pile_svg(ostk_bb, ox + sw // 2 + 22, oy, r=8))
        seats.append(
            f'<div class="seat opp-seat" '
            f'style="left:{ox - sw//2:.0f}px; top:{oy - 34:.0f}px;">'
            f'<div class="sh">{label}</div>'
            f'<div class="ss">{stk_s}</div>'
            f'</div>'
        )

    # ── Center overlay: street / board / pot label ─────────────────────────────
    street_label = street.upper() if street else "PREFLOP"
    comm_html    = " ".join(_tc(c) for c in comm) if comm else ""
    board_block  = (f'<div class="comm-cards">{comm_html}</div>'
                    if comm_html else '<div class="preflop-label">PREFLOP</div>')
    pot_s        = f"{int(pot):,}" if pot else "—"

    return (
        f'<div style="position:relative;width:{W}px;height:{H}px;'
        f'margin:12px auto;overflow:visible;font-family:Arial,sans-serif;">'
        f'<svg width="{W}" height="{H}" style="position:absolute;top:0;left:0;z-index:0;"'
        f' xmlns="http://www.w3.org/2000/svg">'
        f'<defs>'
        f'<radialGradient id="felt_a" cx="50%" cy="50%" r="55%">'
        f'<stop offset="0%" stop-color="#1d5c35"/>'
        f'<stop offset="100%" stop-color="#0c2d1a"/>'
        f'</radialGradient>'
        f'<filter id="ts_a" x="-15%" y="-15%" width="130%" height="140%">'
        f'<feDropShadow dx="0" dy="6" stdDeviation="12" flood-color="#000" flood-opacity="0.65"/>'
        f'</filter>'
        f'<filter id="txt_shd" x="-20%" y="-20%" width="140%" height="140%">'
        f'<feDropShadow dx="0" dy="1" stdDeviation="1.5" flood-color="#000" flood-opacity="0.9"/>'
        f'</filter>'
        f'</defs>'
        f'<ellipse cx="{cx}" cy="{cy}" rx="{rx_t+16}" ry="{ry_t+16}" fill="#6b3a1f" filter="url(#ts_a)"/>'
        f'<ellipse cx="{cx}" cy="{cy}" rx="{rx_t+10}" ry="{ry_t+10}" fill="#7e4a28"/>'
        f'<ellipse cx="{cx}" cy="{cy}" rx="{rx_t}" ry="{ry_t}" fill="url(#felt_a)"/>'
        f'<ellipse cx="{cx}" cy="{cy}" rx="{rx_t-12}" ry="{ry_t-12}"'
        f' fill="none" stroke="#0a2518" stroke-width="1.5" stroke-dasharray="10,6"/>'
        + "\n".join(svg_inner) +
        f'</svg>'
        f'<div style="position:absolute;left:0;top:0;width:{W}px;height:{H}px;z-index:1;'
        f'display:flex;align-items:center;justify-content:center;pointer-events:none;">'
        f'<div style="text-align:center;margin-top:30px;">'
        f'<div class="street-label">{street_label}</div>'
        f'{board_block}'
        f'<div class="pot-label">POT: {pot_s}</div>'
        f'</div></div>'
        + "".join(seats) +
        f'</div>'
    )


def _card_html_big(rank: str, suit: str) -> str:
    """Large playing-card HTML block for the trainer right column."""
    color = {"h": "#c0392b", "d": "#c0392b", "c": "#0d1117", "s": "#0d1117"}.get(suit, "#000")
    sym   = {"h": "♥", "d": "♦", "c": "♣", "s": "♠"}.get(suit, suit)
    return (
        f'<div style="display:inline-block;width:72px;height:104px;background:white;'
        f'border-radius:10px;border:1px solid #ccc;position:relative;'
        f'margin:4px;box-shadow:3px 5px 12px rgba(0,0,0,0.45);vertical-align:top;">'
        f'<div style="position:absolute;top:7px;left:9px;color:{color};'
        f'font-size:16px;font-weight:700;font-family:Arial;line-height:1.15;">'
        f'{rank}<br><span style="font-size:13px">{sym}</span></div>'
        f'<div style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);'
        f'color:{color};font-size:38px;line-height:1;">{sym}</div>'
        f'<div style="position:absolute;bottom:7px;right:9px;color:{color};'
        f'font-size:16px;font-weight:700;font-family:Arial;line-height:1.15;'
        f'transform:rotate(180deg);">{rank}<br><span style="font-size:13px">{sym}</span></div>'
        f'</div>'
    )


def render_trainer_table(gs: dict, hole_cards: tuple, community_cards: list = None, street: str = "") -> str:
    """Casino-grade poker table renderer — SVG felt + HTML seat boxes."""
    seats_data = gs["seats"]
    n          = len(seats_data)
    hero_idx   = gs["hero_idx"]
    pot_bb     = gs["pot_bb"]
    to_call_bb = gs["to_call_bb"]

    W, H       = 800, 510
    cx, cy     = 400, 248
    rx_t, ry_t = 272, 158   # felt ellipse
    rx_s, ry_s = 318, 192   # seat position ellipse
    SW         = 108         # seat box width

    # Position colours
    _POS_COL = {
        "UTG":"#e74c3c","UTG1":"#e74c3c","UTG2":"#e74c3c",
        "MP":"#e67e22","HJ":"#e67e22",
        "CO":"#2ecc71","BTN":"#2ecc71",
        "SB":"#3498db","BB":"#3498db",
    }
    # Emoji avatar per position
    _POS_EMOJI = {
        "UTG":"🐘","UTG1":"🦏","UTG2":"🐂",
        "MP":"🦊","HJ":"🎯",
        "CO":"🦁","BTN":"🐎",
        "SB":"⚡","BB":"🦈",
    }

    def seat_xy(i: int):
        idx = (i - hero_idx) % n
        deg = 270 + idx * (360 / n)
        rad = math.radians(deg)
        return cx + rx_s * math.cos(rad), cy - ry_s * math.sin(rad)

    # ── SVG inner elements ──────────────────────────────────────────────────
    svg_inner = []
    # Felt watermark
    svg_inner.append(
        f'<text x="{cx:.1f}" y="{cy+20:.1f}" text-anchor="middle" '
        f'font-family="Arial" font-size="64" fill="#0c3a1c" opacity="0.14">♠</text>'
    )
    # Inner gold ring decoration
    svg_inner.append(
        f'<ellipse cx="{cx}" cy="{cy}" rx="{rx_t-18}" ry="{ry_t-18}" '
        f'fill="none" stroke="#8B6914" stroke-width="0.7" stroke-dasharray="6,4" opacity="0.35"/>'
    )

    for i, seat in enumerate(seats_data):
        sx, sy  = seat_xy(i)
        action  = seat["action"]
        bet     = seat["bet_bb"]
        pos     = seat["position"]
        is_hero = seat["is_hero"]

        # Bet chips — only non-hero seats
        if bet > 0 and action in ("RAISE", "CALL", "POST") and not is_hero:
            bx = sx + (cx - sx) * 0.42
            by = sy + (cy - sy) * 0.42
            svg_inner.append(_chip_pile_svg(bet, bx, by, r=10))

    # Hero bet chips
    hero_seat = next((s for s in seats_data if s["is_hero"]), None)
    if hero_seat and hero_seat["bet_bb"] > 0 and hero_seat["action"] in ("RAISE", "CALL", "POST"):
        hx, hy = seat_xy(hero_idx)
        hbx = hx + (cx - hx) * 0.38
        hby = hy + (cy - hy) * 0.38
        svg_inner.append(_chip_pile_svg(hero_seat["bet_bb"], hbx, hby, r=10))

    # Dealer button
    _btn_i = next((i for i, s in enumerate(seats_data) if s.get("position") == "BTN"), None)
    if _btn_i is not None:
        _bsx, _bsy = seat_xy(_btn_i)
        _dbx = _bsx + (cx - _bsx) * 0.40
        _dby = _bsy + (cy - _bsy) * 0.40
        svg_inner.append(
            f'<circle cx="{_dbx+1.5:.1f}" cy="{_dby+2:.1f}" r="10" fill="rgba(0,0,0,0.6)"/>'
            f'<circle cx="{_dbx:.1f}" cy="{_dby:.1f}" r="10" '
            f'fill="#f0ede0" stroke="#c49a3a" stroke-width="2"/>'
            f'<circle cx="{_dbx:.1f}" cy="{_dby:.1f}" r="7.5" '
            f'fill="none" stroke="#d4be80" stroke-width="1" opacity="0.7"/>'
            f'<text x="{_dbx:.1f}" y="{_dby+4:.1f}" text-anchor="middle" '
            f'font-family="Arial Black,Arial" font-size="10" font-weight="900" fill="#1a1a1a">D</text>'
        )

    # Board cards + pot chips
    if community_cards:
        svg_inner.append(_board_cards_svg(community_cards, cx, cy - 10, street=street))
        svg_inner.append(_chip_pile_svg(pot_bb, cx, cy + 64, r=10))
    else:
        svg_inner.append(_chip_pile_svg(pot_bb, cx, cy - 16, r=14))

    # ── HTML seat boxes ──────────────────────────────────────────────────────
    html_seats = []
    SUIT_SYM = {"s": "♠", "h": "♥", "d": "♦", "c": "♣"}
    SUIT_COL = {"s": "#0d1117", "h": "#c0392b", "d": "#c0392b", "c": "#0d1117"}

    for i, seat in enumerate(seats_data):
        sx, sy  = seat_xy(i)
        pos     = seat["position"]
        action  = seat["action"]
        rem     = seat["remaining_bb"]
        bet     = seat["bet_bb"]
        is_hero = seat["is_hero"]
        folded  = action == "FOLD"
        pc      = _POS_COL.get(pos, "#7f8c8d")
        emoji   = _POS_EMOJI.get(pos, "🃏")

        # Center box on (sx, sy)
        bx = sx - SW // 2
        by = sy - 44   # half of box height

        base = (
            f"position:absolute;left:{bx:.0f}px;top:{by:.0f}px;width:{SW}px;"
            f"text-align:center;font-family:Arial,sans-serif;z-index:3;"
            f"border-radius:12px;padding:7px 4px 6px;box-sizing:border-box;"
        )

        # ── Avatar div (shared helper) ──────────────────────────────────
        def _av(bg, border, shadow, content):
            return (
                f'<div style="width:46px;height:46px;border-radius:50%;'
                f'background:{bg};border:2.5px solid {border};margin:0 auto 3px;'
                f'display:flex;align-items:center;justify-content:center;'
                f'box-shadow:{shadow};">{content}</div>'
            )

        if is_hero:
            r1, s1 = hole_cards[0]; r2, s2 = hole_cards[1]
            def _cb(rank, suit):
                col = SUIT_COL.get(suit, "#0d1117")
                sym = SUIT_SYM.get(suit, suit)
                return (
                    f'<span style="display:inline-block;background:#faf5e8;'
                    f'border:1px solid #c8b97a;border-radius:4px;'
                    f'padding:2px 5px;margin:0 1px;font-size:14px;'
                    f'font-weight:900;color:{col};line-height:1.3;">'
                    f'{rank}{sym}</span>'
                )
            av  = _av("linear-gradient(145deg,#0a2f12,#061a09)",
                      "#2ecc71",
                      "0 0 16px rgba(46,204,113,0.6),0 0 6px rgba(46,204,113,0.2)",
                      '<span style="font-size:22px;">⭐</span>')
            html_seats.append(
                f'<div style="{base}background:linear-gradient(160deg,#0a2114,#061109);'
                f'border:2.5px solid #2ecc71;'
                f'box-shadow:0 0 24px rgba(46,204,113,0.45),0 4px 16px rgba(0,0,0,0.8);">'
                + av +
                f'<div style="font-size:10px;color:#c49a3a;font-weight:900;'
                f'letter-spacing:1px;line-height:1;">{pos}</div>'
                f'<div style="font-size:7px;color:#2ecc71;letter-spacing:2px;margin-bottom:3px;">HERO</div>'
                f'<div style="margin:2px 0;">{_cb(r1,s1)}{_cb(r2,s2)}</div>'
                f'<div style="font-size:8px;color:#718096;margin-top:1px;">{rem:.1f}bb</div>'
                f'</div>'
            )

        elif folded:
            av = _av("#0a0e14", "#1e2532", "none",
                     f'<span style="font-size:20px;opacity:0.3;">{emoji}</span>')
            html_seats.append(
                f'<div style="{base}background:rgba(10,14,20,0.45);'
                f'border:1px solid #1e2532;opacity:0.32;">'
                + av +
                f'<div style="font-size:9px;color:#2d3748;font-weight:700;">{pos}</div>'
                f'<div style="font-size:8px;color:#2d3748;">✕ fold</div>'
                f'</div>'
            )

        elif action == "RAISE":
            av = _av("linear-gradient(145deg,#1a2f20,#0d1a10)", "#2ecc71",
                     "0 0 12px rgba(46,204,113,0.5)",
                     f'<span style="font-size:22px;">{emoji}</span>')
            html_seats.append(
                f'<div style="{base}background:linear-gradient(160deg,#0c2310,#07150a);'
                f'border:2px solid #27ae60;'
                f'box-shadow:0 0 12px rgba(39,174,96,0.4),0 2px 8px rgba(0,0,0,0.7);">'
                + av +
                f'<div style="font-size:9px;color:{pc};font-weight:900;letter-spacing:.5px;">{pos}</div>'
                f'<div style="font-size:9px;color:#2ecc71;font-weight:800;margin:1px 0;">▲ {bet:.1f}bb</div>'
                f'<div style="font-size:8px;color:#718096;">{rem:.1f}bb</div>'
                f'</div>'
            )

        elif action == "CALL":
            av = _av("linear-gradient(145deg,#0d1e30,#060e1c)", "#3498db",
                     "0 0 12px rgba(52,152,219,0.5)",
                     f'<span style="font-size:22px;">{emoji}</span>')
            html_seats.append(
                f'<div style="{base}background:linear-gradient(160deg,#0a1a30,#060f1e);'
                f'border:2px solid #3498db;'
                f'box-shadow:0 0 12px rgba(52,152,219,0.35),0 2px 8px rgba(0,0,0,0.7);">'
                + av +
                f'<div style="font-size:9px;color:{pc};font-weight:900;letter-spacing:.5px;">{pos}</div>'
                f'<div style="font-size:9px;color:#3498db;font-weight:800;margin:1px 0;">● {bet:.1f}bb</div>'
                f'<div style="font-size:8px;color:#718096;">{rem:.1f}bb</div>'
                f'</div>'
            )

        elif action == "POST":
            av = _av("linear-gradient(145deg,#1c1800,#100e00)", "#f1c40f",
                     "0 0 10px rgba(241,196,15,0.4)",
                     f'<span style="font-size:22px;">{emoji}</span>')
            html_seats.append(
                f'<div style="{base}background:linear-gradient(160deg,#1c1500,#100d00);'
                f'border:2px solid #b7950b;">'
                + av +
                f'<div style="font-size:9px;color:{pc};font-weight:900;letter-spacing:.5px;">{pos}</div>'
                f'<div style="font-size:9px;color:#f1c40f;margin:1px 0;">{bet:.1f}bb blind</div>'
                f'<div style="font-size:8px;color:#718096;">{rem:.1f}bb</div>'
                f'</div>'
            )

        else:  # waiting / inactive
            av = _av("linear-gradient(145deg,#161b22,#0d1117)", "#2d3748",
                     "none",
                     f'<span style="font-size:22px;">{emoji}</span>')
            html_seats.append(
                f'<div style="{base}background:rgba(13,17,23,0.82);'
                f'border:1px solid #2d3748;">'
                + av +
                f'<div style="font-size:9px;color:{pc};font-weight:700;letter-spacing:.5px;">{pos}</div>'
                f'<div style="font-size:8px;color:#4a5568;">{rem:.1f}bb</div>'
                f'</div>'
            )

    # ── Centre overlay: POT + TO CALL ────────────────────────────────────────
    to_call_html = (
        f'<div style="background:rgba(52,152,219,0.18);border:1.5px solid #3498db;'
        f'border-radius:8px;padding:3px 14px;margin-top:6px;display:inline-block;">'
        f'<span style="color:#3498db;font-size:12px;font-weight:800;">'
        f'TO CALL &nbsp;{to_call_bb:.1f}bb</span></div>'
        if to_call_bb > 0 else ""
    )
    pot_align = "flex-end" if community_cards else "center"
    pot_mb    = "18" if community_cards else "0"
    pot_mt    = "" if community_cards else "margin-top:28px;"

    # ── SVG table background ──────────────────────────────────────────────────
    svg_bg = (
        f'<svg width="{W}" height="{H}" style="position:absolute;top:0;left:0;z-index:0;" '
        f'xmlns="http://www.w3.org/2000/svg">'
        f'<defs>'
        f'<radialGradient id="felt_t" cx="50%" cy="42%" r="58%">'
        f'<stop offset="0%"   stop-color="#1e6b3a"/>'
        f'<stop offset="60%"  stop-color="#155228"/>'
        f'<stop offset="100%" stop-color="#0a2e16"/>'
        f'</radialGradient>'
        f'<radialGradient id="felt_hi" cx="50%" cy="35%" r="45%">'
        f'<stop offset="0%"   stop-color="#2e8b57" stop-opacity="0.4"/>'
        f'<stop offset="100%" stop-color="#2e8b57" stop-opacity="0"/>'
        f'</radialGradient>'
        f'<radialGradient id="rim_grad" cx="50%" cy="30%" r="60%">'
        f'<stop offset="0%"   stop-color="#d4a840"/>'
        f'<stop offset="50%"  stop-color="#8a6520"/>'
        f'<stop offset="100%" stop-color="#4a3010"/>'
        f'</radialGradient>'
        f'<filter id="shd_t" x="-20%" y="-20%" width="140%" height="150%">'
        f'<feDropShadow dx="0" dy="10" stdDeviation="20" flood-color="#000" flood-opacity="0.8"/>'
        f'</filter>'
        f'<filter id="txt_shd" x="-20%" y="-20%" width="140%" height="140%">'
        f'<feDropShadow dx="0" dy="1" stdDeviation="1.5" flood-color="#000" flood-opacity="0.9"/>'
        f'</filter>'
        f'</defs>'
        f'<ellipse cx="{cx}" cy="{cy}" rx="{rx_t+30}" ry="{ry_t+30}" '
        f'fill="#1a0800" filter="url(#shd_t)"/>'
        f'<ellipse cx="{cx}" cy="{cy}" rx="{rx_t+22}" ry="{ry_t+22}" fill="#7a4520"/>'
        f'<ellipse cx="{cx}" cy="{cy}" rx="{rx_t+15}" ry="{ry_t+15}" fill="url(#rim_grad)"/>'
        f'<ellipse cx="{cx}" cy="{cy}" rx="{rx_t+8}"  ry="{ry_t+8}"  fill="#3d2010"/>'
        f'<ellipse cx="{cx}" cy="{cy}" rx="{rx_t+3}"  ry="{ry_t+3}"  '
        f'fill="none" stroke="#c49a3a" stroke-width="2.5" opacity="0.8"/>'
        f'<ellipse cx="{cx}" cy="{cy}" rx="{rx_t}"    ry="{ry_t}"    fill="url(#felt_t)"/>'
        f'<ellipse cx="{cx}" cy="{cy}" rx="{rx_t}"    ry="{ry_t}"    fill="url(#felt_hi)"/>'
        f'<ellipse cx="{cx}" cy="{cy}" rx="{rx_t-14}" ry="{ry_t-14}" '
        f'fill="none" stroke="#c49a3a" stroke-width="0.8" stroke-dasharray="8,6" opacity="0.28"/>'
        + "\n".join(svg_inner) +
        f'</svg>'
    )

    return (
        f'<div style="position:relative;width:{W}px;height:{H}px;'
        f'margin:4px auto;overflow:visible;font-family:Arial,sans-serif;">'
        + svg_bg +
        f'<div style="position:absolute;left:0;top:0;width:{W}px;height:{H}px;z-index:1;'
        f'display:flex;align-items:{pot_align};justify-content:center;pointer-events:none;">'
        f'<div style="text-align:center;margin-bottom:{pot_mb}px;{pot_mt}">'
        f'<div style="background:rgba(0,0,0,0.62);border:1.5px solid rgba(196,154,58,0.55);'
        f'border-radius:12px;padding:5px 22px;display:inline-block;'
        f'box-shadow:0 2px 12px rgba(0,0,0,0.6);">'
        f'<span style="color:#c49a3a;font-weight:900;font-size:10px;letter-spacing:2px;">POT</span>'
        f'&nbsp;<span style="color:#ecf0f1;font-weight:700;font-size:15px;">{pot_bb:.1f}bb</span>'
        f'</div>'
        f'{to_call_html}'
        f'</div></div>'
        + "".join(html_seats) +
        f'</div>'
    )


# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("### ⚙️ Settings")
    big_blind     = st.number_input("Big blind value (chips)",
                                    min_value=1, max_value=10000, value=100, step=10)
    num_opponents = st.slider("Active opponents", 1, 8, 1)
    st.divider()
    st.markdown("### 🔧 Manual overrides")
    st.caption("Use if detection fails")
    _POS_OPTIONS    = ["Auto-detect", "UTG", "UTG1", "UTG2", "MP", "HJ", "CO", "BTN", "SB", "BB"]
    _STREET_OPTIONS = ["Auto-detect", "preflop", "flop", "turn", "river"]
    # No key= on these selectboxes — avoids Streamlit widget-state conflict with Mix
    manual_position = st.selectbox("Override position", _POS_OPTIONS)
    manual_street   = st.selectbox("Override street",   _STREET_OPTIONS)

    # Mix button — randomise position + street
    _mc1, _mc2 = st.columns(2)
    with _mc1:
        sidebar_run = st.button("▶  Analyze", type="primary",
                                use_container_width=True, key="sidebar_run_btn",
                                help="Run analysis with current settings")
    with _mc2:
        mix_btn = st.button("🎲  Mix", use_container_width=True, key="mix_btn",
                            help="Pick a random position and street")
    if mix_btn:
        _rnd_pos    = random.choice(["UTG","UTG1","MP","HJ","CO","BTN","SB","BB"])
        _rnd_street = random.choices(
            ["preflop","flop","turn","river"], weights=[4,3,2,2])[0]
        st.session_state["sb_triggered"] = True
        st.session_state["sb_pos"]       = _rnd_pos
        st.session_state["sb_street"]    = _rnd_street
        st.rerun()
    if sidebar_run:
        st.session_state["sb_triggered"] = True
        st.session_state["sb_pos"]    = manual_position
        st.session_state["sb_street"] = manual_street
        st.session_state["sb_opps"]   = num_opponents
        st.session_state["sb_bb"]     = big_blind

    # ── Sidebar results panel ──────────────────────────────────────────────────
    if st.session_state.get("sb_triggered"):
        _pos    = st.session_state.get("sb_pos", "Auto-detect")
        _street = st.session_state.get("sb_street", "Auto-detect")
        _opps   = st.session_state.get("sb_opps", 1)

        st.markdown("---")
        st.markdown("#### 📋 Results")

        # ── position-based RFI range ──────────────────────────────────────────
        if _pos != "Auto-detect":
            rfi_data  = RFI_RANGES.get(_pos, {})
            rfi_hands = rfi_data.get("open", [])
            rfi_desc  = rfi_data.get("description", _pos)

            # colour-coded action badge
            if _pos in ("UTG", "UTG1", "UTG2"):
                badge_col, badge_txt = "#7f1d1d", "EP — Tight"
            elif _pos in ("MP", "HJ"):
                badge_col, badge_txt = "#1e3a5f", "MP — Medium"
            else:
                badge_col, badge_txt = "#14532d", "LP — Wide"

            st.markdown(
                f'<div style="background:{badge_col};border-radius:6px;'
                f'padding:6px 10px;margin-bottom:6px;text-align:center;">'
                f'<b style="color:#fff;font-size:13px;">{_pos}</b>'
                f'<span style="color:#ccc;font-size:11px;"> — {badge_txt}</span></div>',
                unsafe_allow_html=True,
            )

            # street-specific guidance
            if _street == "preflop" or _street == "Auto-detect":
                st.markdown(
                    f"**RFI:** {len(rfi_hands)} combos",
                    help="Raise First In — open when folded to you",
                )
                # show top hands as colour pills
                _TOP_HANDS = list(rfi_hands)[:30]
                if _TOP_HANDS:
                    pills_html = " ".join(
                        f'<span style="display:inline-block;background:#1a2e1a;'
                        f'border:1px solid #2ecc71;border-radius:4px;padding:1px 5px;'
                        f'font-size:11px;color:#2ecc71;margin:1px;">{h}</span>'
                        for h in sorted(_TOP_HANDS)
                    )
                    st.markdown(pills_html, unsafe_allow_html=True)
                    if len(rfi_hands) > 30:
                        st.caption(f"+ {len(rfi_hands) - 30} more — see GTO Charts tab")

            elif _street == "flop":
                cbet_freq = {"UTG": 55, "UTG1": 55, "UTG2": 58, "MP": 60,
                             "HJ": 63, "CO": 67, "BTN": 72, "SB": 65, "BB": 50}.get(_pos, 60)
                st.metric("C-bet frequency", f"{cbet_freq}%")
                st.caption("Continuation bet on the flop — bet ~⅔ pot")

            elif _street == "turn":
                barrel_freq = {"UTG": 40, "UTG1": 40, "UTG2": 42, "MP": 45,
                               "HJ": 48, "CO": 52, "BTN": 58, "SB": 50, "BB": 38}.get(_pos, 45)
                st.metric("Double-barrel", f"{barrel_freq}%")
                st.caption("Double barrel on the turn — bet ½–¾ pot")

            elif _street == "river":
                vb_freq = {"UTG": 32, "UTG1": 32, "UTG2": 35, "MP": 38,
                           "HJ": 40, "CO": 44, "BTN": 50, "SB": 42, "BB": 30}.get(_pos, 38)
                st.metric("Value-bet / bluff", f"{vb_freq}%")
                st.caption("River value-bet / bluff — bet ¾–1x pot")

        else:
            # no position chosen — show opponent count tip
            st.info(
                f"**{_opps} opponent{'s' if _opps > 1 else ''}** — "
                f"tighten your range by {(_opps - 1) * 8}% vs heads-up."
                if _opps > 1 else
                "Select a position for detailed results."
            )

        # clear button
        if st.button("✕ Clear", key="sb_clear", use_container_width=True):
            st.session_state["sb_triggered"] = False

# ── Header + tabs ─────────────────────────────────────────────────────────────

st.markdown("""
<div style="display:flex;align-items:center;gap:16px;padding:4px 0 18px;">
  <!-- Casino card/chip logo -->
  <svg width="58" height="58" viewBox="0 0 58 58" xmlns="http://www.w3.org/2000/svg">
    <defs>
      <radialGradient id="cg" cx="40%" cy="30%" r="65%">
        <stop offset="0%"   stop-color="#f5d060"/>
        <stop offset="100%" stop-color="#8B6914"/>
      </radialGradient>
    </defs>
    <!-- Outer gold ring -->
    <circle cx="29" cy="29" r="28" fill="#0d1117" stroke="url(#cg)" stroke-width="2.5"/>
    <!-- Inner decorative ring -->
    <circle cx="29" cy="29" r="22" fill="none" stroke="#8B6914" stroke-width="1" stroke-dasharray="4,3" opacity="0.6"/>
    <!-- Large gold spade -->
    <path d="M29 10 C29 10 14 23 14 31 C14 37 19 39 24 37 C22 41 21 45 18 46 L40 46 C37 45 36 41 34 37 C39 39 44 37 44 31 C44 23 29 10 29 10 Z" fill="url(#cg)"/>
    <!-- 99 text bottom -->
    <text x="29" y="54" text-anchor="middle" font-family="Arial Black,Arial" font-size="7" font-weight="900" fill="#c49a3a" letter-spacing="1">SHY</text>
  </svg>
  <div>
    <div style="font-size:30px;font-weight:900;letter-spacing:2px;line-height:1;
                background:linear-gradient(135deg,#f5d060,#c49a3a,#8B6914);
                -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                background-clip:text;">
      SHY<span style="color:#ecf0f1;-webkit-text-fill-color:#ecf0f1;">99</span>
    </div>
    <div style="font-size:10px;color:#8B6914;letter-spacing:4px;margin-top:2px;font-weight:700;">
      POKER TRAINER
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

tab_analyzer, tab_charts, tab_trainer = st.tabs(
    ["♠  Analyzer", "📊  GTO Charts", "🎯  Trainer"]
)

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — ANALYZER
# ═══════════════════════════════════════════════════════════════════════════════

# ── helper: render analysis results (shared by both input modes) ──────────────
def _render_analysis(game_state: dict, uploaded_img=None) -> None:
    """Render table view + recommendation panel for a given game_state dict."""
    if manual_position != "Auto-detect":
        game_state["position"] = manual_position
    if manual_street != "Auto-detect":
        game_state["street"] = manual_street

    decision = make_decision(game_state, big_blind=big_blind,
                             num_opponents=num_opponents)

    col_table, col_results = st.columns([1.15, 1])

    with col_table:
        st.markdown("**Table view**")
        st.markdown(render_poker_table(game_state, num_opponents, decision),
                    unsafe_allow_html=True)
        if uploaded_img is not None:
            with st.expander("Original screenshot"):
                uploaded_img.seek(0)
                st.image(Image.open(uploaded_img), use_container_width=True)

    with col_results:
        action = decision.get("action", "UNKNOWN")
        ac     = action if action in ("RAISE","CALL","FOLD","PUSH","CHECK") else "FOLD"
        st.markdown(
            f'<div class="action-box action-{ac}">'
            f'<p class="action-label">{action}</p></div>',
            unsafe_allow_html=True,
        )

        equity   = decision.get("equity")
        pot_odds = decision.get("pot_odds")
        edge     = decision.get("edge")

        s1, s2, s3 = st.columns(3)
        with s1:
            st.markdown('<div class="stat-label">Equity</div>', unsafe_allow_html=True)
            st.markdown(
                f'<div class="stat-value">{equity}%</div>' if equity is not None
                else '<div class="stat-value" style="color:#555">—</div>',
                unsafe_allow_html=True,
            )
        with s2:
            st.markdown('<div class="stat-label">Pot odds</div>', unsafe_allow_html=True)
            st.markdown(
                f'<div class="stat-value">{pot_odds}%</div>' if pot_odds is not None
                else '<div class="stat-value" style="color:#555">—</div>',
                unsafe_allow_html=True,
            )
        with s3:
            st.markdown('<div class="stat-label">Edge</div>', unsafe_allow_html=True)
            if edge is not None:
                sign  = "+" if edge >= 0 else ""
                color = "#2ecc71" if edge >= 0 else "#e74c3c"
                st.markdown(
                    f'<div class="stat-value" style="color:{color}">{sign}{edge}%</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown('<div class="stat-value" style="color:#555">—</div>',
                            unsafe_allow_html=True)

        st.divider()

        st.markdown("**Game state**")
        hole   = game_state.get("hole_cards", [None, None])
        comm   = game_state.get("community_cards", [])
        pos    = game_state.get("position", "?")
        street = game_state.get("street", "?")
        pot    = game_state.get("pot")
        hero_s = game_state.get("hero_stack")

        hole_html  = "".join([_card_chip(hole[0]), _card_chip(hole[1])])
        board_html = ("".join(_card_chip(c) for c in comm)
                      if comm else "<span style='color:#555'>—</span>")

        g1, g2 = st.columns(2)
        with g1:
            st.markdown(f"**Hole cards:** {hole_html}", unsafe_allow_html=True)
            st.markdown(f"**Board:** {board_html}", unsafe_allow_html=True)
            st.markdown(f"**Street:** {street}")
        with g2:
            st.markdown(f"**Position:** {pos}")
            st.markdown(f"**Pot:** {int(pot):,}" if pot else "**Pot:** —")
            st.markdown(f"**Stack:** {int(hero_s):,}" if hero_s else "**Stack:** —")

        st.markdown(
            f'<div class="reasoning-box">{decision.get("reasoning", "")}</div>',
            unsafe_allow_html=True,
        )

        warnings = game_state.get("parse_warnings", [])
        if warnings:
            with st.expander(f"⚠️ {len(warnings)} detection warning(s)"):
                for w in warnings:
                    st.markdown(f'<div class="warning-box">{w}</div>',
                                unsafe_allow_html=True)


with tab_analyzer:

    # ── Mode toggle ───────────────────────────────────────────────────────────
    _RANKS = ["A","K","Q","J","T","9","8","7","6","5","4","3","2"]
    _SUITS = ["s ♠","h ♥","d ♦","c ♣"]
    _SUIT_MAP = {"s ♠":"s","h ♥":"h","d ♦":"d","c ♣":"c"}

    mode = st.radio(
        "Input mode",
        ["📸  Screenshot", "✏️  Manual input"],
        horizontal=True,
        label_visibility="collapsed",
    )
    st.divider()

    # ══════════════════════════════════════════════════════════════════════════
    # MODE A — Screenshot
    # ══════════════════════════════════════════════════════════════════════════
    if mode == "📸  Screenshot":
        uploaded = st.file_uploader(
            "Drop your GGPoker screenshot here",
            type=["png", "jpg", "jpeg"],
            label_visibility="collapsed",
        )

        if uploaded is None:
            st.markdown("""
            <div style="border:2px dashed #2d3d50; border-radius:14px; padding:48px 40px;
                        text-align:center; background:#111827; margin-top:8px;">
                <div style="font-size:48px;">📸</div>
                <div style="font-size:17px; margin-top:10px; color:#7f8c8d; font-weight:500;">
                    Drag &amp; drop a GGPoker screenshot or click Browse
                </div>
                <div style="font-size:13px; margin-top:6px; color:#4a5568;">
                    PNG or JPG &nbsp;•&nbsp; Any resolution
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            with st.spinner("Analysing screenshot..."):
                suffix = ".png" if uploaded.name.endswith(".png") else ".jpg"
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                    tmp.write(uploaded.read())
                    tmp_path = tmp.name
                try:
                    game_state = parse_screenshot(tmp_path)
                except Exception as e:
                    st.error(f"Failed to parse screenshot: {e}")
                    game_state = None
                finally:
                    try:
                        os.unlink(tmp_path)
                    except Exception:
                        pass

            if game_state is not None:
                _render_analysis(game_state, uploaded_img=uploaded)

    # ══════════════════════════════════════════════════════════════════════════
    # MODE B — Manual input
    # ══════════════════════════════════════════════════════════════════════════
    else:
        st.markdown(
            '<div style="color:#7f8c8d;font-size:13px;margin-bottom:12px;">'
            'Enter your hand details and click <b style="color:#2ecc71">▶ Run Analysis</b>.'
            '</div>',
            unsafe_allow_html=True,
        )

        mi_c1, mi_c2 = st.columns(2)

        with mi_c1:
            mi_pos = st.selectbox(
                "Position",
                ["UTG","UTG1","UTG2","MP","HJ","CO","BTN","SB","BB"],
                index=6,
                key="mi_pos",
            )
            mi_street = st.selectbox(
                "Street",
                ["preflop","flop","turn","river"],
                key="mi_street",
            )
            mi_pot = st.number_input(
                "Pot (chips)", min_value=1, value=big_blind * 3,
                step=big_blind, key="mi_pot",
            )
            mi_stack = st.number_input(
                "Hero stack (chips)", min_value=1, value=big_blind * 40,
                step=big_blind, key="mi_stack",
            )

        with mi_c2:
            st.markdown("**Hole card 1**")
            hc1_col1, hc1_col2 = st.columns(2)
            with hc1_col1:
                r1 = st.selectbox("Rank", _RANKS, key="mi_r1")
            with hc1_col2:
                s1_raw = st.selectbox("Suit", _SUITS, key="mi_s1")

            st.markdown("**Hole card 2**")
            hc2_col1, hc2_col2 = st.columns(2)
            with hc2_col1:
                r2 = st.selectbox("Rank", _RANKS, index=1, key="mi_r2")
            with hc2_col2:
                s2_raw = st.selectbox("Suit", _SUITS, index=2, key="mi_s2")

            mi_vstack = st.number_input(
                "Villain stack (chips)", min_value=0, value=big_blind * 40,
                step=big_blind, key="mi_vstack",
            )

        # Board cards (optional, only shown for flop+)
        if mi_street != "preflop":
            st.markdown("**Community cards** (optional)")
            bc_cols = st.columns(5)
            board_cards = []
            for idx, bc in enumerate(bc_cols):
                with bc:
                    br = st.selectbox("R", ["—"] + _RANKS, key=f"mi_br{idx}",
                                      label_visibility="collapsed")
                    bs = st.selectbox("S", _SUITS, key=f"mi_bs{idx}",
                                      label_visibility="collapsed")
                    if br != "—":
                        board_cards.append(br + _SUIT_MAP[bs])
        else:
            board_cards = []

        st.markdown("")
        run_btn = st.button(
            "▶  Run Analysis",
            type="primary",
            use_container_width=True,
            key="mi_run",
        )

        if run_btn:
            s1_mapped = _SUIT_MAP[s1_raw]
            s2_mapped = _SUIT_MAP[s2_raw]
            c1_str = r1 + s1_mapped
            c2_str = r2 + s2_mapped

            if c1_str == c2_str:
                st.error("Hole card 1 and card 2 cannot be the same card.")
            else:
                manual_gs = {
                    "position":        mi_pos,
                    "street":          mi_street,
                    "hole_cards":      [c1_str, c2_str],
                    "community_cards": board_cards,
                    "pot":             float(mi_pot),
                    "hero_stack":      float(mi_stack),
                    "villain_stack":   float(mi_vstack) if mi_vstack else None,
                    "big_blind":       float(big_blind),
                    "parse_warnings":  [],
                }
                _render_analysis(manual_gs)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — GTO CHARTS
# ═══════════════════════════════════════════════════════════════════════════════

with tab_charts:
    st.markdown("### Pre-flop opening ranges (40bb+, full ring)")
    st.caption("RFI = Raise First In — open when action folds to you.")

    POSITIONS_ORDER = ["UTG", "UTG1", "UTG2", "MP", "HJ", "CO", "BTN", "SB"]

    for pos in POSITIONS_ORDER:
        data  = RFI_RANGES.get(pos, {})
        desc  = data.get("description", pos)
        hands = data.get("open", [])
        n     = len(hands)

        with st.expander(f"**{desc}** — {n} combos"):
            if hands:
                pills = " ".join(
                    f'<span class="range-pill">{h}</span>'
                    for h in sorted(hands)
                )
                st.markdown(pills, unsafe_allow_html=True)
            else:
                st.caption("No data.")

    st.divider()
    st.markdown("### 3-bet ranges")
    st.caption("Re-raise ranges by position matchup.")

    for scenario, hands in THREEBET_RANGES.items():
        label = scenario.replace("_vs_", " vs ").replace("_", " ").title()
        n     = len(hands)
        with st.expander(f"**{label}** — {n} combos"):
            if hands:
                pills = " ".join(
                    f'<span class="range-pill">{h}</span>'
                    for h in sorted(hands)
                )
                st.markdown(pills, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 — TRAINER  (fully embedded Streamlit)
# ═══════════════════════════════════════════════════════════════════════════════

with tab_trainer:

    # ── Session-state init ────────────────────────────────────────────────────
    if "t_scenario" not in st.session_state:
        st.session_state.t_scenario  = None
        st.session_state.t_cards     = None
        st.session_state.t_hand_str  = None
        st.session_state.t_gs        = None
        st.session_state.t_decided   = False
        st.session_state.t_decision  = None
        st.session_state.t_eval      = None
        st.session_state.t_hands     = 0
        st.session_state.t_correct   = 0
        st.session_state.t_mixed     = 0
        st.session_state.t_incorrect = 0
        st.session_state.t_community = []
        st.session_state.t_street    = "preflop"
        st.session_state.t_history   = []

    def _t_next() -> None:
        # ── Respect sidebar overrides (Mix button takes priority over selectbox) ─
        _mix_pos    = st.session_state.pop("sb_pos", None)
        _mix_street = st.session_state.pop("sb_street", None)
        _forced_pos    = (_mix_pos    if _mix_pos    and _mix_pos    != "Auto-detect"
                          else manual_position if manual_position != "Auto-detect" else None)
        _forced_street = (_mix_street if _mix_street and _mix_street != "Auto-detect"
                          else manual_street   if manual_street   != "Auto-detect" else None)

        # Pick scenario — filter by forced position if set
        if _forced_pos:
            _pos_sc = [s for s in TRAINER_SCENARIOS
                       if s.get("position") == _forced_pos
                       or s.get("hero_position") == _forced_pos]
            sc = random.choice(_pos_sc) if _pos_sc else random.choice(TRAINER_SCENARIOS)
        else:
            sc = random.choice(TRAINER_SCENARIOS)

        c1, c2 = deal_random_hand()

        # Determine street
        if _forced_street:
            street = _forced_street
        elif random.random() < 0.35:
            street = random.choices(["flop", "turn", "river"], weights=[5, 3, 2])[0]
        else:
            street = "preflop"

        # Deal community cards for post-flop
        if street != "preflop":
            n_board   = {"flop": 3, "turn": 4, "river": 5}[street]
            community = _deal_board((c1, c2), n_board)
        else:
            community = []

        gs_built = scenario_game_state(sc)

        # ── Build hand history ─────────────────────────────────────────────────
        SUIT_SYM = {"s":"♠","h":"♥","d":"♦","c":"♣"}
        def _fmt_card(c):
            if not c or len(c) < 2: return c
            return c[:-1] + SUIT_SYM.get(c[-1].lower(), c[-1])
        def _fmt_cards(lst): return " ".join(_fmt_card(c) for c in lst)

        prior      = sc.get("prior_action", sc.get("description", "—"))
        hero_pos   = gs_built.get("hero_pos", "?")
        to_call    = gs_built.get("to_call_bb", 0)
        pot        = gs_built.get("pot_bb", 1.5)

        # Reconstruct who raised preflop
        prior_low  = prior.lower()
        raiser_pos = None
        for _p in ["utg","utg1","utg2","mp","hj","co","btn","sb","bb"]:
            if _p in prior_low and "raise" in prior_low:
                raiser_pos = _p.upper()
                break
        if raiser_pos is None and "folds to you" in prior_low:
            raiser_pos = hero_pos  # hero is the opener

        history = []

        # --- PREFLOP ---
        if raiser_pos and raiser_pos != hero_pos:
            pf_text = (
                f"{raiser_pos} raises to 2.5bb &nbsp;·&nbsp; "
                + ("SB folds &nbsp;·&nbsp; " if "sb fold" in prior_low else "")
                + f"{hero_pos} calls → pot {pot:.1f}bb"
            )
        elif raiser_pos == hero_pos:
            pf_text = f"{hero_pos} raises to 2.5bb (folds to you)"
        else:
            pf_text = prior
        history.append({"street": "PREFLOP", "col": "#7f8c8d",
                         "cards": [], "lines": [pf_text]})

        # --- FLOP ---
        if street in ("flop","turn","river") and len(community) >= 3:
            flop = community[:3]
            # Simulate: IP player c-bets ~60%, OOP calls with equity
            flop_lines = [f"🃏 &nbsp;<b>{_fmt_cards(flop)}</b>"]
            if hero_pos in ("BB","SB"):           # OOP hero
                flop_lines.append("BB checks &nbsp;·&nbsp; BTN bets 2.0bb &nbsp;·&nbsp; BB calls")
            else:                                  # IP hero
                flop_lines.append("BB checks &nbsp;·&nbsp; BTN bets 2.0bb")
            history.append({"street": "FLOP", "col": "#27ae60",
                             "cards": flop, "lines": flop_lines})

        # --- TURN ---
        if street in ("turn","river") and len(community) >= 4:
            turn_c = community[3]
            turn_lines = [f"🃏 &nbsp;<b>{_fmt_card(turn_c)}</b>"]
            if hero_pos in ("BB","SB"):
                turn_lines.append("BB checks &nbsp;·&nbsp; BTN bets 3.0bb &nbsp;·&nbsp; BB calls")
            else:
                turn_lines.append("BB checks &nbsp;·&nbsp; BTN bets 3.0bb")
            history.append({"street": "TURN", "col": "#f39c12",
                             "cards": [turn_c], "lines": turn_lines})

        # --- RIVER (current decision) ---
        if street == "river" and len(community) >= 5:
            riv_c = community[4]
            riv_lines = [f"🃏 &nbsp;<b>{_fmt_card(riv_c)}</b>"]
            if to_call > 0:
                riv_lines.append(
                    f"BTN bets <b style='color:#f1c40f'>{to_call:.1f}bb</b> "
                    f"(pot {pot:.1f}bb) &nbsp;·&nbsp; "
                    f"<b style='color:#3498db'>← {hero_pos} decision</b>"
                )
            else:
                riv_lines.append(f"<b style='color:#3498db'>← {hero_pos} decision (check or bet)</b>")
            history.append({"street": "RIVER", "col": "#e74c3c",
                             "cards": [riv_c], "lines": riv_lines})

        elif street == "flop" and community:
            history[-1]["lines"].append(
                f"<b style='color:#3498db'>← {hero_pos} decision</b>")
        elif street == "turn" and len(community) >= 4:
            history[-1]["lines"].append(
                f"<b style='color:#3498db'>← {hero_pos} decision</b>")

        if street == "preflop":
            history[0]["lines"].append(
                f"<b style='color:#3498db'>← {hero_pos} decision "
                + (f"(call {to_call:.1f}bb or raise/fold)" if to_call > 0 else "(first to act)")
                + "</b>"
            )

        st.session_state.t_scenario  = sc
        st.session_state.t_cards     = (c1, c2)
        st.session_state.t_hand_str  = cards_to_hand_str(c1, c2)
        st.session_state.t_gs        = gs_built
        st.session_state.t_community = community
        st.session_state.t_street    = street
        st.session_state.t_history   = history
        st.session_state.t_decided   = False
        st.session_state.t_decision  = None
        st.session_state.t_eval      = None

    def _t_decide(action: str) -> None:
        street    = st.session_state.get("t_street", "preflop")
        community = st.session_state.get("t_community", [])

        if street == "preflop" or not community:
            strategy = lookup_gto(st.session_state.t_scenario,
                                  st.session_state.t_hand_str)
            ev = evaluate_action(action, strategy)
        else:
            # Post-flop: build strategy from equity vs pot odds
            from equity import calc_equity_postflop
            hole = [r + s for r, s in st.session_state.t_cards]
            gs   = st.session_state.t_gs
            equity = calc_equity_postflop(hole, community, num_opponents=1)
            if equity is None:
                equity = 0.5
            pot      = gs["pot_bb"]
            to_call  = gs["to_call_bb"]
            if to_call > 0:
                call_frac = to_call / (pot + to_call)
            else:
                call_frac = 0.0
            # Build GTO strategy from equity
            if to_call == 0:
                if equity >= 0.60:
                    strategy = {"RAISE": 75, "CHECK": 25}
                elif equity >= 0.45:
                    strategy = {"CHECK": 70, "RAISE": 30}
                else:
                    strategy = {"CHECK": 85, "FOLD": 15}
            elif equity >= call_frac + 0.12:
                strategy = {"CALL": 60, "RAISE": 40}
            elif equity >= call_frac + 0.03:
                strategy = {"CALL": 80, "FOLD": 20}
            elif equity >= call_frac - 0.05:
                strategy = {"CALL": 45, "FOLD": 55}
            else:
                strategy = {"FOLD": 100}
            ev = evaluate_action(action, strategy)
            # Enrich feedback with equity info
            ev["equity_pct"] = round(equity * 100, 1)
            ev["street"]     = street

        st.session_state.t_decided   = True
        st.session_state.t_decision  = action
        st.session_state.t_eval      = ev
        st.session_state.t_hands    += 1
        grade = ev["grade"]
        if grade == "correct":        st.session_state.t_correct   += 1
        elif grade == "mixed":        st.session_state.t_mixed     += 1
        else:                         st.session_state.t_incorrect += 1

    # First hand on cold start
    if st.session_state.t_scenario is None:
        _t_next()

    # Auto-regenerate: Mix button or selectbox changes
    _cur_street = st.session_state.get("t_street", "preflop")
    _cur_pos    = (st.session_state.t_gs or {}).get("hero_pos", "") if st.session_state.t_scenario else ""
    _mix_pending = st.session_state.get("sb_pos") is not None  # Mix was just pressed
    _need_regen = _mix_pending  # Mix always triggers a new hand
    if manual_street != "Auto-detect" and manual_street != _cur_street:
        _need_regen = True
    if manual_position != "Auto-detect" and _cur_pos and manual_position != _cur_pos:
        _need_regen = True
    if _need_regen and (_mix_pending or not st.session_state.t_decided):
        _t_next()

    sc        = st.session_state.t_scenario
    cards     = st.session_state.t_cards
    hand_str  = st.session_state.t_hand_str
    gs        = st.session_state.t_gs
    decided   = st.session_state.t_decided
    ev        = st.session_state.t_eval
    dec_made  = st.session_state.t_decision
    community = st.session_state.get("t_community", [])
    t_street  = st.session_state.get("t_street", "preflop")

    # ── Active sidebar filters banner ──────────────────────────────────────────
    _active_filters = []
    if manual_position != "Auto-detect":
        _active_filters.append(f"📍 Position: <b style='color:#f1c40f'>{manual_position}</b>")
    if manual_street != "Auto-detect":
        _SCOL = {"preflop":"#7f8c8d","flop":"#27ae60","turn":"#f39c12","river":"#e74c3c"}
        _sc   = _SCOL.get(manual_street, "#7f8c8d")
        _active_filters.append(f"🃏 Street: <b style='color:{_sc}'>{manual_street.upper()}</b>")
    if num_opponents != 1:
        _active_filters.append(f"👥 Opponents: <b style='color:#3498db'>{num_opponents}</b>")
    if _active_filters:
        st.markdown(
            f'<div style="background:rgba(241,196,15,0.08);border:1px solid rgba(241,196,15,0.3);'
            f'border-radius:8px;padding:6px 14px;margin-bottom:8px;font-size:12px;color:#aab7b8;">'
            f'🔧 Active filter — {"  &nbsp;|&nbsp;  ".join(_active_filters)}'
            f'</div>',
            unsafe_allow_html=True,
        )

    # ── Stats bar ─────────────────────────────────────────────────────────────
    n_h  = st.session_state.t_hands
    acc  = round(
        (st.session_state.t_correct + st.session_state.t_mixed) / max(n_h, 1) * 100, 1
    )
    st.markdown(
        f'<div style="font-size:13px;color:#7f8c8d;padding:4px 0 10px;">'
        f'Hands: <b style="color:#ecf0f1">{n_h}</b> &nbsp;|&nbsp; '
        f'✓ <b style="color:#2ecc71">{st.session_state.t_correct}</b>'
        f'&nbsp; ~ <b style="color:#f1c40f">{st.session_state.t_mixed}</b>'
        f'&nbsp; ✗ <b style="color:#e74c3c">{st.session_state.t_incorrect}</b>'
        f'&nbsp;|&nbsp; Accuracy: <b style="color:#ecf0f1">{acc}%</b></div>',
        unsafe_allow_html=True,
    )

    # ── Two-column layout ─────────────────────────────────────────────────────
    col_left, col_right = st.columns([1.3, 1])

    with col_left:
        st.markdown(render_trainer_table(gs, cards, community_cards=community, street=t_street), unsafe_allow_html=True)

    with col_right:
        # Scenario description + street badge
        _STREET_COLORS = {"preflop": "#7f8c8d", "flop": "#27ae60", "turn": "#f39c12", "river": "#e74c3c"}
        _sc = _STREET_COLORS.get(t_street, "#7f8c8d")
        _street_badge = (
            f'<span style="background:{_sc};color:#fff;font-size:10px;font-weight:800;'
            f'border-radius:4px;padding:2px 7px;letter-spacing:1px;margin-right:8px;">'
            f'{t_street.upper()}</span>'
            if t_street != "preflop" else ""
        )
        st.markdown(
            f'<div style="background:#111827;border:1px solid #2d3d50;border-radius:10px;'
            f'padding:12px 16px;margin-bottom:10px;color:#3498db;font-size:14px;'
            f'font-weight:500;line-height:1.5;">{_street_badge}{sc["description"]}</div>',
            unsafe_allow_html=True,
        )

        # Card display + hand notation + metrics — all in one compact HTML block
        r1, s1 = cards[0]
        r2, s2 = cards[1]
        stack_v   = f"{gs['stack_bb']}bb"
        pot_v     = f"{gs['pot_bb']:.1f}bb"
        tocall_v  = f"{gs['to_call_bb']:.1f}bb" if gs["to_call_bb"] > 0 else "—"
        st.markdown(
            f'<div style="text-align:center;margin:8px 0 4px;">'
            f'{_card_html_big(r1, s1)}{_card_html_big(r2, s2)}</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div style="display:flex;align-items:center;justify-content:space-between;'
            f'background:#111827;border-radius:8px;padding:6px 14px;margin:4px 0 8px;">'
            f'<span style="font-size:24px;font-weight:800;color:#ecf0f1;letter-spacing:2px;">{hand_str}</span>'
            f'<span style="font-size:11px;color:#7f8c8d;text-align:right;line-height:1.5;">'
            f'Stack <b style="color:#ecf0f1">{stack_v}</b><br>'
            f'Pot <b style="color:#f1c40f">{pot_v}</b>'
            f'{("<br>Call <b style=color:#3498db>" + tocall_v + "</b>") if gs["to_call_bb"] > 0 else ""}'
            f'</span></div>',
            unsafe_allow_html=True,
        )

        # Community cards display (post-flop)
        if community:
            SUIT_SYM_H = {"s": "♠", "h": "♥", "d": "♦", "c": "♣"}
            SUIT_COL_H = {"s": "#ecf0f1", "h": "#e74c3c", "d": "#e74c3c", "c": "#ecf0f1"}
            cards_html = ""
            for card in community:
                if card and len(card) >= 2:
                    suit = card[-1].lower()
                    rank = card[:-1]
                    col  = SUIT_COL_H.get(suit, "#ecf0f1")
                    sym  = SUIT_SYM_H.get(suit, "")
                    cards_html += (
                        f'<span style="display:inline-block;background:#1a1a2e;'
                        f'border:1.5px solid {col};border-radius:6px;padding:4px 8px;'
                        f'margin:2px;font-size:16px;font-weight:900;color:{col};'
                        f'min-width:32px;text-align:center;'
                        f'box-shadow:0 2px 6px rgba(0,0,0,0.5);">'
                        f'{rank}{sym}</span>'
                    )
            st.markdown(
                f'<div style="text-align:center;margin:4px 0 8px;">'
                f'<div style="font-size:10px;color:#7f8c8d;letter-spacing:2px;margin-bottom:4px;">'
                f'BOARD</div>{cards_html}</div>',
                unsafe_allow_html=True,
            )

        st.divider()

        if not decided:
            # Raise size slider
            suggest  = float(gs["suggest_raise_bb"])
            max_bb   = float(gs["stack_bb"])
            raise_to = st.slider(
                "Raise to (bb):",
                min_value=suggest,
                max_value=max_bb,
                value=suggest,
                step=0.5,
                key="t_raise_size",
            )

            b1, b2, b3 = st.columns(3)
            with b1:
                if st.button("FOLD", key="t_fold_btn",
                             use_container_width=True):
                    _t_decide("FOLD")
                    st.rerun()
            with b2:
                call_lbl = (f"CALL {gs['to_call_bb']:.1f}bb"
                            if gs["to_call_bb"] > 0 else "CHECK")
                call_act = "CALL" if gs["to_call_bb"] > 0 else "CHECK"
                if st.button(call_lbl, key="t_call_btn",
                             use_container_width=True):
                    _t_decide(call_act)
                    st.rerun()
            with b3:
                if st.button(f"RAISE {raise_to:.1f}bb", key="t_raise_btn",
                             use_container_width=True):
                    _t_decide("RAISE")
                    st.rerun()

        else:
            # ── Feedback ──────────────────────────────────────────────────────
            grade  = ev["grade"]
            colors = {"correct": "#2ecc71", "mixed": "#f1c40f",
                      "incorrect": "#e74c3c"}
            color  = colors.get(grade, "#ecf0f1")

            feedback = build_feedback_message(hand_str, sc, dec_made, ev)
            if ev.get("equity_pct") is not None:
                feedback += f"\n\nEquity: {ev['equity_pct']}%  |  Street: {ev.get('street','').upper()}"
            st.markdown(
                f'<div style="background:#111827;border-left:4px solid {color};'
                f'padding:12px 16px;border-radius:8px;font-family:monospace;'
                f'font-size:13px;color:{color};white-space:pre-line;margin-bottom:10px;">'
                f'{feedback}</div>',
                unsafe_allow_html=True,
            )

            # Strategy frequency bar
            strategy   = ev["strategy"]
            bar_colors = {"RAISE": "#2ecc71", "CALL": "#3498db", "FOLD": "#e74c3c"}
            parts = []
            for act, freq in sorted(strategy.items(), key=lambda x: -x[1]):
                if freq == 0:
                    continue
                bc     = bar_colors.get(act, "#7f8c8d")
                hl     = "outline:2px solid white;" if act == dec_made else ""
                parts.append(
                    f'<div style="display:inline-block;width:{freq}%;height:30px;'
                    f'background:{bc};{hl}vertical-align:top;position:relative;">'
                    f'<span style="position:absolute;top:50%;left:50%;'
                    f'transform:translate(-50%,-50%);font-size:10px;font-weight:700;'
                    f'color:white;white-space:nowrap;">{act} {freq}%</span></div>'
                )
            st.markdown(
                f'<div style="width:100%;border-radius:6px;overflow:hidden;margin-bottom:12px;">'
                f'{"".join(parts)}</div>',
                unsafe_allow_html=True,
            )

            if st.button("▶  Next hand", key="t_next_btn",
                         type="primary", use_container_width=True):
                _t_next()
                st.rerun()

    # ── Hand history panel (always visible) ───────────────────────────────────
    t_history = st.session_state.get("t_history", [])
    if t_history:
        with col_right:
            st.markdown("---")
            st.markdown(
                '<div style="font-size:11px;color:#7f8c8d;letter-spacing:2px;'
                'margin-bottom:6px;">📋 HAND HISTORY</div>',
                unsafe_allow_html=True,
            )
            _SCOL = {"PREFLOP":"#7f8c8d","FLOP":"#27ae60",
                     "TURN":"#f39c12","RIVER":"#e74c3c"}
            for entry in t_history:
                sname = entry["street"]
                scol  = _SCOL.get(sname, "#7f8c8d")
                lines_html = "<br>".join(entry["lines"])
                st.markdown(
                    f'<div style="margin-bottom:8px;padding:8px 12px;'
                    f'background:#0d1117;border-left:3px solid {scol};'
                    f'border-radius:0 6px 6px 0;">'
                    f'<span style="background:{scol};color:#fff;font-size:9px;'
                    f'font-weight:900;letter-spacing:1px;border-radius:3px;'
                    f'padding:1px 6px;margin-right:6px;">{sname}</span>'
                    f'<span style="font-size:12px;color:#aab7b8;line-height:1.7;">'
                    f'{lines_html}</span></div>',
                    unsafe_allow_html=True,
                )

    # ── JS: colour the FOLD/CALL/RAISE buttons by text content ───────────────
    if not decided:
        components.html("""
<script>
(function() {
    var STYLES = {
        fold:  'background:#7f1d1d!important;border:1.5px solid #e74c3c!important;color:#fff!important;font-weight:700!important;font-size:14px!important;letter-spacing:1px!important;',
        call:  'background:#1e3a5f!important;border:1.5px solid #3498db!important;color:#fff!important;font-weight:700!important;font-size:14px!important;letter-spacing:1px!important;',
        raise: 'background:#14532d!important;border:1.5px solid #2ecc71!important;color:#fff!important;font-weight:700!important;font-size:14px!important;letter-spacing:1px!important;'
    };
    function applyStyles() {
        try {
            var doc = window.parent.document;
            doc.querySelectorAll('button').forEach(function(btn) {
                var txt = (btn.innerText || '').trim().toUpperCase();
                if (txt === 'FOLD') {
                    btn.style.cssText += STYLES.fold;
                } else if (txt.startsWith('CALL') || txt === 'CHECK') {
                    btn.style.cssText += STYLES.call;
                } else if (txt.startsWith('RAISE')) {
                    btn.style.cssText += STYLES.raise;
                }
            });
        } catch(e) {}
    }
    applyStyles();
    setTimeout(applyStyles, 150);
    setTimeout(applyStyles, 400);
    var obs = new MutationObserver(applyStyles);
    try { obs.observe(window.parent.document.body, {childList:true, subtree:true}); } catch(e) {}
})();
</script>
""", height=0)
