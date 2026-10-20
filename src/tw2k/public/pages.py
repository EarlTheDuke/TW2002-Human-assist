"""Server-rendered lobby pages (plain HTML + one stylesheet, no scripts beyond a refresh)."""

from __future__ import annotations

import json
import time
from html import escape
from typing import Any, Iterable

from ..engine import constants as K
from .security import DAY_PRESETS, UNIVERSE_SIZES, ai_label, credits_phrase, turns_phrase

FULL_TEXT = "The beta is full right now, try again later"

DISCLAIMER_POINTS = (
    "These are free test games.",
    "They run on a home PC, so a game may go down or be reset at any time.",
    "Progress may be lost. There are no guarantees of any kind.",
    "Do not enter personal information, and do not reuse a password from anywhere else.",
    "AI players are not available yet; the computer players are simple code bots.",
)

_CSS = """
:root{color-scheme:dark}
*{box-sizing:border-box}
body{margin:0;background:#05070d;color:#d6e2f0;font:16px/1.5 system-ui,Segoe UI,Roboto,sans-serif}
main{max-width:960px;margin:0 auto;padding:24px 16px 24px}
h1{font-size:28px;margin:8px 0 4px;color:#7fe3ff;letter-spacing:.04em}
h2{font-size:20px;margin:28px 0 8px;color:#ffd27f}
p.sub{margin:0 0 16px;color:#8aa0b8}
a{color:#7fe3ff}
.card{background:#0c1220;border:1px solid #1f2d45;border-radius:10px;padding:16px;margin:12px 0}
.row{display:flex;flex-wrap:wrap;gap:12px;align-items:center;justify-content:space-between}
.btn,button{display:inline-block;background:#12324a;color:#e8f6ff;border:1px solid #2b6c92;border-radius:8px;
  padding:10px 16px;font:inherit;cursor:pointer;text-decoration:none;min-height:44px}
.btn.primary,button.primary{background:#1d6f4a;border-color:#3fbf84}
.btn.warn,button.warn{background:#5a1d1d;border-color:#c25050}
.btn[aria-disabled=true]{opacity:.5;pointer-events:none}
table{width:100%;border-collapse:collapse}
th,td{text-align:left;padding:8px 6px;border-bottom:1px solid #1a2638;vertical-align:middle}
th{color:#8aa0b8;font-weight:600;font-size:14px}
.tag{display:inline-block;padding:2px 8px;border-radius:999px;font-size:13px;background:#1a2638}
.tag.running{background:#14432c}.tag.sleeping{background:#3a3214}.tag.failed{background:#4a1616}
.tag.finished{background:#1e3a5f}
label{display:block;margin:12px 0 4px;color:#b8c8da}
label.check{display:flex;align-items:center;gap:10px;max-width:640px}
input,select{width:100%;max-width:420px;background:#070b14;color:#e8f6ff;border:1px solid #2a3a55;border-radius:8px;
  padding:10px;font:inherit;min-height:44px}
label.check input{width:auto;min-height:44px;max-width:none}
fieldset{border:1px solid #1f2d45;border-radius:10px;margin:12px 0;padding:8px 16px 16px}
legend{color:#ffd27f;padding:0 6px}
.err{background:#3a1212;border:1px solid #a33;border-radius:8px;padding:10px 14px}
.note{color:#8aa0b8;font-size:14px}
ul.points li{margin:6px 0}
code.link{display:block;word-break:break-all;background:#070b14;border:1px solid #1f2d45;padding:8px;border-radius:6px}
footer{border-top:1px solid #142034;padding:14px 16px 20px;font-size:14px;color:#8aa0b8;text-align:center}
@media (max-width:600px){table.games thead{display:none}table.games td{display:block;border:0;padding:4px 0}
  table.games tr{display:block;border-bottom:1px solid #1a2638;padding:8px 0}}
"""


def page(title: str, body: str, *, brand: str, refresh_s: int | None = None) -> str:
    meta = f'<meta http-equiv="refresh" content="{int(refresh_s)}">' if refresh_s else ""
    return (
        "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
        f"{meta}<title>{escape(title)} - {escape(brand)}</title><style>{_CSS}</style></head><body><main>"
        f"<h1>{escape(brand)}</h1>"
        '<p class="sub"><a href="/">Lobby</a> · <a href="/manual">Manual</a> · '
        '<a href="/about">About these test games</a></p>'
        f"{body}</main>"
        "<footer>Closed beta test games &middot; <a href=\"/about\">About these test games</a></footer>"
        "</body></html>"
    )


def disclaimer_points() -> tuple[str, ...]:
    """The about-page lines. Off, they are the stored list. On, the AI line matches the option."""
    if not K.lobby_ai_seat_on():
        return DISCLAIMER_POINTS
    out = []
    for point in DISCLAIMER_POINTS:
        if point.startswith("AI players are not available"):
            out.append(
                "AI opponents are optional seats. Heuristic is free. "
                "An LLM seat uses a key you paste for that game; the server does not store it."
            )
        else:
            out.append(point)
    return tuple(out)


