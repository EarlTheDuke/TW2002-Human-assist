# Sector fighters

Lab table first, then the four rules this slice builds. Offensive and defensive combat are not rebuilt here. Sources are the files under `docs/reference/tw2002/`.

## Lab table

| rule | original | ours before | mark | this slice |
| --- | --- | --- | --- | --- |
| Offensive fighters | Attack at 1:1. One line in formulas.html sends 1.25 times the ship's max fighters plus max shields. A later note on the same page sends 1.25 times the fighters needed to destroy the ship at 1:1, using the max, not the fighters aboard. The rest stay for the next entry. | One exchange. Each side loses the other side times a random 0.8 to 1.1. No wave cap. | SOURCE-CONFLICT inside `cabal_strategy_site/formulas.html` (the 1.25 line near the entry order, and the version-.55 note). `Misc_offensive_pod.txt` is the other file the gap map names. | Not rebuilt. Next slice. |
| Defensive fighters | They block entry. The ship is asked to attack, retreat, or surrender. They do not shoot first. Odds 1:1. | Defensive mode does nothing on entry. | CONFIRMED. `Iago_War_Manual.txt` (attack or retreat). `cabal_strategy_site/formulas.html` adds surrender. | Not built. The challenge, the retreat, and the "they never shoot first" path are the next slice. Surrender as its own action is below. |
| Toll fighters | Five credits per fighter to stay or pass. The ship may pay, retreat, or attack. Formulas.html also lists surrender. The owner, or a corp mate for corp fighters, collects by going to the sector and picking the fighters up. Destroying the fighters pays the attacker what they have collected. | On entry, `min(credits, max(10, min(10000, count)))` is taken and paid to the owner at once. | CONFIRMED. `Iago_War_Manual.txt`. `cabal_strategy_site/formulas.html`. | Five credits per fighter, into a pot on the deployment. The owner collects by recalling the fighters. Destroying the group pays the pot to the attacker. See deliberate differences for the missing attack prompt. |
| No retreat | You cannot retreat from fighters if you arrived by a one-way warp or by TransWarp from a non-adjacent sector, or if a planetary interdictor holds the sector. An interdictor controller does not block the retreat. | No retreat action. | CONFIRMED. `classictw_museum_wiki/tw-attac_TW2002_v3_revision_history_to_v3.11.html` (the retreat fix, and the interdictor line). | Not built. It needs the defensive challenge. Next slice. |
| Surrender | You may surrender to defensive or toll fighters instead of fighting. A later note says the option stays available while you still have fighters, with a warning. | Missing. | CONFIRMED that the option exists. `cabal_strategy_site/formulas.html` ("surrender your ship"). `classictw_museum_wiki/TWGS_v2_Revision_History.html` (available even if fighters remain). What the ship loses is not printed. | Chosen default: the action destroys the ship with the death this game already uses. |
| Fighters per sector | v1.03d: 5000 with no planet, 30000 if a planet is there. You can destroy the planet and leave the 30000. v3 number not found. | No cap. | UNVERIFIED for v3. The v1.03d numbers are CONFIRMED in `Iago_War_Manual.txt`. | Chosen default: those two numbers. A deploy that would pass the cap is refused. A group already over the cap is not shrunk. |
| Mines per sector | v1.03d: 99 mines in the sector, planet or not. v3 number not found. | No cap. | UNVERIFIED for v3. CONFIRMED for v1.03d in `Iago_War_Manual.txt`. | Chosen default: 99 sitting mines, all owners and both sitting types together. |
| Pick your own back up | Visit the sector and pick up your fighters. That visit is also how toll credits are collected. | No recall action. | CONFIRMED. `Iago_War_Manual.txt` (pick up the fighters to collect the toll). The Bible line the gap map cites is about planet fighters in a cloning note, not this sector pickup. | `recall_deployed`, only while you stand in the sector, only your own fighters and mines. |

## Switch

`SECTOR_FIGHTER_MODE` defaults to `tw2002`. `legacy` is the old path: no sector cap, the old toll paid straight to the owner, and recall and surrender refused.

## What the engine does

Recall. `recall_deployed` with `what` `fighters` or `mines`, and `qty`. Mines also take `kind` (`armid` or `limpet`). It is legal only in the sector you are in, and only for a deployment you own. One turn. A quantity that does not fit on the ship is refused whole, and nothing moves. Toll credits on the fighters move with the fighters you pick up, in proportion, and the last fighter takes whatever is left. The event facts are `what`, `qty`, and `kind`. The credit number is not in the facts or the summary. An outsider's sector brief does not include `toll_credits`. The owner does.

