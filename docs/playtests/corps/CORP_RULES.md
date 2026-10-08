# Corporations

`CORP_MODE` `tw2002` | `legacy`. Legacy is the engine before this slice: create only at StarDock for 500,000, the C.E.O. alone invites, join needs that invite, a corp treasury exists, deployments have no personal/corporate flag, and the last leaver dissolves the corp.

Sources: EIS Corporate Menu, Someguy Twinstr, the v3.11 revision notes, the docs-wiki glossary, the TWGS Extern tables, cabal corps, and the TEDIT member cap. TWGS 3.11 is the default. MBBS breaks ties.

## Rules

| # | Rule | Mark | Constant | Test |
| --- | --- | --- | --- | --- |
| cr1 | Corp verbs work in any sector, in the ship or landed | CONFIRMED | — | `test_cr1_cr2_create_is_free_anywhere`, `test_qc_cr1_corp_verbs_work_landed` |
| cr2 | Make a corp anywhere. Cost 0. 0 turns. Maker is C.E.O. | UNVERIFIED cost and turns | `CORP_CREATE_COST` 0, `CORP_TURN_COST` 0 | `test_cr1_cr2_create_is_free_anywhere`, `test_qc_create_cost_alt_legal_matches_handler` |
| cr3 | C.E.O. sets a password. A new corp is closed until one is set. A change invalidates old passes. The password is never in a rival view | CONFIRMED that the password exists; UNVERIFIED blank start | `CORP_NEW_PASSWORD` "", reuses `CORPSHIP_PASSWORD_MAX_LEN` and `CORPSHIP_PASSWORD_CASE` | `test_cr3_cr4_cr5_cr6_password_and_one_breakin`, `test_qc_join_legal_hides_closed_corps_and_spent_breakins`, `test_qc_password_length_invite_targets_and_ceo_approver` |
| cr4 | Any member hands out the current password. C.E.O.-only is the alt | SOURCE-CONFLICT | `CORP_APPROVER` member | `test_cr3_cr4_cr5_cr6_password_and_one_breakin`, `test_qc_password_length_invite_targets_and_ceo_approver`, `test_qc_invite_is_hidden_from_other_pass_holders` |
| cr5 | Join needs the current password, not a stored invite | CONFIRMED | — | `test_cr3_cr4_cr5_cr6_password_and_one_breakin`, `test_qc_pb6_changed_password_invalidates_old_pass`. Decided in slice 64 (cl7): a correct password still joins after a wrong guess |
| cr6 | One wrong password a day. Further tries are refused before compare. No alignment loss. The corp is not told | UNVERIFIED loss and notice | `CORP_BREAKIN_PER_DAY` 1, `CORP_BREAKIN_ALIGN_LOSS` 0, `CORP_BREAKIN_TELL_CEO` False | `test_cr3_cr4_cr5_cr6_password_and_one_breakin`, `test_qc_join_legal_hides_closed_corps_and_spent_breakins`. Decided in slice 64 (cl7): the cap counts wrong guesses, so a correct password still joins |
| cr7 | At most 5 members, including the C.E.O. The server cap is ignored | CONFIRMED | `CORP_MAX_MEMBERS` 5 | `test_cr7_sixth_member_is_refused` |
| cr8 | Good and evil may share a corp. Same-side, with an oust at the tick, is the alt. Alignment 0 counts as good | SOURCE-CONFLICT; side UNVERIFIED | `CORP_ALIGNMENT_RULE` mixed, `CORP_SIDE_OF_ZERO` good | `test_qc_same_side_join_and_oust`, `test_qc_pb8_alignment_rule_mixed_never_ousts_and_same_side_does` |
| cr9 | A mixed corp loses floor(highest good alignment / 4) experience at Extern. Floor 1. Least-extreme is the alt | SOURCE-CONFLICT; floor UNVERIFIED | `MIXED_CORP_EXP_RULE` highest_good, `MIXED_CORP_EXP_DIVISOR` 4, `MIXED_CORP_EXP_FLOOR` 1 | `test_cr9_hek_penalty`, `test_qc_pb9_penalty_formula_and_straight_corp`, `test_qc_mixed_rule_never_applies_same_side`, `test_qc_mixed_penalty_ignores_eliminated_and_extern_dissolves_dead_ceo_corp`, `test_qc_exp_penalty_is_private` |
| cr10 | A member who leaves keeps his ship and personal assets. A planet that carries the ticker goes to the C.E.O. | CONFIRMED; owner mapping DERIVED | `CORP_LEAVER_PLANETS` corp_keeps | `test_qc_leaver_planets_corp_keeps_and_leaver_keeps`, `test_qc_leaver_is_not_recognized_by_the_corporate_group_he_last_fed` |
| cr11 | The C.E.O. leaving dissolves the corp. No succession | CONFIRMED | — | `test_cr11_ceo_leave_dissolves_and_rogues_fighters` |
| cr12 | Corporate fighters and mines in the C.E.O.'s sector become his. Fighters elsewhere go rogue. Mines elsewhere go rogue. Planets stay with their owner | Mines UNVERIFIED; planets are the existing deliberate difference | `CORP_DISBAND_MINES` rogue, `CORP_DISBAND_PLANETS` owner_keeps | `test_cr11_ceo_leave_dissolves_and_rogues_fighters`, `test_qc_disband_mines_ceo_sector_personal_elsewhere_rogue_or_removed`, `test_qc_v306_orphan_names_the_real_former_owner` |
| cr13 | Rogue groups have owner `rogue`, stay hostile, cannot be recalled, and a kill has no killer | Mode UNVERIFIED | `ROGUE_OWNER_ID` rogue, `ROGUE_KEEP_MODE` True | `test_qc_pb13_rogue_group_forgets_its_corp_and_cannot_be_recalled`, `test_qc_rogue_kill_has_no_killer_and_no_keyerror` |
| cr14 | The C.E.O. may drop a member from anywhere. The member keeps what is on his ship | CONFIRMED | — | `test_cr14_drop_keeps_ship_fighters`, `test_qc_leaver_planets_corp_keeps_and_leaver_keeps` |
| cr15 | An eliminated C.E.O. dissolves the corp. An eliminated member is removed. A podded trader stays | DERIVED | — | `test_qc_eliminated_ceo_sector_fighters_go_rogue`, `test_qc_mixed_penalty_ignores_eliminated_and_extern_dissolves_dead_ceo_corp` |
| cr16 | Members in the same sector, both in their ships, may give or take credits, fighters, shields, and mines. The receiver's limits apply. Over the limit is refused. A cloaked target is refused | Landed and mine kinds UNVERIFIED | `CORP_TRANSFER_LANDED` refuse, `CORP_TRANSFER_TAKE` True, `CORP_TRANSFER_MINE_KINDS` armid and limpet | `test_cr16_transfer_refuses_over_the_receiver_room`, `test_qc_transfer_take_and_give_matrix`, `test_qc_transfer_refuses_an_eliminated_member_and_fractions`, `test_qc_pb16_transfer_refuses_landed_and_cloaked_partners`, `test_qc_pb18_transfer_with_a_non_member_is_refused`, `test_qc_credit_transfer_cannot_exceed_the_givers_cash`, `test_qc_transfer_have_check_turns_and_fog` |
| cr17 | Deployments are personal or corporate. A member who omits the choice deploys corporate | Default UNVERIFIED | `CORP_DEPLOY_DEFAULT` corporate | `test_qc_deploy_legal_offers_ownership_and_recall_lists_corporate_groups`, `test_qc_redeploy_zero_without_ownership_keeps_the_kind`, `test_qc_ownership_guards_on_deploy`, `test_qc_sector_view_shows_fighter_ownership`, `test_qc_holo_view_labels_fighter_ownership` |
| cr18 | A personal group recognizes only its owner. A corporate group recognizes every current member. An ally is a friend of both | CONFIRMED; alliance is ours | `ALLIANCE_DEPLOY_FRIENDLY` all | `test_cr18_personal_fighters_hit_a_corp_mate`, `test_qc_corporate_group_lets_a_member_pass_and_blocks_others`, `test_qc_pb20_corporate_limpet_never_attaches_to_a_member`, `test_qc_pb21_toll_bill_and_surrender_follow_deploy_friend`, `test_qc_limpet_view_follows_s12_for_corp_mates` |
| cr19 | A member adds to his corp's corporate group. Qty 0 changes mode or ownership. A member may reclaim a corporate group as personal | Reclaim UNVERIFIED | `CORP_RECLAIM_BY` member | `test_qc_pb22_member_adds_to_the_corp_group_without_combat`, `test_qc_redeploy_zero_without_ownership_keeps_the_kind`, `test_qc_ownership_guards_on_deploy` |
| cr20 | Any member may recall a corporate group. Toll credits go to the member who recalls them | Toll UNVERIFIED | `CORP_TOLL_TO` collector | `test_qc_deploy_legal_offers_ownership_and_recall_lists_corporate_groups`, `test_qc_failed_recall_keeps_the_owner`, `test_qc_leaver_cannot_recall_the_corporate_group_he_deployed` |
| cr21 | The member who last added owns the group for reports. Planet fighters stay with the planet | CONFIRMED | — | `test_qc_pb22_member_adds_to_the_corp_group_without_combat`, `test_qc_failed_recall_keeps_the_owner` |
| cr22 | Members see each member's sector, planet flag, fighters, shields, mines, and credits. A cloak hides the sector | CONFIRMED | — | `test_qc_cr22_members_see_member_assets_and_a_cloak_hides_the_sector` |
| cr23 | Members see each corp planet's sector, name, population, production, stock, fighters, citadel, shields, and credits | CONFIRMED | — | `test_qc_member_block_planets_and_penalty_estimate` |
| cr24 | Everyone sees the corporation list and a ranking by summed experience and summed alignment | Sums UNVERIFIED | `CORP_RANK_EXP` sum, `CORP_RANK_ALIGN` sum | `test_qc_rivals_see_only_the_public_list`, `test_qc_ranking_sums_members_and_ties_by_ticker`, `test_qc_pb25_ranking_orders_by_experience_not_ticker` |
| cr25 | Any member may send a memo. C.E.O.-only is the alt | SOURCE-CONFLICT | `CORP_MEMO_SENDERS` member | `test_qc_cr25_member_memo_and_ceo_alt` |
| cr26 | There is no corporate bank. Deposit and withdraw are unsupported. Citadels pay from personal credits | CONFIRMED | `CORP_TREASURY` off | `test_cr26_treasury_verbs_are_unsupported`, `test_qc_legacy_create_needs_stardock_and_treasury_works` |
| cr27 | Corp traffic, the password, transfers, member assets, and the planet list stay inside the corp. The public list does not | DERIVED | — | `test_cr27_password_stays_off_the_event`, `test_qc_password_never_reaches_a_non_member`, `test_qc_invite_is_hidden_from_other_pass_holders`, `test_qc_pb24_rivals_see_no_corp_traffic`, `test_qc_transfer_have_check_turns_and_fog` |
| cr28 | New events: password set, drop, dissolved, ousted, transfer, exp penalty, break-in failed, rogue | DERIVED | — | `test_qc_cr28_rogue_event_is_public_without_owner_and_dissolve_reaches_members`, `test_qc_exp_penalty_is_private` |
| cr29 | Seat bots do not use corp verbs. A pair policy exists for the match check | DERIVED | `BOT_CORP_POLICY` off | `test_qc_policy_off_never_uses_corp_verbs`, `test_qc_pair_policy_forms_one_corp_and_deploys_corporate` |
| cr30 | One prompt line, only when the mode is on | DERIVED | — | `test_qc_cr30_prompt_numbers_follow_the_constants` |
| cr31 | Net worth is unchanged except a frozen legacy treasury and rogue groups counting for nobody | DERIVED | — | `test_qc_cr31_net_worth_ignores_corporate_and_rogue_groups` |
| cr32 | The legal list and the handler agree for every corp verb and for deploy ownership | DERIVED | — | `test_cr32_legal_create_matches_away_from_stardock`, `test_qc_corp_verbs_legal_matches_handler_property`, `test_qc_create_cost_alt_legal_matches_handler` |

