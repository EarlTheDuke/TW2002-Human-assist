#!/bin/sh
# Open a free temporary Cloudflare quick tunnel to a lobby that is already running.
# This script never starts, stops, or restarts the game server. Ben runs that himself.
set -eu

PORT=""
if [ "${1:-}" = "--port" ]; then
  PORT="${2:-}"
fi
if [ -z "$PORT" ]; then
  PORT="${TW2K_LOBBY_PORT:-8099}"
fi

if ! command -v cloudflared >/dev/null 2>&1; then
  cat <<'EOF'
cloudflared is not installed.

Official install steps:
  Windows (winget):  winget install --id Cloudflare.cloudflared
  macOS (Homebrew):  brew install cloudflared
  Other systems:     https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/downloads/
EOF
  exit 1
fi

echo "Sharing the lobby that is already running at http://127.0.0.1:${PORT}"
echo "This script does not start, stop, or restart the game server."
echo "Press Ctrl+C to stop the tunnel. The lobby keeps running."
echo "The public link changes on every run. Old links stop working."
echo ""

cloudflared tunnel --no-autoupdate --url "http://127.0.0.1:${PORT}" 2>&1 | awk '
  /https:\/\/[a-z0-9-]+\.trycloudflare\.com/ && !seen {
    seen = 1
    if (match($0, /https:\/\/[a-z0-9-]+\.trycloudflare\.com/)) {
      pub = substr($0, RSTART, RLENGTH)
      print ""
      print "Public link: " pub
      print "Lobby:       " pub "/"
      print "Seat:        " pub "/g/<game-id>/bot?seat=<seat>&token=<token>&layout=redesign"
      print "Send each seat link to one player. The token is the password for that seat."
      print ""
    }
  }
  { print }
'
