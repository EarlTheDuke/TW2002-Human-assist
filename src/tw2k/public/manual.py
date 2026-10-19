"""Player's manual. Server-rendered HTML. Every number is read from the engine at request time."""

from __future__ import annotations

from html import escape

from ..engine import constants as K
from .pages import DISCLAIMER_POINTS

# One anchor per section. The table of contents and the tests both use this list.
SECTIONS: tuple[tuple[str, str], ...] = (
    ("getting-started", "Getting started"),
    ("walkthrough", "First-day walkthrough"),
    ("command-keys", "Command keys"),
    ("moving", "Moving, the course card and Express autopilot"),
    ("trading", "Trading and haggling"),
    ("ports", "Ports and StarDock"),
    ("combat", "Combat"),
    ("ferrengi", "Ferrengi"),
    ("planets", "Planets"),
    ("citadels", "Citadels"),
    ("colonists", "Colonists and Terra"),
    ("corporations", "Corporations"),
    ("alignment", "Alignment, experience and ranks"),
    ("tax", "Tax, bank and interest"),
    ("turns", "Turns and days"),
    ("disclaimer", "Beta disclaimer"),
)

_CSS = """
:root{color-scheme:dark}
*{box-sizing:border-box}
html,body{margin:0;background:#05070d;color:#d6e2f0;font:16px/1.5 system-ui,Segoe UI,Roboto,sans-serif}
main{max-width:960px;margin:0 auto;padding:24px 16px 48px}
h1{font-size:28px;margin:8px 0 4px;color:#7fe3ff}
h2{font-size:22px;margin:32px 0 8px;color:#ffd27f}
h3{font-size:18px;margin:18px 0 8px;color:#d6e2f0}
p,li,td,th,a,footer,.note{font-size:16px}
p.sub{margin:0 0 16px;color:#c5d4e6}
a{color:#7fe3ff}
table{width:100%;border-collapse:collapse;table-layout:fixed}
th,td{text-align:left;padding:8px 6px;border-bottom:1px solid #1a2638;vertical-align:top;overflow-wrap:anywhere}
th{color:#ffd27f;font-weight:600}
.note{color:#c5d4e6}
nav.toc ol{padding-left:1.4em}
footer{border-top:1px solid #142034;padding:14px 16px 20px;color:#c5d4e6}
"""

_KEYS = (
    ("M", "Move to an adjacent sector"),
    ("P", "Port and trade"),
    ("L", "Land on a planet"),
    ("D", "Re-display the sector"),
    ("S", "Long range scan"),
    ("A", "Attack"),
    ("F", "Take or leave fighters (in space). Stock fighters while landed"),
    ("H", "Handle mines"),
    ("U", "Use a Genesis torpedo"),
    ("E", "Ether probe"),
    ("C", "Computer"),
    ("I", "Ship info"),
    ("Y", "Read mail"),
    (".", "Wait one turn"),
    ("T", "Corporate menu in space. Take product while landed"),
    ("R", "Release a beacon"),
    ("X", "Transporter pad"),
    ("W", "Tow a spacecraft"),
    ("V", "Game status in space. Leave product while landed"),
    ("Z", "Rules and help (the short panel). The manual is this page"),
    ("G", "Show deployed fighters in space. Take fighters while landed"),
    ("B", "Self destruct in space. Build a citadel while landed"),
    ("J", "Jettison cargo"),
    ("Q", "Quit"),
    ("?", "Help"),
    ("N", "Move colonists while landed"),
    ("Enter", "Engage Express when a course is plotted"),
)

_COMPUTER = (
    ("F", "Course plotter"),
    ("P", "Fire a photon missile"),
    ("R", "Port report"),
    ("K", "Your known universe"),
    ("A", "Make an announcement"),
    ("O", "Avoid sectors"),
    ("Q", "Exit the computer"),
)


def _n(value: int | float) -> str:
    if isinstance(value, float) and not value.is_integer():
        return f"{value:,.2f}"
    return f"{int(value):,}"


def _on(flag: bool) -> str:
    return "on" if flag else "off"


def _src(text: str) -> str:
    return f'<p class="note">Original rule source: {escape(text)}</p>'


