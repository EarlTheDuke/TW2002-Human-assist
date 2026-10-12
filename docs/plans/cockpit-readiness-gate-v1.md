# cockpit-readiness-gate-v1

2026-10-11. Docs only. This is the bar for a cockpit-only game. It is not a claim that the game has been played.

Ben can play from the bot screen, without typing an action into the API, when all of these are true:

- Every engine verb has a button. Wait ends the turn. Hold slot is the H button. A refused click prints FAILED and the engine's reason.
- Terra colonists, the bank, cloak, the disruptor, limpet removal, beacons, rob, steal, port upgrade, port build, the corporation password, drop, transfer, the three ship flags, and the three police verbs each have a button. Join sends the password.
- The three-day smoke clicks only Wait, reaches day 3, writes a screenshot and an action log, and records no failed wait. It binds a port at 8050 or above.
- The legacy pin stays 9b607d3dae940c0b1a69f6d7. The 10-day digests stay 24863a3d and 98a47c8a, rejected 0/0.

Those checks passed on c9e2bcc. The engine did not change in this note, so the pin and the digests stay those numbers. No new switch. No plant.

Still open, and not part of this bar: colonist 1,000 versus 1,000,000 on a class M level 1. The switches stay legacy until Ben turns one on.

## Game 6, from the cockpit play log

P7 played the bot screen on port 8043. The seat really had 300 credits, not the 250,000 the settings page said. The screen's credit number is the real one.

What played: landing, colonist assignment, buying a freighter, and holding a slot all described themselves. A refused build named the missing ore.

What failed, and cockpit-play-fixes-v1 has since changed on the screen: an unchecked plot still flew; the known-sector list was short; warp cost was not on the button; empty port stock looked like a pair of numbers; the yard and the shop did not say what you were buying; lift-off said only that it was ok; a landing line stayed up after leaving; an idle citadel was called in progress; the waiting line named whether a rival was a model.

The day and the turns left were already on the scoreboard. Experience rank was already there. A closed panel now repeats the ship, the port, the planet, that rank, and which listed chairs still have a turn. A rival's location stays hidden unless that rival is in your sector. Net-worth rank beside experience rank is a later switch.
