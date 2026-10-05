# Ship combat core

Rules table first, then what the engine does. Sources are the files under `docs/reference/tw2002/`. Marks: CONFIRMED (a source prints it), SOURCE-CONFLICT (sources disagree, the reading is given), UNVERIFIED (no source prints it; the value here is chosen and says so).

## Rules table

### (a) Fighters that meet an entering ship

| # | rule | original | mark and source | this slice |
| --- | --- | --- | --- | --- |
| a1 | Order on entry | Navigation hazard, limpet, armid (50%), sector Q-cannon, then the fighters. | CONFIRMED. `cabal_strategy_site/formulas.html` ("Entering a hostile sector"). | Mines, then the fighters, as before. Quasar cannons still fire after the move (existing, not reordered). |
| a2 | Defensive fighters | They challenge the ship. It must attack, retreat, or surrender. They do not shoot first. Odds 1:1. | CONFIRMED. `formulas.html` ("forced to either attack, retreat or surrender", odds table "Defensive 1:1"). `stardock_manuals_and_text_docs/Iago_War_Manual.txt` (defensive fighters keep a hostile trader out unless destroyed; attack or retreat). `eis_tw2002_v3_docs/Tactical.html` (they "fight when attacked"). | Built. The ship moves in and is held by a challenge until it answers. |
| a3 | Toll fighters | Pay 5 credits per fighter, attack, retreat, or surrender. Odds 1:1. | CONFIRMED. `formulas.html` (toll line and odds table "Tolled 1:1"). `Iago_War_Manual.txt` (pay, retreat, or attack; 5 per fighter). | Built. Paying is its own action now, `pay_toll`. The warp no longer bills on entry and no longer refuses a ship that cannot pay. |
| a4 | Attacking the fighters | The ship's fighters times its combat odds is the damage. The sector fighters defend at 1:1. | CONFIRMED that the ship's odds multiply. `classictw_docs_wiki/Combat.html` ("number of fighters you use multiplied by the ship's combat factor"). `formulas.html` odds table. The exact loss split is UNVERIFIED. | Built, deterministic. Sent `q`, odds `A`, group `N`: if `q*A >= N` the group is gone and the ship loses `ceil(N/A)`. Otherwise the ship loses all `q` and the group loses `floor(q*A)`. The ship is never destroyed by defensive or toll fighters. |
| a5 | Fighters sent per attack | Capped by the hull's fighters per attack. | CONFIRMED. `classictw_museum_wiki/Document_TradeWars_2002_Bible.html` ship chart ("Fig Max / Fig Per Attack"). `Gypsy_Big_Dummies_Guide.html` ("Max Fighters Per Attack"). `Misc_shipodds.txt` transcript ("How many fighters do you wish to use (0 to 6,000)"). | Built. `qty` is 1 to `min(fighters aboard, fighters_per_attack)`. |
| a6 | Retreat | Back to the last sector visited. | CONFIRMED. `Iago_War_Manual.txt` (retreat to the last sector visited, even across the universe). ("Normally, one retreats to the last sector visited", the retreat-bug note). | Built. `retreat` moves to the sector the ship came from. |
| a7 | No retreat | Not after a one-way warp, not after TransWarp from a non-adjacent sector, not while a planetary interdictor generator holds the sector. An interdictor controller ship does not block. Your own planet's generator does not hold you. | SOURCE-CONFLICT, resolved for v3. Iago (older) retreats "all the way across the universe -- as in the case of a twarp"; the v3 revision history fixed retreat so it does not cross a one-way or non-adjacent TransWarp. v3 is taken. The interdictor lines are CONFIRMED. `classictw_museum_wiki/tw-attac_TW2002_v3_revision_history_to_v3.11.html` (retreat fix; interdictor lines). | Built. Retreat is illegal when there is no warp from here back to the last sector, or when a hostile planet in the sector can interdict (citadel level and fuel, same test as warp interdiction). |
| a8 | Cost of retreat | Not printed. Mines in the sector you retreat into do not go off. | UNVERIFIED for the cost. The mines line is CONFIRMED in `Iago_War_Manual.txt` (retreat-bug note: "Any mines there will not go off"). | Chosen: the hull's turns per warp. No fighters or shields lost. No hazards fire in the sector it returns to. |
| a9 | Surrender | Offered to defensive and toll fighters. Stays available with fighters aboard, with a warning. Offensive fighters take no surrender. | CONFIRMED that the option exists. `formulas.html` ("surrender your ship"). Revision history v3 ("Added Surrender to sector fighter menu"). `classictw_museum_wiki/TWGS_v2_Revision_History.html` (available with fighters left, warned). What the ship loses: UNVERIFIED (the original drops you in a pod). | Built. Legal only inside a live challenge. It runs the existing death (StarDock respawn, credit loss, starter hull); escape pods are the next slice. The legal list carries a warning when fighters are aboard. |
| a10 | Offensive wave | One line: 1.25 times (max fighters + max shields). The v.55 note: work out the fighters needed to destroy the ship from its max fighters and shields at 1:1, send 1.25 times that, or all that remain if fewer; a ship at 1:1.3 odds or better survives. | SOURCE-CONFLICT in wording only. At 1:1 the two lines give the same number. The note adds "or all that remain" and says the wave ignores the ship's odds, which then decide survival. `formulas.html` (both lines). `Misc_offensive_pod.txt`. | Not built. Offensive fighters keep the random exchange. Next slice. |
| a11 | Photon missile | Does not go off against defensive or toll fighters. | CONFIRMED. `cabal_strategy_site/glossary.html`. | Not changed. |

