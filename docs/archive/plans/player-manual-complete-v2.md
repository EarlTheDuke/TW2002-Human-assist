# player-manual-complete-v2

Plan only. The player's manual is server-rendered help. This slice does not change a rule. Helper row 165 was not used.

The page is `src/tw2k/public/manual.py`. Every price, cap, and channel number is read from the engine when the page is built.

## Sections added

- Hardware. Cloak, corbomite, mine disruptor, beacons, limpet removal, ether probes and shoot-down, photons, density, holo, and the planet scanner. Caps are for the starting hull.
- StarDock services. Ship rename, tavern, underground, bank, police, bust clearing, commission, and bounties.
- Communications. Hail, mail, radio channels up to `RADIO_CHANNEL_MAX`, and FedComm.
- Computer reports. Daily log, daily counts, corporation rankings, trader rankings, and the computer letters for NavPoints, backtrack, quick stats, find route, the ship catalog, your planets, and planet specs.
- Death and escape pods. The pod, how many losses a day you can survive, the death delay, and the experience loss.
- Feds and Ferrengi. Federal captains, the three federal ships, FedSpace tows, Ferrengal, and the gold-alien grudge. The v3.11 profile leaves the gold grudge off.
- Towing and TransWarp. Tow, ship TransWarp, the transporter (including the Interdictor range), and citadel TransWarp.
- Turns. Dawn refill sits next to the day clock. A legacy game refills every turn at dawn. A v3.11 game gives spent turns back across the day and does not refill the whole pocket at dawn. There is no separate turn-clock field on this tip beyond `turn_regen_day_seconds` and the day-roll helper.

A "Rules in this game" table is the first block. It names the profile and a mode for each section.

## How the profile is read

`v311_profile()` is true only when `V311_PROFILE` is `"v311"`. Setting it to `"1"` leaves the page on the legacy wording. The test checks both.

A switched rule on a v3.11 page always starts with "in v3.11 games", then states the live rule when that helper is on, or the older rule when the helper is off. The gold-alien grudge is one of those older rules: the v3.11 profile leaves it off. A legacy page says "In legacy games" when the helper is off, or "In this game" when it is on.

## Coverage

`MANUAL_COVERAGE` maps each player action and each `*_MODE` in `V311_PROFILE_HELPERS` to a section. `EXEMPT` holds the six switches a player does not set: the AI result shape, AI arguments, three code-bot habits, and the empty-seat idle clock. Each exempt row has a reason.

## Not changed

No engine switch, no cockpit key behavior, no `/bot` page. `pages.py`, `lobby.py`, and `worker.py` were not edited.
