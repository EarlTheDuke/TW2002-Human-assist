# Cockpit design brainstorm

2026-09-29. Docs only. Commander merges its own ideas and folds the winners into `cockpit-polish-v1` before that slice starts.

The full cockpit already has the video on top of the Known-space map, both large, and a collapsed Bridge card in the side column. `mode=cu` stays a 1280×800 turn screen and is out of scope here. Every idea below uses only data this seat already has: own ship, own credits and turns, own known sectors, ports, and warps, own events, own Bridge log. Nothing reads another seat's memory or a live port the seat has not visited.

Inspiration, in one line each:

- Classic TradeWars: one dense screen of numbers. Sector, port class (`BBS`), warp numbers, holds, fighters, shields, credits, turns. Color means buy or sell.
- Elite Dangerous: the view is the center. Instruments sit on the frame. One lamp changes color when you are in trouble.
- FTL: the ship is a picture. Power, hull, and systems are bars you can see without reading a sentence. A grey control says why it is dead.
- EVE: brackets and a short overview. The next action is a button with a timer, not a menu.
- Star Citizen: the side screen is a swappable MFD. Comms is a call, not a form. The flight recorder can be played again.

## Ideas

1. **Instrument bar.** Credits, turns left, day, sector, ship name, and alignment as one row of readouts under the title. **Why:** those six numbers are the turn. **S.** Fog-safe.
2. **Port-class color.** A warp this seat remembers as a buyer or seller gets the classic buy/sell tint, on the button and on the map node. An unvisited neighbour stays a bare number. **Why:** `BBS` should be a color you can hit with key `1`. **S.** Fog-safe if the tint comes only from `known_ports` / `known_sectors`, never from the live adjacent port.
3. **Warp ring on the window.** The adjacent sectors sit as a numbered ring around the video, keys `1`–`9` in the same order as today. **Why:** the next hop is the decision, so it belongs on the glass. **M.** Fog-safe (sector ids are already shown; port color follows idea 2).
4. **Ship as a schematic.** Holds, shields, fighters, and genesis torpedoes are filled rooms on a small hull, FTL-style, next to the video. **Why:** "42 fighters" is slower than a bar that is half full. **M.** Fog-safe (own ship).
5. **One alert lamp.** Amber for a mine, photon, or incoming hit on this seat. Red when this ship is destroyed. Quiet otherwise. **Why:** Elite and FTL both use one color you cannot miss. **S.** Fog-safe (own events only).
6. **Side MFD.** The side column is one screen that swaps Ship, Port, Planets, Bridge, and Moments. The video and the map never move to make room. **Why:** stacked cards are why the page has dead space and why Bridge is easy to lose. **M.** Fog-safe (same data, less chrome).
7. **Bridge as a hail.** Captain notes and pilot replies are two sides of a call. The status chip is a lamp: pending amber, taken blue, done green, declined red, and it updates on the 2.5 s poll without reopening the card. **Why:** an order should look answered. **S.** Fog-safe (own seat log). Keep `/bridge/pending` including `taken`. The per-process rate limit stays as it is.
8. **Route on the map.** A plotted course draws a line across known space from the sectors this seat already knows. No new route call. **Why:** the text preview "3 hops, first 44" is a subtitle; the line is the route. **M.** Fog-safe (`known_warps` only).
9. **Turn spool.** A short bar fills while it is your turn and clears when the action posts, same deadline the computer-use screen already shows. **Why:** the full cockpit should feel the clock the bot already sees. **S.** Fog-safe (own turn).
10. **Buttons that say why.** A disabled warp, trade, or plot says the reason on the control (`no turns`, `empty hold`, `not adjacent`) instead of going grey and silent. **Why:** FTL never hides the reason a system is dark. **S.** Fog-safe (own legality).
11. **Moments as a flight recorder.** Rows leave the debug column. Each row replays that clip in the video window. **Why:** a recorder you cannot play is a log file. **M.** Fog-safe (own clips). Reduced motion shows the poster.
12. **Seat frame tint.** The panel frame takes one color from this seat's id, not from anyone else's alignment. **Why:** you should know which chair you are in before you read the header. **S.** Fog-safe.
13. **Local brackets.** Ships and planets already in this sector's observation get a one-line bracket under the video: name and relation only. **Why:** EVE's overview is the "who is here" glance. **S.** Fog-safe only for entities the observation already lists. Do not add occupants the seat cannot see.
14. **Computer page.** A toggle reveals the same facts as a dense TradeWars readout (sector, port, warps, holds, turns) for players who want the original screen. **Why:** the pretty HUD should not throw away the screen that made the game fast. **M.** Fog-safe (same payload). `mode=cu` does not grow a second page.
15. **Stencil mode.** With reduced motion, glow, spool, and video become stills and flat panels. Layout does not change. **Why:** the cockpit has to work with the motion already turned off. **S.** Fog-safe.

