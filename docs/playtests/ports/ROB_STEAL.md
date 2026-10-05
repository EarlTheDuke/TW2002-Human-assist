# Robbing and stealing at ports

Rules table first, then what the engine does. Sources are under `C:\Users\sugar\tw2002_reference\` (gap map rows 2.12-2.14, conflict 7; cabal formulas.html "Evil Rob/Steal Settings", glossary Bust / Fake Bust / Bust Clearing; docs.classictw.com Busted + Evil_or_Red_Cashing; Someguy_MBBS_manual "Playing Evil"; Gypsy Big Dummies Guide evil basics; TW2002 v3.05 revision notes for daily bust clearing). Target is TWGS 3.11; MBBS breaks ties. Marks: CONFIRMED / SOURCE-CONFLICT / UNVERIFIED.

Today's build (kept as `ROB_MODE = "legacy"`): no rob or steal verbs. Alignment and experience exist under RANK_MODE; ports have no credit vault.

## Rules table

| # | rule | original | mark and source | this slice (ROB_MODE tw2002) |
| --- | --- | --- | --- | --- |
| **Who can** | | | | |
| r1 | Alignment gate | A trader with alignment at or below -100 (evil / "red") may rob credits or steal product at a normal trading port. | SOURCE-CONFLICT at exactly -100: Evil_or_Red_Cashing and cabal "below -100"; Gypsy "-100 or more" evil; Someguy "negative alignment greater than -100" (player meaning: evil enough). | Built: `alignment <= -100` (`K.ROB_MIN_ALIGNMENT`). Easy to flip to `< -100`. |
| r2 | Experience | Experience sets how much you may safely take (see caps). Low exp still may attempt; over the cap raises bust odds to certain (or near-certain) in the original when far over. | CONFIRMED in shape: cabal formulas, Someguy Playing Evil, Gypsy (Holds x 20 safe for steal). | Built: caps below; over-cap attempts always bust. |
| r3 | StarDock | StarDock has no commodity market and is not robbed/stolen from. | CONFIRMED: EIS StarDockMenu; gap 2.18. | Built: excluded. |
| r4 | Class 0 / Federal | Class 0 ports (Sol/Terra, Alpha, Rylos) are special supply ports, not red-cash targets. This game's FEDERAL class-0 decoration ports match. | CONFIRMED in shape for Class 0 as non-trade evil targets (gap 1.7); UNVERIFIED that every source says "cannot rob Class 0" in those words. | Built: PortClass.FEDERAL and STARDOCK excluded. |
| **Rob credits** | | | | |
| r5 | Rob formula (safe max) | Max credits per attempt: Classic `EXP * 3`; MBBS `EXP * 6`. Sysop RobFactor: `(3 / RobFactor) * EXP` with RobFactor a percent (0.5 -> x6). | SOURCE-CONFLICT 7 (gap map). Cabal formulas.html prints both. TWGS Classic default x3; MBBS fixed x6. Ben's tie-break: MBBS. | Built: `K.ROB_CREDIT_FACTOR = 6` (MBBS). Classic 3 is one constant change away. |
| r6 | Port vault | Ports hold credits that traders leave by buying; reds rob that vault. | CONFIRMED in shape: Someguy ("Most ports have credits in them"), Gypsy Rob-Move-Rob, cabal Megga-Rob ranges. Exact seed formula UNVERIFIED. | Built: `Port.credits` seeded at generation from listed stock value; buy from port adds to vault; sell to port drains vault (floor 0). Rob takes `min(requested, vault, exp_cap)`. |
| r7 | Rob request | Player names how many credits to take. | CONFIRMED: in-game rob prompt (Evil_or_Red_Cashing). | Built: `rob` args `amount` (int). |
| **Steal product** | | | | |
| r8 | Steal formula (safe max holds) | Max holds: Classic `EXP / 30`; MBBS `EXP / 21`. Sysop StealFactor: `EXP / (30 * StealFactor)` (0.7 -> /21). Drop fractions. | SOURCE-CONFLICT 7. Cabal formulas.html. MBBS tie-break. | Built: `K.STEAL_HOLD_DIVISOR = 21`. Floor of exp/divisor. |
| r9 | What you steal | Product comes out of port stock into empty holds. SSM sells equipment then steals it back from a buy-port. | CONFIRMED in shape: Gypsy SSM, Someguy sell/steal, Misc_Evil_Functions. TEDIT "Steal from Buy Port" exists (cabal/glossary). Default ON/OFF UNVERIFIED. | Built: steal any traded commodity the port has in stock (buy or sell side), limited by empty holds, stock, and exp cap. Steal-from-buy-port allowed (SSM needs it). |
| r10 | Steal request | Player names commodity and qty. | CONFIRMED in shape. | Built: `steal` args `commodity`, `qty`. |
| **Bust chance** | | | | |
| r11 | Base chance | About 1 in 50 when within the safe cap. "You WILL bust." | CONFIRMED: cabal formulas, glossary, Busted.html, Gypsy. | Built: `K.ROB_BUST_DENOMINATOR = 50` (roll `rng.randrange(50) == 0`). |
| r12 | Over cap | Taking more than the safe max is dangerous; community treats it as near-certain bust. Exact curve UNVERIFIED. | UNVERIFIED (exact over-cap odds). | Built: amount/qty over the safe max -> always bust. |
| r13 | Fake bust | The game remembers the last port you successfully robbed or stole at. Trying the same port again always busts. | CONFIRMED: glossary "Fake Bust", Evil_or_Red_Cashing, Someguy Playing Evil. | Built: `Player.last_crime_sector_id`. Same sector again -> always bust. |
| **Bust cost** | | | | |
| r14 | Experience | Bust costs 10% of experience. | CONFIRMED: Busted.html, glossary, Someguy. | Built: `experience -= experience // 10`. |
| r15 | Holds (steal bust) | Lose 9% of the holds used in the failed steal attempt. Holds never go below 1. | CONFIRMED: Busted.html. | Built: `holds_lost = max(0, (qty * 9) // 100)`; holds floored at 1; cargo truncated to new holds. |
| r16 | Holds (rob bust) | Lose holds equal to 1% of the credits you tried to rob. Holds never go below 1. | CONFIRMED: Busted.html, glossary. | Built: `holds_lost = max(0, amount // 100)`; same floor and cargo trim. |
| r17 | Fine / fighters / ship / alignment on bust | Spec asked. Sources print exp + holds only. No credit fine, no fighter loss, no ship loss, no alignment change on bust. | CONFIRMED absent from Busted.html, glossary, Someguy. | Built: no fine, no fighters/ship hit, no alignment change on bust. |
| **Bust memory** | | | | |
| r18 | Bust list per port | A port remembers only the last trader who took a *real* bust there. That trader may not use the port (trade / rob / steal) until cleared. | CONFIRMED: glossary Bust Clearing, Someguy ("never go back there, even to trade"). | Built: `Port.bust_player_id`. Blocked on trade/rob/steal legality + handlers. |
| r19 | Clearing by another red | When another red takes a *real* bust at that port, the previous name is replaced (cleared for the first). | CONFIRMED: glossary, Someguy. | Built: real bust sets `bust_player_id` to the new buster. |
| r20 | Fake bust does not clear | A fake bust (same port twice) does not clear another player's bust list entry. | CONFIRMED: Someguy Playing Evil. | Built: fake bust applies penalties but does not write `bust_player_id`. |
| r21 | Daily / Extern clear | Busts clear daily (v3.05; MBBS daily). Someguy also describes a 14-day clear in one MBBS write-up. | SOURCE-CONFLICT (daily vs 14-day). Gap map 2.14 and cabal glossary / v3.05 prefer daily. | Built: every `tick_day` clears all `Port.bust_player_id`. |
| **Success awards** | | | | |
| r22 | Alignment / experience on success | Cabal prints SST/SDT *rates* (e.g. SST align -15/turn, exp +7.33/turn at 250 holds) but no closed-form per-hold success table. Formulas.html align table does not list rob/steal success. | UNVERIFIED (exact per-attempt formula). Rates imply steals pull alignment more evil and add some experience. | Built with easy constants: steal success `alignment -= max(1, qty // 6)`, `experience += max(1, qty // 15)`; rob success `alignment -= max(1, amount // 10_000)`, `experience += max(1, amount // 10_000)`. Documented as UNVERIFIED. |
| **Turns / daily limits** | | | | |
| r23 | Turn cost | Docking costs 1 turn; further port actions in the same visit cost 0. | CONFIRMED: Bible / DOCS docking; economy `trade_turn_cost` already. | Built: rob/steal use the same dock-visit turn rule. |
| r24 | Daily attempt limit | No source prints a max robs/steals per day (only bust clear and pods-per-day elsewhere). | UNVERIFIED (absent). | Built: no daily attempt cap. |
| **Mode** | | | | |
| r25 | ROB_MODE | New switch. | — | `tw2002` (default) enables verbs; `legacy` keeps today's "not available" (actions absent from the legal list, handlers refuse). |