def ai_call_estimate(turns_per_day: int, opponents: int, brain: str) -> str:
    """Calls per game day for the pace on the form.

    UNVERIFIED: one model call per turn per LLM seat. Heuristic is zero.
    """
    if brain != "llm" or int(opponents) <= 0:
        return "Estimate: 0 model calls per game day with the heuristic brain."
    calls = max(0, int(turns_per_day)) * int(opponents) * int(K.LOBBY_AI_CALLS_PER_TURN)
    seats = int(opponents)
    noun = "seat" if seats == 1 else "seats"
    return (
        f"Estimate: about {calls:,} model calls per game day "
        f"for {seats} LLM {noun} at this pace (one call per turn, UNVERIFIED)."
    )


def disclaimer(brand: str, next_url: str = "/") -> str:
    points = "".join(f"<li>{escape(p)}</li>" for p in disclaimer_points())
    body = (
        "<p class=\"sub\">Before you play</p><div class=\"card\"><ul class=\"points\">" + points + "</ul>"
        "<form method=\"post\" action=\"/accept\">"
        f"<input type=\"hidden\" name=\"next\" value=\"{escape(next_url)}\">"
        "<button class=\"primary\" type=\"submit\">I understand</button></form></div>"
    )
    return page("Before you play", body, brand=brand)


def about(brand: str) -> str:
    points = "".join(f"<li>{escape(p)}</li>" for p in disclaimer_points())
    body = ("<p class=\"sub\">About these test games</p><div class=\"card\"><ul class=\"points\">" + points +
            "</ul><p><a class=\"btn\" href=\"/\">Back to the lobby</a></p></div>")
    return page("About", body, brand=brand)


def _status_tag(status: str) -> str:
    return f"<span class=\"tag {escape(status)}\">{escape(status)}</span>"


_DAY_NAMES = {"10m": "10 minutes", "30m": "30 minutes", "1h": "1 hour", "24h": "Real time, 24 h (original)"}


def day_length_hint(day_seconds: int, turns_per_day: int, max_days: int) -> str:
    """Plain consequence of a day length, from the preset, the turn pocket and the day count."""
    seconds = max(1, int(day_seconds))
    turns = max(1, int(turns_per_day))
    days = max(1, int(max_days))
    if seconds % 86400 == 0:
        name = f"{seconds // 86400 * 24} h" if seconds != 86400 else "24 h"
    elif seconds % 3600 == 0:
        name = f"{seconds // 3600} h"
    elif seconds % 60 == 0:
        name = f"{seconds // 60} min"
    else:
        name = f"{seconds} s"
    per = seconds / turns
    if per < 90:
        every = f"{per:.1f}".rstrip("0").rstrip(".") + " s"
    else:
        every = f"{per / 60:.1f}".rstrip("0").rstrip(".") + " min"
    total = seconds * days
    if total % 86400 == 0:
        span = f"{total // 86400} real day" + ("s" if total != 86400 else "")
    else:
        hours, rem = divmod(total, 3600)
        minutes = rem // 60
        if hours and minutes:
            span = f"{hours} h {minutes} min"
        elif hours:
            span = f"{hours} h"
        elif minutes:
            span = f"{minutes} min"
        else:
            span = f"{total} s"
    if seconds >= 86400:
        return f"{name} days: a turn comes back every {every}, like the original; {days} days take {span}"
    if per < 60:
        return f"{name} days: {days} days take about {span}; a turn comes back every {every}, so turns rarely run out"
    return f"{name} days: {days} days take about {span}; a turn comes back every {every}"


def _day_note(g: dict[str, Any], info: dict[str, Any]) -> str:
    """The running day, or the finished line once the engine has ended the match.

    A 10-day game dawns day 11 when time runs out. The lobby says day 10 of 10.
    """
    raw = info.get("day")
    if raw is None:
        return ""
    try:
        day = int(raw)
    except (TypeError, ValueError):
        return ""
    settings = g.get("settings") or {}
    try:
        cap = int(settings.get("max_days") or 0)
    except (TypeError, ValueError):
        cap = 0
    done = g.get("status") == "finished" or bool(info.get("finished")) or (cap > 0 and day > cap)
    if not done:
        return f"day {day}"
    played = min(day, cap) if cap else day
    shown = cap or played
    name = str(info.get("winner") or "").strip()
    reason = str(info.get("win_reason") or "").strip()
    if name and reason:
        return f"finished, day {played} of {shown}, winner {name} ({reason})"
    if name:
        return f"finished, day {played} of {shown}, winner {name}"
    return f"finished, day {played} of {shown}"


def _day_label(seconds: int) -> str:
    for k, v in DAY_PRESETS.items():
        if v == int(seconds):
            return k
    return f"{int(seconds)}s"


def _end_button(g: dict[str, Any]) -> str:
    """Confirm dialog names the game; the form sends confirm=true only after OK."""
    question = escape(json.dumps(f"End {g['name']} for everyone?"))
    gid = escape(g["id"])
    return (
        f"<form method=\"post\" action=\"/games/{gid}/end\" style=\"display:inline\" "
        f"onsubmit=\"if(!window.confirm({question}))return false;this.elements.confirm.value='true';\">"
        "<input type=\"hidden\" name=\"confirm\" value=\"\">"
        f"<button class=\"warn\" type=\"submit\" data-end-game=\"{gid}\">End game</button></form>"
    )