def _table(headers: tuple[str, ...], rows: list[tuple[str, ...]]) -> str:
    head = "".join(f"<th>{escape(cell)}</th>" for cell in headers)
    body = []
    for row in rows:
        body.append("<tr>" + "".join(f"<td>{escape(cell)}</td>" for cell in row) + "</tr>")
    return "<table><thead><tr>" + head + "</tr></thead><tbody>" + "".join(body) + "</tbody></table>"


def _letters(trades: tuple[bool | None, bool | None, bool | None]) -> str:
    out = []
    for flag in trades:
        if flag is None:
            return "special"
        out.append("B" if flag else "S")
    return "".join(out)


def _facts(config) -> dict:
    turns_asked = int(getattr(config, "turns_per_day", None) or K.STARTING_TURNS_PER_DAY)
    override = getattr(config, "starting_credits_override", None) if config is not None else None
    credits, turns, fighters = K.opening_loadout(K.STARTING_CREDITS, turns_asked, 0, override)
    ship = K.ship_specs()[K.STARTING_SHIP]
    day_seconds = getattr(config, "turn_regen_day_seconds", None) if config is not None else None
    if day_seconds is None:
        day_seconds = K.TURN_REGEN_DAY_SECONDS
    fuel, organics, equipment = K.PLANET_PROD_PER_UNIT["M"]
    rate, over, align = K.tax_terms()
    max_days = int(getattr(config, "max_days", None) or 10)
    return {
        "credits": int(credits),
        "turns": int(turns),
        "fighters": int(fighters),
        "ship": str(ship["display_name"]),
        "holds": int(ship["holds"]),
        "tpw": int(ship["turns_per_warp"]),
        "hold_cost": int(ship["base_hold_cost"]),
        "day_seconds": int(day_seconds),
        "fuel_ratio": int(fuel),
        "org_ratio": int(organics),
        "eq_ratio": int(equipment),
        "tax_rate": int(rate),
        "tax_over": int(over),
        "tax_align": int(align),
        "max_days": max_days,
        "scoped": config is not None,
    }


def render(brand: str, config=None, *, lobby: bool = True) -> str:
    """The manual for this process, or for one game when config is that game's GameConfig.

    lobby=False is the per-game page: its links go back to that game's cockpit.
    """
    f = _facts(config)
    scope = (
        "These numbers are this game's settings."
        if f["scoped"]
        else "These numbers are the rules loaded in this process. Open the manual from a game to see that game's settings."
    )
    toc = "".join(f'<li><a href="#{sid}">{escape(title)}</a></li>' for sid, title in SECTIONS)
    if not lobby:
        nav = '<p class="sub"><a href="/bot">Cockpit</a> · <a href="/manual">Manual</a></p>'
        foot = '<a href="/bot">Cockpit</a> · <a href="/manual">Manual</a>'
    else:
        nav = ('<p class="sub"><a href="/">Lobby</a> · <a href="/manual">Manual</a> · '
               '<a href="/about">About these test games</a></p>')
        foot = '<a href="/">Lobby</a> · <a href="/manual">Manual</a> · <a href="/about">About these test games</a>'
    parts = [
        "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">",
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">",
        f"<title>Player manual - {escape(brand)}</title><style>{_CSS}</style></head><body><main>",
        f"<h1>{escape(brand)}</h1>",
        nav,
        f"<p>{escape(scope)}</p>",
        f'<nav class="toc" aria-label="Contents"><h2>Contents</h2><ol>{toc}</ol></nav>',
    ]
    for sid, _title in SECTIONS:
        parts.append(_section(sid, f))
    parts.append(
        "</main><footer>Closed beta test games · " + foot + "</footer>"
        "</body></html>"
    )
    return "".join(parts)


def _section(sid: str, f: dict) -> str:
    title = dict(SECTIONS)[sid]
    body = {
        "getting-started": _getting_started,
        "walkthrough": _walkthrough,
        "command-keys": _command_keys,
        "moving": _moving,
        "trading": _trading,
        "ports": _ports,
        "combat": _combat,
        "ferrengi": _ferrengi,
        "planets": _planets,
        "citadels": _citadels,
        "colonists": _colonists,
        "corporations": _corporations,
        "alignment": _alignment,
        "tax": _tax,
        "turns": _turns,
        "disclaimer": _disclaimer,
    }[sid](f)
    return f'<section id="{sid}"><h2>{escape(title)}</h2>{body}</section>'