## SOURCE-CONFLICT

- cr4 who may hand out a pass: `CORP_APPROVER` member (EIS Join) vs ceo (EIS Corporate Security, and today's invite).
- cr8 alignment: `CORP_ALIGNMENT_RULE` mixed (TWGS Extern, the HEK table, cabal) vs same_side (EIS, Twinstr, the Bible).
- cr9 penalty: `MIXED_CORP_EXP_RULE` highest_good (HEK: 2328/4 = 582) vs least_extreme (Butch).
- cr25 who may memo: `CORP_MEMO_SENDERS` member (the menu lists it under Corporations Only) vs ceo (EIS Make a Corporation calls memos a C.E.O. privilege).

## UNVERIFIED

cr2 cost and turns (`CORP_CREATE_COST` 0, `CORP_TURN_COST` 0). cr3 a new corp starts closed (`CORP_NEW_PASSWORD` ""). cr6 alignment loss and whether the C.E.O. is told (`CORP_BREAKIN_ALIGN_LOSS` 0, `CORP_BREAKIN_TELL_CEO` False). cr8 alignment 0 is good (`CORP_SIDE_OF_ZERO` good). cr9 experience floor (`MIXED_CORP_EXP_FLOOR` 1). cr12 mines outside the C.E.O.'s sector (`CORP_DISBAND_MINES` rogue). cr13 a rogue group keeps its mode (`ROGUE_KEEP_MODE` True). cr16 landed partners and which mines transfer (`CORP_TRANSFER_LANDED` refuse, `CORP_TRANSFER_MINE_KINDS`). cr17 the default when a member omits ownership (`CORP_DEPLOY_DEFAULT` corporate). cr19 who may reclaim (`CORP_RECLAIM_BY` member). cr20 who receives toll credits (`CORP_TOLL_TO` collector). cr24 ranking sums (`CORP_RANK_EXP` sum, `CORP_RANK_ALIGN` sum).

## Deliberate differences

Tickers and names instead of corp numbers. Passes travel as inbox messages. The Extern step runs at the day tick. Planets need a named owner, so a corp-kept planet is assigned to the C.E.O., and disband keeps `owner_keeps` (GAP_MAP conflict 18) unless `CORP_DISBAND_PLANETS` is `v306`. Elimination stands in for a deleted player. Alliances stay, and an ally is a friend of both deployment kinds. A treasury saved under legacy stays frozen. Bots do not use corporations unless `BOT_CORP_POLICY` is `pair`.

## QC (slice 57, Grok Bot, 2026-10-06)

Reviewed 8628960..5695588 rule by rule. Fixes:

- Fog:
  - CORP_EXP_PENALTY goes to the member it hits only.
  - CORP_INVITE goes to the actor, the members and the named target only.
  - CORP_ROGUE has no actor. A public row naming the C.E.O. read as a sighting of him in the rogue sector for every rival.
  - Fighter ownership is labelled in the sector view and the holo view.
- Legacy: corp_set_password, corp_drop and corp_transfer are absent from legal lists and unsupported.
- Transfers: whole quantities only, and only live partners.
- Disband:
  - An eliminated C.E.O. counts as gone.
  - The v306 orphan event names the real former owner.
  - A rogue kill has no killer and no KeyError.
- Deployments:
  - A qty-0 redeploy keeps the kind.
  - Deploy legality goes through `_controls`, with qty min 0.
  - Recall goes through `_recall_owns`, so a leaver cannot recall the corporate group he last fed.
  - Sector hazards skip only the player's own group or a friendly one.
- Rules and alts:
  - `mixed_loss` follows the rule, the formula and same_side.
  - The member block has planet production and stock.
  - Join legality hides closed corps and spent break-ins.
  - The corp_memo handler honours `CORP_MEMO_SENDERS` ceo like the legal list.
  - The prompt numbers follow `CORP_CREATE_COST` and `CORP_TURN_COST`.
- `BOT_CORP_POLICY` pair was missing and is now implemented (cr29). Seat 1 makes PAR, sets the password and invites seat 2, who joins from the pass. Deploys are corporate. The match script has `--corp-policy` and `--corp-report`.
- The Test column above used to name 31 tests that did not exist. It now names real tests, in `tests/test_corp_rules_v1.py` and `tests/test_corp_rules_qc5657.py`.

Planted bugs: spec variants (pb1-pb26, 42 stubs) 42/42 caught. Without the QC tests, the slice's tests caught 20/42. QC plants: 37/37.

Legacy: the pin 9b607d3dae940c0b1a69f6d7 is green on Linux and Windows. The 10-day N3,N3,N2,N2,N1,H digest outside the suite is 221826d9bd9a6a6c85668224, which matches the docstring.

(e) `scripts/corp_rules_scenario_lab.py` prints PASS, and `test_qc_scenario_lab_e_passes` runs it in the suite. The run:

- A makes XYZ away from StarDock for 0 credits.
- B's join with no password set is refused.
- A sets "Zx9". B's guess "zx9" is refused ("wrong password"), and his correct guess the same day is refused too ("one break-in attempt per day").
- The next day B joins, and evil C joins.
- At Extern, A, B and C each lose 300 (1200 / 4).
- A gives B 1,000 fighters. This is refused, because B has room for 500. B takes 300 shields from A.
- A deploys 200 corporate fighters. B passes them, and non-member D is attacked.
- B deploys 100 personal fighters, and A is attacked when he enters.
- A drops C. C keeps his 40 fighters, and C's corporate planet goes to A.
- A leaves:
  - The corp is dissolved.
  - The corporate fighters in A's sector become A's personal fighters.
  - The 200 in the other sector go rogue and attack B.
- corp_deposit is unsupported.

(c)/(d) 10-day N3,N3,N2,N2,N1,H, rejected 0, exceptions 0:

| Seed | Policy off | Policy pair |
| --- | --- | --- |
| 250925 | 1,871,215, equal to the slice-56 bank run | 2,244,131 |
| 424242 | 1,626,702, equal to the slice-56 bank run | 1,327,988 |

Under pair, PAR forms on day 1 with P1 and P2. There are 0 fights between members, 0 rogue groups and no mixed penalty in 10 days. With the policy off nobody is in a corp, and the totals equal the bank runs.

Under pair, both seats made 0 corporate deployments, because the code bots never deploy fighters in these matches. The pair totals differ from off by butterfly effects: mates are allies at the ship and planet sites.

(f) 30-day seed 250925 (engine at QC 23cccd9), invariants after every action and tick. The checks:

- every corporate group's ticker names a live corp;
- rogue groups have no player owner;
- members ≤ 5;
- member tickers match;
- save/load.

Off (with bank stress) and pair both reached day 30 with 0 problems and 0 exceptions. Pair had 0 rejects. Save/load was identical, apart from the pre-existing `known_sectors` set order. Pair counters:

- 1 corp (PAR: P1 and P2), 1 create, 1 password, 1 invite, 1 join;
- 0 transfers;
- 8 mixed-corp experience penalties (the pair's sides differed on some days);
- 0 rogue groups, 0 corporate groups, 0 hostile actions between members.

Live smoke: server on box :8047, 4 heuristic seats, 3 days. It finished, `/state` includes `corporations`, and there were no errors.

Open calls for Ben:

- A corp mate sees personal limpets (s12 is kept). Decided in slice 64 (cl6): a mate sees corporate limpets only.
- A correct password after a failed guess the same day is refused (cr6 against cr5). Decided in slice 64 (cl7): a correct password still joins.
- The rogue toll pot keeps growing. Decided in slice 64 (cl8): dissolve keeps the pot, and the destroyer takes it.
- The planetary lab's corp table is pinned to legacy.
- The combat.py rogue-killer fix is outside the spec's listed combat sites.
- Bots never deploy fighters, so pair shows no corporate deployments.