def lobby(brand: str, *, games: Iterable[dict[str, Any]], mine: Iterable[dict[str, Any]], closed: bool,
          full: bool, live: dict[str, dict[str, Any]], owned: Iterable[dict[str, Any]] | None = None,
          notes: dict[str, str] | None = None, seat_links: dict[str, str] | None = None,
          seat_rows: dict[str, list[dict[str, str]]] | None = None) -> str:
    mine = list(mine)
    owned = list(owned or [])
    seated = {g["id"] for g in mine}
    running_owned = {g["id"] for g in owned if g["status"] == "running"}
    rows = []
    for g in games:
        s = g["settings"]
        info = live.get(g["id"], {})
        day = _day_note(g, info)
        open_seats = g.get("open_seats", 0)
        join = (f"<form method=\"post\" action=\"/games/{g['id']}/join\" style=\"display:inline\">"
                "<button class=\"primary\" type=\"submit\">Join</button></form>") if open_seats and not closed else ""
        watch = "" if g["id"] in seated else f"<a class=\"btn\" href=\"/g/{g['id']}/watch\">Watch</a>"
        detail = (seat_rows or {}).get(g["id"]) or []
        if detail:
            bits = []
            for item in detail:
                bits.append(
                    f'<div data-cockpit="seat">{escape(item.get("status") or "")} '
                    f'<a class="btn" href="{escape(item.get("href") or "")}">Open {escape(item.get("seat") or "seat")}</a> '
                    f'<form method="post" action="{escape(item.get("stop") or "")}" style="display:inline">'
                    f'<button type="submit">Stop</button></form></div>'
                )
            cockpit_line = "".join(bits)
            cockpit_link = ""
        else:
            cockpit_note = escape((notes or {}).get(g["id"], ""))
            cockpit_href = (seat_links or {}).get(g["id"], "")
            cockpit_link = (
                f'<a class="btn" href="{escape(cockpit_href)}" data-cockpit="seat">AI seat</a>'
                if cockpit_href else ""
            )
            cockpit_line = f"<br>{cockpit_note}" if cockpit_note else ""
        # The seat row carries the button once the creator has sat down.
        end = _end_button(g) if g["id"] in running_owned and g["id"] not in seated else ""
        rows.append(
            f"<tr><td><b>{escape(g['name'])}</b><br><span class=\"note\">"
            f"{'v3.11' if s['rules'] == 'v311' else 'legacy'} rules &middot; {s['universe_size']} sectors &middot; "
            f"{_day_label(s['day_seconds'])} days &middot; {s['bots']} bots{_ai_card(s)}"
            f"<br>{escape(credits_phrase(s))}"
            f"<br>{escape(turns_phrase(s))}{cockpit_line}</span></td>"
            f"<td>{_status_tag(g['status'])} <span class=\"note\">{escape(day)}</span></td>"
            f"<td>{open_seats} of {s['humans']} seats open</td><td>{join} {watch} {cockpit_link} {end}</td></tr>"
        )
    table = ("<table class=\"games\"><thead><tr><th>Game</th><th>Status</th><th>Seats</th><th></th></tr></thead>"
             "<tbody>" + "".join(rows) + "</tbody></table>") if rows else "<p class=\"note\">No open games yet.</p>"
    seat_rows = []
    for g in mine:
        if g["status"] in ("archived", "finished"):
            continue
        end = _end_button(g) if g["id"] in running_owned else ""
        seat_rows.append(
            f"<tr><td><b>{escape(g['name'])}</b> &middot; seat {escape(g['my_seat'])}</td>"
            f"<td>{_status_tag(g['status'])}</td>"
            f"<td><a class=\"btn primary\" href=\"/resume/{g['id']}\">Resume my seat</a> {end}</td></tr>"
        )
    for g in owned:
        if g["status"] != "running" or g["id"] in seated or g["listed"]:
            continue
        seat_rows.append(
            f"<tr><td><b>{escape(g['name'])}</b> &middot; link only</td><td>{_status_tag(g['status'])}</td>"
            f"<td>{_end_button(g)}</td></tr>"
        )
    my_rows = "".join(seat_rows)
    mine_html = (f"<h2>Your seats</h2><div class=\"card\"><table class=\"games\"><tbody>{my_rows}</tbody></table></div>"
                 if my_rows else "")
    finished = []
    seen: set[str] = set()
    for g in list(mine) + list(owned):
        if g["status"] != "finished" or g["id"] in seen:
            continue
        seen.add(g["id"])
        finished.append(
            f"<tr data-finished=\"{escape(g['id'])}\"><td><b>{escape(g['name'])}</b></td>"
            f"<td>{_status_tag('finished')} <span class=\"note\">{escape(_day_note(g, live.get(g['id'], {})))}</span></td>"
            f"<td></td></tr>"
        )
    finished_html = (
        f"<h2>Finished</h2><div class=\"card\" id=\"finished\"><table class=\"games\"><tbody>{''.join(finished)}</tbody></table></div>"
        if finished else ""
    )
    if closed:
        new = "<div class=\"err\">New games are switched off right now.</div>"
    elif full:
        new = f"<div class=\"err\">{escape(FULL_TEXT)}.</div>"
    else:
        new = "<a class=\"btn primary\" href=\"/new\">New game</a>"
    reopen = (
        '<div id="reopen" class="card" hidden></div><script>(function(){'
        'var box=document.getElementById("reopen");if(!box)return;var raw="";'
        'try{raw=localStorage.getItem("tw2k-my-seats")||"";}catch(e){return;}'
        'var rows=[];try{rows=raw?JSON.parse(raw):[];}catch(e){return;}'
        'if(!rows||!rows.length)return;var html="<h2>Re-open my seat</h2>";'
        'rows.forEach(function(r){if(!r||!r.gid||!r.seat||!r.token)return;'
        'var href="/g/"+encodeURIComponent(r.gid)+"/bot?seat="+encodeURIComponent(r.seat)'
        '+"&mode=cu#token="+encodeURIComponent(r.token);'
        'html+="<p><a class=\\"btn primary\\" data-reopen=\\""+String(r.seat).replace(/[^A-Za-z0-9]/g,"")'
        '+"\\" href=\\""+href+"\\">Re-open "+String(r.seat).replace(/[<>&]/g,"")+"</a></p>";});'
        'box.innerHTML=html;box.hidden=false;})();</script>'
    )
    body = (f"<p class=\"sub\">Closed beta lobby</p>{mine_html}{reopen}"
            f"<div class=\"row\"><h2>Games</h2>{new}</div>"
            f"<div class=\"card\">{table}</div>{finished_html}")
    return page("Lobby", body, brand=brand)


