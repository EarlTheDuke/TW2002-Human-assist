"""Mode-dependent sentences an LLM seat reads. Built from constants at call time.

Legacy prompts do not call this module. Parity prompts do.
"""

from __future__ import annotations

from ..engine import constants as K

_STARDOCK_FULL = "StarDock (sector 1) is where `buy_ship`, `buy_equip`, and `corp_create` work."
_STARDOCK_FULL_NEW = "StarDock (sector 1) is where `buy_ship` and `buy_equip` work. `corp_create` is free in any sector."
_STARDOCK_MIN = "StarDock (sector 1): `buy_ship`, `buy_equip`, `corp_create`."
_STARDOCK_MIN_NEW = "StarDock (sector 1): `buy_ship`, `buy_equip`. `corp_create` is free in any sector."
_CLUSTER = "already plan to build a corp, cluster — shared treasury makes ferrying trivial."
_CLUSTER_NEW = "already plan to build a corp, cluster — a mate in the same sector can hand you credits."
_FLAG = "corporate_flagship  163,500, 85 holds (CORP MEMBER ONLY)"
_FLAG_CEO = "corporate_flagship  163,500, 85 holds (C.E.O. ONLY)"
_CORP_LIST = "corp_create corp_invite corp_join corp_leave corp_deposit corp_withdraw corp_memo"
_CORP_LIST_NEW = (
    "corp_create corp_set_password corp_invite corp_join corp_leave corp_drop corp_transfer corp_memo"
)
_PLOT = '- `plot_course {"target":<sector_id>}` — BFS autopilot up to 10 warps; each still costs its turn price.'
_CORP_START = '- `corp_create {"ticker":"XYZ","name":"..."}` — 500k cr at StarDock.'
_CORP_END = "show only name/alive/corp)."


def plot_course_line() -> str:
    depth = int(K.PLOT_COURSE_MAX_DEPTH)
    return (
        f'- `plot_course {{"target":<sector_id>,"execute":true}}` — moves along the shortest known path, '
        f"up to {depth} warps. Each warp costs its normal turns. `execute` false only previews."
    )


def corp_blurb() -> str:
    cost = int(K.CORP_CREATE_COST)
    price = "free" if cost <= 0 else f"{cost} credits"
    return (
        f'- `corp_create {{"ticker":"XYZ","name":"..."}}` — {price} in any sector. '
        'The C.E.O. then sets `corp_set_password {"password":"..."}`.\n'
        '- `corp_invite {"target":"P3"}`. `corp_join {"ticker":"XYZ","password":"<from the invite>"}`. '
        f"One wrong password a day ({int(K.CORP_BREAKIN_PER_DAY)}).\n"
        '- `corp_leave`. `corp_drop {"target":"P3"}` is C.E.O. only.\n'
        '- `corp_transfer {"target":"P3","item":"credits","qty":N,"direction":"give"}` in the same sector, '
        "both traders in their ships. Direction is give or take.\n"
        '- `corp_memo {"message":"..."}` — team channel; last 5 appear in `corp.recent_memos`.\n'
        "- Mates do not shoot each other. A member pays for a citadel from the credits on that member's ship. "
        "Only the C.E.O. buys the Corporate FlagShip."
    )


def apply(text: str) -> str:
    """Rewrite contradiction lines. The caller checks llm_parity_on()."""
    if K.corp_rules_on() and str(K.CORP_TREASURY) == "off":
        text = text.replace(_STARDOCK_FULL, _STARDOCK_FULL_NEW)
        text = text.replace(_STARDOCK_MIN, _STARDOCK_MIN_NEW)
        text = text.replace(_CLUSTER, _CLUSTER_NEW)
        text = text.replace(_CORP_LIST, _CORP_LIST_NEW)
        start = text.find(_CORP_START)
        end = text.find(_CORP_END, start) if start >= 0 else -1
        if start >= 0 and end > start:
            end += len(_CORP_END)
            text = text[:start] + corp_blurb() + text[end:]
    if K.corp_bots_on() and K.CFS_CEO_RULE == "purchase":
        text = text.replace(_FLAG, _FLAG_CEO)
    text = text.replace(_PLOT, plot_course_line())
    return text
