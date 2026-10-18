# selfhost-beta-v1 — closed beta on Ben's PC (COMMANDER NOTE 61)

Up to 10 games at once for 5-10 invited players, served from this PC through a Cloudflare
Tunnel. Code bots only (no LLM seats, no AI-key field, no voice). v3.11 rules by default.

## What runs where

| Piece | Where | Notes |
|---|---|---|
| Lobby (`tw2k lobby`) | `127.0.0.1:8099` | front door, new-game screen, join links, proxy for `/g/<id>/...` |
| Game workers (`tw2k serve`) | `127.0.0.1:8100`-`8119` | one process per game, started and owned by the lobby |
| State | `saves\selfhost\` (gitignored via `saves/`) | `lobby.sqlite3`, `lobby.key`, `games\<id>\snapshots`, `archive\`, `logs\` |
| Tunnel (`cloudflared`) | this PC, outbound only | sends `https://<your host>` to `http://127.0.0.1:8099` |

The lobby binds loopback only. It checks every game port right before use, skips busy ones,
and never touches a port outside `TW2K_GAME_PORTS` or a process it did not start. It refuses to
start with any port in 8031-8098. Workers sit in a Windows Job Object, so they end when the
lobby ends (even on a crash). Stop is graceful first (snapshot, then exit), then
`taskkill /T` on the lobby's own worker PID only.

Settings (env, all optional): `TW2K_LOBBY_PORT` (8099), `TW2K_GAME_PORTS` (8100-8119),
`TW2K_LOBBY_ROOT` (saves\selfhost), `TW2K_LOBBY_IDLE_MIN` (30), `TW2K_LOBBY_ARCHIVE_DAYS` (7),
`TW2K_LOBBY_MAX_GAMES` (10), `TW2K_LOBBY_MAX_SEATS` (10), `TW2K_BRAND` (Galaxy War Command),
`TW2K_LOBBY_DAY_PRESETS` (extra day lengths, e.g. `2m=120`, for tests), `TW2K_STATUS_ORIGINS`
(CORS origins for `/status`, default `https://thesingularity.netlify.app`).

## Start and stop (this PC)

```powershell
cd "C:\Users\sugar\Desktop\ALL AI GAMES\Projects in prgress\TW2002 Human assist cursor"
powershell -ExecutionPolicy Bypass -File scripts\selfhost\start.ps1          # lobby only
powershell -ExecutionPolicy Bypass -File scripts\selfhost\start.ps1 -Quick   # lobby + Quick Tunnel
powershell -ExecutionPolicy Bypass -File scripts\selfhost\status.ps1
powershell -ExecutionPolicy Bypass -File scripts\selfhost\stop.ps1           # snapshots every game, then stops
```

The admin page is `http://127.0.0.1:8099/admin`. It answers only on this PC: a request that
came through the tunnel carries Cloudflare headers and gets a 404. It lists every game with
port, PID, CPU and RAM, and has Sleep and Stop per game plus a kill switch that stops every
game and closes the beta to new games and joins until "Reopen the beta" is pressed.

## Cloudflare Tunnel

The tunnel is an outbound connection from this PC to Cloudflare. It **does not expose** Ben's
home IP address and opens **no** inbound ports on the router or Windows firewall; players only
ever see Cloudflare's addresses. Cur does not sign in to Cloudflare, create tunnels or change
DNS. Every step below that touches the Cloudflare account is Ben's.

### 1. Install cloudflared

```powershell
winget install --id Cloudflare.cloudflared
cloudflared --version
```

### 2. First test: a Quick Tunnel (no account, no domain)

```powershell
cloudflared tunnel --url http://127.0.0.1:8099
```

It prints a random `https://<words>.trycloudflare.com` address. Open it on a phone on mobile
data, accept the notice, create a game, take a seat, and check the cockpit updates (that proves
websockets and long polls work through the tunnel). The address changes every run and the
tunnel stops when the window closes (Ctrl+C). Good for a first test and for Commander's retest;
not for the beta itself.

### 3. The real beta: a named tunnel

A named tunnel needs a domain whose DNS is on Cloudflare (a cheap domain added to Ben's
Cloudflare account). `thesingularity.netlify.app` cannot be used: it is a Netlify subdomain and
its DNS is not Ben's to point at a tunnel. Below, `play.example.com` stands for the chosen name.

```powershell
cloudflared tunnel login                 # Ben signs in in the browser; saves cert.pem
cloudflared tunnel create gwc-beta       # prints the tunnel UUID and writes <UUID>.json
cloudflared tunnel route dns gwc-beta play.example.com
```

`%USERPROFILE%\.cloudflared\config.yml`:

```yaml
tunnel: gwc-beta
credentials-file: C:\Users\sugar\.cloudflared\<UUID>.json
ingress:
  - hostname: play.example.com
    service: http://127.0.0.1:8099
  - service: http_status:404
```

The last rule is the catch-all: any other host name gets a 404 and nothing else on this PC is
reachable. Check and run it:

```powershell
cloudflared tunnel ingress validate
cloudflared tunnel run gwc-beta
```

### 4. Run it as a Windows service

```powershell
cloudflared service install              # elevated PowerShell; uses the config.yml above
Get-Service cloudflared
```

The service starts with Windows. The lobby itself is started with `scripts\selfhost\start.ps1`
(or a Task Scheduler entry "At log on" running that script).

### 5. Websocket check

Cloudflare Tunnel passes websockets by default (no setting needed). Check it once through the
public address: open a game's Watch page and press F12, Network, filter "WS". The `/g/<id>/ws`
row must show status 101 and new frames as the game runs; the event feed on the page keeps
moving. The lobby proxies that websocket both ways to the game worker.