def _ai_card(settings: dict[str, Any]) -> str:
    """Lobby row fragment. Empty when the game has no AI seats, so today's rows stay put."""
    try:
        n = int(settings.get("ai_opponents") or 0)
    except (TypeError, ValueError):
        return ""
    if n <= 0:
        return ""
    label = ai_label(str(settings.get("ai_brain") or "heuristic"))
    return f" &middot; {n} {escape(label)}"


def _opt(value: str, label: str, selected: str) -> str:
    sel = " selected" if str(value) == str(selected) else ""
    return f"<option value=\"{escape(str(value))}\"{sel}>{escape(label)}</option>"


def _waiting_banner(waiting: Iterable[dict[str, Any]] | None) -> str:
    rows = [row for row in (waiting or []) if row.get("href")]
    if not rows:
        return ""
    links = " · ".join(
        f'<a href="{escape(str(row["href"]))}">Join it</a> ({escape(str(row.get("name") or "game"))})'
        for row in rows
    )
    return (
        f'<div class="card" data-waiting="game"><p><b>You have a game waiting.</b> {links}'
        " before making another.</p></div>"
    )


def new_game(brand: str, *, error: str | None = None, values: dict[str, Any] | None = None,
             presets: dict[str, int] | None = None,
             waiting: Iterable[dict[str, Any]] | None = None) -> str:
    v = {"name": "", "rules": "v311", "universe_size": "1000", "max_days": "30", "turns_per_day": "original",
         "starting_package": "v311", "bots": "2", "ferrengi": "on", "day": "30m", "humans": "1",
         "visibility": "listed", "starting_credits": "original", "starting_credits_custom": "",
         "home_planet_name": "", "turns_per_day_custom": "", "hold_until_human": "on"}
    # The key and the endpoint are never copied into the page, including after a validation error.
    v.update({k: str(val) for k, val in (values or {}).items() if k not in ("ai_key", "ai_endpoint")})
    err = f"<div class=\"err\">{escape(error)}</div>" if error else ""
    sizes = "".join(_opt(str(n), f"{n} sectors", v["universe_size"]) for n in UNIVERSE_SIZES)
    days = "".join(_opt(k, _DAY_NAMES.get(k, f"{k} ({secs} s)"), v["day"])
                   for k, secs in (presets or DAY_PRESETS).items())
    bots = "".join(_opt(str(n), str(n), v["bots"]) for n in range(6))
    humans = "".join(_opt(str(n), str(n), v["humans"]) for n in range(1, 5))
    hold_checked = " checked" if v.get("hold_until_human") == "on" else ""
    picked_turns = v.get("turns_per_day") or "original"
    if picked_turns == "custom":
        try:
            hint_turns = int(v.get("turns_per_day_custom") or 250)
        except ValueError:
            hint_turns = 250
    elif picked_turns in ("original", ""):
        hint_turns = 250
    else:
        try:
            hint_turns = int(picked_turns)
        except ValueError:
            hint_turns = 250
    ai_fields = ""
    ai_script = ""
    if K.lobby_ai_seat_on():
        v.setdefault("ai_opponents", "0")
        v.setdefault("ai_brain", "heuristic")
        try:
            ai_n = int(v["ai_opponents"])
        except (TypeError, ValueError):
            ai_n = 0
        brain = v["ai_brain"] if v["ai_brain"] in ("heuristic", "llm") else "heuristic"
        ai_opts = "".join(_opt(str(n), str(n), v["ai_opponents"]) for n in range(5))
        brains = (
            _opt("heuristic", "Heuristic (free)", brain)
            + _opt("llm", "LLM (your key)", brain)
        )
        hidden = "" if brain == "llm" else " hidden"
        estimate = escape(ai_call_estimate(hint_turns, ai_n, brain))
        per = int(K.LOBBY_AI_CALLS_PER_TURN)
        ai_fields = (
            f'<label for="ai_opponents">AI opponents</label><select id="ai_opponents" name="ai_opponents">{ai_opts}</select>'
            f'<label for="ai_brain">Brain for each AI seat</label><select id="ai_brain" name="ai_brain">{brains}</select>'
            f'<div id="aiKeyBox"{hidden}>'
            '<label for="ai_endpoint">Endpoint URL</label>'
            '<input id="ai_endpoint" name="ai_endpoint" type="url" autocomplete="off" value="">'
            '<label for="ai_key">API key</label>'
            '<input id="ai_key" name="ai_key" type="password" autocomplete="off" value="">'
            '<p class="note">Your key stays in memory for this game only. It is not stored, and it is not shown again.</p>'
            "</div>"
            f'<p class="note" id="aiCallHint">{estimate}</p>'
        )
        ai_script = (
            "<script>\n"
            f"const aiCallsPerTurn = {per};\n"
            "function aiTurns() {\n"
            "  const picked = document.getElementById('turns_per_day').value;\n"
            "  if (picked === 'custom') return Number(document.getElementById('turns_per_day_custom').value) || 250;\n"
            "  if (picked === 'original' || picked === '') return 250;\n"
            "  return Number(picked) || 250;\n"
            "}\n"
            "function paintAiHint() {\n"
            "  const turns = aiTurns();\n"
            "  const seats = Number(document.getElementById('ai_opponents').value) || 0;\n"
            "  const brain = document.getElementById('ai_brain').value;\n"
            "  const box = document.getElementById('aiKeyBox');\n"
            "  if (box) box.hidden = brain !== 'llm';\n"
            "  const hint = document.getElementById('aiCallHint');\n"
            "  if (!hint) return;\n"
            "  if (brain !== 'llm' || seats < 1) {\n"
            "    hint.textContent = 'Estimate: 0 model calls per game day with the heuristic brain.';\n"
            "    return;\n"
            "  }\n"
            "  const calls = turns * seats * aiCallsPerTurn;\n"
            "  const noun = seats === 1 ? 'seat' : 'seats';\n"
            "  hint.textContent = 'Estimate: about ' + calls.toLocaleString() + ' model calls per game day for '\n"
            "    + seats + ' LLM ' + noun + ' at this pace (one call per turn, UNVERIFIED).';\n"
            "}\n"
            "['ai_opponents','ai_brain','turns_per_day','turns_per_day_custom'].forEach((id) => {\n"
            "  const el = document.getElementById(id);\n"
            "  if (el) el.addEventListener('input', paintAiHint);\n"
            "  if (el) el.addEventListener('change', paintAiHint);\n"
            "});\n"
            "</script>\n"
        )
    length_fields = ""
    length_script = ""
    if K.full_length_turn_limits_on():
        v.setdefault("game_length", "fast")
        picked_length = v["game_length"] if v["game_length"] in ("fast", "full") else "fast"
        length_fields = (
            '<label for="game_length">Game length</label>'
            f'<select id="game_length" name="game_length">'
            f'{_opt("fast", "Fast test days", picked_length)}'
            f'{_opt("full", "Full-length", picked_length)}</select>'
            "<p class=\"note\">Fast test days keep today's day length and turn pocket. "
            "Full-length uses a 24-hour day and the v3.11 daily turn limit "
            f"({K.FULL_LENGTH_TURNS_PER_DAY:,} on a {K.FULL_LENGTH_REFERENCE_DAYS}-day game). "
            "A longer game lowers that limit so the whole game stays near "
            f"{K.FULL_LENGTH_TURNS_PER_DAY * K.FULL_LENGTH_REFERENCE_DAYS:,} turns.</p>"
        )
        length_script = (
            "<script>\n"
            "document.getElementById('game_length').addEventListener('change', function () {\n"
            "  if (this.value !== 'full') return;\n"
            "  const day = document.getElementById('day');\n"
            "  if (day) { for (const opt of day.options) { if (opt.value === '24h') day.value = '24h'; } }\n"
            "  if (typeof paintDayHint === 'function') paintDayHint();\n"
            "});\n"
            "</script>\n"
        )
    cockpit_fields = ""
    if K.ai_cockpit_seat_on():
        v.setdefault("ai_cockpit", "off")
        v.setdefault("ai_cockpit_provider", "scripted")
        v.setdefault("ai_cockpit_model", "")
        v.setdefault("ai_cockpit_count", "1")
        v.setdefault("ai_cockpit_level", "hard")
        provider = v["ai_cockpit_provider"] if v["ai_cockpit_provider"] in (
            "scripted", "grok", "openai", "anthropic") else "scripted"
        try:
            count_picked = str(int(v.get("ai_cockpit_count") or 1))
        except (TypeError, ValueError):
            count_picked = "1"
        if count_picked not in ("1", "2", "3", "4"):
            count_picked = "1"
        level_picked = v["ai_cockpit_level"] if v["ai_cockpit_level"] in ("easy", "normal", "hard") else "hard"
        counts = "".join(_opt(str(n), str(n), count_picked) for n in range(1, 5))
        levels = (
            _opt("easy", "Easy", level_picked)
            + _opt("normal", "Normal", level_picked)
            + _opt("hard", "Hard", level_picked)
        )
        providers = (
            _opt("scripted", "Scripted (no key)", provider)
            + _opt("grok", "Grok", provider)
            + _opt("openai", "OpenAI", provider)
            + _opt("anthropic", "Anthropic", provider)
        )
        checked = " checked" if v.get("ai_cockpit") == "on" else ""
        cockpit_fields = (
            '<input type="hidden" name="ai_cockpit" value="off">'
            f'<label class="check" for="ai_cockpit"><input id="ai_cockpit" name="ai_cockpit" '
            f'type="checkbox" value="on"{checked}>AI cockpit seat</label>'
            '<p class="note">Up to four more seats. Each plays from the rendered cockpit on its own. '
            "Easy looks briefly and takes a weak trade. Normal trades a shorter route. "
            "Hard plays the long game, leaves a sector the screen has marked dangerous, "
            "and shops only when the days left can pay for it. "
            "A live provider reads its key from the lobby process environment. The key is not stored and not shown.</p>"
            f'<label for="ai_cockpit_count">AI cockpit seats</label>'
            f'<select id="ai_cockpit_count" name="ai_cockpit_count">{counts}</select>'
            f'<label for="ai_cockpit_level">Difficulty</label>'
            f'<select id="ai_cockpit_level" name="ai_cockpit_level">{levels}</select>'
            f'<label for="ai_cockpit_provider">AI cockpit provider</label>'
            f'<select id="ai_cockpit_provider" name="ai_cockpit_provider">{providers}</select>'
            '<label for="ai_cockpit_model">Model</label>'
            f'<input id="ai_cockpit_model" name="ai_cockpit_model" maxlength="80" '
            f'value="{escape(v["ai_cockpit_model"])}">'
        )
    body = f"""<p class="sub">New game</p>{_waiting_banner(waiting)}{err}
<form method="post" action="/new" class="card">
<label for="name">Game name</label><input id="name" name="name" maxlength="40" required value="{escape(v['name'])}">
<fieldset><legend>Rules</legend>
<label for="rules">Rule set</label><select id="rules" name="rules">{_opt('v311', 'v3.11 (recommended)', v['rules'])}{_opt('legacy', 'Legacy (this project)', v['rules'])}</select>
<p class="note" id="rulesPortHint">Ports open full and restock 5% of max each dawn.</p>
<label for="starting_package">Starting package</label><select id="starting_package" name="starting_package">{_opt('v311', 'v3.11 starting package', v['starting_package'])}{_opt('classic', 'Classic (legacy rules only)', v['starting_package'])}</select>
<p class="note">v3.11 rules always use the v3.11 starting package.</p>
<label for="starting_credits">Starting credits</label><select id="starting_credits" name="starting_credits">{_opt('original', 'Original (v3.11 default, 300 cr)', v['starting_credits'])}{_opt('10000', '10,000', v['starting_credits'])}{_opt('100000', '100,000', v['starting_credits'])}{_opt('1000000', '1,000,000', v['starting_credits'])}{_opt('custom', 'Custom', v['starting_credits'])}</select>
<label for="starting_credits_custom">Custom amount</label><input id="starting_credits_custom" name="starting_credits_custom" type="number" min="0" max="10000000" value="{escape(v['starting_credits_custom'])}">
<p class="note">Original leaves the package as it is (300 cr under v3.11). A preset or a custom amount, 0 to 10,000,000, is the opening credits for every human and every bot.</p>
<label for="turns_per_day">Turns per day</label><select id="turns_per_day" name="turns_per_day">{_opt('original', 'Original (250)', v['turns_per_day'])}{_opt('500', '500', v['turns_per_day'])}{_opt('1000', '1,000', v['turns_per_day'])}{_opt('custom', 'Custom', v['turns_per_day'])}</select>
<label for="turns_per_day_custom">Custom turns per day</label><input id="turns_per_day_custom" name="turns_per_day_custom" type="number" min="50" max="5000" value="{escape(v['turns_per_day_custom'])}">
<p class="note">Original is 250 turns for every seat, the same pocket as today. 500, 1,000, or a custom amount from 50 to 5,000 replaces that pocket for every human and every bot.</p>
<label for="universe_size">Universe size</label><select id="universe_size" name="universe_size">{sizes}</select>
<label for="max_days">Max days</label><input id="max_days" name="max_days" type="number" min="1" max="365" value="{escape(v['max_days'])}">
{length_fields}<label for="day">Day length</label><select id="day" name="day">{days}</select>
<p class="note" id="dayHint">{escape(day_length_hint(int((presets or DAY_PRESETS).get(v['day'], 1800)), hint_turns, int(v['max_days'] or 30)))}</p>
<script>
const dayPresets = {json.dumps(presets or DAY_PRESETS)};
function paintDayHint() {{
  const secs = dayPresets[document.getElementById("day").value] || 0;
  const picked = document.getElementById("turns_per_day").value;
  const turns = picked === "custom"
    ? (Number(document.getElementById("turns_per_day_custom").value) || 250)
    : (picked === "original" || picked === "" ? 250 : (Number(picked) || 250));
  const days = Number(document.getElementById("max_days").value) || 1;
  const per = secs / turns;
  const every = per < 90 ? (Math.round(per * 10) / 10).toString().replace(/\\.0$/, "") + " s"
    : (Math.round(per / 6) / 10).toString().replace(/\\.0$/, "") + " min";
  const total = secs * days;
  let span;
  if (total % 86400 === 0) span = (total / 86400) + " real day" + (total === 86400 ? "" : "s");
  else {{
    const h = Math.floor(total / 3600), m = Math.floor((total % 3600) / 60);
    span = h && m ? h + " h " + m + " min" : (h ? h + " h" : m + " min");
  }}
  let name = secs % 60 === 0 && secs < 3600 ? (secs / 60) + " min" : (secs % 3600 === 0 ? (secs / 3600) + " h" : secs + " s");
  if (secs === 86400) name = "24 h";
  const hint = secs >= 86400
    ? name + " days: a turn comes back every " + every + ", like the original; " + days + " days take " + span
    : (per < 60
      ? name + " days: " + days + " days take about " + span + "; a turn comes back every " + every + ", so turns rarely run out"
      : name + " days: " + days + " days take about " + span + "; a turn comes back every " + every);
  document.getElementById("dayHint").textContent = hint;
}}
["day", "turns_per_day", "turns_per_day_custom", "max_days"].forEach((id) => document.getElementById(id).addEventListener("input", paintDayHint));
</script>
{length_script}
</fieldset>
<fieldset><legend>Players</legend>
<label for="home_planet_name">Home planet name</label><input id="home_planet_name" name="home_planet_name" maxlength="30" value="{escape(v['home_planet_name'])}">
<p class="note">Optional. 1 to 30 characters. Blank uses your trader name plus 's Home.</p>
<label for="humans">Open human seats</label><select id="humans" name="humans">{humans}</select>
<label for="bots">Code bots</label><select id="bots" name="bots">{bots}</select>
{ai_fields}{ai_script}<label for="ferrengi">Ferrengi</label><select id="ferrengi" name="ferrengi">{_opt('on', 'On', v['ferrengi'])}{_opt('off', 'Off', v['ferrengi'])}</select>
{cockpit_fields}<label for="visibility">Who can find it</label><select id="visibility" name="visibility">{_opt('listed', 'Listed in the lobby', v['visibility'])}{_opt('link', 'Link only', v['visibility'])}</select>
<input type="hidden" name="hold_until_human" value="off">
<label class="check" for="hold_until_human"><input id="hold_until_human" name="hold_until_human" type="checkbox" value="on"{hold_checked}>Hold the clock until the first player opens a seat</label>
<p class="note">On for a new game from this form. The day clock and the bots wait until someone opens a seat. Uncheck to start at once, which is how games start today when this box is left off.</p>
</fieldset>
<button class="primary" type="submit">Create game</button> <a class="btn" href="/">Cancel</a>
</form>"""
    return page("New game", body, brand=brand)