### (b) Ship against ship

| # | rule | original | mark and source | this slice |
| --- | --- | --- | --- | --- |
| b1 | Attacker picks the count | The attacker is asked how many fighters to use. | CONFIRMED. `eis_tw2002_v3_docs/Tactical.html`. `Misc_shipodds.txt` transcript. | Built. `attack {target, qty}`. A missing `qty` sends the most it may. |
| b2 | Per-ship odds | Each hull has one offensive odds figure. | CONFIRMED. Bible ship chart ("Battle/Offensive Odds"). `TWFAQ_FERRSPEC_ferrengi.txt` (Ferrengi 1.0 / 1.2 / 1.4, "approximate"). | Built. Read from `SHIP_SPECS_TW2002` (`offensive_odds`) for all 16 hulls in both economies. Ferrengi defend at 1.0 (the smallest Ferrengi hull; ours do not carry a Ferrengi class). |
| b3 | Per-attack cap | `fighters_per_attack` on the hull. | CONFIRMED (a5 sources). | Built (a5). |
| b4 | Damage and defense | Damage = fighters sent times attacker odds. The defender's real defense = (fighters + shields) times its odds. Fighters needed = real defense / attacker odds. | CONFIRMED. `Gypsy_Big_Dummies_Guide.html` ("Formula For 1 Attack Ship Captures"). `classictw_docs_wiki/Combat.html`. | Built with exact fractions. |
| b5 | Shields first | Shields absorb the damage, then the fighters take the rest. | CONFIRMED. `classictw_docs_wiki/Combat.html`. | Built. A photon-disabled defender's shields do not absorb. |
| b6 | What each side loses | Attacker loses about what it took to beat the defense. | UNVERIFIED as a formula. `Misc_shipodds.txt` shows a player losing 182 fighters against a target worth 699 and 79 against 260 (the odds are disputed in that thread). | Chosen: if `q*A >= R` the attacker loses `ceil(R/A)` (never more than `q`) and the defender loses all fighters and shields. Otherwise the attacker loses all `q` and the defender loses `floor(q*A/D)` units, shields first. The attacker's ship is never destroyed by its own attack (UNVERIFIED, chosen). |
| b7 | Defender destroyed | A ship with no fighters left can be destroyed or captured. | CONFIRMED. `classictw_docs_wiki/Combat.html`. | Built: an attack that beats the whole real defense (b4) destroys the ship, through the existing death path (players) or the Ferrengi bounty path. A lost attack never destroys it, even if its fighters reach 0 behind shields. Capture is not built. |
| b8 | Flee when outgunned | The defender flees if the attacker's fighters are more than 1.25 times (defender fighters + shields). Strictly greater. Fighters on hand, not max, not odds. Applies when auto-flee is on or the trader is offline. | CONFIRMED. `cabal_strategy_site/fleeing.html`. | Built after the wave, on what is left. Every seat counts as auto-flee on (deliberate: there is no online/offline seat state). |
| b9 | Who never flees | Guardian ships (Tholian Sentinel). An attacker with an active interdictor generator, or an active planetary interdictor in the sector, stops the flee. Lack of turns does not. | CONFIRMED. `fleeing.html`.  ("Guardian ships will never flee, period", Tholian named). | Built. Tholian Sentinel never flees. An Interdictor Cruiser attacker counts as an active generator. A hostile planet that can interdict blocks it (no fuel is burned for this check). A landed ship does not flee. |
| b10 | Where it flees | One hop to an adjacent sector with no fighters except its own or its corp's. None qualify: no flee. Mines, Q-cannons and hazards do not fire. | CONFIRMED. `fleeing.html`. Which of several sectors: UNVERIFIED. | Built. A seeded random pick among the qualifying neighbors. Own and allied fighters count as friendly. |
| b11 | Flee penalty | One turn, only if the next action is to land or port. Any other turn-using action first cancels it. | CONFIRMED. `classictw_docs_wiki/Glossary.html` ("Flee Penalty", v3.11.54). | Built. The legal list shows the extra turn only on a land or port action that spends a turn, and never past the day's last turn, the same as the handler (follow-up). |
| b12 | Turn cost of an attack | Not printed. | UNVERIFIED. | Not changed: 5 turns. |
| b13 | Tholian 4:1 at a corp planet | Tholian defends at 4:1 at a corp planet, 1:1 attacking. | CONFIRMED. `Gypsy_Big_Dummies_Guide.html`. | Not built. |

