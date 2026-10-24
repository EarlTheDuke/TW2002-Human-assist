# Ship-odds exchange (CMB-c)

Plan only. This slice does not change combat code. The live TWGS server is not reachable from here, so a number that no reference file prints is marked UNVERIFIED rather than filled in.

NOTE 96 rechecked the repo and the open pull requests. `RULINGS_v311.md` is not in the tree, and no pull request has landed a ship-odds section from Cur's NOTE 90. The loss split stays `ceil(R / A)` / `floor(P / D)`. It is queued in `docs/plans/live-twgs-test-queue-v1.md`.

## What is already on the tip

`COMBAT_MODE` defaults to `tw2002`. A player attack then runs `_resolve_ship_attack_tw2002` (`src/tw2k/engine/combat.py`). That exchange already multiplies by the hull's offensive odds. It is not the legacy three-round exchange.

The legacy exchange, `_resolve_ship_combat`, still runs when `COMBAT_MODE` is `legacy`. Each side's whole fighter stack is the volley, times a random 0.8 to 1.2, for up to three rounds. Shields soak first. No hull odds. That is the strict 1:1-style exchange this plan is about replacing, and it is already off by default.

## Sources

- Bible ship chart, "Battle/Offensive Odds". Read in this tree from `SHIP_SPECS_TW2002` through `combat_hull` (`src/tw2k/engine/constants.py`). Examples: Merchant Cruiser 1.0, Scout Marauder 2.0, Missile Frigate 1.3, BattleShip 1.6, Escape Pod 0.6. The chart is the odds table. It does not print the loss arithmetic.
- `classictw_docs_wiki/Combat.html`: the fighters you use, multiplied by the ship's combat factor. CONFIRMED that the odds multiply. The loss split is not printed.
- `Gypsy_Big_Dummies_Guide.html`, "Formula For 1 Attack Ship Captures": damage is fighters sent times attacker odds; real defense is (fighters + shields) times defender odds; fighters needed is real defense / attacker odds. CONFIRMED as that product. How many fighters each side then loses is not printed.
- `eis_tw2002_v3_docs/Tactical.html` and `Misc_shipodds.txt`: the attacker chooses how many fighters to send. CONFIRMED. The transcript's loss counts (182 against a target worth 699, 79 against 260) are disputed in that thread, so they are not a formula.
- `docs/reference/tw2002/GAP_MAP.md` row 5.7: the exact formula is UNVERIFIED.
- `docs/playtests/combat/SHIP_COMBAT.md` rows b4 and b6: the engine's reading, and the mark that the loss split is UNVERIFIED.

## Formula the engine uses today (chosen, not a live measurement)

One attack. The attacker sends `q` fighters, at most the hull's fighters-per-attack and at most the fighters aboard.

- Attacker power `P = q * A`, where `A` is the attacker's chart odds.
- Defender strength `R = (shields + fighters) * D`, where `D` is the defender's chart odds. Shields are skipped if that ship is photon-disabled.
- If `P >= R`, the defender loses every shield and fighter. The attacker loses `ceil(R / A)` fighters, and never more than `q`.
- Otherwise the attacker loses all `q`. The defender loses `floor(P / D)` units, shields first, then fighters.

Worked example, not from a live server. A Missile Frigate (1.3) sends 100 fighters at a Merchant Cruiser (1.0) holding 40 fighters and 20 shields. `P = 130`, `R = 60`. `130 >= 60`, so the cruiser is cleaned out and the frigate loses `ceil(60 / 1.3) = 47` fighters. The same 100 fighters from a Merchant Cruiser (1.0) give `P = 100`, still enough, and the attacker loses `ceil(60 / 1.0) = 60`.

A strict 1:1 exchange would ignore `A` and `D` and trade one fighter for one shield or fighter. The Bible chart is what makes the frigate spend fewer fighters than the cruiser for the same defense. That is the change this plan is for. It is already what `COMBAT_MODE` `tw2002` does. This slice does not put that path behind a new switch, because turning it off by default would change the profile-off digests.

## UNVERIFIED

- The loss split above is the reading in `SHIP_COMBAT.md` b6. No reference file prints `ceil(R / A)` or `floor(P / D)`. A live exchange (Missile Frigate at 1.3 and Merchant Cruiser at 1.0, 100 fighters, a target with known fighters and shields) is the measurement that would confirm or replace it. That server is not reachable here.
- Whether the defender's odds are the same "offensive odds" column, or a separate defensive factor. The engine uses the one chart column for both sides. A second column is not in the Bible chart this tree has.
- `Misc_shipodds.txt` loss counts. The thread itself disputes the odds, so they are not used as a vector.
- Tholian Sentinel defending a corp planet at 4:1 (`SHIP_COMBAT.md` b13). Not built. The 4:1 figure is printed; wiring it is out of this plan.
- Attack turn cost. Measured on live KillTest as 0 for a ship attack (`docs/playtests/twgs-live/attack-turn-cost-ven.txt`). Only a Merchant Cruiser. `ATTACK_TURN_MODE` (profile row 228) charges 0. Stored `TURN_COST["attack"]` stays 5.
- Whether the attacker's own ship can be destroyed by the attack it started. The tw2002 attack does not destroy the attacker. UNVERIFIED.
- Alien exchanges. NOTE 71 already forces a 1:1 soak when `ALIEN_COMBAT_FIX_MODE` is live. That is a different switch and stays as it is.
- Ferrengi odds. `TWFAQ_FERRSPEC` calls its figures approximate. The engine's Ferrengi defender odds are a separate table, not this plan.
