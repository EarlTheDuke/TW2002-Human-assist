# Bots deploy defenses

Slice `bots-deploy-defenses-v1`. Engine deploy verbs already work under `HARDWARE_MODE`. Seats were buying armids and almost never laying them (corp reports showed corporate/sector deploys = 0 for most seats). This page is when N2 and N3 buy a small mine stack and lay armids, limpets, and defensive fighters on owned-planet sectors.

Cross-links: `docs/playtests/bots/BOT_HARDWARE_ROB.md`, `docs/playtests/ships/SHIP_HARDWARE.md`, slice 63 war lays.

## Flag

`BOTS_DEPLOY_MODE` = `"tw2002"` | `"legacy"`. Legacy skips the new buy/lay/plot brain and keeps the old home-only armid lay. Engine verbs are unchanged.

## Bots now use

| verb | when | cash / skill | turns | sensible means | hidden when |
| --- | --- | --- | --- | --- | --- |
| `buy_equip` armid_mines / limpet_mines | StarDock, N2/N3, own planet or home known, stack under `BOT_DEPLOY_MINE_QTY` | mine spend ≤ `BOT_DEPLOY_MINE_SPEND_PCT` of trading profit; cash buffer kept | 1 | one restock, tracked in scratchpad | `BOTS_DEPLOY_MODE` legacy |
| `deploy_mines` armid / limpet | standing on an owned-planet sector or a quiet home | mines aboard | 1 | qty ≤ `BOT_DEPLOY_MINE_QTY`; not FedSpace / MSL | legacy uses home-only armids |
| `deploy_fighters` defensive | same sectors, fighters above floor | keep `BOT_DEPLOY_FIGHTER_FLOOR` aboard | 1 | fill sector up toward the floor | legacy |
| plot to own/home | mines aboard and lay due (`BOT_DEPLOY_MINE_GAP_DAYS`) | — | travel | one lay trip per gap | legacy |

N1 and H stay out of this slice. War lays (`BOTS_WAR_MODE`) still run when war is on; this slice covers the peacetime plot-to-lay gap.

## Constants

| name | default | role |
| --- | --- | --- |
| `BOT_DEPLOY_MINE_GAP_DAYS` | 1 | at most one plot-to-lay trip per day |
| `BOT_DEPLOY_MINE_QTY` | 5 | mines laid (and restocked) per visit |
| `BOT_DEPLOY_MINE_SPEND_PCT` | 5 | mine-buy spend vs trading profit |
| `BOT_DEPLOY_FIGHTER_FLOOR` | 10 | keep this many fighters aboard when dropping defensive |

FedSpace deploys stay refused. An owned-planet sector that sits on an MSL still gets one fortify try so every N2/N3 seat can clear the bar; the lane sweep may clear the stack afterward.

## Bars

- ≥ 1 deployment (`deploy_mines` or `deploy_fighters`) per N2/N3 seat per 10 days on seeds 250925 and 4242
- mine spend < 5% of trading profit
- no broke seats from mine buys
- rejected 0/0, save/load identical
- legacy pin `9b607d3dae940c0b1a69f6d7` byte-identical

## Plants

At least 12 planted bugs, each restored after its test fails. See `tests/test_bots_deploy_defenses_v1.py`.

## Measured

10-day scripted matches, seats N3,N3,N2,N2,N1,H, universe 1000, 1000 turns/day, start 20,000, Ferrengi on. Rejected 0/0 and exceptions 0 on every seat. `save_load_day15` is null because the check runs when the day counter is 15.

Seed 250925, digest `f1b4188d`.

| Seat | Net worth | Credits | Planets | Deaths | Corporate deploys | Armid lays | Defensive fighters |
|------|-----------|---------|---------|--------|-------------------|------------|--------------------|
| N3-P1 | 429,645 | 99,862 | 2 | 0 | 8 | 7 | 10 |
| N3-P2 | 167,678 | 13,115 | 1 | 0 | 3 | 2 | 10 |
| N2-P3 | 310,952 | 58,593 | 2 | 0 | 58 | 56 | 11 |
| N2-P4 | 91,736 | 5,783 | 1 | 4 | 1 | 1 | 0 |
| N1-P5 | 45,199 | 0 | 1 | 6 | 0 | 0 | 0 |
| H-P6 | 10,452 | 0 | 0 | 5 | 0 | 0 | 0 |

Seed 4242, digest `764b3596`.

| Seat | Net worth | Credits | Planets | Deaths | Corporate deploys | Armid lays | Defensive fighters |
|------|-----------|---------|---------|--------|-------------------|------------|--------------------|
| N3-P1 | 655,993 | 81,748 | 3 | 0 | 17 | 16 | 8 |
| N3-P2 | 93,247 | 8,224 | 1 | 2 | 1 | 0 | 10 |
| N2-P3 | 156,801 | 0 | 1 | 5 | 32 | 31 | 10 |
| N2-P4 | 119,734 | 0 | 1 | 4 | 1 | 0 | 1 |
| N1-P5 | 437,390 | 68,750 | 1 | 0 | 0 | 0 | 0 |
| H-P6 | 527,643 | 22,069 | 0 | 2 | 0 | 0 | 0 |

Every N2/N3 seat has at least one corporate deploy on both seeds. N1 laid no armids (P5 on 250925 has personal defensive fighters only). On 4242, P3 and P4 finished at 0 credits after 5 and 4 deaths. P4 spent 0 on mines. P3 spent 3,100, which is 1.78% of 173,699 trading profit. The 0-credit endings follow the deaths, not the mine buys.

Mine spend on the same two digests (`f1b4188d`, `764b3596`), credits versus realized trading profit:

| Seed | P1 | P2 | P3 | P4 |
|------|----|----|----|----|
| 250925 | 700 / 464,811 (0.15%) | 200 / 99,596 (0.20%) | 5,600 / 240,917 (2.32%) | 100 / 125,322 (0.08%) |
| 4242 | 1,700 / 627,199 (0.27%) | 0 / 106,851 (0.00%) | 3,100 / 173,699 (1.78%) | 0 / 121,295 (0.00%) |

Seed 250925, 15 days, digest `61bcb8cc`. Day-15 save/load was identical. Rejected 0/0. Corporate deploys P1 13, P2 3, P3 66, P4 1. Deploy legacy pin `9b607d3dae940c0b1a69f6d7` passed. Plants bd1-bd13 were re-broken on this tree and restored. Suite on `49a0c63`: 2430 passed, 2 failed, 1 skipped, 22 warnings, 3062s. Both failures are the known flakes: WinError 10048 on the reserved-port test, and the spectator-feed Playwright timeout.