## Switch

`COMBAT_MODE` defaults to `tw2002`. `legacy` keeps the old three-round dice for `attack`, the old `params.target` only, the old entry path (toll billed on the warp and refused when unaffordable, defensive fighters do nothing), and surrender refused with the old wording. The defensive challenge also needs `SECTOR_FIGHTER_MODE` at `tw2002`; with sector fighters at `legacy` the old entry path runs whatever `COMBAT_MODE` says.

## What the engine does

Challenge. A warp into a sector with hostile defensive or toll fighters moves the ship in (mines first, as before) and opens a challenge on the player: the sector, the sector it came from, the mode, and whether it may retreat. A course stops at that sector. While the challenge is open the only legal answers are `attack` with target `fighters`, `retreat`, `surrender`, and `pay_toll` (toll only). Hail, broadcast, query_limpets and wait stay open. A challenge still open when the day ends (the ship only waited) ends at the day tick in a free retreat to the sector the ship came from (`runner._overnight_retreats`, a `retreat` event with `overnight`), so a ship never stays in a held sector past the day. A ship that may not retreat (one-way lane, interdictor) stays held and must still answer. Everything else is refused in the legal list and the handler with "answer the fighters first", and no turn is spent. The challenge ends when the group is destroyed, the toll is paid, the ship retreats, the ship surrenders, or the group is gone. The observation shows it under `fighter_challenge` (mode, count, may retreat) and the group is already in the sector brief. Corp mates and allies are not challenged.

Ship attack. `attack {target, qty}` against a player in the sector or a Ferrengi. The list offers attack only with at least one fighter aboard and not photon-disabled, and `qty.max` is the per-attack cap. Results follow b4 to b11. The combat event keeps the old keys with one round, plus `sent` and `defender_fled`. Where a fled ship went is not in the event.

