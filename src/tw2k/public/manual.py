"""Player's manual. Server-rendered HTML. Every number is read from the engine at request time."""

from __future__ import annotations

from html import escape

from ..engine import constants as K
from .pages import disclaimer_points

# One anchor per section. The table of contents and the tests both use this list.
SECTIONS: tuple[tuple[str, str], ...] = (
    ("getting-started", "Getting started"),
    ("walkthrough", "First-day walkthrough"),
    ("command-keys", "Command keys"),
    ("moving", "Moving, the course card and Express autopilot"),
    ("trading", "Trading and haggling"),
    ("ports", "Ports and StarDock"),
    ("ship-trade-in", "Ship trade-in"),
    ("combat", "Combat"),
    ("ferrengi", "Ferrengi"),
    ("planets", "Planets"),
    ("citadels", "Citadels"),
    ("colonists", "Colonists and Terra"),
    ("corporations", "Corporations"),
    ("alignment", "Alignment, experience and ranks"),
    ("rankings", "Rankings and the end of the game"),
    ("tax", "Tax, bank and interest"),
    ("turns", "Turns and days"),
    ("hardware", "Hardware"),
    ("stardock-services", "StarDock services"),
    ("communications", "Communications"),
    ("computer-reports", "Computer reports"),
    ("death-and-pods", "Death and escape pods"),
    ("feds-and-ferrengi-v311", "Feds and Ferrengi"),
    ("towing-and-transwarp", "Towing and TransWarp"),
    ("warp-pictures", "Warp pictures"),
    ("ai-opponents", "AI opponents"),
    ("sharing", "Joining from a share link"),
    ("staying-up", "If the computer or the browser stops"),
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
    ("L", "Trader rankings"),
    ("C", "Ship catalog"),
    ("Y", "Planets you own"),
    ("J", "Planet specs"),
    ("D", "Today's log"),
    ("M", "Read mail"),
    ("B", "Backtrack one sector"),
    ("S", "Quick stats"),
    ("E", "Find a known route"),
    ("Q", "Exit the computer"),
)


def _n(value: int | float) -> str:
    if isinstance(value, float) and not value.is_integer():
        return f"{value:,.2f}"
    return f"{int(value):,}"


def _on(flag: bool) -> str:
    return "on" if flag else "off"


def _profile(name: str, on: bool, *, only_v311: bool) -> str:
    """Name a switched rule, say if only the v3.11 profile turns it on, and if it is on here."""
    state = "on" if on else "off"
    who = "Only the v3.11 profile turns this on." if only_v311 else "The v3.11 profile turns this on."
    return f"{name}: {who} In this process it is {state}."


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
    turns_override = getattr(config, "turns_per_day_override", None) if config is not None else None
    credits, turns, fighters = K.opening_loadout(
        K.STARTING_CREDITS, turns_asked, 0, override, turns_override)
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
        "game_length": getattr(config, "game_length", None) if config is not None else None,
        "scoped": config is not None,
        "bust_clear_days": getattr(config, "bust_clear_days", None) if config is not None else None,
        "death_delay": K.death_delay_days(config),
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
        _rules_block(),
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
        "ship-trade-in": _ship_trade_in,
        "combat": _combat,
        "ferrengi": _ferrengi,
        "planets": _planets,
        "citadels": _citadels,
        "colonists": _colonists,
        "corporations": _corporations,
        "alignment": _alignment,
        "rankings": _rankings,
        "tax": _tax,
        "turns": _turns,
        "hardware": _hardware,
        "stardock-services": _stardock_services,
        "communications": _communications,
        "computer-reports": _computer_reports,
        "death-and-pods": _death_and_pods,
        "feds-and-ferrengi-v311": _feds_and_ferrengi,
        "towing-and-transwarp": _towing_and_transwarp,
        "warp-pictures": _warp_pictures,
        "ai-opponents": _ai_opponents,
        "sharing": _sharing,
        "staying-up": _staying_up,
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
    computer = []
    for key, meaning in _COMPUTER:
        if key == "B":
            computer.append((
                "N",
                f"NavPoints. {_n(K.NAVPOINT_SLOTS)} named sectors you already know. Plot uses that known path.",
            ))
            if K.v311_profile():
                meaning = (
                    "Begin Self Destruct. The prompt is ARE YOU SURE CAPTAIN? (Y/N) [N]. "
                    "N or Enter prints Self Destruct Aborted... and changes nothing. Y destroys the ship. "
                    "< returns to the previous sector."
                )
        computer.append((key, meaning))
    return (
        "<p>These are the redesign cockpit keys. They are the original Trade Wars letters. "
        "The same letter can mean a different order while you are landed.</p>"
        + _table(("Key", "What it does"), _KEYS)
        + "<h3>Computer menu</h3><p>Press C first. These letters do not change what a key does in space.</p>"
        + _table(("Key", "What it does"), computer)
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
        + _gated(
            K.haggle_table_live(),
            "a counter follows the cabal product table. Equipment at MCIC -20 takes 110.2 percent, "
            "and fuel at MCIC -90 takes 149.4 percent. A product or MCIC that page does not print keeps the straight line.",
            "every product uses one straight line from 110 percent to 149 percent.",
        )
        + _buy_anchor()
        + _price_scale()
        + _busts(f)
        + _evil_trade_loop()
        + _src("Port haggling notes (HAGGLE.md), the live buy-price anchor, and the bust clear on the day tick.")
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
        + ", sells hardware and ships and holds the bank. "
        + (
            "On the live class map it is shown as Class 9. Its stored id stays 8, and Class 9 in the trade book is still the built SSS port."
            if K.port_class_live()
            else "Its stored class id is 8."
        )
        + " Class 0 is the federal port.</p>"
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
        "<p>No death delay is loaded. A pod can act on the turn you land in it. "
        "A wait of several midnights is not a rule in this process.</p>"
        + _photon_wave()
        + _probes()
        + _src("RULINGS v3.11 section 6 (fighter exchange), Addendum A (the escape pod), "
               "and the photon wave in the hardware rules.")
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
        + _gated(
            K.ferrengi_attack_live(),
            f"a Ferrengi attack sends one volley, at most {_n(K.FERRENGI_FIGHTERS_PER_ATTACK[K.FERRENGI_HULL_ASSAULT])} "
            f"fighters from an Assault Trader, {_n(K.FERRENGI_FIGHTERS_PER_ATTACK[K.FERRENGI_HULL_CRUISER])} from a "
            f"Battle Cruiser, or {_n(K.FERRENGI_FIGHTERS_PER_ATTACK[K.FERRENGI_HULL_DREAD])} from a Dreadnought, "
            "at that hull's odds.",
            "a Ferrengi attack uses three rolls and can send every fighter it has.",
        )
        + _src("Ferrengi encounter rules in the engine: tribute first, then a grudge if you attack. "
               "FERRSPEC fighters per attack.")
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
        + _gated(
            K.planet_zdy_live(),
            f"destroying a planet that another trader is on kills that trader. "
            f"You gain {_n(K.ZDY_EXP_NUM)} experience for each {_n(K.ZDY_EXP_DEN)} of their experience, "
            f"and alignment moves by {_n(K.ZDY_ALIGN_NUM)} the other way for each {_n(K.ZDY_ALIGN_DEN)} of their alignment. "
            f"Blowing the planet is still {_n(K.xp_award('destroy_planet'))} experience and "
            f"{_n(K.PLANET_DESTROY_ALIGNMENT_TW2002)} alignment.",
            "destroying a planet lifts anyone else off it. You do not gain their experience.",
        )
        + _planet_kill()
        + _src("S1 planet handbook class table, the home-planet opening, the Genesis torpedo price, and the cabal planet-kill awards.")
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
        + _gated(
            K.citadel_park_live(),
            "a ship on your own level 1 citadel is parked inside it. A Fed tow skips it, and another trader cannot attack it there.",
            "landing on a citadel leaves the ship in the sector. It is not parked inside.",
        )
        + _gated(
            K.quasar_atm_order_live(),
            "a landing takes one atmosphere shot, and a second only after the last shield falls.",
            "a landing with no shields takes two atmosphere shots before the fight.",
        )
        + _gated(
            K.planet_interdict_safe_live(),
            f"an interdictor does not hold a ship at StarDock. Terra is that sector. "
            f"Anywhere else it still burns {_n(K.INTERDICTOR_FUEL)} fuel.",
            "an interdictor in StarDock holds a ship the same as anywhere else.",
        )
        + _quasar_and_interdictor()
        + _src("Citadel class cost table and the handbook perk lines (treasury, Quasar, interdictor).")
        + _src("Citadel class cost table, the handbook perk lines, the atmosphere shot, and the StarDock interdictor.")
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
        "Members share the corporation's planets. Creating one, joining one, and the password are on that menu. "
        "The C.E.O. leaving ends the corporation.</p>"
        + _corp_leave()
        + _corp_join()
        + _corp_planets()
        + _src("Corporation menu, the v3.11 leave and join rules, and the planet rule loaded for a disbanded corporation.")
    )