### Deliberate differences

- No mega-rob byte-overrun (MBBS-only bug; cabal / Misc_megarob.txt). Out of scope.
- Success align/exp use simple UNVERIFIED constants (r22), not a fitted SST simulator.
- Port credit seed is a stock-value heuristic (r6), not a dumped TWGS vault formula.
- Steal-from-buy-port allowed by default (r9) so SSM shape works; no TEDIT toggle yet.
- Bust list blocks trade as Someguy describes; no separate "Police" UI.

## What the engine does (ROB_MODE tw2002)

- `K.ROB_MODE` defaults to `tw2002`. `legacy` hides rob/steal and refuses them.
- Actions: `rob` `{amount}`, `steal` `{commodity, qty}`.
- Caps, bust odds, fake bust, bust list, daily clear, StarDock/Class 0 exclusions as the table.
- Seat brains do not rob or steal yet; rejected stays 0; N2/N3 bars keep their existing RANK_MODE pins where present.

## Delivered

- Rules table, ROB_MODE switch, planted bugs, seats legal, scripted match before and after. See the commit message and the parent report.

## Planted bugs

Each bug maps to a failing assertion in 	ests/test_rob_steal_v1.py (legal list and handler). Caught 10 of 10 named plants plus switch/doc/seat checks.

| # | planted bug | where | caught by |
| --- | --- | --- | --- |
| p1 | ROB_MODE legacy still offers a working rob | legal list + handler | 	est_plant_legacy_hides_rob_and_steal |
| p2 | alignment above -100 can still rob | legal list + handler | 	est_plant_good_alignment_cannot_rob |
| p3 | StarDock accepts rob | legal list + handler | 	est_plant_stardock_excluded |
| p4 | Class 0 / FEDERAL accepts steal | legal list | 	est_plant_class0_excluded |
| p5 | over-cap rob can succeed on a lucky roll | handler | 	est_plant_over_cap_always_busts |
| p6 | second crime at same port succeeds / writes bust list | handler | 	est_plant_fake_bust_same_port |
| p7 | real bust still allows trade; daily clear forgotten | legal list + handler + tick_day | 	est_plant_bust_blocks_trade_until_clear |
| p8 | steal success leaves stock and alignment unchanged | handler | 	est_plant_steal_success_moves_stock_and_align |
| p9 | steal bust uses rob's 1%-of-credits hold loss | handler | 	est_plant_steal_bust_holds_nine_percent |
| p10 | second red's real bust leaves the first blocked | handler + legal list | 	est_plant_another_red_real_bust_clears_first |