Fog. Other ships' fighters and shields stay hidden in the observation, as before. The original sector display shows a trader's fighters; this slice does not add that (fog unchanged by rule).

## Deliberate differences

- Fights are deterministic. The original has some wiggle; there is no source for its size.
- Every defender is treated as offline with auto-flee on.
- A landing in a toll sector is no longer billed in tw2002 combat mode. The toll is answered at the challenge on entry.
- A ship that cannot pay a toll now enters and is challenged, instead of being refused at the warp. It still meets the mines first, as the original does.
- Retreat costs the hull's turns per warp and is free of hazards. The original cost is not printed.
- Surrender runs the death path: an escape pod back to the previous sector, or Ship Destroyed (DEATH_ESCAPE_PODS.md d20).
- Ferrengi attacking a player keep the old dice, and a Ferrengi target never flees. The Ferrengi rebuild is not in this slice.
- Only a warp (or a course, which is warps) opens a challenge. Planet TransWarp and the transporter already need the owner's own fighters at the far end. A respawn at StarDock opens none.
- A challenged ship may still hail, broadcast, query limpets (all free), and wait (one turn, the challenge stays). Wait is open so an idle or timed-out seat, which the server answers with an automatic wait, cannot stall the day. Everything else waits for the answer. The original lets fighters stop a trader "entering or remaining in" the sector (`Iago_War_Manual.txt`), so waiting cannot be a way to stay: at the day tick an open challenge retreats the ship for free to where it came from. The retreat costs no turn because it happens between days; the original has no day tick to copy. A ship on a one-way lane or held by an interdictor has no retreat and stays challenged until it attacks, pays or surrenders.
- `scripts/media_record_fixtures.py` pins `COMBAT_MODE` to legacy. The video clip fixtures were recorded on the three-round fight (an attacker that loses dies); they test clip choice, not combat rules.
- Not built: the offensive 1.25 wave, capture, salvage, Corbomite, the Tholian 4:1 corp-planet bonus, corp toll collection, alignment and experience from kills.

## Next slice

Escape pods (the surrender and death path). The offensive wave after a10.

## Seat brains

`seat_brain.py` answers an open challenge before its ladder: pay if it may, else retreat, else attack the fighters if every fighter aboard at the hull's odds clears the group (one legal wave per attack), else surrender. A seat that is only short of turns for the retreat or the winning attack waits for the next day instead of surrendering. A sector it retreated from is avoided for the rest of that day unless the seat can now beat the group; entering it again the same day it attacks if it can win. (QC fix: the first version walked straight back in after every retreat, surrendered at the end of a day for want of turns, and surrendered to a group larger than one wave.) Nothing else in the brains changed; they still never start a ship attack. `heuristic.py` answers a challenge the same way, skips a neighbour it retreated from that day when it has another exit, and sends a legal `qty` when it attacks a Ferrengi.

## Plants

Planted one at a time against the real engine (`tests/test_ship_combat_core_v1.py`, `tests/test_sector_fighter_rules_v1.py`, `tests/test_parity_s4.py`), then put back byte for byte (sha256 checked) before the suite. 17 of 17 caught.