def _getting_started(f: dict) -> str:
    pocket = ("Every seat gets that same pocket." if K.starting_package_live()
              else "Later seats still use the old credit skew.")
    return (
        "<p>You are a trader in a closed beta of a Trade Wars 2002 style game. "
        f"The first seat starts in a {escape(f['ship'])} with {_n(f['credits'])} credits, "
        f"{_n(f['fighters'])} fighters, {_n(f['holds'])} holds and {_n(f['turns'])} turns. "
        f"{pocket}</p>"
        "<p>Read this page, then use the cockpit. The header Manual button opens this page in a new tab. "
        "Z still opens the short rules panel. ? still opens help.</p>"
        "<p>The map shows sectors you have visited and the lanes between them. A lane can be one-way. "
        "The course card (Computer, then F) plots a path and does not spend a turn. Engage Express flies it.</p>"
        + _src("Trade Wars 2002 command set and the v3.11 starting package measured for this clone. "
               "Numbers on this page are read from the engine, not typed in.")
    )


def _walkthrough(f: dict) -> str:
    home = (
        f"When the home-planet rule is {_on(K.home_planet_live())}, you begin landed on a class M planet "
        f"outside FedSpace (sectors {_n(min(K.FEDSPACE_SECTORS))} through {_n(max(K.FEDSPACE_SECTORS))}) "
        f"with {_n(K.HOME_PLANET_FUEL)} fuel, {_n(K.HOME_PLANET_ORGANICS)} organics and "
        f"{_n(K.HOME_PLANET_EQUIPMENT)} equipment. Lift off, then come back."
    )
    return (
        "<ol>"
        f"<li>Look at the ship. It is a {escape(f['ship'])}: {_n(f['holds'])} holds, "
        f"{_n(f['fighters'])} fighters, {_n(f['credits'])} credits, {_n(f['turns'])} turns. "
        f"Each warp on this hull costs {_n(f['tpw'])} turns.</li>"
        f"<li>{home}</li>"
        "<li>Open the map. Note which lanes point only one way. Do not assume you can fly back the way you came.</li>"
        "<li>Press C, then F, and plot a course to a nearby port. Read the course card. "
        "Engage Express only when the first hop costs no more than the turns you have left.</li>"
        "<li>Trade. A port letter B means the port buys that good from you. S means the port sells it to you. "
        "The three letters are fuel, organics, equipment. Sell where the port buys, buy where the next port sells.</li>"
        f"<li>Colonists come from Terra in sector {_n(K.STARDOCK_SECTOR)}. "
        f"The pool starts at {_n(K.terra_start_pool())} and grows {_n(K.TERRA_REGEN_PER_DAY)} a day. "
        f"One hold carries {_n(K.colonists_per_hold())} colonists and the load costs {_n(K.TERRA_LOAD_TURNS)} turn. "
        "They are free. Take them to your planet and set the population.</li>"
        f"<li>Buy more holds when a hold pays for itself. The first extra hold on this hull is listed at "
        f"{_n(f['hold_cost'])} credits.</li>"
        f"<li>Stay away from Ferrengi until you can pay or fight. FedSpace is sectors "
        f"{_n(min(K.FEDSPACE_SECTORS))} through {_n(max(K.FEDSPACE_SECTORS))}. "
        f"StarDock is sector {_n(K.STARDOCK_SECTOR)}. Do not start a fight there.</li>"
        "</ol>"
        + _src("v3.11 new-trader opening: Merchant Cruiser, the measured credit and turn pocket, "
               "Terra as the colonist source, and the course card from the cockpit map work.")
    )


def _command_keys(_f: dict) -> str:
    return (
        "<p>These are the redesign cockpit keys. They are the original Trade Wars letters. "
        "The same letter can mean a different order while you are landed.</p>"
        + _table(("Key", "What it does"), _KEYS)
        + "<h3>Computer menu</h3><p>Press C first.</p>"
        + _table(("Key", "What it does"), _COMPUTER)
        + _src("Trade Wars 2002 command letters, as wired on the redesign cockpit.")
    )


