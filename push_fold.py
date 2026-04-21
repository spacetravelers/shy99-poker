"""
module2_engine/push_fold.py
-----------------------------
Push/fold ranges for short stack play (< 20bb).

Based on Nash equilibrium push/fold tables.
Covers all 9 Full Ring positions.

Usage
-----
    from push_fold import should_push, should_call_push
"""

# ── Nash push ranges by effective stack (bb) and position ─────────────────────
# Format: {position: {max_bb: [hands...]}}
# Read as: "push these hands with UP TO max_bb stack"

PUSH_RANGES = {
    "BTN": {
        6:  ["AA","KK","QQ","JJ","TT","99","88","77","66","55","44","33","22",
              "AKs","AQs","AJs","ATs","A9s","A8s","A7s","A6s","A5s","A4s","A3s","A2s",
              "AKo","AQo","AJo","ATo","A9o","A8o","A7o","A6o","A5o","A4o","A3o","A2o",
              "KQs","KJs","KTs","K9s","K8s","K7s","KQo","KJo","KTo","K9o",
              "QJs","QTs","Q9s","QJo","QTo","JTs","JTo","T9s","98s","87s","76s","65s","54s"],
        10: ["AA","KK","QQ","JJ","TT","99","88","77","66","55","44","33","22",
             "AKs","AQs","AJs","ATs","A9s","A8s","A7s","A6s","A5s","A4s","A3s","A2s",
             "AKo","AQo","AJo","ATo","A9o","A8o","A7o","A6o","A5o",
             "KQs","KJs","KTs","K9s","K8s","KQo","KJo","KTo",
             "QJs","QTs","Q9s","QJo","JTs","T9s","98s","87s","76s","65s","54s"],
        15: ["AA","KK","QQ","JJ","TT","99","88","77","66","55","44","33","22",
             "AKs","AQs","AJs","ATs","A9s","A8s","A7s","A6s","A5s","A4s","A3s",
             "AKo","AQo","AJo","ATo","A9o","A8o",
             "KQs","KJs","KTs","K9s","KQo","KJo","KTo",
             "QJs","QTs","QJo","JTs","T9s","98s","87s","76s","65s"],
        20: ["AA","KK","QQ","JJ","TT","99","88","77","66","55","44",
             "AKs","AQs","AJs","ATs","A9s","A8s","A7s","A5s","A4s",
             "AKo","AQo","AJo","ATo","A9o",
             "KQs","KJs","KTs","KQo","KJo",
             "QJs","QTs","JTs","T9s","98s","87s","76s"],
    },
    "CO": {
        6:  ["AA","KK","QQ","JJ","TT","99","88","77","66","55","44","33","22",
              "AKs","AQs","AJs","ATs","A9s","A8s","A7s","A6s","A5s","A4s","A3s","A2s",
              "AKo","AQo","AJo","ATo","A9o","A8o","A7o","A6o",
              "KQs","KJs","KTs","K9s","KQo","KJo","KTo",
              "QJs","QTs","QJo","JTs","T9s","98s","87s","76s","65s","54s"],
        10: ["AA","KK","QQ","JJ","TT","99","88","77","66","55","44","33","22",
             "AKs","AQs","AJs","ATs","A9s","A8s","A7s","A6s","A5s","A4s","A3s",
             "AKo","AQo","AJo","ATo","A9o","A8o",
             "KQs","KJs","KTs","K9s","KQo","KJo",
             "QJs","QTs","JTs","T9s","98s","87s","76s","65s"],
        15: ["AA","KK","QQ","JJ","TT","99","88","77","66","55","44","33",
             "AKs","AQs","AJs","ATs","A9s","A8s","A7s","A5s","A4s",
             "AKo","AQo","AJo","ATo","A9o",
             "KQs","KJs","KTs","KQo","KJo",
             "QJs","JTs","T9s","98s","87s","76s"],
        20: ["AA","KK","QQ","JJ","TT","99","88","77","66","55",
             "AKs","AQs","AJs","ATs","A9s","A8s","A5s",
             "AKo","AQo","AJo","ATo",
             "KQs","KJs","KQo",
             "QJs","JTs","T9s","98s"],
    },
    "SB": {
        6:  ["AA","KK","QQ","JJ","TT","99","88","77","66","55","44","33","22",
              "AKs","AQs","AJs","ATs","A9s","A8s","A7s","A6s","A5s","A4s","A3s","A2s",
              "AKo","AQo","AJo","ATo","A9o","A8o","A7o","A6o","A5o","A4o","A3o",
              "KQs","KJs","KTs","K9s","K8s","KQo","KJo","KTo",
              "QJs","QTs","QJo","JTs","T9s","98s","87s","76s","65s","54s"],
        10: ["AA","KK","QQ","JJ","TT","99","88","77","66","55","44","33","22",
             "AKs","AQs","AJs","ATs","A9s","A8s","A7s","A6s","A5s","A4s","A3s","A2s",
             "AKo","AQo","AJo","ATo","A9o","A8o","A7o",
             "KQs","KJs","KTs","K9s","KQo","KJo","KTo",
             "QJs","QTs","QJo","JTs","T9s","98s","87s","76s","65s"],
        15: ["AA","KK","QQ","JJ","TT","99","88","77","66","55","44","33","22",
             "AKs","AQs","AJs","ATs","A9s","A8s","A7s","A6s","A5s","A4s","A3s",
             "AKo","AQo","AJo","ATo","A9o","A8o","A6o",
             "KQs","KJs","KTs","K9s","KQo","KJo",
             "QJs","QTs","JTs","T9s","98s","87s","76s"],
        20: ["AA","KK","QQ","JJ","TT","99","88","77","66","55","44",
             "AKs","AQs","AJs","ATs","A9s","A8s","A7s","A5s","A4s","A3s",
             "AKo","AQo","AJo","ATo","A9o",
             "KQs","KJs","KTs","KQo","KJo",
             "QJs","JTs","T9s","98s","87s"],
    },
    "default": {
        6:  ["AA","KK","QQ","JJ","TT","99","88","77","66","55","44","33","22",
              "AKs","AQs","AJs","ATs","A9s","A8s","A7s","A6s","A5s",
              "AKo","AQo","AJo","ATo","A9o",
              "KQs","KJs","KTs","KQo","KJo",
              "QJs","JTs","T9s","98s","87s"],
        10: ["AA","KK","QQ","JJ","TT","99","88","77","66","55","44","33",
             "AKs","AQs","AJs","ATs","A9s","A8s","A5s",
             "AKo","AQo","AJo","ATo",
             "KQs","KJs","KQo",
             "QJs","JTs","T9s"],
        15: ["AA","KK","QQ","JJ","TT","99","88","77","66",
             "AKs","AQs","AJs","ATs","A9s","A5s",
             "AKo","AQo","AJo",
             "KQs","KQo","QJs"],
        20: ["AA","KK","QQ","JJ","TT","99","88",
             "AKs","AQs","AJs","ATs",
             "AKo","AQo","AJo",
             "KQs","KQo"],
    }
}

