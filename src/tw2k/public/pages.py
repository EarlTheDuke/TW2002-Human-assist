"""Server-rendered lobby pages (plain HTML + one stylesheet, no scripts beyond a refresh)."""

from __future__ import annotations

import time
from html import escape
from typing import Any, Iterable

from .security import DAY_PRESETS, UNIVERSE_SIZES, credits_phrase

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
label{display:block;margin:12px 0 4px;color:#b8c8da}
input,select{width:100%;max-width:420px;background:#070b14;color:#e8f6ff;border:1px solid #2a3a55;border-radius:8px;
  padding:10px;font:inherit;min-height:44px}
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
        f"<h1>{escape(brand)}</h1>{body}</main>"
        "<footer>Closed beta test games &middot; <a href=\"/about\">About these test games</a></footer>"
        "</body></html>"
    )


def disclaimer(brand: str, next_url: str = "/") -> str:
    points = "".join(f"<li>{escape(p)}</li>" for p in DISCLAIMER_POINTS)
    body = (
        "<p class=\"sub\">Before you play</p><div class=\"card\"><ul class=\"points\">" + points + "</ul>"
        "<form method=\"post\" action=\"/accept\">"
        f"<input type=\"hidden\" name=\"next\" value=\"{escape(next_url)}\">"
        "<button class=\"primary\" type=\"submit\">I understand</button></form></div>"
    )
    return page("Before you play", body, brand=brand)


def about(brand: str) -> str:
    points = "".join(f"<li>{escape(p)}</li>" for p in DISCLAIMER_POINTS)
    body = ("<p class=\"sub\">About these test games</p><div class=\"card\"><ul class=\"points\">" + points +
            "</ul><p><a class=\"btn\" href=\"/\">Back to the lobby</a></p></div>")
    return page("About", body, brand=brand)


def _status_tag(status: str) -> str:
    return f"<span class=\"tag {escape(status)}\">{escape(status)}</span>"


_DAY_NAMES = {"10m": "10 minutes", "30m": "30 minutes", "1h": "1 hour", "24h": "24 hours"}


def _day_label(seconds: int) -> str:
    for k, v in DAY_PRESETS.items():
        if v == int(seconds):
            return k
    return f"{int(seconds)}s"


def lobby(brand: str, *, games: Iterable[dict[str, Any]], mine: Iterable[dict[str, Any]], closed: bool,
          full: bool, live: dict[str, dict[str, Any]]) -> str:
    mine = list(mine)
    seated = {g["id"] for g in mine}
    rows = []
    for g in games:
        s = g["settings"]
        info = live.get(g["id"], {})
        day = f"day {info['day']}" if info.get("day") is not None else ""
        open_seats = g.get("open_seats", 0)
        join = (f"<form method=\"post\" action=\"/games/{g['id']}/join\" style=\"display:inline\">"
                "<button class=\"primary\" type=\"submit\">Join</button></form>") if open_seats and not closed else ""
        watch = "" if g["id"] in seated else f"<a class=\"btn\" href=\"/g/{g['id']}/watch\">Watch</a>"
        rows.append(
            f"<tr><td><b>{escape(g['name'])}</b><br><span class=\"note\">"
            f"{'v3.11' if s['rules'] == 'v311' else 'legacy'} rules &middot; {s['universe_size']} sectors &middot; "
            f"{_day_label(s['day_seconds'])} days &middot; {s['bots']} bots<br>{escape(credits_phrase(s))}</span></td>"
            f"<td>{_status_tag(g['status'])} <span class=\"note\">{escape(day)}</span></td>"
            f"<td>{open_seats} of {s['humans']} seats open</td><td>{join} {watch}</td></tr>"
        )
    table = ("<table class=\"games\"><thead><tr><th>Game</th><th>Status</th><th>Seats</th><th></th></tr></thead>"
             "<tbody>" + "".join(rows) + "</tbody></table>") if rows else "<p class=\"note\">No open games yet.</p>"
    my_rows = "".join(
        f"<tr><td><b>{escape(g['name'])}</b> &middot; seat {escape(g['my_seat'])}</td><td>{_status_tag(g['status'])}</td>"
        f"<td><a class=\"btn primary\" href=\"/resume/{g['id']}\">Resume my seat</a></td></tr>"
        for g in mine if g["status"] not in ("archived",)
    )
    mine_html = (f"<h2>Your seats</h2><div class=\"card\"><table class=\"games\"><tbody>{my_rows}</tbody></table></div>"
                 if my_rows else "")
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
            f"<div class=\"card\">{table}</div>")
    return page("Lobby", body, brand=brand)


def _opt(value: str, label: str, selected: str) -> str:
    sel = " selected" if str(value) == str(selected) else ""
    return f"<option value=\"{escape(str(value))}\"{sel}>{escape(label)}</option>"