def _corp_leave() -> str:
    if K.corp_leaver_to_ceo():
        body = (
            "Fighters and mines you deployed for the corporation move to the C.E.O. when you leave. "
            "The corporation mark stays on them. Fighters and limpets that were only yours stay yours. "
            "Fighters outside the C.E.O.'s sector go rogue when the C.E.O. leaves and the corporation ends."
        )
    else:
        body = (
            "Fighters and mines you deployed for the corporation keep your name on them when you leave. "
            "They do not move to the C.E.O."
        )
    return (
        f"<p>{_profile('Fighters to the C.E.O. when a member leaves', K.corp_leaver_to_ceo(), only_v311=True)} "
        f"{body}</p>"
    )


def _corp_join() -> str:
    rule = K.corp_alignment_rule()
    if rule == "join_check":
        join = (
            "A join is refused when your alignment and the C.E.O.'s have opposite signs. "
            "Alignment 0 fits either side. A member who later changes sign is not removed."
        )
    elif rule == "same_side":
        join = (
            "A join is refused unless you are on the same alignment side as the C.E.O. "
            "Alignment 0 counts as good."
        )
    else:
        join = "Good and evil traders may join the same corporation."
    if rule == "same_side":
        penalty = (
            "A member whose alignment side no longer matches the C.E.O. is removed. "
            "The mixed-corp experience loss does not run."
        )
    else:
        divisor = int(K.MIXED_CORP_EXP_DIVISOR)
        floor = int(K.MIXED_CORP_EXP_FLOOR)
        if K.mixed_corp_least_extreme():
            formula = (
                "the smaller of the highest good alignment and the strongest evil alignment, "
                f"divided by {_n(divisor)}"
            )
        else:
            formula = f"the highest good alignment, divided by {_n(divisor)}"
        penalty = (
            f"{_profile('Least-extreme mixed-corp experience', K.mixed_corp_least_extreme(), only_v311=True)} "
            "When the corporation has both a good member and an evil member, every alive member "
            f"loses experience at the next day. The loss is {formula}. "
            f"Experience does not go below {_n(floor)}."
        )
    if K.corp_breakin_align_live():
        breakin = (
            "The first wrong corporation password in a day costs 1 alignment. "
            "Experience does not change. A later wrong password that day does not."
        )
    else:
        breakin = "A wrong corporation password does not change alignment."
    return (
        f"<p>{_profile('Alignment join check', rule == 'join_check', only_v311=True)} {join}</p>"
        f"<p>{penalty}</p>"
        f"<p>{_profile('Corp break-in alignment', K.corp_breakin_align_live(), only_v311=False)} {breakin}</p>"
    )


def _corp_planets() -> str:
    if K.CORP_LEAVER_PLANETS == "leaver_keeps":
        leave = "Planets you owned stay yours when you leave, and they leave the corporation."
    else:
        leave = (
            "Planets you owned for the corporation become the C.E.O.'s when you leave. "
            "You do not keep them."
        )
    v306 = K.corp_planet_disband_v306()
    if v306:
        end = (
            "When the corporation ends, planets in the C.E.O.'s sector become the C.E.O.'s. "
            "Every other corporation planet is unclaimed."
        )
    else:
        end = (
            "When the corporation ends, a planet stays with its owner if that owner is still playing. "
            "A planet whose owner is gone is unclaimed."
        )
    return (
        f"<p>{leave} {_profile('Corp planet disband', v306, only_v311=False)} {end}</p>"
    )


def _alignment(_f: dict) -> str:
    if K.rank_tw2002():
        rows = [
            (_n(thresh), good, evil)
            for thresh, good, evil in zip(K.RANK_THRESHOLDS, K.GOOD_RANKS, K.EVIL_RANKS, strict=True)
        ]
        tables = (
            "<p>Zero alignment or above uses the good title. Below zero uses the evil title. "
            "Below 2 experience the title is Civilian.</p>"
            + _table(("Experience", "Good title", "Evil title"), rows)
        )
    else:
        tables = (
            _table(("Experience", "Rank"), [(_n(xp), name) for xp, name in K.RANK_TABLE])
            + _table(("Alignment", "Name"), [(_n(score), name) for score, name in K.ALIGNMENT_TIERS])
        )
    return (
        "<p>Experience comes from trades, kills and building. Alignment moves when you dump colonists, "
        "kill, or take other acts the engine scores. The tables below are the ones loaded in this process. "
        "This rank table follows the rank mode loaded in this process. It is not a v3.11-only switch.</p>"
        + tables
        + _src("The engine rank table. Under the tw2002 rank mode the good and evil titles are separate.")
    )


def _rankings(f: dict) -> str:
    from ..engine.victory import end_rule_line

    if K.trader_rank_list_live():
        listing = (
            "Game status lists every trader by experience: place, name, title, experience, corporation, "
            "ship, and whether they are alive. It does not show credits, net worth, or where they are."
        )
    else:
        listing = "The list of every trader by experience is not published."
    if K.nw_estimate_live():
        worth = (
            f"The net-worth note on that screen is: {K.NW_ESTIMATE_NOTE} "
            "It does not change who wins."
        )
    else:
        worth = "The paid-cargo net-worth note is not shown."
    return (
        f"<p>{escape(end_rule_line(int(f['max_days'])))}</p>"
        f"<p>{_profile('Experience ranking of every trader', K.trader_rank_list_live(), only_v311=False)} "
        f"{listing}</p>"
        "<p>When the day cap ends the game, the screen starts "
        "GAME OVER - time ran out after the last day, then the places and the measure, "
        "experience or net worth.</p>"
        "<p>v3.11 ranks traders by experience. Net worth has no printed formula. "
        "The day cap, the last player standing, the credit bar, and a creator end stay, "
        "because no v3.11 page prints a number for them. "
        "The end announcement is that GAME OVER panel. "
        "A 155-character player line is the communications rule.</p>"
        f"<p>{_profile('Paid-cargo net-worth note', K.nw_estimate_live(), only_v311=False)} {worth}</p>"
        + _creator_end()
        + _src("The end rule and the end screen are built by the victory code. "
               "The creator end is a lobby and cockpit control, not a profile switch.")
    )


def _creator_end() -> str:
    return (
        "<p>The person who created the game can end it for everyone before the day cap. "
        "On the lobby the button says End game. On the redesign cockpit, in that creator's own seat, "
        "the button says End game for everyone. The game asks you to confirm. "
        "The end screen says GAME OVER - Ended by the game's creator. "
        "Places use the same measure as a day-cap finish. "
        "This is not a v3.11-only rule.</p>"
    )


def _ship_trade_in(f: dict) -> str:
    credit = int(K.trade_in_credit(K.STARTING_SHIP))
    pct = round(K.trade_in_fraction() * 100)
    if K.trade_in_parts_live():
        receipt = K.trade_in_receipt(K.STARTING_SHIP)
        body = (
            "The yard credits the old ship part by part: hull, holds, drive, computer, fighters, shields, "
            "and a density or holo scanner. Mines and other gear are not on the receipt. "
            f"Each part pays 90 percent of its catalog price, and one credit less when that tenth is exact. "
            f"A catalog price of 10,000 credits pays {_n(K.part_trade_credit(10_000))}. "
            f"Fighters use a catalog of {_n(K.FIGHTER_TRADE_CATALOG)} each. "
            f"Shields use a catalog of {_n(K.SHIELD_TRADE_CATALOG)} each. "
            f"The starting {escape(f['ship'])}, empty, credits {_n(receipt['hull'])} for the hull, "
            f"{_n(receipt['holds'])} for {_n(receipt['hold_count'])} holds, "
            f"{_n(receipt['drive'])} for the drive and {_n(receipt['computer'])} for the computer. "
            f"The total is {_n(receipt['total'])}."
        )
        pod = "An escape pod is priced as the parts on it."
    else:
        body = (
            f"The yard pays {pct} percent of the hull's sticker price. "
            f"The starting {escape(f['ship'])} is worth {_n(credit)} credits toward the next ship. "
            "Holds, fighters and shields on the old ship are not itemised."
        )
        pod = "An escape pod is priced as a Scout Marauder."
    if K.trade_in_live():
        surplus = "If that credit is more than the next hull, the yard pays you the difference."
    else:
        surplus = "A credit larger than the next hull is not paid back."
    return (
        f"<p>{body} {surplus} {pod}</p>"
        f"<p>{_profile('Part-by-part trade-in', K.trade_in_parts_live(), only_v311=False)} "
        f"{_profile('Trade-in surplus', K.trade_in_live(), only_v311=False)}</p>"
        + _src("The shipyard trade-in. Parts mode itemises the ship. The surplus gate is the live trade-in fraction.")
    )