| plant | where | caught by |
| --- | --- | --- |
| odds ignored | handler `combat.py` | `test_odds_multiply_the_attackers_fighters` (test_ship_combat_core_v1.py:135): `AssertionError: assert 400 == (400 - 60)` |
| odds ignored on the fighter group | handler `combat.py` | `test_fighter_attack_uses_the_hulls_odds` (test_ship_combat_core_v1.py:440): `AssertionError: assert FighterDeployment(owner_id='A', count=50, mo...` |
| per-attack cap ignored | legal list `legality.py` | `test_per_attack_cap_is_in_the_list_and_the_handler` (test_ship_combat_core_v1.py:171): `assert 300 == 250` |
| per-attack cap ignored | handler `runner.py` | `test_per_attack_cap_is_in_the_list_and_the_handler` (test_ship_combat_core_v1.py:173): `assert not True` |
| shields skipped | handler `combat.py` | `test_odds_multiply_the_attackers_fighters` (test_ship_combat_core_v1.py:134): `AssertionError: assert 100 == 0` |
| wrong flee threshold (1.0) | handler `combat.py` | `test_defender_flees_only_past_one_and_a_quarter` (test_ship_combat_core_v1.py:222): `AssertionError: assert 10 == 30` |
| retreat free of cost | handler `runner.py` | `test_retreat_goes_back_costs_a_warp_and_fires_nothing` (test_ship_combat_core_v1.py:367): `AssertionError: assert 3 == (3 + 3)` |
| retreat free of cost | legal list `legality.py` | `test_retreat_goes_back_costs_a_warp_and_fires_nothing` (test_ship_combat_core_v1.py:361): `AssertionError: assert (True and 0 == 3)` |
| fighters created on retreat | handler `runner.py` | `test_retreat_goes_back_costs_a_warp_and_fires_nothing` (test_ship_combat_core_v1.py:368): `assert (201, 100) == (200, 100)` |
| attacker loss not applied | handler `combat.py` | `test_odds_multiply_the_attackers_fighters` (test_ship_combat_core_v1.py:136): `AssertionError: assert 500 == 400` |
| attack offered with 0 fighters | legal list `legality.py` | `test_attack_with_no_fighters_is_not_offered_or_taken` (test_ship_combat_core_v1.py:200): `AssertionError: assert not True` |
| challenge gate skipped | handler `runner.py` | `test_defensive_fighters_challenge_and_hold_every_other_verb` (test_ship_combat_core_v1.py:328): `AssertionError: warp` |
| challenge gate skipped | legal list `legality.py` | `test_defensive_fighters_challenge_and_hold_every_other_verb` (test_ship_combat_core_v1.py:318): `AssertionError: warp` |
| retreat through a one-way warp | legal list `legality.py` | `test_no_retreat_after_a_one_way_warp_or_under_an_interdictor` (test_ship_combat_core_v1.py:377): `AssertionError: assert (not True)` |
| retreat through a one-way warp | handler `runner.py` | `test_no_retreat_after_a_one_way_warp_or_under_an_interdictor` (test_ship_combat_core_v1.py:379): `assert (not True)` |
| toll billed at 1 credit | handler `runner.py` | `test_pay_toll_is_five_per_fighter_into_the_pot` (test_ship_combat_core_v1.py:399): `AssertionError: assert 92 == 60` |
| surrender offered without a challenge | legal list `legality.py` | `test_offensive_fighters_take_no_surrender_and_open_no_challenge` (test_ship_combat_core_v1.py:468): `AssertionError: assert not True` |

## Follow-ups (combat challenge follow-ups)

From the ship-combat QC. Tests: `tests/test_combat_challenge_followups_v1.py`.

- (a) Waiting in a challenge: at the day tick an open, still-standing challenge ends in a free retreat to the sector the ship came from (same move as `retreat`: previous sector set, port visit ended, sector learned, no hazards; the `retreat` event carries `overnight: true` and the day it happened). A stale challenge (group gone, friendly, or the ship moved) is just cleared. One-way lanes and interdictors keep the ship held. Seat brains and the heuristic seat already wait when short of turns; the next day they start in the sector they came from with no challenge and play on (N1, N2, N3, H checked, no rejected action).
- (b) Flee penalty: the legal list adds `min(1, turns left after the action)` to a land or port action that spends a turn, and 0 to a free second trade, which is what `apply_action` charges. Before, the list showed +1 on the day's last turn and on a free trade while the handler charged nothing.
- Not done (optional): a retreat back into a sector where hostile fighters were laid since the ship left still opens no challenge. Opening one there can bounce a ship between two held sectors (each retreat targets the other); that needs its own rule.
