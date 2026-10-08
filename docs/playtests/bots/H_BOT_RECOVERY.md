# H bot recovery (slice 65)

The built-in H seat, and the N1 seat on seed 424242, die and come back in a Scout with no cash. Day 10 net worth stays under 100,000: H is 50,003 on seed 250925 and 7,975 on seed 424242 (slice 61 S7).

## Today, before this slice

Both buyers treat an escape pod the same way.

- H is `HeuristicAgent._leave_pod`. At StarDock it buys a CargoTran when credits minus the net cost still leave 20,000. Otherwise it buys a Scout and keeps nothing.
- N1 is `SeatBrain._leave_pod` (`value_allocator` off, `feed_organics` off). It buys a CargoTran when credits minus the net cost still leave `cash_buffer` (2,000). Otherwise it buys a Scout and keeps nothing.
- The bank withdraw that runs first asks for a CargoTran plus that same keep. It does not ask for a Merchant Cruiser. If the withdraw is too small, the buy still takes the Scout.
- Hull prices: Scout Marauder 15,950 (25 holds), Merchant Freighter 33,400 (65 holds), Merchant Cruiser 41,300 (20 holds), CargoTran 51,950 (75 holds).

## Decision

`H_RECOVERY_MODE` is `"tw2002"` by default and `"legacy"` for the old buy. `h_recovery_on()` is that flag alone. Legacy stays byte-identical. The pin flips this mode with the other `*_MODE` flags.

When the flag is on, only H and N1 change. N2 and N3 keep today's buy.

After a death, at StarDock, withdraw first, then buy, then trade.

1. Pick the cargo hull with the most holds that the purse can buy while leaving the death reserve in the bank. Order: CargoTran (75 holds), Merchant Freighter (65), Merchant Cruiser (20). A Scout is only the last resort.
2. The purse is credits plus what the bank can withdraw. The death reserve starts as one Merchant Cruiser, 41,300, and it stays in the bank. If that blocks every cargo hull, drop the reserve to one Scout, 15,950. If that still blocks, drop it to the H keep, 10,000. If the hull still does not fit, do not withdraw. A drain that leaves 1 credit emptied the bank and the next death took the cash.
3. The withdraw happens before the buy. The buy does not spend the reserve that step 2 kept.
4. Once the new hull is aboard, the seat goes back to its normal trade route. No new verb. No prompt change. No combat-odds change.
5. Away from StarDock, a purse over 50,000 plots back and the spare cash is deposited before the next route. Ship credits die with the hull. The bank does not.
6. An empty bank, with more than the keep aboard and no cargo, plots to StarDock before the first trade. A free Scout with no trading float and cash in the bank plots home. A ship that can already buy a load stays out and trades. If the whole purse covers a cargo hull, that net is withdrawn even when the keep floor would have blocked it.

## Bars

Seeds 250925 and 424242, the same six-seat scripted match the later slices use (N3, N3, N2, N2, N1, H).

- H day-10 net worth is at least 100,000 on both seeds.
- H has 0 broke days.
- Rejected 0/0. Save/load identical.
- With the flag off, the other seats' digests stay on the legacy pin.

## Pin

`H_RECOVERY_MODE` is in the explicit legacy flips. Nothing reads it yet. The corp-fix golden `9b607d3dae940c0b1a69f6d7` still matches: 1 passed in 42s.

## In the code

H and N1 withdraw first, then buy the best cargo hull that leaves the reserve. A hull the wallet cannot afford is still a withdraw target when the only block is insufficient credits. N2 and N3 still use today's CargoTran-or-Scout buy. Tests `test_hr1` through `test_hr6` passed.

## 10-day, first column

Seed 250925, `H_RECOVERY_MODE` tw2002, 206s, before the hidden-hull fix. H day-10 net worth 50,188, still a Scout, bank withdraws 0, broke 0, rejected 0/0. The other seats matched the earlier column. The legal list had hidden the cargo hulls.

The same column after that fix, 213s, is identical: H 50,188, Scout, withdraws 0. Ship Destroyed hands back a free Scout, and the withdraw only ran while the ship was an escape pod.

The free-Scout column, 219s, is worse. H day-10 net worth 9,523, still a Scout, broke 1 day, withdraws 41,379. The last-resort step drained the bank and the next death took the cash. The third floor is now the 10,000 H keep, and a hull that still does not fit causes no withdraw.

The cash-floor column, 248s, bought the freighter. H climbed to 694,845 on day 9, then one death took 610,309 off the ship and day 10 finished at 73,503, still a freighter, broke 0, rejected 0/0. A purse over 50,000 now plots back to StarDock.

The purse column, 191s, clears this seed. H day-10 net worth 316,222, broke 0, rejected 0/0, save identical. Bank balance 308,247, deposits 308,247, withdraws 0, credits lost 14,276 across 2 deaths. Day path 42,650, 57,103, 66,317, 109,963, 160,563, 218,871, 266,135, 341,326, 411,147, 316,222. Day 10 ends in the free Scout because those deaths came after the purse was already banked.

Seed 424242 on that same tip, 501s, misses. H day-10 net worth 7,975 from day 2 on, broke 9, Scout, 7 deaths, 8 sells, bank 0, withdraws 0, credits lost 17,570. N1 stays at 17,975 from day 1, Scout, 0 sells, bank 10,000, withdraws 0. The first death took the purse before any deposit, and 10,000 in the bank cannot buy a cargo hull so it stayed locked. An empty bank now plots home before the first trade, and a keep is withdrawn when no hull fits.

The thin-bank column, 232s, is higher and still short. H reached 105,751 on day 4, then sat at 40,159 from day 5 through day 10, Scout, broke 0, 2 deaths, 344 sells, bank 22,184, withdraws 10,000, credits lost 34,917. The save round-trip differed. After the death the Scout plotted home every turn and never sold again. A ship that can already buy a load stays out and trades. A purse that can cover a freighter withdraws that net even when the keep floor would have blocked it.

The trade-again column, 439s, clears this seed. H day-10 net worth 662,652, CargoTran, broke 0, rejected 0/0, save identical. Day path 42,650, 18,195, 60,757, 80,410, 191,989, 306,310, 399,779, 544,844, 662,052, 662,652. Bank 500,000, deposits 510,000, withdraws 10,000, credits lost 22,692 across 2 deaths, 631 sells. N1 finished at 389,707 in a CargoTran, 163 sells, broke 1. Seed 250925 is being confirmed on this same tip.

Plant at least 10 bugs and re-break each one on the final commit before this slice is marked Delivered.