def _buy_anchor() -> str:
    anchors = K.PORT_PRICE_LIVE_BUY_FULL
    hungry = (
        f"fuel {_n(anchors['fuel_ore'])}, organics {_n(anchors['organics'])}, "
        f"equipment {_n(anchors['equipment'])}"
    )
    if K.port_price_live() and K.port_buy_price_anchor_on():
        body = (
            f"A port that buys from you, when it is empty, pays these hungry quotes: {hungry}. "
            f"As the hold fills, the quote eases by {_n(K.PORT_BUY_FILL_EASE)} times how full it is. "
            "A full port pays less than a hungry one. A federal port stays at the base price."
        )
    elif K.port_price_live():
        body = (
            f"The live price anchors are {hungry}, and a buying port pays that anchor only when its hold is full. "
            "A hungry port quotes higher. The hungry-quote anchor is off."
        )
    else:
        body = (
            "Buying-port prices use the older stock curve. "
            f"The hungry quotes {hungry} are not applied."
        )
    return (
        f"<p>{_profile('Hungry buy-price anchor', K.port_buy_price_anchor_on(), only_v311=False)} {body}</p>"
    )


def _price_scale() -> str:
    """GAP 2.5. The chart totals are per 250 holds; the page prints the nearest credit."""
    if K.price_scale_live():
        sell = {k: K.price_scale_unit(v) for k, v in K.PRICE_SCALE_SELL_250.items()}
        buy = {k: K.price_scale_unit(v) for k, v in K.PRICE_SCALE_BUY_250.items()}
        body = (
            "A full selling port at MCIC 50, experience 0, asks the economy2 chart: "
            f"fuel {_n(sell['fuel_ore'])}, organics {_n(sell['organics'])}, "
            f"equipment {_n(sell['equipment'])} a hold. "
            "An empty buying port at MCIC -50 pays "
            f"fuel {_n(buy['fuel_ore'])}, organics {_n(buy['organics'])}, "
            f"equipment {_n(buy['equipment'])}. "
            "Those are the 250-hold chart totals, rounded to a whole credit a hold. "
            "Stock, MCIC, and experience still move the quote from that point."
        )
    else:
        body = "Port quotes stay on the current stock curve. The economy2 chart totals are not the quote."
    return (
        f"<p>{_profile('Chart price scale', K.price_scale_live(), only_v311=False)} {body}</p>"
    )


def _busts(f: dict) -> str:
    on = K.rob_tw2002() and K.bust_record_clear_live()
    days = f.get("bust_clear_days")
    if not K.rob_tw2002():
        rule = "Port busts are not in force."
    elif not on:
        rule = (
            "A bust blocks trade, rob, and steal at that port until the next day. "
            "Every day clears every bust. A game setting of 7 is ignored."
        )
    elif days == 7:
        rule = (
            "A bust blocks trade, rob, and steal at that port until the records clear. "
            "This game clears bust records every 7 days, when the day number is a multiple of 7."
        )
    elif days == 1:
        rule = (
            "A bust blocks trade, rob, and steal at that port until the next day. "
            "This game clears bust records every 1 day."
        )
    else:
        rule = (
            "A bust blocks trade, rob, and steal at that port until the records clear. "
            "No interval is set, so bust records clear every day. "
            "A game can set the interval to 1 or to 7. "
            "7 clears when the day number is a multiple of 7."
        )
    return f"<p>{_profile('Bust-clear interval', on, only_v311=False)} {rule}</p>"


def _evil_trade_loop() -> str:
    floor = _n(K.ROB_MIN_ALIGNMENT)
    if K.evil_trade_loop_live():
        body = (
            f"A trader at alignment {floor} or lower steals equipment, lands, and dumps it, "
            "then beams to another of their ships. With no equipment to steal, they rob, then beam. "
            f"A steal is at most experience divided by {_n(K.STEAL_HOLD_DIVISOR)} holds. "
            f"A rob is at most experience times {_n(K.ROB_CREDIT_FACTOR)} credits. "
            "Cargo stays aboard until it is dumped or sold. Beaming does not carry it."
        )
    else:
        body = (
            "The steal-dump-transport and rob-transport loops are off. "
            "Rob and steal still follow the port rules already loaded."
        )
    return f"<p>{_profile('Evil trade loops', K.evil_trade_loop_live(), only_v311=False)} {body}</p>"


def _photon_wave() -> str:
    days = int(K.PHOTON_WAVE_DURATION)
    span = "the next day" if days == 1 else f"{_n(days)} days"
    if K.hardware_tw2002():
        body = (
            "A photon fired into the next sector, Computer then P, shuts that sector's armid mines and fighters "
            f"until {span}. "
            "The shooter, and anyone already in that sector, is marked so the planet quasar does not fire, "
            f"unless the citadel is level 5 or higher and has at least {_n(K.QUASAR_PHOTON_SHIELD_MIN)} shields. "
            "A ship that was not there, and enters while the wave is still up, still faces the quasar. "
            "NavHaz can still hit."
        )
        state = "on"
    else:
        body = "The photon wave that shuts mines and fighters is not in force."
        state = "off"
    return (
        f"<p>{body} This is the hardware rule already loaded. It is not a v3.11-only switch. "
        f"In this process it is {state}.</p>"
        + _gated(
            K.photon_limpet_live(),
            "a limpet still attaches while that wave is up. Armid mines still do not detonate.",
            "a limpet does not attach while that wave is up.",
        )
    )


def _probes() -> str:
    on = K.ship_chart_cap_live()
    if on:
        cap = f"A ship stops at {_n(K.PROBE_CHART_MAX)} ether probes. One more is refused."
    else:
        cap = "No maximum number of ether probes is loaded on a ship."
    return (
        f"<p>An ether probe costs {_n(K.ether_probe_cost())} credits. "
        f"{_profile('Ether probe cap', on, only_v311=False)} {cap}</p>"
    )


def _tax(f: dict) -> str:
    return (
        f"<p>Nightly tax in this process is {_n(f['tax_rate'])} percent of credits you carry over "
        f"{_n(f['tax_over'])}, and only when alignment is at least {_n(f['tax_align'])}.</p>"
        f"<p>The ship bank is at StarDock. Its listed interest is {_n(K.BANK_INTEREST_PCT)} percent. "
        f"A planet treasury, once the citadel has one, pays {_n(K.PLANET_TREASURY_INTEREST_PCT)} percent a day.</p>"
        + _src("v3 tax terms (rate, cash floor, alignment) and the planet treasury interest.")
    )


def _full_length_copy(max_days: int | None, active: bool) -> str:
    """v3.11 sysop turns-per-day, and how a longer game lowers the daily limit."""
    cap = int(K.FULL_LENGTH_TURNS_PER_DAY)
    days = int(K.FULL_LENGTH_REFERENCE_DAYS)
    budget = cap * days
    floor = int(K.TURNS_OVERRIDE_MIN)
    this = ""
    if active and max_days:
        mine = K.full_length_daily_cap(int(max_days))
        this = (
            f"<p>This game is full-length: {_n(int(max_days))} days, "
            f"{_n(mine)} turns per day, and a day of {_n(int(K.FULL_LENGTH_DAY_SECONDS))} seconds.</p>"
        )
    return (
        "<p>Full-length games use a 24-hour day and the v3.11 sysop turn limit of "
        f"{_n(cap)} turns per day. A game of {_n(days)} days or fewer keeps that {_n(cap)}. "
        f"A longer game lowers the daily limit so the whole game stays near {_n(budget)} turns "
        f"({_n(days)} times {_n(cap)}), and the limit never goes below {_n(floor)}. "
        "Fast test days keep the day length and the turn pocket already chosen for the game.</p>"
        + this
        + _src(
            "Cabal glossary Classic: 1,000 sectors and 250 turns per day. "
            "RULINGS s2 uses the same 250. "
            "Gypsy's Big Dummy's Guide lists 750 turns for one sample game; that sample is not this default."
        )
    )


