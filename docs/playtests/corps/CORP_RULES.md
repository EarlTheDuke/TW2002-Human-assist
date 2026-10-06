# Corporations

`CORP_MODE` `tw2002` | `legacy`. Legacy is the engine before this slice: create only at StarDock for 500,000, the C.E.O. alone invites, join needs that invite, a corp treasury exists, deployments have no personal/corporate flag, and the last leaver dissolves the corp.

Sources: EIS Corporate Menu, Someguy Twinstr, the v3.11 revision notes, the docs-wiki glossary, the TWGS Extern tables, cabal corps, and the TEDIT member cap. TWGS 3.11 is the default. MBBS breaks ties.

## Rules

| # | Rule | Mark | Constant | Test |
| --- | --- | --- | --- | --- |
| cr1 | Corp verbs work in any sector, in the ship or landed | CONFIRMED | — | `test_cr1_menu_is_global` |
| cr2 | Make a corp anywhere. Cost 0. 0 turns. Maker is C.E.O. | UNVERIFIED cost and turns | `CORP_CREATE_COST` 0, `CORP_TURN_COST` 0 | `test_cr2_create_is_free_anywhere` |
| cr3 | C.E.O. sets a password. A new corp is closed until one is set. A change invalidates old passes. The password is never in a rival view | CONFIRMED that the password exists; UNVERIFIED blank start | `CORP_NEW_PASSWORD` "", reuses `CORPSHIP_PASSWORD_MAX_LEN` and `CORPSHIP_PASSWORD_CASE` | `test_cr3_password` |
| cr4 | Any member hands out the current password. C.E.O.-only is the alt | SOURCE-CONFLICT | `CORP_APPROVER` member | `test_cr4_member_may_pass` |
| cr5 | Join needs the current password, not a stored invite | CONFIRMED | — | `test_cr5_join_by_password` |
| cr6 | One wrong password a day. Further tries are refused before compare. No alignment loss. The corp is not told | UNVERIFIED loss and notice | `CORP_BREAKIN_PER_DAY` 1, `CORP_BREAKIN_ALIGN_LOSS` 0, `CORP_BREAKIN_TELL_CEO` False | `test_cr6_one_breakin` |
| cr7 | At most 5 members, including the C.E.O. The server cap is ignored | CONFIRMED | `CORP_MAX_MEMBERS` 5 | `test_cr7_cap_is_five` |
| cr8 | Good and evil may share a corp. Same-side, with an oust at the tick, is the alt. Alignment 0 counts as good | SOURCE-CONFLICT; side UNVERIFIED | `CORP_ALIGNMENT_RULE` mixed, `CORP_SIDE_OF_ZERO` good | `test_cr8_mixed_is_legal` |
| cr9 | A mixed corp loses floor(highest good alignment / 4) experience at Extern. Floor 1. Least-extreme is the alt | SOURCE-CONFLICT; floor UNVERIFIED | `MIXED_CORP_EXP_RULE` highest_good, `MIXED_CORP_EXP_DIVISOR` 4, `MIXED_CORP_EXP_FLOOR` 1 | `test_cr9_hek_penalty` |
| cr10 | A member who leaves keeps his ship and personal assets. A planet that carries the ticker goes to the C.E.O. | CONFIRMED; owner mapping DERIVED | `CORP_LEAVER_PLANETS` corp_keeps | `test_cr10_leave` |
| cr11 | The C.E.O. leaving dissolves the corp. No succession | CONFIRMED | — | `test_cr11_ceo_leave_dissolves` |
| cr12 | Corporate fighters and mines in the C.E.O.'s sector become his. Fighters elsewhere go rogue. Mines elsewhere go rogue. Planets stay with their owner | Mines UNVERIFIED; planets are the existing deliberate difference | `CORP_DISBAND_MINES` rogue, `CORP_DISBAND_PLANETS` owner_keeps | `test_cr12_disband_assets` |
| cr13 | Rogue groups have owner `rogue`, stay hostile, cannot be recalled, and a kill has no killer | Mode UNVERIFIED | `ROGUE_OWNER_ID` rogue, `ROGUE_KEEP_MODE` True | `test_cr13_rogue` |
| cr14 | The C.E.O. may drop a member from anywhere. The member keeps what is on his ship | CONFIRMED | — | `test_cr14_drop` |
| cr15 | An eliminated C.E.O. dissolves the corp. An eliminated member is removed. A podded trader stays | DERIVED | — | `test_cr15_eliminated` |
| cr16 | Members in the same sector, both in their ships, may give or take credits, fighters, shields, and mines. The receiver's limits apply. Over the limit is refused. A cloaked target is refused | Landed and mine kinds UNVERIFIED | `CORP_TRANSFER_LANDED` refuse, `CORP_TRANSFER_TAKE` True, `CORP_TRANSFER_MINE_KINDS` armid and limpet | `test_cr16_transfer` |
| cr17 | Deployments are personal or corporate. A member who omits the choice deploys corporate | Default UNVERIFIED | `CORP_DEPLOY_DEFAULT` corporate | `test_cr17_ownership` |
| cr18 | A personal group recognizes only its owner. A corporate group recognizes every current member. An ally is a friend of both | CONFIRMED; alliance is ours | `ALLIANCE_DEPLOY_FRIENDLY` all | `test_cr18_recognition` |
| cr19 | A member adds to his corp's corporate group. Qty 0 changes mode or ownership. A member may reclaim a corporate group as personal | Reclaim UNVERIFIED | `CORP_RECLAIM_BY` member | `test_cr19_reclaim` |
| cr20 | Any member may recall a corporate group. Toll credits go to the member who recalls them | Toll UNVERIFIED | `CORP_TOLL_TO` collector | `test_cr20_recall` |
| cr21 | The member who last added owns the group for reports. Planet fighters stay with the planet | CONFIRMED | — | `test_cr21_bookkeeping` |
| cr22 | Members see each member's sector, planet flag, fighters, shields, mines, and credits. A cloak hides the sector | CONFIRMED | — | `test_cr22_member_assets` |
| cr23 | Members see each corp planet's sector, name, population, production, stock, fighters, citadel, shields, and credits | CONFIRMED | — | `test_cr23_planets` |
| cr24 | Everyone sees the corporation list and a ranking by summed experience and summed alignment | Sums UNVERIFIED | `CORP_RANK_EXP` sum, `CORP_RANK_ALIGN` sum | `test_cr24_public_list` |
| cr25 | Any member may send a memo. C.E.O.-only is the alt | SOURCE-CONFLICT | `CORP_MEMO_SENDERS` member | `test_cr25_memo` |
| cr26 | There is no corporate bank. Deposit and withdraw are unsupported. Citadels pay from personal credits | CONFIRMED | `CORP_TREASURY` off | `test_cr26_no_treasury` |
| cr27 | Corp traffic, the password, transfers, member assets, and the planet list stay inside the corp. The public list does not | DERIVED | — | `test_cr27_fog` |
| cr28 | New events: password set, drop, dissolved, ousted, transfer, exp penalty, break-in failed, rogue | DERIVED | — | `test_cr28_events` |
| cr29 | Seat bots do not use corp verbs. A pair policy exists for the match check | DERIVED | `BOT_CORP_POLICY` off | `test_cr29_bot_off` |
| cr30 | One prompt line, only when the mode is on | DERIVED | — | `test_cr30_prompt` |
| cr31 | Net worth is unchanged except a frozen legacy treasury and rogue groups counting for nobody | DERIVED | — | `test_cr31_net_worth` |
| cr32 | The legal list and the handler agree for every corp verb and for deploy ownership | DERIVED | — | `test_cr32_legal_matches_handler` |

