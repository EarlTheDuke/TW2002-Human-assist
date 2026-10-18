# combat-message-clarity-v1 (COMMANDER NOTE 63)

Redesign cockpit only (`COCKPIT_LAYOUT=redesign`); `/bot` legacy is unchanged. No engine change: the
three lines are written by `web/redesign.js`.

* The Ferrengi boarding prompt said "surrender costs 5 cargo holds, or 10% of the credits on board",
  but the tribute (`apply_ferrengi_tribute`) always takes 5 holds and all cargo, and takes 10% of the
  credits only when the ship carries no cargo. The prompt now says "surrender costs 5 cargo holds and
  all your cargo; with empty holds, 5 cargo holds and 10% of the credits on board". The amounts are
  unchanged (still UNVERIFIED in constants.py).
* After a kill the attacker's line ended "Credits on board lost: 30 cr" (the Ferrengi tribute already
  listed in the same line). That label now shows only when your own ship was destroyed or captured.
* A queued command that replaces an older queued one now says so: "Warp to 75 will run when your turn
  comes. This replaces your queued attack." A second queued warp to a different sector replaces the
  first warp (before, the first one stayed queued while the line named the new one).

Screens (taken by `tests/test_cockpit_combat_message_clarity_v1.py`):

* `1920-board.png`, `390-board.png` - the boarding prompt in the log.
* `1920-ignored.png`, `390-ignored.png` - ignoring the boarding: "it took 5 cargo holds and 30 cr".
* `1920-killer.png`, `390-killer.png` - the attacker's kill line: the tribute once, no "Credits on board lost".
* `1920-victim.png`, `390-victim.png` - the victim's line: "Credits on board lost: 300 cr".
* `1920-replaced.png`, `390-replaced.png` - "This replaces your queued attack."