def _turns(f: dict) -> str:
    from .pages import day_length_hint

    minutes = f["day_seconds"] / 60
    minute_text = str(int(minutes)) if minutes == int(minutes) else f"{minutes:.1f}"
    hint = day_length_hint(f["day_seconds"], f["turns"], f["max_days"])
    show = f.get("game_length") == "full" or K.full_length_turn_limits_on()
    extra = _full_length_copy(f.get("max_days"), f.get("game_length") == "full") if show else ""
    length = (
        "<p>Game length is the host setting FULL_LENGTH_TURN_LIMITS_MODE. "
        "Only the value v311 turns it on. The string 1 does not, and the v3.11 profile does not. "
        "It is not one of the profile switches. "
        "While it is off, the new-game form has no Game length field, and a stored full day does not change the turn pocket. "
        "While it is on, the host picks Fast test days or a 24-hour day. "
        "On a 24-hour game the redesign cockpit shows Turns left today: the turns you have left, of the daily limit. "
        f"Classic Trade Wars 2002 v3.11 used a 24-hour day and a sysop limit of {_n(K.FULL_LENGTH_TURNS_PER_DAY)} turns. "
        "A fast test day is this beta's shorter clock. "
        "Open this page from a 24-hour game to see that game's day count and daily limit.</p>"
    )
    return (
        f"<p>You start the day with {_n(f['turns'])} turns. A warp on the starting hull costs {_n(f['tpw'])} of them. "
        f"A day lasts {_n(f['day_seconds'])} seconds ({minute_text} minutes) in this game.</p>"
        f"<p>{escape(hint)}</p>"
        + length
        + extra
        + _day_clock()
        + _dawn_refill()
        + _src("The game's turn pocket and day length, read from this game's settings when you opened the manual from a game.")
    )


def _day_clock() -> str:
    if K.turn_regen_live():
        regen = (
            "Spent turns come back across the day and never past the daily allowance. "
            "A new day does not refill the whole pocket at once. "
            "On a longer day the same pocket comes back more slowly."
        )
    else:
        regen = "A new day refills every turn. Turns do not trickle back during the day."
    if K.day_roll_clock_live():
        clock = (
            "The day rolls when the clock mark passes, even while a seat still holds its turn. "
            "The next mark is the old mark plus the day length."
        )
    else:
        clock = "The day does not roll while a seat holds its turn."
    legacy = ""
    if K.legacy_day_clock_live() and not K.day_roll_clock_live():
        legacy = (
            "<p>A legacy game that has its own day length rolls that day on the clock, "
            "even while a seat holds its turn. Dawn refills the turns. "
            "With no day length the day waits until every seat is done.</p>"
        )
    return (
        f"<p>{_profile('Turn regen across the day', K.turn_regen_live(), only_v311=False)} {regen}</p>"
        f"<p>{_profile('Day roll while a seat holds the turn', K.day_roll_clock_live(), only_v311=True)} {clock}</p>"
        f"{legacy}"
    )


def _ai_opponents(_f: dict) -> str:
    return (
        "<p>A lobby game can add AI opponents next to the code bots when the host has turned that option on. "
        "Each AI seat plays through the same cockpit a person uses. It does not look at the game's private data.</p>"
        "<p>The brain for each of those seats is Heuristic (free) or LLM (your key). "
        "Heuristic needs no key. LLM is bring your own key: you paste an API key and an endpoint URL for that game. "
        "The server never pays for a model and never ships a key.</p>"
        "<p>What is kept: the number of AI seats and which brain you picked. "
        "What is not kept: the key and the endpoint stay in the server's memory for that game only. "
        "They are not written to disk, saves, logs, the spectator feed, error pages, or the admin page. "
        "A log line shows key **** and the last four characters. "
        "After you submit, the key is not sent back to any browser. "
        "The key is dropped when the game ends or the server restarts. "
        "The seat then plays the heuristic brain, and the cockpit says so.</p>"
        "<p>AI seats are labelled AI (heuristic) or AI (LLM) in the lobby, the rankings, the end screen, "
        "and the trader list. The seat timer and the day clock treat them like any seat. "
        "An AI seat posts no faster than the server's per-seat action limit. "
        "The new-game form shows an estimate of model calls per game day for the pace you picked. "
        "There is a per-game call cap and a per-minute limit. Past either one, or if the endpoint errors, "
        "the seat plays the heuristic brain.</p>"
        + _computer_levels()
        + '<p class="note">Hosting notes for this option live with the lobby, not in the v3.11 rule set.</p>'
    )


def _planet_kill() -> str:
    """NOTE 143. PLANET_ZDY_MODE is not loaded in this process. The awards are the cabal figures."""
    blow_exp = _n(K.xp_award("destroy_planet"))
    blow_align = _n(K.PLANET_DESTROY_ALIGNMENT_TW2002)
    return (
        "<p>Destroying a planet that another trader is on is the switch PLANET_ZDY_MODE. "
        "The value v311 turns it on, and so does the v3.11 profile. The string 1 does not. "
        "While it is on, that trader is killed. You gain 1,666 experience for each 10,000 of their experience, "
        f"and alignment moves the other way by 3,333 for each 10,000 of their alignment. "
        f"Blowing the planet is still {blow_exp} experience and {blow_align} alignment. "
        "While it is off, destroying a planet lifts anyone else off it. You do not gain their experience. "
        "Classic Trade Wars 2002 v3.11 pods that trader and pays those two products on top of the blow.</p>"
    )


def _quasar_and_interdictor() -> str:
    """NOTE 143. The two citadel switches are not loaded in this process."""
    return (
        "<p>The order of an atmosphere shot is QUASAR_ATM_ORDER_MODE. "
        "The value v311 turns it on, and so does the v3.11 profile. The string 1 does not. "
        "While it is on, a landing takes one atmosphere shot, and a second only after the last shield falls. "
        "While it is off, a landing with no shields takes two atmosphere shots before the fight. "
        "Classic Trade Wars 2002 v3.11 uses the one-shot order.</p>"
        "<p>An interdictor at StarDock is PLANET_INTERDICT_SAFE_MODE. "
        "The value v311 turns it on, and so does the v3.11 profile. The string 1 does not. "
        f"While it is on, an interdictor does not hold a ship at StarDock, sector {_n(K.STARDOCK_SECTOR)}. "
        "Terra's colonists are in that sector, so the generator is quiet there. "
        f"Anywhere else it still burns {_n(K.INTERDICTOR_FUEL)} fuel, and the sector cannon can still fire. "
        "While it is off, an interdictor in StarDock holds a ship the same as anywhere else. "
        "Classic Trade Wars 2002 v3.11 leaves the generator quiet at StarDock and Terra.</p>"
    )


def _comms_panel() -> str:
    """NOTE 142 and NOTE 145. Always names COMMS_V311_MODE and both switch states."""
    return (
        "<p>The redesign cockpit has a Comms panel on the deck. It is the turn log, labeled Comms, and the send form. "
        "You see that form when COMMS_V311_MODE is v311. The v3.11 profile turns that switch on. The string 1 does not. "
        "While COMMS_V311_MODE is off, the send form stays hidden. You read mail with Y, a direct hail is its own order, "
        "and a hail is filed as mail. "
        "The older cockpit page does not show this panel. Its Comms card stays the inbox and the diplomacy list.</p>"
        "<p>While the panel is on, messages show at the start of your turn and last "
        f"{_n(K.HAIL_SHOW_SECONDS)} seconds. A line is {_n(K.COMMS_LINE_MAX)} characters. You wait 2 seconds between sends. "
        "The form is To, then Message, then Send. To is Fed Comm, Sub-space radio, Hail, or Corporation. "
        f"Sub-space radio uses a channel from 1 to {_n(K.RADIO_CHANNEL_MAX)}. "
        "Everyone tuned to that channel hears it. Channel 0 turns the radio off, and that is how you start. Tune sets the channel. "
        "Fed Comm goes to every trader who has not turned it off. The Fed Comm button turns that listening on or off. "
        "A hail goes to one trader in your sector and is not stored as mail. "
        "If that trader is away, or has turned hails off, you see that it fell on deaf ears. "
        "A corporation memo goes only to the other members. "
        "What you typed is shown as text, so a tag or an ampersand stays visible.</p>"
        "<p>An AI cockpit seat reads those lines on the same panel. "
        "It answers a hail or a corporation memo with Send. The reply is a short line. "
        "It waits 2 seconds between messages and stops after a few sends. "
        "It may send one corporation memo about its plan. "
        "It does not treat your message as an instruction, and it does not repeat it back.</p>"
        "<p>Classic Trade Wars 2002 v3.11 uses those four messages: sub-space radio, Fed Comm, a private hail, and a corporation memo. "
        "A hail there is not stored as mail. Channel 0 is off. "
        "The older path on this page, while the switch is off, still files a hail as mail and keeps corporation radio to corp mates. "
        "A computer player that answers on the panel is not part of classic Trade Wars.</p>"
    )