def _moving(_f: dict) -> str:
    return (
        "<p>M warps to an adjacent sector. The button under a warp shows the turn cost. "
        "A grey warp costs more turns than you have.</p>"
        "<p>C then F plots a course. Plotting is free. The course card lists every hop, the turn cost of each hop, "
        "and which lanes are one-way. Engage Express flies the next hop, then the one after, until you stop it or the course ends. "
        "Enter does the same thing when a course is on screen.</p>"
        "<p>Avoid (Computer, O) tells the plotter to stay out of a sector. Clearing the list uses sector 0.</p>"
        + _src("Trade Wars course plotter, plus the cockpit course card: a plot spends no turn and Express flies the plotted hops.")
    )


def _trading(f: dict) -> str:
    room = K.PORT_HAGGLE_LIVE_ROOM_PCT
    end = K.PORT_HAGGLE_LIVE_END_PCT
    return (
        "<p>P docks and trades. The first trade of a visit costs "
        f"{_n(K.PORT_DOCK_TURN_COST)} turn. A later trade in the same sector costs none.</p>"
        f"<p>A successful trade gives {_n(K.XP_AWARDS['trade'])} experience, up to {_n(K.PORT_HAGGLE_XP_CAP)} from haggling. "
        f"Price also moves with experience, capped at {_n(K.PORT_PRICE_EXPERIENCE_CAP)}.</p>"
        f"<p>The live haggle window is {_on(K.haggle_window_live())} in this process. "
        f"When it is on, a counter has to sit between {_n(room)} and {_n(end)} percent of the quote. "
        f"The older window runs from {_n(K.PORT_HAGGLE_MIN_PCT)} to {_n(K.PORT_HAGGLE_MAX_PCT)} percent. "
        f"A failed haggle costs {_n(K.PORT_HAGGLE_FAIL_TURNS)} turn.</p>"
        + _src("Port haggling notes (HAGGLE.md) and the experience award for a trade.")
    )


def _ports(_f: dict) -> str:
    rows = []
    for cid in range(0, 10):
        trades = K.port_class_trades(cid)
        meaning = _letters(trades)
        if meaning == "special":
            meaning = "StarDock and special services" if cid in (0, 8) else "no standard goods"
        else:
            meaning = f"{meaning}: B buys from you, S sells to you (fuel, organics, equipment)"
        rows.append((str(cid), meaning))
    return (
        "<p>Port class letters are read from the engine for this process. "
        f"The live class map is {_on(K.port_class_live())}.</p>"
        + _table(("Class", "What it trades"), rows)
        + "<p>StarDock, in sector "
        + _n(K.STARDOCK_SECTOR)
        + ", sells hardware and ships and holds the bank. Class 0 is the federal port.</p>"
        + _src("Trade Wars port class chart. B means the port buys that commodity from the player.")
    )


def _combat(_f: dict) -> str:
    odds = (
        "On in this process: offensive fighters trade 1 for 1."
        if K.offensive_clash_held()
        else "Off in this process: offensive fighters use the legacy exchange, not the 1-for-1 wave."
    )
    pod_credits = (
        f"A pod holds {_n(K.POD_CASH_CREDITS)} credits."
        if K.pod_cash_live()
        else "The pod-cash rule is off, so a pod does not use that credit amount."
    )
    loss = int(K.POD_EXP_LOSS * 100)
    return (
        "<p>Fighters and shields are the ship's weapons and armour. Toll fighters and defensive fighters "
        "sit in a sector or on a planet and fight ships that pass or land. Mines hit a ship that enters. "
        "A photon is fired from the computer menu.</p>"
        f"<p>The v3.11 fighter exchange: {odds}</p>"
        f"<p>A kill drops you in an escape pod. You lose the ship. Experience drops by {loss} percent "
        f"({_n(K.POD_EXP_LOSS)} of what you had). {pod_credits} "
        "Addendum A is the written source for what the pod keeps.</p>"
        + _src("RULINGS v3.11 section 6 (fighter exchange) and Addendum A (the escape pod and its credits).")
    )