def new_game(brand: str, *, error: str | None = None, values: dict[str, Any] | None = None,
             presets: dict[str, int] | None = None) -> str:
    v = {"name": "", "rules": "v311", "universe_size": "1000", "max_days": "30", "turns_per_day": "250",
         "starting_package": "v311", "bots": "2", "ferrengi": "on", "day": "30m", "humans": "1",
         "visibility": "listed", "starting_credits": "original", "starting_credits_custom": "",
         "home_planet_name": ""}
    v.update({k: str(val) for k, val in (values or {}).items()})
    err = f"<div class=\"err\">{escape(error)}</div>" if error else ""
    sizes = "".join(_opt(str(n), f"{n} sectors", v["universe_size"]) for n in UNIVERSE_SIZES)
    days = "".join(_opt(k, _DAY_NAMES.get(k, f"{k} ({secs} s)"), v["day"])
                   for k, secs in (presets or DAY_PRESETS).items())
    bots = "".join(_opt(str(n), str(n), v["bots"]) for n in range(6))
    humans = "".join(_opt(str(n), str(n), v["humans"]) for n in range(1, 5))
    body = f"""<p class="sub">New game</p>{err}
<form method="post" action="/new" class="card">
<label for="name">Game name</label><input id="name" name="name" maxlength="40" required value="{escape(v['name'])}">
<fieldset><legend>Rules</legend>
<label for="rules">Rule set</label><select id="rules" name="rules">{_opt('v311', 'v3.11 (recommended)', v['rules'])}{_opt('legacy', 'Legacy (this project)', v['rules'])}</select>
<label for="starting_package">Starting package</label><select id="starting_package" name="starting_package">{_opt('v311', 'v3.11 starting package', v['starting_package'])}{_opt('classic', 'Classic (legacy rules only)', v['starting_package'])}</select>
<p class="note">v3.11 rules always use the v3.11 starting package.</p>
<label for="starting_credits">Starting credits</label><select id="starting_credits" name="starting_credits">{_opt('original', 'Original (v3.11 default, 300 cr)', v['starting_credits'])}{_opt('10000', '10,000', v['starting_credits'])}{_opt('100000', '100,000', v['starting_credits'])}{_opt('1000000', '1,000,000', v['starting_credits'])}{_opt('custom', 'Custom', v['starting_credits'])}</select>
<label for="starting_credits_custom">Custom amount</label><input id="starting_credits_custom" name="starting_credits_custom" type="number" min="0" max="10000000" value="{escape(v['starting_credits_custom'])}">
<p class="note">Original leaves the package as it is (300 cr under v3.11). A preset or a custom amount, 0 to 10,000,000, is the opening credits for every human and every bot.</p>
<label for="universe_size">Universe size</label><select id="universe_size" name="universe_size">{sizes}</select>
<label for="max_days">Max days</label><input id="max_days" name="max_days" type="number" min="1" max="365" value="{escape(v['max_days'])}">
<label for="turns_per_day">Turns per day</label><input id="turns_per_day" name="turns_per_day" type="number" min="20" max="2000" value="{escape(v['turns_per_day'])}">
<label for="day">Day length</label><select id="day" name="day">{days}</select>
</fieldset>
<fieldset><legend>Players</legend>
<label for="home_planet_name">Home planet name</label><input id="home_planet_name" name="home_planet_name" maxlength="30" value="{escape(v['home_planet_name'])}">
<p class="note">Optional. 1 to 30 characters. Blank uses your trader name plus 's Home.</p>
<label for="humans">Open human seats</label><select id="humans" name="humans">{humans}</select>
<label for="bots">Code bots</label><select id="bots" name="bots">{bots}</select>
<label for="ferrengi">Ferrengi</label><select id="ferrengi" name="ferrengi">{_opt('on', 'On', v['ferrengi'])}{_opt('off', 'Off', v['ferrengi'])}</select>
<label for="visibility">Who can find it</label><select id="visibility" name="visibility">{_opt('listed', 'Listed in the lobby', v['visibility'])}{_opt('link', 'Link only', v['visibility'])}</select>
</fieldset>
<button class="primary" type="submit">Create game</button> <a class="btn" href="/">Cancel</a>
</form>"""
    return page("New game", body, brand=brand)


def created(brand: str, *, game: dict[str, Any], join_links: list[tuple[str, str]], watch_link: str) -> str:
    links = "".join(f"<p>Seat {escape(seat)}<code class=\"link\">{escape(url)}</code></p>" for seat, url in join_links)
    body = (f"<p class=\"sub\">Game created</p><div class=\"card\"><h2>{escape(game['name'])}</h2>"
            "<p>One join link per open seat. Send each link to one player; the first person to open it gets the seat.</p>"
            f"{links}<p>Watch link (read-only)<code class=\"link\">{escape(watch_link)}</code></p>"
            f"<form method=\"post\" action=\"/games/{game['id']}/join\" style=\"display:inline\">"
            "<button class=\"primary\" type=\"submit\">Take a seat myself</button></form> "
            "<a class=\"btn\" href=\"/\">Back to the lobby</a></div>")
    return page("Game created", body, brand=brand)


def join_confirm(brand: str, *, game: dict[str, Any], seat: str, key: str, error: str | None = None) -> str:
    err = f"<div class=\"err\">{escape(error)}</div>" if error else ""
    body = (f"<p class=\"sub\">Join a game</p><div class=\"card\"><h2>{escape(game['name'])}</h2>"
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