def _warp_pictures(_f: dict) -> str:
    return (
        "<p>On the redesign cockpit, a short picture of your ship plays when the ship actually moves. "
        "A warp that changes sector plays one. An autopilot that finishes at least one hop plays one. "
        "Plotting a course does not. A refused warp does not. Another trader's move does not play on your screen.</p>"
        "<p>Each ship type has ten pictures. The game picks one at random and does not play that same picture twice in a row. "
        "The ten pictures differ in the camera angle, the star streaks, the engine glow color and length, and the exit flash. "
        "They are drawn for this cockpit. They are not the old Trade Wars ship art.</p>"
        "<p>The viewport buttons are Live, Stills, and Off. Live plays the picture. "
        "Stills is the pause: one frame, and no motion. "
        "Off leaves the viewport dark and does not count a play, even if the ship moves. "
        "Skip hides the picture.</p>"
        "<p>You see these pictures when the cockpit layout is the redesign. "
        "The page query layout=redesign asks for that layout. "
        "There is no profile switch for them. The v3.11 profile does not turn them on or off. "
        "The older cockpit page does not play them.</p>"
        "<p>Classic Trade Wars 2002 v3.11 does not animate a warp. A successful move is a new sector listing in text.</p>"
        + _src("The redesign warp pictures. Original cockpit art, not the Trade Wars shipyard drawings.")
    )


def _computer_levels() -> str:
    return (
        "<h3>Levels of play</h3>"
        "<p>Computer players are still being tuned. This page does not pin a route, a daily profit, or a rank they are meant to reach.</p>"
        "<p>Code bots are the count on the new-game form. They trade and fight inside the game. They do not open a cockpit. "
        "How sharp a code bot is is still being tuned.</p>"
        f"<p>AI opponents are {_on(K.lobby_ai_seat_on())} in this process. "
        "That option is LOBBY_AI_SEAT_MODE. Only the value on turns it on. The v3.11 profile does not. "
        "Heuristic plays from the facts a seat is allowed to see and needs no key. "
        "An LLM seat uses the key the host pasted for that game. "
        "Both are labelled in the trader list. Their tactics are still being tuned.</p>"
        f"<p>An AI cockpit seat is {_on(K.ai_cockpit_seat_on())} in this process. "
        "That option is AI_COCKPIT_SEAT_MODE. The value tw2002 turns it on. The v3.11 profile does not. "
        "The seat opens the same redesign cockpit you do and reads this manual before it trades. "
        "Scripted play uses the buttons on the screen. "
        "Grok, OpenAI, or Anthropic does the same when a key is set for that run. "
        "An empty key does not call the model. The seat plays the scripted trader, and the log names the missing variable without printing a key. "
        "On the Comms panel, when that panel is on, it can answer as the Communications section says. "
        "How hard it trades is still being tuned.</p>"
        "<p>Classic Trade Wars 2002 v3.11 had no computer player that opened a cockpit. "
        "Ferrengi are aliens, covered in their own section. None of these seats is a profile switch.</p>"
    )


def _sharing(_f: dict) -> str:
    return (
        "<p>A host can share a game that is already running. The share command opens a temporary public address and points it at the lobby. "
        "It does not start the game, stop it, or restart it.</p>"
        "<p>You open an https address that ends in trycloudflare.com. "
        "The lobby link is the front door. A seat link names the game, the seat, and the token, and it asks for the redesign cockpit with layout=redesign. "
        "The token is the password for that seat. Send each seat link to one person. "
        "Treat the link like a password. Do not put it on a public page.</p>"
        "<p>The public address changes every time the host starts the share again. The game on the host computer is the same game. "
        "An old link stops opening. The admin page stays on the host computer. A request through the public address does not get it. "
        "Closing the share window stops the public address. The game keeps running.</p>"
        "<p>There is no profile switch for the share link. The v3.11 profile does not turn it on. "
        "Classic Trade Wars 2002 v3.11 was a bulletin board. It did not hand out a public web address.</p>"
        + _src("The beta share link. A temporary public address for a lobby that is already running.")
    )


def _staying_up(_f: dict) -> str:
    return (
        "<p>The rules table marks this section off. The lobby on this computer is not saving games across a restart yet. "
        "When that save is on, this is what you see.</p>"
        "<p>The lobby saves while people are playing. A save happens when the day changes, again shortly after someone moves, "
        "and every few minutes if the game is quiet.</p>"
        "<p>If the host starts the lobby again, the games that were still going are on the list. "
        "The same seat link still works, token and all. You do not make a new link for the same seat. "
        "A 24-hour day keeps going from the saved mark. It does not start that day over.</p>"
        "<p>If your browser drops, the redesign cockpit shows Lost the host. Reconnecting. "
        "It waits half a second, then a second, then longer, up to 15 seconds, and it loads your seat again when the host answers. "
        "You do not refresh the page. A refused command does not stop that retry. "
        "The older cockpit page is unchanged.</p>"
        "<p>The AI cockpit seat comes back with the game. You do not press anything to start that seat again.</p>"
        "<p>If a save cannot be read, the lobby stays open. It tries the save before that one first. "
        "When none of them can be read, it says that game's save could not be read, and it does not start that game. "
        "You do not get a crash page.</p>"
        "<p>There is no profile switch for this. The v3.11 profile does not turn it on. "
        "Classic Trade Wars 2002 v3.11 kept its own save on the bulletin board. "
        "This is how this beta comes back after a restart.</p>"
        + _src("The beta save and the redesign reconnect. Not a Trade Wars rule.")
    )


def _disclaimer(_f: dict) -> str:
    items = "".join(f"<li>{escape(point)}</li>" for point in disclaimer_points())
    return (
        "<ul>" + items + "</ul>"
        "<p>This manual describes the game as the engine is configured in this process. "
        "It does not change any rule.</p>"
        + _src("The beta disclaimer shown before you enter a test game.")
    )


def _gated(on: bool, live: str, old: str) -> str:
    """One sentence for a switched rule. A v3.11 page always says so, even when that helper is off."""
    if K.v311_profile():
        sentence = f"in v3.11 games, {live if on else old}"
    elif on:
        sentence = f"In this game, {live}"
    else:
        sentence = f"In legacy games, {old}"
    return f"<p>{sentence}</p>"


def _mode(flag: bool, *, follows_profile: bool) -> str:
    if not follows_profile:
        return "on" if flag else "off"
    if K.v311_profile() and flag:
        return "v3.11"
    if flag:
        return "on"
    return "legacy"


def _rules_block() -> str:
    profile = "v3.11" if K.v311_profile() else "legacy"
    rows: list[tuple[str, str]] = [("Profile", profile)]
    flags: dict[str, tuple[bool, bool]] = {
        "getting-started": (K.starting_package_live(), True),
        "walkthrough": (K.home_planet_live(), True),
        "command-keys": (True, False),
        "moving": (K.course_max_live(), True),
        "trading": (K.haggle_live(), True),
        "ports": (K.port_class_live(), True),
        "ship-trade-in": (K.trade_in_live(), True),
        "combat": (K.offensive_clash_held(), True),
        "ferrengi": (K.ferrengi_engage_on(), True),
        "planets": (K.planet_prod_live(), True),
        "citadels": (K.citadel_park_live(), True),
        "colonists": (K.terra_colonist_live(), True),
        "corporations": (K.corp_rank_live(), True),
        "alignment": (K.discovery_exp_live(), True),
        "rankings": (K.exp_score_live(), True),
        "tax": (K.tax_v311(), True),
        "turns": (K.turn_regen_live(), True),
        "hardware": (K.planet_scanner_live(), True),
        "stardock-services": (K.ship_rename_live(), True),
        "communications": (K.radio_channel_live(), True),
        "computer-reports": (K.daily_stats_live(), True),
        "death-and-pods": (K.death_pod_live(), True),
        "feds-and-ferrengi-v311": (K.fed_ships_live(), True),
        "towing-and-transwarp": (K.tow_on() and K.ship_tw_on(), False),
        "warp-pictures": (True, False),
        "ai-opponents": (True, False),
        "sharing": (True, False),
        "staying-up": (False, False),
        "disclaimer": (True, False),
    }
    for sid, title in SECTIONS:
        flag, follows = flags[sid]
        rows.append((title, _mode(flag, follows_profile=follows)))
    return (
        '<section id="rules-in-this-game"><h2>Rules in this game</h2>'
        "<p>The profile row names the rule set for this game. "
        "A section marked v3.11 follows the v3.11 rule. Legacy means that rule is the older one. "
        "On means the rule is already what a normal game does.</p>"
        + _table(("Item", "Mode"), rows)
        + "</section>"
    )