def created(brand: str, *, game: dict[str, Any], join_links: list[tuple[str, str]], watch_link: str,
            cockpit: dict[str, Any] | None = None) -> str:
    links = "".join(f"<p>Seat {escape(seat)}<code class=\"link\">{escape(url)}</code></p>" for seat, url in join_links)
    settings = game.get("settings") or {}
    key = _day_label(int(settings["day_seconds"])) if settings.get("day_seconds") else ""
    length = _DAY_NAMES.get(key, key)
    shown = f"<p>Day length: {escape(length)}</p>" if length else ""
    if settings.get("game_length") == "full":
        shown += "<p>Full-length game. The daily turn limit is the v3.11 pocket, lowered when the game is longer than 30 days.</p>"
    ai_n = 0
    try:
        ai_n = int(settings.get("ai_opponents") or 0)
    except (TypeError, ValueError):
        ai_n = 0
    ai_line = ""
    if ai_n > 0:
        brain = str(settings.get("ai_brain") or "heuristic")
        label = ai_label(brain)
        try:
            turns_n = int(settings.get("turns_per_day") or 0)
        except (TypeError, ValueError):
            turns_n = 0
        ai_line = (
            f"<p>{ai_n} {escape(label)}. Those seats are not join links. "
            f"{escape(ai_call_estimate(turns_n, ai_n, brain))}</p>"
        )
    cockpit_line = ""
    seats = list((cockpit or {}).get("seats") or [])
    if seats:
        blocks = []
        for item in seats:
            href = escape(str(item.get("href") or ""))
            seat = escape(str(item.get("seat") or "the AI seat"))
            stop = escape(str(item.get("stop") or ""))
            blocks.append(
                f'<p data-cockpit="status">{escape(str(item.get("status") or ""))}</p>'
                f'<p><a class="btn" href="{href}" data-cockpit="seat">Open {seat}</a> '
                f'<form method="post" action="{stop}" style="display:inline">'
                f'<button type="submit" data-cockpit="stop">Stop {seat}</button></form></p>'
            )
        cockpit_line = "".join(blocks)
    elif cockpit and cockpit.get("status"):
        href = escape(cockpit.get("href") or "")
        seat = escape(cockpit.get("seat") or "the AI seat")
        cockpit_line = (
            f'<p data-cockpit="status">{escape(cockpit["status"])}</p>'
            f'<p>Watch it on the spectator link above, or open the seat view '
            f'<a class="btn" href="{href}" data-cockpit="seat">Open {seat}</a>.</p>'
        )
    body = (f"<p class=\"sub\">Game created</p><div class=\"card\"><h2>{escape(game['name'])}</h2>"
            f"{shown}{ai_line}{cockpit_line}"
            "<p>One join link per open seat. Send each link to one player; the first person to open it gets the seat.</p>"
            f"{links}<p>Watch link (read-only)<code class=\"link\">{escape(watch_link)}</code></p>"
            f"<form method=\"post\" action=\"/games/{game['id']}/join\" style=\"display:inline\">"
            "<button class=\"primary\" type=\"submit\">Take a seat myself</button></form> "
            "<a class=\"btn\" href=\"/\">Back to the lobby</a></div>")
    return page("Game created", body, brand=brand)