# Nash call ranges (BB calling a shove)
CALL_RANGES_BB = {
    6:  ["AA","KK","QQ","JJ","TT","99","88","77","66","55","44","33","22",
          "AKs","AQs","AJs","ATs","A9s","A8s","A7s","A6s","A5s","A4s","A3s","A2s",
          "AKo","AQo","AJo","ATo","A9o","A8o","A7o","A6o",
          "KQs","KJs","KTs","K9s","KQo","KJo","KTo",
          "QJs","QTs","QJo","JTs","T9s","98s","87s","76s","65s"],
    10: ["AA","KK","QQ","JJ","TT","99","88","77","66","55","44",
         "AKs","AQs","AJs","ATs","A9s","A8s","A7s","A5s","A4s",
         "AKo","AQo","AJo","ATo","A9o",
         "KQs","KJs","KTs","KQo","KJo",
         "QJs","QTs","JTs","T9s","98s","87s"],
    15: ["AA","KK","QQ","JJ","TT","99","88","77","66",
         "AKs","AQs","AJs","ATs","A9s","A8s","A5s",
         "AKo","AQo","AJo","ATo",
         "KQs","KJs","KQo",
         "QJs","JTs","T9s"],
    20: ["AA","KK","QQ","JJ","TT","99","88",
         "AKs","AQs","AJs","ATs","A9s",
         "AKo","AQo","AJo",
         "KQs","KQo","QJs"],
}


def _get_push_range(position: str, stack_bb: float) -> list:
    pos = position.upper()
    ranges = PUSH_RANGES.get(pos, PUSH_RANGES["default"])
    for bb_limit in sorted(ranges.keys()):
        if stack_bb <= bb_limit:
            return ranges[bb_limit]
    return ranges[max(ranges.keys())]


def _get_call_range_bb(stack_bb: float) -> list:
    for bb_limit in sorted(CALL_RANGES_BB.keys()):
        if stack_bb <= bb_limit:
            return CALL_RANGES_BB[bb_limit]
    return CALL_RANGES_BB[max(CALL_RANGES_BB.keys())]


def should_push(hand_str: str, position: str, stack_bb: float) -> dict:
    """
    Determine if hero should push all-in pre-flop.

    Returns dict: action, in_push_range, stack_bb
    """
    push_range = _get_push_range(position, stack_bb)
    in_range = hand_str in push_range if hand_str else False
    return {
        "action": "PUSH" if in_range else "FOLD",
        "in_push_range": in_range,
        "stack_bb": round(stack_bb, 1),
        "position": position,
    }


def should_call_push(hand_str: str, stack_bb: float) -> dict:
    """
    Determine if BB should call an all-in shove.

    Returns dict: action, in_call_range, stack_bb
    """
    call_range = _get_call_range_bb(stack_bb)
    in_range = hand_str in call_range if hand_str else False
    return {
        "action": "CALL" if in_range else "FOLD",
        "in_call_range": in_range,
        "stack_bb": round(stack_bb, 1),
    }