def _dawn_refill() -> str:
    if K.turn_regen_live():
        return _gated(
            True,
            "dawn does not refill the whole pocket. Spent turns come back across the day and stop at the daily allowance.",
            "dawn refills every turn.",
        )
    return _gated(
        False,
        "dawn does not refill the whole pocket.",
        "dawn refills every turn you spent. Turns do not trickle back during the day.",
    )


def _cap(class_key: str, item: str) -> str:
    room = K.equip_room(class_key, item, 0)
    if room is None:
        return "no cap"
    return _n(room)


def _hardware(f: dict) -> str:
    ship = K.STARTING_SHIP
    name = escape(f["ship"])
    prices = K.hardware_v2_prices()
    probe_cap = _cap(ship, "ether_probes")
    rows = [
        ("Cloak", _n(K.CLOAK_COST), _cap(ship, "cloak")),
        ("Corbomite", _n(prices.get("corbomite", K.CORBOMITE_COST)), _cap(ship, "corbomite")),
        ("Mine disruptor", _n(K.disruptor_cost()), _cap(ship, "mine_disruptor")),
        ("Marker beacon", _n(prices.get("marker_beacon", K.BEACON_COST)), _cap(ship, "marker_beacon")),
        ("Ether probe", _n(K.ether_probe_cost()), probe_cap),
        ("Photon missile", _n(K.PHOTON_MISSILE_COST), _n(int((K.hull_spec(ship) or {}).get("max_photons") or 0))),
        ("Density scanner", _n(K.scanner_cost("density_scanner")), "one scanner"),
        ("Holo scanner", _n(K.scanner_cost("holo_scanner")), "one scanner, replaces density"),
        ("Planet scanner", _n(K.PLANET_SCANNER_COST) if K.planet_scanner_live() else "not sold", _cap(ship, "planet_scanner")),
    ]
    limpet = (
        f"<p>Limpet removal is a service at StarDock or a Class 0 port, not an item you carry. "
        f"The fee is {_n(K.LIMPET_REMOVAL_COST)} credits and it clears every limpet on your ship.</p>"
    )
    scanner = _gated(
        K.planet_scanner_live(),
        f"StarDock sells a planet scanner for {_n(K.PLANET_SCANNER_COST)} credits. "
        "It shows the fighters on a planet that has no shields. A shielded planet stays dark.",
        "StarDock does not sell a planet scanner. Planet fighters stay visible without one.",
    )
    fog = _gated(
        K.scanner_fog_live(),
        "until you land, or until a planet scanner reads an unshielded planet, the owner, fighters and shields stay hidden.",
        "a sector list still names a planet's owner, and the owner still sees fighters without landing.",
    )
    return (
        f"<p>Prices and caps below are for the starting hull, the {name}. "
        "Another hull uses its own chart. A cap of 0 means this hull cannot carry that item.</p>"
        + _table(("Item", "Price", "Cap on the starting hull"), rows)
        + limpet
        + "<p>An ether probe flies the lanes toward the sector you name and stops at the first hostile fighters.</p>"
        + _gated(
            K.probe_shootdown_live(),
            "the report names who owned the fighters that destroyed the probe.",
            "the report says the probe was destroyed. It does not name who owned the fighters.",
        )
        + scanner
        + fog
        + _gated(
            K.photon_follow_damp_live(),
            "a ship that enters a sector while a photon wave is up also has the planet quasar damped.",
            "a ship that was not in the sector when the photon fired still faces the quasar.",
        )
        + _src("StarDock hardware prices and per-ship caps, read from the engine for the starting hull.")
    )


def _stardock_services(f: dict) -> str:
    rename = _gated(
        K.ship_rename_live(),
        f"the shipyard changes this ship's name and registration for {_n(K.SHIP_RENAME_COST)} credits. "
        f"The name can be {_n(K.SHIP_RENAME_NAME_MAX)} characters.",
        "the shipyard does not sell a new name or registration.",
    )
    bust_days = f.get("bust_clear_days")
    if K.bust_record_clear_live() and bust_days in (1, 7):
        bust_live = f"Police clear bust records every {_n(int(bust_days))} day, when that switch is on."
    else:
        bust_live = (
            "Police can clear bust records every day, or every 7 days when the game sets that interval. "
            "With no interval set, they clear every day."
        )
    bust = _gated(
        K.bust_record_clear_live(),
        bust_live,
        "a bust blocks that port until the next day, and every day clears every bust.",
    )
    return (
        "<p>StarDock, in sector "
        f"{_n(K.STARDOCK_SECTOR)}, holds the shipyard, the tavern, the underground, the bank and Police HQ.</p>"
        + rename
        + f"<p>The tavern is {_on(K.tavern_on())}. An announcement costs {_n(K.TAVERN_ANNOUNCE_COST)} credits. "
        f"A drink or a meal costs {_n(K.TAVERN_DRINK_COST)} credits. Talk and graffiti are free. "
        f"Grimy charges {_n(K.GRIMY_TRACE_COST)} credits to trace a trader and "
        f"{_n(K.GRIMY_PASSWORD_COST)} credits for a password.</p>"
        + f"<p>The underground opens when your alignment is {_n(K.UG_MAX_ALIGNMENT)} or lower. "
        f"A contract starts at {_n(K.UG_CONTRACT_MIN)} credits, "
        f"{_n(K.UG_CREDITS_PER_ALIGN)} credits per alignment point.</p>"
        + "<p>The bank takes deposits, withdrawals and transfers. The tax section states the interest.</p>"
        + f"<p>Police HQ is in sector {_n(K.STARDOCK_SECTOR)}. "
        f"Alignment must be at least {_n(K.POLICE_MIN_ALIGNMENT)}. "
        f"A commission is granted from alignment {_n(K.COMMISSION_APPLY_MIN)} up to, but not including, "
        f"{_n(K.COMMISSION_ALIGNMENT)}. It sets your alignment to {_n(K.COMMISSION_ALIGNMENT)}.</p>"
        + f"<p>A bounty is posted at Police HQ on an evil trader. The minimum is {_n(K.REWARD_MIN)} credits. "
        f"You gain 1 alignment per {_n(K.REWARD_ALIGN_PER)} credits posted. "
        "The killer claims it at the same desk after that trader's ship is destroyed.</p>"
        + bust
        + _src("StarDock services: shipyard, tavern, underground, bank, Police HQ, commission and bounties.")
    )


def _communications(_f: dict) -> str:
    """One section. It always names COMMS_V311_MODE and says what the switch does on and off."""
    if K.comms_v311_live():
        now = (
            "<p>The Comms panel sits on the deck with the other panels. "
            f"Messages are shown at the start of your turn and last {_n(K.HAIL_SHOW_SECONDS)} seconds. "
            f"A line is {_n(K.COMMS_LINE_MAX)} characters. "
            f"You wait {_n(K.COMMS_MIN_GAP_S)} seconds between messages.</p>"
            + _gated(
                True,
                f"sub-space radio uses a channel from 1 to {_n(K.RADIO_CHANNEL_MAX)}. "
                "Everyone tuned to that channel hears it. Channel 0 turns the radio off, and that is how you start. "
                "Fed Comm goes to every trader who has not turned it off. "
                "A hail goes to one trader in your sector and is not stored as mail. "
                "A corporation memo goes only to the other members. "
                "An AI cockpit seat reads those lines on this same panel and answers a hail or a memo with Send. "
                "The reply is a short line, it waits 2 seconds between messages, and it may send one corporation memo about its plan.",
                "",
            )
        )
    else:
        hail = _gated(
            K.mail_live(),
            f"a hail to an open cockpit flashes for {_n(K.HAIL_SHOW_SECONDS)} seconds. "
            "A hail to a trader who is away waits as mail, and the cockpit says there is new mail.",
            "a hail is delivered into the other trader's mail either way. There is no separate flash.",
        )
        radio = _gated(
            K.radio_channel_live(),
            f"your corporation shares a radio channel from 0 to {_n(K.RADIO_CHANNEL_MAX)}. "
            "Only corp mates on that channel hear it.",
            "corporation chat is the one memo. There is no radio channel.",
        )
        fed = _gated(
            K.fedcomm_live(),
            f"when the nightly sweep clears your fighters in a Federation lane, you also get the line: {escape(K.FEDCOMM_MSL_LINE)}",
            "the nightly sweep still clears Federation lanes. You do not get a separate Federation note.",
        )
        now = (
            "<p>Y reads mail. A direct hail is its own order. Computer A makes an announcement. "
            "A corporation memo is on the corporate menu.</p>"
            + hail
            + radio
            + fed
        )
    return (
        now
        + _comms_panel()
        + _src(
            "Hail, mail, the corporation radio channel, Fed Comm, sub-space radio, "
            "a private hail, the corporation memo, and the redesign Comms panel."
        )
    )