Caps. A new or added fighter group stops at 5000, or 30000 when the sector has a planet. Sitting mines stop at 99. Atomic mines still detonate at once and do not sit, so they do not count toward the 99. The legal list and the handler both refuse a quantity that would pass the cap. The turn is not spent.

Toll. A warp into hostile toll fighters, or a hostile landing in a sector that has them, moves `5 * count` credits from the ship into `toll_credits` on the deployment. The owner is not paid yet. Corp mates and allies are not charged, the same skip the old toll used. If the ship cannot pay the whole bill, the warp or landing is refused, nothing is charged, and no turn is spent. The warp legal list carries `toll_due_by` for those neighbor sectors, the same 5-per-fighter figure. Destroying the group pays whatever the pot still holds to the attacker. That number is not added to the combat facts.

Surrender. `surrender` while you stand with hostile defensive or toll fighters. One turn. The ship is destroyed by the existing death: StarDock, a quarter of the credits gone, the fighters left where they were. Offensive fighters do not take a surrender. The event facts are the mode only.

## Deliberate differences

- The toll prompt's attack and retreat choices are not a menu. The warp pays the whole bill or it does not enter. Attacking the fighters is still the existing clash, by deploying onto them or by meeting offensive fighters. Retreat from a one-way warp, TransWarp, or an interdictor is the next slice, with the defensive challenge.
- A ship that cannot pay never enters, so it also skips the mines in that sector. The original fires mines before the fighter prompt.
- Only the deploying player recalls and collects. Iago lets a corp mate collect corp fighters. These deployments have an owner id and no corp flag.
- Surrender uses this game's death, not the original escape pod.
- Offensive odds stay the random exchange. Defensive fighters still do not fire and do not block. Both are the next slice.
- v3 sector caps were not in the library. The v1.03d numbers are the default on purpose.

## Next slice

Defensive fighters that challenge (attack, retreat, or surrender) and do not shoot first. The offensive 1.25 wave, after the two formulas.html lines are picked apart. No-retreat for a one-way warp, a non-adjacent TransWarp, and a planetary interdictor.

## Seat brain

`seat_brain.py` was not edited. The prompt verb list names `recall_deployed` and `surrender`, and the toll sentence now says 5 credits per fighter instead of a flat 100. The harness verb catalog is `ActionKind`, so the parity pin moved from 45 to 47. Acceptance bars were not retuned.

## Plants

Each line was put back before the suite. The test file hardcodes 5000, 30000, 99, and 5. It does not read those constants back.

| plant | where | result |
| --- | --- | --- |
| Fighter cap comparison skipped (`if False and have + qty > cap`) | handler `runner.py` | `test_fighter_cap_is_in_the_list_and_the_handler` line 65: `assert not True` — deploy of 11 onto 4990 returned ok |
| Fighter room skipped (`fighter_max = fighters`) | legal list `legality.py` | same test line 63: `assert 20 == 10` |
| Mine cap comparison skipped (`if False and sitting + qty > cap`) | handler `runner.py` | `test_mine_cap_is_in_the_list_and_the_handler` line 104: `assert not True` — deploy of 3 onto 97 returned ok |
| Mine room skipped (`mine_max = have`) | legal list `legality.py` | same test line 102: `assert 5 == 2` |
| Toll billed at 1 credit (`count * 1`) | handler `runner.py` | `test_toll_price_is_in_the_list_and_the_handler` line 130: `assert 996 == 980` — payer lost 4, not 20 |
| Toll due listed at 1 credit (`count * 1`) | legal list `legality.py` | same test line 126: `assert 4 == 20` |
| Recall owner check skipped (`dep.owner_id != pid` removed) | handler `runner.py` | `test_recall_owner_gate_is_in_the_list_and_the_handler` line 202: `assert not True` — the other ship picked the fighters up |
| Recall owner check skipped (`owner_id == player_id` removed) | legal list `legality.py` | same test line 199: `assert not True` — recall was listed legal |
| Surrender mode check skipped (`mode not in defensive/toll` forced false) | handler `runner.py` | `test_surrender_gate_is_in_the_list_and_the_handler` line 242: `assert not True` — offensive fighters destroyed the ship |
| Surrender mode check skipped (same gate forced false) | legal list `legality.py` | same test line 240: `assert not True` — surrender was listed legal |
