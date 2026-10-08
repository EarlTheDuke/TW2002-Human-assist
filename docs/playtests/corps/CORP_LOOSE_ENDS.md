# Corp loose ends

`CORP_FIX_MODE` `tw2002` | `legacy`. Legacy is the game at `d1396b1`. This slice closes eight parked calls from slices 53, 55, 56, and 57. It does not change bot strategy, prompts, or combat odds.

Sources: Cabal tips (CABT), Iago, MBBS, V8, the FAQ, and the playtest docs `SHIP_TOW.md`, `CORP_SHIPS_FURB.md`, `CORP_RULES.md`, `SCANNERS_HIDDEN_INFO.md`, and `GALACTIC_BANK_TAX.md`. TWGS 3.11 is the default. MBBS breaks a tie.

## Rules

| # | Rule | Mark | Constant | Decision | Test |
| --- | --- | --- | --- | --- | --- |
| cl1 | Mode on. Legacy leaves every row below as it is today. Corp rows also stay off when `CORP_MODE` is legacy. Kill rows need only `corp_fix_on()` | OURS | `CORP_FIX_MODE` tw2002 | fix | `test_cl1_mode` |
| cl2 | A current corp mate can hold a member's unmanned ship over Extern. The tower must be alive, in the same sector, not landed, within the fighter limit, and fedsafe. One lock, one ship. An ally does not count | CONFIRMED | `TOW_EXTERN_HOLDER` owner_or_corp, `TOW_EXTERN_ALLY_HOLDS` False | fix | `test_cl2_a_corp_mate_holds_the_ship_over_extern` |
| cl3 | An ex-member cannot trade in a borrowed corporate hull. A current member trading the corporate hull he flies keeps today's rule | UNVERIFIED | `CORPSHIP_EXMEMBER_TRADEIN` refuse | fix | `test_cl3_an_ex_member_cannot_trade_in_a_borrowed_hull` |
| cl4 | Corbomite on your own unmanned hull fires when you destroy it. A flown ship never self-detonates | MATCHES | `CORBOMITE_OWN_SHIP` fires | already matches | `test_cl4_your_own_unmanned_corbomite_fires_on_you` |
| cl5 | The salvage overkill ratio is built. The default stays no limit. CTWF Furbing states no limit, which is why `none` stays the default. The ratio reading is the cs22 alternative | SOURCE-CONFLICT | `SALVAGE_OVERKILL` none, `SALVAGE_OVERKILL_RATIO` 2 | fix the branch, default unchanged | `test_cl5_ratio_keeps_a_measured_attack_and_drops_an_overkill` |
| cl6 | A corp mate sees corporate limpets only. Personal limpets stay with the owner. Density anomalies stay as they are | UNVERIFIED | `LIMPET_CORP_VIEW` corporate_only | fix | `test_cl6_a_mate_sees_only_a_corporate_limpet` |
| cl7 | A correct corp password joins even after a wrong guess the same day. The daily cap counts wrong guesses only | UNVERIFIED | `CORP_BREAKIN_RULE` wrong_guesses | fix | `test_cl7_a_correct_password_joins_after_a_wrong_guess` |
| cl8 | A rogue toll group keeps charging and keeps its pot. The destroyer takes the whole pot. No cap and no decay | CONFIRMED | `ROGUE_TOLL_POT_CAP` None, `ROGUE_TOLL_CHARGES` True | already matches, plus the dissolve leak | `test_cl8_disband_and_a_dead_ceo_keep_the_toll_pot` |
| cl9 | A current corp member who recalls corporate toll fighters collects the pot. An ex-member does not | CONFIRMED | — | verify, fix only if the start commit differs | `test_cl9_a_member_collects_the_toll_pot_and_an_ex_member_does_not` |
| cl10 | A corp mate pays no toll to his own corp's toll group | CONFIRMED | — | already matches | `test_cl10_a_corp_mate_pays_no_toll_to_his_own_group` |
| cl11 | An attacker killed by return fire pays the defender. A planet-defence death pays the planet owner. Ferrengi, alien, and federal killers keep their existing routes | CONFIRMED | `DEATH_CREDITS_RETURN_FIRE` defender, `DEATH_CREDITS_PLANET_DEFENCE` owner | fix | `test_cl11_return_fire_pays_the_defender_and_a_planet_pays_its_owner` |
| cl12 | A corbomite kill pays the owner when that owner is still alive, including a pod. It never pays an eliminated player, and it never pays twice when both ships die | UNVERIFIED | `DEATH_CREDITS_CORBOMITE` owner | already matches, made explicit | `test_cl12_corbomite_pays_a_living_owner_once` |
| cl13 | No new random draw. No new hidden observation. Events carry only ids the witnesses can already see | OURS | — | fix | `test_cl13_dissolve_draws_no_rng_and_events_name_only_known_ids` |
| cl14 | The older playtest docs point at this slice | OURS | — | fix | `test_cl14_older_docs_point_at_this_slice` |

## Decisions used

D1 `TOW_EXTERN_HOLDER` owner_or_corp. D2 `CORPSHIP_EXMEMBER_TRADEIN` refuse. D3 `LIMPET_CORP_VIEW` corporate_only. D4 `CORP_BREAKIN_RULE` wrong_guesses. D5 return fire pays the defender and planet defence pays the owner. D6 corbomite payout stays with the owner. D7 `SALVAGE_OVERKILL` stays none. D8 the rogue toll pot stays uncapped.

## Legacy pin

Recorded before any rule code. In-suite 3-day N3,N2,N1,H seed 250925 digest `9b607d3dae940c0b1a69f6d7`. Outside the suite, the 10-day N3,N3,N2,N2,N1,H seed 250925 digest is `221826d9bd9a6a6c85668224` (332s). `CORP_FIX_MODE` is named on the older single-mode flip lists. The constant does not exist yet, so those flips do not change the digest. There is no separate fed-outpost pin file.

## Not built

No bot strategy change. No prompt change. No combat-odds change. No alliance, corp treasury, tavern, or port-upgrade work. `prompts.py` still says `query_limpets` shows your planted limpets. That line is left for a later parity slice. `rules_text.py` says one wrong password a day, which still matches cl7.
