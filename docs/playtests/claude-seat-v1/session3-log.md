# Claude seat session 3: armed bots, combat, the rest of the menu (2026-11-08)

Same rules as the pilot. Lobby restarted with every fix so far, including bots that
outfit at the v3.11 StarDock.

Game: lobby `1664d115`, 1 seat + 3 bots, 500 sectors, v3.11, 1-hour days, 5 days,
1,000,000 starting credits.

Goals: confirm bots now arm; fight an armed bot; TransWarp turn cost on the form; dawn
messages at the day roll; ether probe; port build/upgrade; anything left on the menu.

## Session 3 result

- **Bots now arm** (630 fighters each, from 30) — the session-2 bot fix works live.
- Ship-to-ship combat works and reads well; the kill is now named in the result line.
- Ether probes now show what they saw (the most useful fix this session).
- TransWarp form shows the turn saving; port upgrade wording fixed.
- **Not done:** a fight with an armed bot. With holo scanners the bots steer clear of
  sectors holding my fighters, and they move every round, so chasing missed each time.
  Next try: sit in a sector *without* deployed fighters on a bot's trade lane, or open a
  second human seat and fight another player.
- Not reached: the day-roll messages (no day ended while I played this session), build a
  port (needs a planet in a port-less sector), Ferrengi (none seen in three sessions).

| # | Wanted | Looked at | Found? | Friction / note |
| --- | --- | --- | --- | --- |
| 1 | Outfit (scripted clicks) | Shipyard + 7 gear buys | Yes | Same as session 2; StarDock 221 from the manual. |
| 2 | Are bots armed now? | Holo scan from StarDock | Yes | **Bot fix confirmed live:** "Orion 630 fighters, Lyra 630 fighters, Vega 630 fighters" (were 30 all game in session 2). |
| 3 | Fight | Warp next door → Attack | Yes | Bots had left, but an alien trader was there: sector line "Ships : Loro's scout marauder, Loro, 250 fighters". Attack form: target list + "fighters (1 to 1,000)". Clear. |
| 4 | — | Result after the attack | Partly | "You lost 294 fighters and 0 shields, 2,206 fighters remain. Loro lost 250 fighters and 44 shields. Credits +3,283." The kill was only in the log ("Guest 1 destroyed Loro"). **Fixed:** result line now ends "Loro is destroyed". +38 experience, alignment +61 (Good), rank Sergeant. "Turns spent 0" for an attack — check against the original. |
| 5 | Chase Vega | Holo scan → warp next door | No | Gone again on arrival. Set a trap instead: 1,000 offensive fighters at hub 74 (10 lanes, next to StarDock). |
| 6 | Ether probe | E → target 400 | Partly | "probe reached 400 (6 sectors) and self-destructed" — and nothing else. The map gained the sectors, but **what the probe saw was never shown**; the original prints each sector it passes. The engine keeps those readouts (`probe_log`) and the page receives them. **Fixed:** an "Ether probe report" opens after a probe: each sector with ports, planets, traders, aliens, Ferrengi, fighters (owner), mines, or "empty"; and where it was shot down. Rows are in sector order (the event's route stays fogged by design — tests/test_scanners_qc_v1.py), matched to the probe by its tick. Verified live: 6 sectors incl. "Port Kepler-451 SBB; Orl, 243 fighters". |
| 7 | Upgrade my home port | HERE → Upgrade this port | Yes | Worked: 10 units of fuel ore for 2,500 cr took capacity 2,617 → 2,717. **Wording fixed:** "250 cr a unit, 10 holds" read as cargo holds; now "each unit adds 10 to the port's capacity". No total shown as you type (minor). |
| 8 | TransWarp turn cost on the form | Buy 50 fuel at home → TransWarp | Yes | **Fixed (my session-2 change read the wrong field):** now "Fuel cost 15 ore. About 3 turns (flying the 5 hops lane by lane: 15)." Jumped 463 → 74. |
| 9 | Did the trap at 74 catch a bot? | Sector line after ~40 min | No | Untouched. Likely why: the bots now carry holo scanners and the heuristic avoids sectors a scan shows hostile fighters in. Armed bots dodge traps — fights happen by catching them in a sector. |