def _computer_reports(_f: dict) -> str:
    stats = _gated(
        K.daily_stats_live(),
        "game status counts ports, planets, traders, aliens, and fighters and mines in use. "
        "Fighters sitting on an unmanned ship are left out of that fighter total.",
        "game status does not publish those daily counts.",
    )
    corps = _gated(
        K.corp_rank_live(),
        "corporations are ranked by the members' experience added together, with their alignment added beside it.",
        "there is no corporation ranking screen.",
    )
    traders = _gated(
        K.trader_rank_list_live(),
        "Computer L lists every trader by experience: place, name, title, experience, corporation, ship, and whether they are alive.",
        "Computer L has no experience list of every trader.",
    )
    return (
        "<p>Press C, then the letter. D is today's log, including a hit on fighters you own. "
        "S is quick stats: name, rank, experience, alignment, turns left, credits, day, fighters, shields and holds. "
        "N stores named sectors you already know. B warps back one sector when a lane goes there. "
        "E finds a path between two sectors already in your computer. "
        "C lists the ship catalog. Y lists planets you own. J shows one planet's specs. "
        "R is the port report. K is the map you have seen.</p>"
        + stats
        + corps
        + traders
        + _src("Computer reports on the redesign cockpit, including the daily log, daily counts and rankings.")
    )


def _death_and_pods(f: dict) -> str:
    delay_days = int(f.get("death_delay") or 0) if K.death_delay_live() else 0
    if delay_days > 0:
        wait = f"a new pod cannot move until {_n(delay_days)} midnights have passed."
    else:
        wait = "no death delay is set, so a new pod can move at once."
    pod = _gated(
        K.death_pod_live(),
        f"a destroyed ship becomes an escape pod with a clean loadout. You lose {_n(int(K.POD_EXP_LOSS * 100))} percent of your experience.",
        f"a destroyed ship becomes an escape pod. You lose {_n(int(K.POD_EXP_LOSS * 100))} percent of your experience. "
        "The clean pod loadout is not applied.",
    )
    cash = _gated(
        K.pod_cash_live(),
        f"after another player kills you, the pod holds {_n(K.POD_CASH_CREDITS)} credits.",
        "the pod does not use that fixed credit amount.",
    )
    lock = _gated(
        K.death_delay_live(),
        wait,
        "a pod can act on the turn you land in it. A wait of several midnights is not applied.",
    )
    figs = _gated(
        K.reentry_fighters_live(),
        f"the free Scout carries {_n(K.reentry_fighter_grant())} fighters, "
        f"the smaller of {_n(K.REENTRY_FIGHTER_CAP)} and this game's initial fighters.",
        "the free Scout at StarDock has no fighters.",
    )
    return (
        f"<p>You can lose a ship {_n(K.PODS_PER_DAY)} times in one day and come back in a pod. "
        "The next loss that day is Ship Destroyed: no turns until the day rolls, then a free Scout at StarDock.</p>"
        + pod
        + cash
        + lock
        + figs
        + _src("Escape pod, how many losses a day you can survive, the death delay, and the free Scout's fighters.")
    )


def _feds_and_ferrengi(_f: dict) -> str:
    from ..engine.fed import FED_SPECS
    captains = ", ".join(f"{rank} {name}" for name, rank, _density in FED_SPECS)
    ships = _gated(
        K.fed_ships_live(),
        "three federal ships are in space: Intrepid at StarDock, then Valiant and Lexington in the next two sectors.",
        "those three federal ships are not placed.",
    )
    tow_limit = K.fed_tow_fighter_limit()
    tow = (
        f"<p>{_profile('FedSpace tow limit', K.fed_tow_limit_live(), only_v311=False)} "
        f"FedSpace holds at most {_n(K.FED_SHIPS_PER_SECTOR)} ships in a sector and tows the rest. "
        f"A ship with more than {_n(tow_limit)} fighters is towed.</p>"
    )
    if K.fedsafe_fighter_cap_live():
        shield = (
            f"A trader with more than {_n(K.FEDSAFE_FIGHTER_CAP)} fighters is not protected in FedSpace."
        )
    else:
        shield = "How many fighters you carry does not remove FedSpace protection."
    fighter_cap = (
        f"<p>{_profile('FedSpace fighter protection', K.fedsafe_fighter_cap_live(), only_v311=False)} "
        f"{shield}</p>"
    )
    drop = _gated(
        K.fedspace_deploy_live(),
        "dropping fighters in FedSpace is answered at once. You lose a tenth of the fighters and a tenth of the holds.",
        "you cannot drop fighters in FedSpace.",
    )
    quasar = _gated(
        K.ferrengal_quasar_live(),
        "entering Ferrengal draws one quasar shot. Landing there does not.",
        "Ferrengal does not fire a quasar at a ship that enters.",
    )
    gold = _gated(
        K.gold_alien_live(),
        f"destroying an alien while another of that race is in the sector puts you on that race's list of {_n(K.GOLD_GRUDGE_LIMIT)}. "
        "The fight itself does not get harder.",
        "destroying an alien does not start a race grudge.",
    )
    return (
        f"<p>The federal captains are {escape(captains)}.</p>"
        + ships
        + tow
        + fighter_cap
        + drop
        + "<p>Ferrengi rules are in the Ferrengi section. Ferrengal is their home sector.</p>"
        + quasar
        + gold
        + _src("Federal ships, FedSpace tows, Ferrengal, and the gold-alien grudge.")
    )


def _towing_and_transwarp(f: dict) -> str:
    ship = K.STARTING_SHIP
    reach = K.transport_range(ship)
    interdictor = K.transport_range("interdictor_cruiser")
    tow = (
        f"<p>W tows another ship when towing is {_on(K.tow_on())}. "
        f"You cannot tow a ship that still has fighters on board. "
        f"The turn cost adds your hull's turns per warp to {_n(K.TOW_TOWEE_TPW_MULT)} times the towed hull's. "
        "A pod cannot be towed. Releasing the tow is its own order.</p>"
    )
    tw = (
        f"<p>Ship TransWarp is {_on(K.ship_tw_on())}. The drive costs {_n(K.SHIP_TW_TYPE1_COST)} credits "
        f"and burns {_n(K.SHIP_TW_ORE_PER_HOP)} fuel ore per hop. "
        "The Imperial StarShip, the Corporate Flagship and the Havoc Gunstar can carry it. "
        f"A tow upgrade costs {_n(K.SHIP_TW_TYPE2_COST)} credits and burns {_n(K.SHIP_TW_TOW_ORE_PER_HOP)} ore per hop.</p>"
    )
    pad = (
        f"<p>X is the transporter. The starting hull, the {escape(f['ship'])}, beams {_n(reach)} hops. "
        f"An Interdictor beams {_n(interdictor)} hops.</p>"
    )
    hull = _gated(
        K.special_hull_rules_on(),
        "an Interdictor also holds every other ship in its sector, and a Tholian defending its own corporation's planet fights at 4 to 1.",
        "an Interdictor does not hold other ships, and a Tholian does not fight at 4 to 1.",
    )
    planet = (
        f"<p>A citadel TransWarp needs level {_n(K.PLANET_TRANSWARP_MIN_LEVEL)} and burns "
        f"{_n(K.PLANET_TRANSWARP_FUEL_PER_SECTOR)} fuel per sector.</p>"
    )
    return (
        tow + tw + pad + hull + planet
        + _src("Towing, ship TransWarp, the transporter pad, and citadel TransWarp.")
    )


