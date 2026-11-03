# manual-sync-v1

Plan only. The player's manual is server-rendered help. This slice does not change a rule, a switch, or `/bot`.

The page is `src/tw2k/public/manual.py`. A section says what the player sees and does, which setting it depends on, and how that differs from classic Trade Wars 2002 v3.11. The words "in v3.11 games" stay on the profile sentence. Setting `V311_PROFILE` to `1` does not change that sentence.

## What the page now says

- Communications. The redesign Comms panel (To, Message, Send) is `COMMS_V311_MODE`. The v3.11 profile turns it on. `1` does not. While it is off, hail, radio, and Fed Comm stay the older sentences. While it is on, radio is channels 1 to `RADIO_CHANNEL_MAX`, channel 0 is off, a hail is not mail, and an AI cockpit seat can answer a hail or a corporation memo with Send.
- Planets and citadels. `PLANET_ZDY_MODE` kills a trader who is on a planet you destroy and pays the cabal shares (1,666 and 3,333 per 10,000) on top of the blow. `QUASAR_ATM_ORDER_MODE` is one atmosphere shot, then another only after the last shield falls. `PLANET_INTERDICT_SAFE_MODE` keeps the interdictor quiet at StarDock. Each one is on for `v311` or the v3.11 profile. `1` does not turn them on. Those three switches are not loaded in this process, so the page also states the older result.
- Turns. `FULL_LENGTH_TURN_LIMITS_MODE` is the host's game length. Only `v311` turns it on. `1` and the v3.11 profile do not, and it is not a profile helper. A 24-hour game shows Turns left today on the redesign cockpit. Classic v3.11 used a 24-hour day and 250 turns.
- Joining from a share link. A temporary `trycloudflare.com` address for a lobby that is already running. A seat link carries the token and `layout=redesign`. No profile switch.
- If the computer or the browser stops. The rules table marks this section off until the lobby is saving games across a restart. The section still says what you see when that save is on: the same seat link, Lost the host. Reconnecting. on the redesign cockpit, and a damaged save that does not crash the lobby. No profile switch.
- AI opponents. Levels of play stay general. Code bots, heuristic and LLM opponents, and the AI cockpit seat are named, with `LOBBY_AI_SEAT_MODE` and `AI_COCKPIT_SEAT_MODE`. The v3.11 profile turns neither on. Routes and ranks are still being tuned, so the page does not pin them.
- Warp pictures. Ten pictures per ship, picked at random, not twice in a row, and only when the ship moves. They differ in camera, star streaks, engine glow, and the exit flash. Live, Stills, Off, and Skip are the viewport controls. Redesign layout only. No profile switch. Classic v3.11 does not animate a warp.

## Not merged when this page was written

Communications (#74 and #77), the three planet switches (#76), the restart save (#73), and the distinct warp plumes (#78) were still queued. The share link (#65) and the game-length choice (#66) were already on this branch. The page describes the queued behavior anyway. It does not call a helper this process does not have.

## Not changed

No engine switch, no cockpit key, no `/bot` page. Profile-off digests stay `24863a3d` and `98a47c8a` because the engine was not edited.