def join_confirm(brand: str, *, game: dict[str, Any], seat: str, key: str, error: str | None = None) -> str:
    err = f"<div class=\"err\">{escape(error)}</div>" if error else ""
    settings = game.get("settings") or {}
    key = _day_label(int(settings["day_seconds"])) if settings.get("day_seconds") else ""
    length = _DAY_NAMES.get(key, key)
    shown = f"<p>Day length: {escape(length)}</p>" if length else ""
    body = (f"<p class=\"sub\">Join a game</p><div class=\"card\"><h2>{escape(game['name'])}</h2>"
            f"{shown}"
            f"<p>You were invited to seat {escape(seat)}.</p>{err}"
            f"<form method=\"post\" action=\"/games/{game['id']}/join\">"
            f"<input type=\"hidden\" name=\"seat\" value=\"{escape(seat)}\"><input type=\"hidden\" name=\"k\" value=\"{escape(key)}\">"
            "<label for=\"home_planet_name\">Home planet name</label>"
            "<input id=\"home_planet_name\" name=\"home_planet_name\" maxlength=\"30\">"
            "<p class=\"note\">Optional. 1 to 30 characters. Blank keeps the name from the new-game form.</p>"
            "<button class=\"primary\" type=\"submit\">Take this seat</button></form></div>")
    return page("Join", body, brand=brand)