# Action or switch -> section id. The v2 test requires every player action and every
# profile switch to be here or in EXEMPT. The page itself does not print these names.
_COVERS: dict[str, tuple[str, ...]] = {
    "getting-started": ("STARTING_PACKAGE_MODE", "HOME_PLANET_MODE"),
    "moving": (
        "warp", "plot_course", "avoid",
        "COURSE_MAX_MODE", "ONE_WAY_SHARE_MODE", "AUTOPILOT_PORT_STOP_MODE", "AVOID_MODE",
        "BIG_BANG_DENSITY_MODE",
    ),
    "trading": (
        "trade", "rob", "steal", "planet_trade",
        "PORT_PRICE_MODE", "PRICE_SCALE_MODE", "HAGGLE_WINDOW_MODE", "HAGGLE_LIVE_MODE", "HAGGLE_COUNTER_MODE",
        "HAGGLE_EXP_MODE", "HAGGLE_TABLE_MODE", "PORT_BUY_PRICE_ANCHOR_MODE", "PORT_REGEN_MODE", "PORT_STOCK_FIDELITY_MODE",
        "PORT_CLASS_MAP_MODE", "PORT_CLASS_NUMBER_FIX_MODE", "CLASS0_HOLD_FORMULA_MODE",
        "HOLD_RULES_MODE", "SHOP_PRICE_MODE", "EVIL_TRADE_LOOP_MODE",
    ),
    "ports": (
        "port_upgrade", "port_build",
        "PORT_ATTACK_MODE", "PORT_ATTACK_ALL_CLASSES_MODE", "SPECIAL_PORT_DEFENCE_MODE",
    ),
    "ship-trade-in": (
        "buy_ship", "sell_ship",
        "SHIP_ROSTER_MODE", "TRADE_IN_MODE", "TRADE_IN_PARTS_MODE", "YARD_STATS_MODE",
    ),
    "combat": (
        "attack", "cloak", "fire_disruptor", "photon_missile", "deploy_atomic", "surrender",
        "retreat", "pay_toll", "recall_deployed", "deploy_fighters", "deploy_mines",
        "jettison", "self_destruct",
        "OFFENSIVE_CLASH_MODE", "KILL_CASH_MODE", "SHIP_FLEE_MODE", "PLANET_LANDING_COMBAT_MODE",
        "RIVAL_STRENGTH_MODE", "SPECIAL_HULL_RULES_MODE", "PHOTON_FOLLOW_DAMP_MODE",
        "CAPTURE_CREDIT_LINE_MODE", "ATOMIC_DETONATOR_MODE", "ALIEN_COMBAT_FIX_MODE", "SHIP_EXIT_MODE",
        "PHOTON_LIMPET_MODE",
    ),
    "ferrengi": (
        "FERRENGI_ENGAGE_MODE", "FERRENGI_GRUDGE_MODE", "FERRENGI_PACE_MODE", "FERRENGI_REWARD_MODE",
        "FERRENGI_ATTACK_MODE",
    ),
    "planets": (
        "land_planet", "liftoff", "deploy_genesis", "claim_planet", "planet_destroy",
        "load_planet_cargo", "dump_planet_cargo",
        "GENESIS_NAME_MODE", "GENESIS_START_MODE", "PLANET_PROD_MODE", "PLANET_COLLISION_MODE",
        "PLANET_BUST_EXP_MODE", "PLANET_COLONIST_CAP_MODE", "PLANET_GROWTH_MODE", "PLANET_NW_MODE",
        "OWN_PLANET_TURN_MODE", "OWN_PLANET_FIGHTER_MODE", "LANDED_STATE_MODE", "PLANET_ZDY_MODE",
    ),
    "citadels": (
        "build_citadel", "set_military_reaction", "deposit_treasury", "withdraw_treasury",
        "set_quasar_sector", "set_quasar_atm", "deposit_planet_defense", "withdraw_planet_defense",
        "CITADEL_DAYS_MODE", "CITADEL_COST_MODE", "CITADEL_PERK_MODE", "CITADEL_PARK_MODE",
        "CITADEL_TABLE_FIX_MODE", "TREASURY_CAP_MODE", "PLANET_SHIELD_ACTIVE_MODE",
        "PLANET_SHIELD_MODE", "PLANET_DIVIDEND_PAY_MODE",
        "QUASAR_ATM_ORDER_MODE", "PLANET_INTERDICT_SAFE_MODE",
    ),
    "colonists": (
        "assign_colonists", "terra_colonists",
        "TERRA_COLONIST_MODE", "COLONIST_UNITS_MODE", "COLONIST_NW_UNITS_MODE",
        "START_COLONIST_NW_MODE", "CLASS_M_DROP_MODE", "CLASS_M_FIDELITY_MODE",
        "CLASS_M_GENESIS_MODE", "CLASS_M_NW_MODE", "ASSIGN_POOL_FIX_MODE",
    ),
    "corporations": (
        "corp_create", "corp_invite", "corp_join", "corp_leave", "corp_set_password", "corp_drop",
        "corp_transfer", "corp_deposit", "corp_withdraw", "corp_memo",
        "propose_alliance", "accept_alliance", "break_alliance",
        "ship_set_corporate", "ship_set_personal", "ship_set_password",
        "CORP_EXP_PENALTY_MODE", "CORP_PLANET_DISBAND_MODE", "CORP_BREAKIN_ALIGN_MODE",
    ),
    "alignment": ("DISCOVERY_EXP_MODE", "EXP_SOURCES_MODE"),
    "rankings": (
        "EXP_SCORE_MODE", "RANK_DISPLAY_MODE", "NW_ESTIMATE_MODE", "GENESIS_SCORE_MODE",
        "PLANET_VALUE_SCORE_MODE",
    ),
    "tax": ("bank_deposit", "bank_withdraw", "bank_transfer", "TAX_RULE_MODE"),
    "turns": (
        "wait", "TURN_REGEN_MODE", "DAY_ROLL_CLOCK_MODE", "LEGACY_DAY_CLOCK_MODE", "LIVE_PACE_MODE",
    ),
    "hardware": (
        "buy_equip", "scan", "probe", "query_limpets", "remove_limpet", "launch_beacon",
        "HARDWARE_PRICE_MODE", "DETECT_GEAR_MODE", "PLANET_SCANNER_MODE", "SCANNER_FOG_MODE",
        "SHIP_CHART_CAP_MODE", "PROBE_SHOOTDOWN_MODE",
    ),
    "stardock-services": (
        "ship_rename", "apply_commission", "post_reward", "claim_reward",
        "tavern_announce", "tavern_talk", "tavern_graffiti", "tavern_order",
        "grimy_ask", "grimy_curse", "underground_enter", "underground_contract", "underground_claim",
        "tricron", "cineplex",
        "SHIP_RENAME_MODE", "BUST_CLEAR_MODE",
    ),
    "communications": (
        "hail", "broadcast", "radio", "MAIL_MODE", "RADIO_CHANNEL_MODE", "FEDCOMM_MODE", "COMMS_V311_MODE",
    ),
    "computer-reports": (
        "DAILY_STATS_MODE", "CORP_RANK_MODE", "TRADER_RANK_LIST_MODE",
        "OWNER_HAZARD_NOTICE_MODE", "SIEGE_REPORT_MODE",
    ),
    "death-and-pods": ("DEATH_DELAY_MODE", "DEATH_POD_MODE", "POD_CASH_MODE", "REENTRY_FIGHTERS_MODE"),
    "feds-and-ferrengi-v311": (
        "FED_SHIPS_MODE", "FEDSPACE_DEPLOY_MODE", "FERRENGAL_QUASAR_MODE",
        "FEDSAFE_FIGHTER_CAP_MODE", "FED_TOW_LIMIT_MODE",
    ),
    "towing-and-transwarp": (
        "ship_transwarp", "ship_transport", "tow_engage", "tow_release",
        "planet_transwarp", "planet_buy_transporter", "planet_transport",
    ),
}

MANUAL_COVERAGE: dict[str, str] = {
    name: sid for sid, names in _COVERS.items() for name in names
}

# Not a thing a player does. Each reason is why it is left off the page's coverage map.
EXEMPT: tuple[tuple[str, str], ...] = (
    ("ACTION_RESULT_MODE", "How an AI seat's result is shaped. A player does not set it."),
    ("API_ARGS_MODE", "How an AI seat sends arguments. A player does not set it."),
    ("BOT_HAZARD_MEMORY_MODE", "A code bot remembers a hazard. A player does not use it."),
    ("BOT_DIPLOMACY_MODE", "A code bot answers a hail. A player does not use it."),
    ("BOT_BANK_FLOAT_MODE", "A code bot keeps cash before a deposit. A player does not use it."),
    ("SEAT_IDLE_START_MODE", "When an empty seat's idle clock starts. A player does not set it."),
)