def _ferrengi(_f: dict) -> str:
    if K.ferrengi_reward_live():
        kill = (
            f"A good trader (alignment above 0) gains {_n(K.FERRENGI_ALIGN_ON_KILL)} alignment. "
            "A neutral or evil trader does not. Experience is a flat award by hull. "
        )
    else:
        kill = f"Killing one moves alignment by {_n(K.FERRENGI_ALIGN_ON_KILL)}. "
    return (
        f"<p>A Ferrengi encounter is {escape(K.FERRENGI_ENCOUNTER)}. "
        f"Tribute asks for about {_n(K.FERRENGI_TRIBUTE_HOLDS)} holds or "
        f"{_n(int(K.FERRENGI_TRIBUTE_CREDIT_PCT * 100))} percent of your credits.</p>"
        "<p>You can pay, flee or fight. Attacking one makes a grudge: that Ferrengi, and later ones, treat you as hostile. "
        f"{kill}"
        f"They start leaving you alone for the first {_n(K.FERRENGI_STARTUP_GRACE_DAYS)} days, "
        f"and a bounty is {_n(K.FERRENGI_BOUNTY_PER_AGG)} credits per point of aggression.</p>"
        + _src("Ferrengi encounter rules in the engine: tribute first, then a grudge if you attack.")
    )


def _planets(f: dict) -> str:
    rows = []
    for cls, ratios in K.PLANET_PROD_PER_UNIT.items():
        cap = K.PLANET_MAX_COLONISTS.get(cls)
        cap_text = _n(cap) if cap is not None else "none"
        rows.append((cls, _n(ratios[0]), _n(ratios[1]), _n(ratios[2]), cap_text))
    return (
        "<p>A planet has a class. The live production rule is "
        f"{_on(K.planet_prod_live())}. The table is colonists needed for one unit of fuel, organics and equipment. "
        "Zero means that class does not make that good.</p>"
        + _table(("Class", "Fuel", "Organics", "Equipment", "Colonist cap"), rows)
        + f"<p>Class M, the home class, needs {_n(f['fuel_ratio'])} colonists per fuel unit, "
        f"{_n(f['org_ratio'])} per organics unit and {_n(f['eq_ratio'])} per equipment unit "
        "when that rule is on. A new home planet's stock is "
        f"{_n(K.HOME_PLANET_FUEL)} fuel, {_n(K.HOME_PLANET_ORGANICS)} organics and "
        f"{_n(K.HOME_PLANET_EQUIPMENT)} equipment when the home-planet rule is {_on(K.home_planet_live())}.</p>"
        f"<p>A Genesis torpedo costs {_n(K.genesis_torpedo_cost())} credits and "
        f"{_n(K.GENESIS_DEPLOY_TURN_COST)} turns. It cannot be used within "
        f"{_n(K.GENESIS_MIN_HOPS_FROM_STARDOCK)} hops of StarDock. "
        f"A sector holds at most {_n(K.PLANETS_PER_SECTOR_CAP)} planets.</p>"
        "<p>You can give a planet orders only when you or your corporation own it. "
        "Terra is not a planet you can claim.</p>"
        + _src("S1 planet handbook class table, the home-planet opening, and the Genesis torpedo price.")
    )


def _citadels(_f: dict) -> str:
    rows = []
    for cls in K.CITADEL_CLASS_COSTS:
        for level in range(1, K.CITADEL_LEVELS + 1):
            colonists, fuel, organics, equipment, days = K.citadel_class_cost(cls, level)
            rows.append((cls, str(level), _n(colonists), _n(fuel), _n(organics), _n(equipment), _n(days)))
    perks = "".join(
        f"<li>Level {_n(level)}: {escape(name)}. {escape(text)}</li>"
        for level, name, text in K.citadel_perks()
    )
    return (
        "<p>A citadel is built on a planet you own. The table is colonists, fuel, organics, equipment and days "
        f"for each class and level. The class-M fidelity rule is {_on(K.class_m_fidelity_live())}.</p>"
        + _table(("Class", "Level", "Colonists", "Fuel", "Organics", "Equipment", "Days"), rows)
        + f"<ul>{perks}</ul>"
        f"<p>The treasury pays {_n(K.PLANET_TREASURY_INTEREST_PCT)} percent a day. "
        f"The Quasar cannon needs level {_n(K.QUASAR_MIN_LEVEL)}. "
        f"The interdictor needs level {_n(K.INTERDICTOR_MIN_LEVEL)} and burns {_n(K.INTERDICTOR_FUEL)} fuel.</p>"
        + _src("Citadel class cost table and the handbook perk lines (treasury, Quasar, interdictor).")
    )