## SOURCE-CONFLICT

- cr4 who may hand out a pass: `CORP_APPROVER` member (EIS Join) vs ceo (EIS Corporate Security, and today's invite).
- cr8 alignment: `CORP_ALIGNMENT_RULE` mixed (TWGS Extern, the HEK table, cabal) vs same_side (EIS, Twinstr, the Bible).
- cr9 penalty: `MIXED_CORP_EXP_RULE` highest_good (HEK: 2328/4 = 582) vs least_extreme (Butch).
- cr25 who may memo: `CORP_MEMO_SENDERS` member (the menu lists it under Corporations Only) vs ceo (EIS Make a Corporation calls memos a C.E.O. privilege).

## UNVERIFIED

cr2 cost and turns (`CORP_CREATE_COST` 0, `CORP_TURN_COST` 0). cr3 a new corp starts closed (`CORP_NEW_PASSWORD` ""). cr6 alignment loss and whether the C.E.O. is told (`CORP_BREAKIN_ALIGN_LOSS` 0, `CORP_BREAKIN_TELL_CEO` False). cr8 alignment 0 is good (`CORP_SIDE_OF_ZERO` good). cr9 experience floor (`MIXED_CORP_EXP_FLOOR` 1). cr12 mines outside the C.E.O.'s sector (`CORP_DISBAND_MINES` rogue). cr13 a rogue group keeps its mode (`ROGUE_KEEP_MODE` True). cr16 landed partners and which mines transfer (`CORP_TRANSFER_LANDED` refuse, `CORP_TRANSFER_MINE_KINDS`). cr17 the default when a member omits ownership (`CORP_DEPLOY_DEFAULT` corporate). cr19 who may reclaim (`CORP_RECLAIM_BY` member). cr20 who receives toll credits (`CORP_TOLL_TO` collector). cr24 ranking sums (`CORP_RANK_EXP` sum, `CORP_RANK_ALIGN` sum).

## Deliberate differences

Tickers and names instead of corp numbers. Passes travel as inbox messages. The Extern step runs at the day tick. Planets need a named owner, so a corp-kept planet is assigned to the C.E.O., and disband keeps `owner_keeps` (GAP_MAP conflict 18) unless `CORP_DISBAND_PLANETS` is `v306`. Elimination stands in for a deleted player. Alliances stay, and an ally is a friend of both deployment kinds. A treasury saved under legacy stays frozen. Bots do not use corporations unless `BOT_CORP_POLICY` is `pair`.
