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


def plot_course_call(target: object = "<sector_id>") -> str:
    """The one plot_course syntax the prompt and the route notice both use."""
    return 'plot_course {"target":' + str(target) + ',"execute":true}'


def plot_course_line() -> str:
    depth = int(K.PLOT_COURSE_MAX_DEPTH)
    return (
        f"- `{plot_course_call()}` — moves along the shortest known path, "
        f"up to {depth} warps. Each warp costs its normal turns. `execute` false only previews."
    )


def bank_block() -> str:
    return (
        f'`bank_deposit {{"amount":N}}`, `bank_withdraw {{"amount":N}}` and '
        f'`bank_transfer {{"to_player":"P3","amount":N}}` work at StarDock only and cost '
        f"{int(K.BANK_TURN_COST)} turns. The account holds up to {int(K.BANK_MAX_BALANCE):,} credits. "
        "Banked credits are not lost when your ship is destroyed and are not taxed. Credits on the ship "
        f"are lost if the ship is destroyed. Alignment {int(K.TAX_MIN_ALIGNMENT)} or higher, carrying over "
        f"{int(K.TAX_THRESHOLD):,} credits, pays {int(K.TAX_RATE_PCT)}% at the start of each day.\n"
    )


def port_block() -> str:
    costs = K.PORT_UPGRADE_UNIT_COST
    prices = ", ".join(f"{name} {int(costs[name])}" for name in ("fuel_ore", "organics", "equipment"))
    return (
        f'`port_upgrade {{"commodity":"fuel_ore|organics|equipment","units":N}}` costs {prices} credits per unit '
        f"and adds {int(K.PORT_UPGRADE_HOLDS_PER_UNIT)} holds. StarDock and class 0 are not upgraded. "
        '`port_build {"planet_id":N,"port_class":"BBS","name":"..."}` needs your planet, or your corporation\'s, '
        "in this sector. Each build day spends that class's materials from the planet stockpile.\n"
    )


def corpship_block() -> str:
    n = int(K.CORPSHIP_PASSWORD_MAX_LEN)
    return (
        f'`ship_set_corporate {{}}` flags the ship you are flying for your corporation. '
        f'`ship_set_personal {{}}` flags it personal. '
        f'`ship_set_password {{"password":"..."}}` is 1 to {n} characters. '
        "Mates can enter that ship and tow it. The password keeps them out until they pass it. "
        "Your own personal unmanned ship can be destroyed for cargo holds: (its holds + 3) / 3, "
        "added to the ship you are flying, never past that hull's maximum. "
        "A corporate ship of your own corporation cannot be attacked.\n"
    )


def corp_extra() -> str:
    return (
        f"A corporation holds {int(K.CORP_MAX_MEMBERS)} traders. "
        "`deploy_fighters` and `deploy_mines` take ownership personal or corporate. "
        "The C.E.O. leaving dissolves the corporation. "
        "A corporation with both good and evil traders loses experience at the day tick.\n"
    )


def alien_line() -> str:
    share = K.ALIEN_KILL_ALIGN_SHARE
    return (
        'Attack an alien in your sector with `attack {"target":"alien:<n>","qty":N}`. '
        f"A kill moves your alignment by {share} of the alien's alignment, against the alien.\n"
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
    extra: list[str] = []
    if K.bank_on():
        extra.append(bank_block())
    if K.port_upgrade_on():
        extra.append(port_block())
    if K.corpship_on():
        extra.append(corpship_block())
    if K.corp_rules_on():
        extra.append(corp_extra())
    if K.alien_on():
        extra.append(alien_line())
    if extra:
        text = text.rstrip() + "\n" + "".join(extra)
    return text
