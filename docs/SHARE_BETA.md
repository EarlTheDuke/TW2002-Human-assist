# Sharing a beta game

This is for Ben, on the PC where the lobby is already running.

The share script opens a free temporary public link and points it at the lobby.
You start the lobby yourself, the way you already do. The script does not start it,
does not stop it, and does not restart it.

## Open the link

On Windows:

```
powershell -ExecutionPolicy Bypass -File scripts\share_beta_cloudflare.ps1
```

On Mac or Linux:

```
sh scripts/share_beta_cloudflare.sh
```

The lobby port is 8099 unless you say otherwise (`-Port 8100` on Windows, `--port 8100` on Mac or Linux).

Leave that window open. When Cloudflare is ready, the window prints three lines:

- Public link. That is the `https://` address for this run.
- Lobby. Open that in a browser to reach the front door.
- Seat. Copy that shape, fill in the game, the seat, and the token, and send it to one player.

A seat link looks like this:

```
https://<the-words>.trycloudflare.com/g/<game-id>/bot?seat=P1&token=<token>&layout=redesign
```

`layout=redesign` is the cockpit. `token` is the password for that seat. Send each seat link to one person.

If `cloudflared` is missing, the script prints the install steps and stops. It still does not touch the lobby.

## Safety

- The lobby keeps listening on this PC only (`127.0.0.1`). The tunnel makes an outbound connection and carries the public link back to it.
- Anyone who has the public link can open the lobby. Anyone who has a seat link can sit in that seat. Treat the link like a password. Do not put it on a public page or in a chat that you cannot delete.
- The admin page stays on this PC (`http://127.0.0.1:8099/admin`). A request that comes through the tunnel does not get the admin page.
- This is a free quick tunnel. It is a public web address, not a private network. Cloudflare carries the traffic for as long as the window stays open.
- The game keeps running if you close the tunnel. Closing the game is a separate step, on the lobby, not in this script.

## Stop the tunnel

Press Ctrl+C in the window where the script is running.

That stops the tunnel. The lobby and the games keep running. Players' old links stop opening. Start the script again when you want a new link.

## The link changes every run

Each run prints a new `https://....trycloudflare.com` address. The previous address dies when you stop the tunnel or start another one. The game on this PC is the same game. Send the new lobby link, and send new seat links, because the host name in the old ones no longer works.