### 6. How to stop

* Players: `scripts\selfhost\stop.ps1` (saves every game first). Games come back with the same
  seats when the lobby starts again; players press "Resume my seat" (their old seat token was
  rotated).
* Tunnel: Quick Tunnel — Ctrl+C in its window. Service — `Stop-Service cloudflared` (elevated);
  remove with `cloudflared service uninstall`. Delete the tunnel with
  `cloudflared tunnel delete gwc-beta` and the DNS record in the Cloudflare dashboard.
* Emergency: the kill switch on `http://127.0.0.1:8099/admin`.

### 7. Keep the PC awake

```powershell
powercfg /change standby-timeout-ac 0
powercfg /change hibernate-timeout-ac 0
```

Leave the screen allowed to turn off (`powercfg /change monitor-timeout-ac 10`). Windows Update
restarts: set active hours to cover the beta, or pause updates for the test week.

What players see when the PC sleeps or reboots: the tunnel drops, so Cloudflare shows its own
"origin unreachable" error page (502/1033) instead of the lobby. Nothing is lost beyond the last
snapshot (every day roll and every 5 minutes). After the PC is back and `start.ps1` has run, games
that were running restart from their snapshots, and players press "Resume my seat".

## Security notes (what the lobby enforces)

* Guest cookie `gwc_guest`: 32 random bytes, HttpOnly, SameSite=Lax, Secure on https. The lobby
  stores only its SHA-256.
* A seat token is made fresh, set on the worker over a loopback-only route, and handed to the
  player once through `/g/<id>/bot/claim` (which turns it into the seat cookie). The lobby keeps
  only its SHA-256; workers get tokens by environment variable, never a file.
* In public mode a worker answers `/control/*`, `/api/*` and everything else outside the cockpit,
  harness, claim, static and spectator routes only for a loopback call carrying its per-game
  lobby secret. A worker refuses to start in public mode without its spectator token and secret.
* Rate limits per player IP (`CF-Connecting-IP`, trusted only from the local tunnel) and per
  guest: 3 new games an hour, 20 joins per 10 minutes, 12 seat actions a second. 64 KB body cap.
  Every new-game field is checked against a fixed list.
* Logs (`saves\selfhost\logs\`, rotated) carry an HMAC tag of the IP and 8 hex of the guest hash;
  never tokens, cookies or full IPs.

## Netlify play link

Plan only. The EarlTheDuke/singularity-portfolio repo (https://thesingularity.netlify.app/) is not
cloned, edited or pushed in this NOTE. Its public file list was read on GitHub: it is a static
site (`index.html` plus one page per project such as `galaxy-explorer.html`), `netlify.toml`
for headers and redirects, and one function `netlify/functions/proxy.js`. `netlify.toml` sets
`X-Frame-Options: SAMEORIGIN` and no Content-Security-Policy, so the portfolio itself needs no
`connect-src` or `frame-src` change to fetch `/status` or show an iframe.

Below, `play.example.com` stands for the named-tunnel host Ben picks.

* **Button**: on the portfolio home page, a project card with a
  "Play Galaxy War Command (beta)" button: `<a href="https://play.example.com/" target="_blank"
  rel="noopener">`. Under it a one-line badge filled by
  `fetch("https://play.example.com/status")`: "Beta online - N games running" / "Beta full" /
  "Beta closed" from the JSON, or "Beta offline" when the fetch fails (the PC is asleep or off).
* **Status**: `GET /status` returns `{"online", "brand", "games_running", "open_seats", "full",
  "closed"}` with `Cache-Control: no-store`. The lobby sends `Access-Control-Allow-Origin` only
  for origins in `TW2K_STATUS_ORIGINS` (default `https://thesingularity.netlify.app`), never `*`.
* **Demo iframe**: a watch-only view of an always-on demo game (code bots only, no human seat,
  started from the admin page). Lobby work for a later NOTE: a `/demo` route that serves the
  spectator view of the one game marked as the demo, with the disclaimer shown as a banner
  inside the frame instead of the accept gate, and the spectator token injected by the lobby
  (no cookie, because third-party cookies are blocked in many browsers). Every other lobby
  page keeps `X-Frame-Options: DENY` and `Content-Security-Policy: frame-ancestors 'none'`;
  only `/demo` (and its `/g/<demo id>/` assets) would send
  `Content-Security-Policy: frame-ancestors https://thesingularity.netlify.app` (a new
  `TW2K_FRAME_ORIGINS` setting). Fallback when the PC is offline: the page shows a static
  screenshot (the spectator screen from `docs/playtests/selfhost-beta-v1/spectator-1920.png`)
  with the caption "The demo runs on a home PC and is offline right now".
* **files to change** in singularity-portfolio (Ben's call, not done here):
  * `index.html` - add the project card, the button and the small status script.
  * `galaxy-war-command.html` (new) - the demo page: the iframe
    `<iframe src="https://play.example.com/demo" loading="lazy" title="Galaxy War Command demo">`,
    the offline fallback image, and the same button.
  * `assets/galaxy-war-command/demo-1920.png` (new) - the fallback screenshot.
  * `netlify.toml` - two `[[redirects]]`: `/play` to `https://play.example.com/` (302) and
    `/galaxy-war-command` to `/galaxy-war-command.html`. No header change is needed.
  * In this repo (later NOTE): `src/tw2k/public/lobby.py` (`/demo`, `TW2K_FRAME_ORIGINS`) and
    `src/tw2k/public/pages.py` (the demo banner).