## Mockups

These are the full cockpit at 1440×900. `mode=cu` is not redrawn. The map stays under the video in all three.

### A. Deck (recommended)

Status bar across the top. Video, then the map, in the center. One MFD on the left. Verbs on the right. Bridge is a tab on the MFD, not a card that pushes the map.

```
+--+--------------------------------------------------------------+--+
|  |  12,400 cr   180 turns   Day 2   Sec 44   Merchant   Good    |  |
+--+--------------------------------------------------------------+--+
|  |                                                              |  |
|  |                     [ video  16:9 ]                          |W1|
|MFD|                      alert lamp                             |W2|
|Ship                                                              |  |
|Port|                                                            |SC|
|Brdg|                                                            |AN|
|Mom |              [ known space, route drawn ]                  |PL|
|  |                                                              |OT|
+--+--------------------------------------------------------------+--+
```

### B. Visor

The window is almost the whole center. Instruments are a ring: warps on the left of the glass, ship bars on the right, port prices along the bottom of the glass. The map is still under the video, shorter only if the ring needs the margin. This is the Elite / Star Citizen read.

```
+------------------------------------------------------------------+
| cr 12,400    turns 180    Day 2    Sec 44         [lamp]  Good   |
+------------------------------------------------------------------+
| 1  12 BBS |                                        | holds #### |
| 2  19     |            [ video  16:9 ]             | ftrs  ##-- |
| 3  44 SSB |                                        | shld  #### |
| 4   7     |         you are here: 44               | gens  #--- |
+-----------+----------------------------------------+------------+
| Ore  buy 120 / sell 40     Org  buy 80     Eqp  sell 200         |
+------------------------------------------------------------------+
|                    [ known space, route drawn ]                  |
+------------------------------------------------------------------+
| Bridge: "hold at 44"                         [taken]  reply ___ |
+------------------------------------------------------------------+
```

### C. Computer

Same facts, TradeWars density, for a toggle. No new data. The video and map collapse to a one-line "view closed" so the numbers fit. Opening the view returns to mockup A.

```
Sector 44  (Fed)          Port: Sol   BBS
Warps: (1) 12 BBS  (2) 19  (3) 44 SSB  (4) 7
Holds 18/40   Ore 12   Org 0   Eqp 6
Fighters 42   Shields 100   Turns 180   Cr 12,400
Align Good    Ship Merchant Cruiser     Day 2 of 7
Last: bought 10 ore at 44
Bridge (1 open): hold at 44  [taken]
```

## Top 5, in order

These fit `cockpit-polish-v1` without moving the map, without touching `mode=cu`, and without new game data.

1. **Instrument bar** (idea 1). It is the first thing a TradeWars player looks for, and the polish slice already calls for it.
2. **Port-class color on remembered warps and map nodes** (idea 2). Small, and it is the difference between a themed page and a cockpit.
3. **One side MFD** (idea 6), with Bridge as a labeled tab (idea 7) and Moments as a playable recorder in that same MFD (idea 11). This is also where the page-load shift and the dead space get fixed: one panel, stable from the first paint.
4. **Alert lamp and live order chips** (ideas 5 and 7). The chip must change from pending to taken to done while the card stays open.
5. **Route line on the known-space map** (idea 8), drawn only from warps this seat already knows.

Leave the warp ring (3), the hull schematic (4), the local brackets (13), and the computer page (14) for a later slice. They are good, and they are larger than a polish pass. Stencil mode (15), button reasons (10), the turn spool (9), and the seat tint (12) can ride along with the top 5 if they stay small.

Do not change: game logic, fog of war, keyboard shortcuts, the map-under-video layout, or the computer-use page (`scrollHeight` stays 800).
