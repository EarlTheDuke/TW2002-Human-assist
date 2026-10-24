# NOTE 103 quick-stats and backtrack keys

No new live keypress. This note reads the sources already in the repo and the 19 Oct 2026 capture. The cockpit prompt keys were already `>` and `<`. They stay.

## Cockpit handlers

File `web/redesign.js`.

| Key | Where | Function | What the player sees |
|---|---|---|---|
| `>` | command prompt, `key` | `quickStats` | menu `data-screen=quick-stats`. Name, rank, experience, alignment, turns, credits, day, fighters, shields, holds |
| `<` | command prompt, `key` | `backtrack` | `act("warp")` to `cameFrom` when that sector is still a warp out. Otherwise "No previous sector." or "You cannot backtrack to N from here." |
| S | Computer menu, `CKEYS` | `quickStats` | the same quick-stats screen |
| B | Computer menu, `CKEYS` | `backtrack`, or `beginSelfDestruct` when `self_destruct` is legal | legacy backtrack. A v3.11 game asks "ARE YOU SURE CAPTAIN? (Y/N) [N]". NOTE 110 |
| `/` | not bound | | the EIS quick-stats key. Stays unbound |
| `,` | not bound | | the unshifted comma backtrack, discontinued in v3.05 |

`cameFrom` is set in `noteCourse` from this seat's warp event. The keydown listener names `<` and `>` before `toUpperCase`. The player's manual command list names the same two prompt keys.

## Sources

`<` is backtrack. CONFIRMED.

- EIS `MainMenu.html` hidden key `<<>` Return to Previous Sector. The note under it says `<,>` (no shift) was discontinued as of v3.05.
- v3.11 revision history, v3.05: the backtrack key is `<` only, not `<` or `,`.
- v3.11 revision history, 02/04/97: the hidden back-track key `<` (or `,`) moves the ship to the last sector visited. The line names adjacent port pairs.
- `docs/playtests/twgs-live/computer-b.txt` (TWGS v2.20b, Trade Wars 2002 3.34b, 19 Oct 2026). After a hop from 157 to 50, `<` printed `<Move>`, "Warping to Sector 157", "That Warp Lane is not adjacent.", a 4-hop path, and "Engage the Autopilot?". Declined.

`>` is quick stats on this cockpit. DIFFERENT / UNVERIFIED against the docs.

- EIS `GlobalCommands.html` Quick-stats is `</>`. The docs wrap the key in angle brackets, so the key is `/`.
- EIS `CompMisc.html` Personal Settings: the quick-stats key `</>` toggles persistent info, or prints the lines when that option is off.
- v3.06 revision history: the quick-stats line appears when `/` is pressed. Persistent Info Display was removed.
- `GeneralNew.html` Quick-stats says type `</>` from any prompt. That is the same slash. An earlier queue line read it as both `<` and `>`.

No capture presses `>` or `/`. The cockpit key stays `>`. `/` is not added.

Non-adjacent `<`. DIFFERENT. The 3.34b capture plots a course. This cockpit refuses when the previous sector is not a warp out. The 02/04/97 line and `MainMenu.html` describe a move, and the port-pair use, and they do not describe a plotted course. The refuse stays. An adjacent `<` on live TWGS was not pressed. UNVERIFIED.

## Queue

`docs/plans/live-twgs-test-queue-v1.md` NOTE 103 and `docs/plans/live-twgs-run-sheet-v1.md` item `n103-quick-backtrack`. The remaining live presses are `>`, `/`, an adjacent `<`, and a one-way `<`.