def _colonists(_f: dict) -> str:
    return (
        f"<p>Terra is in sector {_n(K.STARDOCK_SECTOR)}. It is not a planet, it cannot be claimed, and its colonists are free. "
        f"The pool starts at {_n(K.terra_start_pool())} and regrows {_n(K.TERRA_REGEN_PER_DAY)} a day. "
        f"One hold takes {_n(K.colonists_per_hold())} colonists. Loading them costs {_n(K.TERRA_LOAD_TURNS)} turn.</p>"
        "<p>On a planet, population grows while it is under half the class cap and dies back while it is over half, "
        "when the live production rule is on. Moving colonists between the ship and the planet is an order you give while landed, "
        "and only on a planet you own.</p>"
        + _src("Terra colonist rules (sector 1, free, one turn to load) and the planet population cap.")
    )


def _corporations(_f: dict) -> str:
    return (
        f"<p>T opens the corporate menu. A corporation has a password. "
        f"It can hold up to {_n(K.CORP_MAX_MEMBERS)} members. "
        "Members share the corporation's planets. Creating one, joining one, and the password are on that menu.</p>"
        + _src("Corporation rules: a password, a member cap, and planets the corporation keeps.")
    )


def _alignment(_f: dict) -> str:
    ranks = _table(("Experience", "Rank"), tuple((_n(xp), name) for xp, name in K.RANK_TABLE))
    tiers = _table(("Alignment", "Name"), tuple((_n(score), name) for score, name in K.ALIGNMENT_TIERS))
    return (
        "<p>Experience comes from trades, kills and building. Alignment moves when you dump colonists, "
        "kill, or take other acts the engine scores. The tables below are the ones loaded in this process.</p>"
        + ranks + tiers
        + _src("The engine rank table and alignment tiers.")
    )


def _tax(f: dict) -> str:
    return (
        f"<p>Nightly tax in this process is {_n(f['tax_rate'])} percent of credits you carry over "
        f"{_n(f['tax_over'])}, and only when alignment is at least {_n(f['tax_align'])}.</p>"
        f"<p>The ship bank is at StarDock. Its listed interest is {_n(K.BANK_INTEREST_PCT)} percent. "
        f"A planet treasury, once the citadel has one, pays {_n(K.PLANET_TREASURY_INTEREST_PCT)} percent a day.</p>"
        + _src("v3 tax terms (rate, cash floor, alignment) and the planet treasury interest.")
    )


def _turns(f: dict) -> str:
    from .pages import day_length_hint

    minutes = f["day_seconds"] / 60
    minute_text = str(int(minutes)) if minutes == int(minutes) else f"{minutes:.1f}"
    hint = day_length_hint(f["day_seconds"], f["turns"], f["max_days"])
    return (
        f"<p>You start the day with {_n(f['turns'])} turns. A warp on the starting hull costs {_n(f['tpw'])} of them. "
        f"A day lasts {_n(f['day_seconds'])} seconds ({minute_text} minutes) in this game.</p>"
        f"<p>{escape(hint)}</p>"
        "<p>Under v3.11, turns come back a little at a time all day. The day rolls on the clock, "
        "not when everyone is out of turns. On a longer day the same pocket comes back more slowly.</p>"
        + _src("The game's turn pocket and day length, read from this game's settings when you opened the manual from a game.")
    )


def _disclaimer(_f: dict) -> str:
    items = "".join(f"<li>{escape(point)}</li>" for point in DISCLAIMER_POINTS)
    return (
        "<ul>" + items + "</ul>"
        "<p>This manual describes the game as the engine is configured in this process. "
        "It does not change any rule.</p>"
        + _src("The beta disclaimer shown before you enter a test game.")
    )