def message(brand: str, title: str, text: str, *, back: bool = True, refresh_s: int | None = None) -> str:
    link = "<p><a class=\"btn\" href=\"/\">Back to the lobby</a></p>" if back else ""
    return page(title, f"<div class=\"card\"><h2>{escape(title)}</h2><p>{escape(text)}</p>{link}</div>",
                brand=brand, refresh_s=refresh_s)


def waking(brand: str, name: str) -> str:
    return message(brand, "Waking up", f"{name} was sleeping. It is starting again; this page refreshes by itself.",
                   refresh_s=4)


def admin(brand: str, *, games: list[dict[str, Any]], workers: dict[str, dict[str, Any]], closed: bool,
          csrf: str) -> str:
    rows = []
    for g in games:
        w = workers.get(g["id"], {})
        stop = "".join(
            f"<form method=\"post\" action=\"/admin/games/{g['id']}/{act}\" style=\"display:inline\">"
            f"<input type=\"hidden\" name=\"csrf\" value=\"{csrf}\"><button class=\"{cls}\" type=\"submit\">{label}</button>"
            "</form> " for act, cls, label in (("sleep", "", "Sleep"), ("stop", "warn", "Stop"))) if w else ""
        age = time.time() - g["created_at"]
        rows.append(
            f"<tr><td><b>{escape(g['name'])}</b><br><span class=\"note\">{g['id']} &middot; {age / 3600:.1f} h old</span></td>"
            f"<td>{_status_tag(g['status'])}</td><td>{g.get('port') or ''}</td><td>{w.get('pid', '')}</td>"
            f"<td>{w.get('cpu', '')}</td><td>{w.get('rss_mb', '')}</td><td>{stop}</td></tr>")
    kill_label = "Reopen the beta" if closed else "Kill switch: stop every game and close the beta"
    kill_action = "/admin/open" if closed else "/admin/kill"
    body = (f"<p class=\"sub\">Local admin (this PC only)</p>"
            f"<form method=\"post\" action=\"{kill_action}\"><input type=\"hidden\" name=\"csrf\" value=\"{csrf}\">"
            f"<button class=\"{'primary' if closed else 'warn'}\" type=\"submit\">{kill_label}</button></form>"
            "<div class=\"card\"><table><thead><tr><th>Game</th><th>Status</th><th>Port</th><th>PID</th><th>CPU %</th>"
            "<th>RAM MB</th><th></th></tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>")
    return page("Admin", body, brand=brand)
