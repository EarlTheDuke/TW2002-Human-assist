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
2. The purse is credits plus what the bank can withdraw. The death reserve is one Merchant Cruiser, 41,300, and it stays in the bank. If that reserve blocks every cargo hull, drop the reserve to one Scout, 15,950, and pick again. If that still blocks every cargo hull, buy the best hull that leaves at least 1 credit on the ship and does not empty the bank.
3. The withdraw happens before the buy. The buy does not spend the reserve that step 2 kept.
4. Once the new hull is aboard, the seat goes back to its normal trade route. No new verb. No prompt change. No combat-odds change.

## Bars

Seeds 250925 and 424242, the same six-seat scripted match the later slices use (N3, N3, N2, N2, N1, H).

- H day-10 net worth is at least 100,000 on both seeds.
- H has 0 broke days.
- Rejected 0/0. Save/load identical.
- With the flag off, the other seats' digests stay on the legacy pin.

## Pin

`H_RECOVERY_MODE` is in the explicit legacy flips. Nothing reads it yet. The corp-fix golden `9b607d3dae940c0b1a69f6d7` still matches: 1 passed in 42s.

## In the code

H and N1 withdraw first, then buy the best cargo hull that leaves the reserve. N2 and N3 still use today's CargoTran-or-Scout buy. Tests: `test_hr1` through `test_hr5`, 5 passed, plus the older pod tests still pass. The 10-day bars are not run yet. Plant at least 10 bugs and re-break each one on the final commit before this slice is marked Delivered.
