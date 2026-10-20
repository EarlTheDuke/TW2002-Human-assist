"""cloudflare-share-v1. Public lobby and seat links follow the page, including https/wss."""

from __future__ import annotations

from pathlib import Path

from tw2k.public.share_url import (
    lobby_link,
    rebase_onto,
    request_origin,
    seat_link,
    websocket_url,
)
from tw2k.public.worker import rewrite_location, rewrite_text

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
PAGE = "https://blue-pond.trycloudflare.com/g/ab12/bot?layout=redesign"
LOCAL = "http://127.0.0.1:8099/bot"


def test_proxied_seat_link_keeps_token_and_layout_on_the_public_origin() -> None:
    origin = request_origin(
        {"host": "127.0.0.1:8099", "x-forwarded-host": "blue-pond.trycloudflare.com", "x-forwarded-proto": "https"},
        "http",
        "127.0.0.1:8099",
    )
    assert origin == "https://blue-pond.trycloudflare.com"
    assert lobby_link(origin) == "https://blue-pond.trycloudflare.com/"
    link = seat_link(origin, "ab12", "P1", "sekret")
    assert link == "https://blue-pond.trycloudflare.com/g/ab12/bot?seat=P1&token=sekret&layout=redesign"
    moved = rebase_onto(PAGE, "http://127.0.0.1:8099/g/ab12/bot?seat=P1&token=sekret&layout=redesign")
    assert moved == link
    assert "127.0.0.1" not in moved


def test_websocket_follows_the_page_scheme() -> None:
    assert websocket_url(PAGE, "/g/ab12/ws") == "wss://blue-pond.trycloudflare.com/g/ab12/ws"
    assert websocket_url(LOCAL) == "ws://127.0.0.1:8099/ws"
    moved = rebase_onto(PAGE, "ws://127.0.0.1:8102/g/ab12/ws")
    assert moved == "wss://blue-pond.trycloudflare.com/g/ab12/ws"
    local = rebase_onto(LOCAL, "ws://127.0.0.1:8099/ws")
    assert local == "ws://127.0.0.1:8099/ws"


def test_loopback_redirect_becomes_a_path_on_the_game_prefix() -> None:
    loc = rewrite_location(
        "http://127.0.0.1:8102/bot?seat=P1&token=sekret&layout=redesign",
        "/g/ab12",
    )
    assert loc == "/g/ab12/bot?seat=P1&token=sekret&layout=redesign"
    assert "127.0.0.1" not in loc
    assert rewrite_location("https://blue-pond.trycloudflare.com/bot?seat=P1", "/g/ab12") == (
        "https://blue-pond.trycloudflare.com/bot?seat=P1"
    )


def test_served_scripts_follow_the_proxy_and_stay_put_locally() -> None:
    bot = (WEB / "bot.js").read_text(encoding="utf-8")
    app = (WEB / "app.js").read_text(encoding="utf-8")
    play = (WEB / "play.js").read_text(encoding="utf-8")
    redesign = (WEB / "redesign.js").read_text(encoding="utf-8")
    assert rewrite_text("/static/bot.js", bot, base="", brand_name="") == bot
    assert rewrite_text("/static/app.js", app, base="", brand_name="") == app

    proxied_bot = rewrite_text("/static/bot.js", bot, base="/g/ab12", brand_name="")
    assert "`/g/ab12/harness/v1" in proxied_bot
    assert "`/harness/v1" not in proxied_bot

    proxied_app = rewrite_text("/static/app.js", app, base="/g/ab12", brand_name="")
    assert "${location.host}/g/ab12/ws" in proxied_app
    assert 'location.protocol === "https:" ? "wss:" : "ws:"' in proxied_app

    proxied_play = rewrite_text("/static/play.js", play, base="/g/ab12", brand_name="")
    assert "${window.location.host}/g/ab12/ws" in proxied_play
    assert "window.location.protocol === \"https:\" ? \"wss:\" : \"ws:\"" in proxied_play

    proxied_redesign = rewrite_text("/static/redesign.js", redesign, base="/g/ab12", brand_name="")
    assert '"/g/ab12/harness/v1"' in proxied_redesign
    assert '"/api/games/' in proxied_redesign

    embedded = rewrite_text(
        "/bot",
        'new WebSocket("ws://127.0.0.1:8099/ws"); <a href="http://127.0.0.1:8099/g/ab12/bot?seat=P1&token=sekret&layout=redesign">',
        base="/g/ab12",
        brand_name="",
    )
    assert "127.0.0.1" not in embedded
    assert "location.protocol==='https:'?'wss:':'ws:'" in embedded
    assert "/g/ab12/bot?seat=P1&token=sekret&layout=redesign" in embedded


def test_share_scripts_only_open_a_tunnel() -> None:
    ps1 = (ROOT / "scripts" / "share_beta_cloudflare.ps1").read_text(encoding="utf-8")
    sh = (ROOT / "scripts" / "share_beta_cloudflare.sh").read_text(encoding="utf-8")
    doc = (ROOT / "docs" / "SHARE_BETA.md").read_text(encoding="utf-8")
    for text in (ps1, sh):
        assert "cloudflared" in text and "tunnel" in text
        assert "--url" in text and "http://127.0.0.1:" in text
        assert "8099" in text
        assert "winget install --id Cloudflare.cloudflared" in text
        assert "brew install cloudflared" in text
        assert "downloads/" in text
        assert "layout=redesign" in text and "token=" in text
        assert "does not start, stop, or restart the game server" in text
        assert "tw2k.cli" not in text
        assert "-m tw2k" not in text
        assert "Start-Process" not in text
        assert "taskkill" not in text.lower()
    assert "Ctrl+C" in doc
    assert "layout=redesign" in doc and "token" in doc
    assert "changes" in doc.lower()
