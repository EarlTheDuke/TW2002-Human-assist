"""Seat-bot S2 - progress-based stall detector (tw2k.agents.stall).

Cases from the Kimi3 match (docs/playtests/multibot-2026-09-23-kimi3/FEEDBACK.md):
* StarDock <-> home colonist ferry alternates targets -> must NOT stall.
* Re-plotting the same target (StarDock) while approaching -> must NOT stall.
* 14 <-> 571 warp loop with an empty hold -> MUST stall.
* Sector-68 buy fuel -> land -> dump -> liftoff under a colonize intent -> MUST stall.
"""

from __future__ import annotations

from tw2k.agents.stall import Intent, StallDetector, known_distance, snapshot
from tw2k.engine import GameConfig, generate_universe
from tw2k.engine.models import Player
from tw2k.engine.observation import build_observation

# Known map: StarDock 1 - 2 - 3 - 19 (home, planet 38); side pocket 14 <-> 571.
WARPS = {1: [2], 2: [1, 3], 3: [2, 19], 19: [3], 14: [571], 571: [14, 3]}


def obs(sector: int, *, day: int = 1, credits: int = 50_000, colonists: int = 0, fuel: int = 0,
        planet_col: int = 2500, citadel=(1, 1), known=None, genesis: int = 0) -> dict:
    return {
        "day": day,
        "sector": {"id": sector},
        "credits": credits,
        "ship": {"class": "cargotran", "genesis": genesis,
                 "cargo": {"colonists": colonists, "fuel_ore": fuel, "organics": 0, "equipment": 0}},
        "known_warps": {str(k): v for k, v in WARPS.items()},
        "known_sectors": [{"id": s} for s in (known or WARPS)],
        "owned_planets": [{"id": 38, "sector_id": 19, "citadel_level": citadel[0], "citadel_target": citadel[1],
                           "colonists_total": planet_col}],
    }


def test_known_distance_uses_memory_only() -> None:
    kw = {int(k): tuple(v) for k, v in WARPS.items()}
    assert known_distance(kw, 1, 19) == 3
    assert known_distance(kw, 19, 1) == 3
    assert known_distance(kw, 1, 999) is None


def test_stardock_home_ferry_alternation_never_stalls() -> None:
    det = StallDetector(window=3)
    home, dock = 19, 1
    col = 2500
    stalled = []
    for _trip in range(4):
        # At StarDock: buy colonists, then fly home (target 19).
        det.observe(obs(dock, planet_col=col), Intent("colonize", home))
        r = det.observe(obs(dock, colonists=75, credits=49_250, planet_col=col), Intent("colonize", home))
        stalled.append(r.stalled)
        for s in (2, 3, 19):
            stalled.append(det.observe(obs(s, colonists=75, planet_col=col), Intent("colonize", home)).stalled)
        # Home: land + assign (colonists move to the planet), then fly back (target 1).
        col += 75
        stalled.append(det.observe(obs(home, planet_col=col), Intent("colonize", dock)).stalled)
        for s in (3, 2, 1):
            stalled.append(det.observe(obs(s, planet_col=col), Intent("colonize", dock)).stalled)
    assert not any(stalled), stalled


def test_same_target_replot_while_approaching_is_progress() -> None:
    det = StallDetector(window=2)
    det.observe(obs(19), Intent("travel", 1))
    reports = [det.observe(obs(s), Intent("travel", 1)) for s in (3, 2, 1)]
    assert all(r.progress for r in reports), [r.summary() for r in reports]
    assert "arrived 1" in reports[-1].reasons


def test_true_14_571_loop_stalls() -> None:
    det = StallDetector(window=6)
    det.observe(obs(14), Intent("travel", 1))
    reports = []
    for i in range(12):
        reports.append(det.observe(obs(571 if i % 2 == 0 else 14), Intent("travel", 1)))
    # The first hop 14 -> 571 is genuinely closer to StarDock (571 links to 3); after that it only oscillates.
    assert reports[0].progress
    assert not any(r.progress for r in reports[1:])
    assert reports[6].stalled and not reports[5].stalled
    assert "14" in reports[-1].summary() and "571" in reports[-1].summary()


def test_loop_without_target_that_revisits_known_sectors_stalls() -> None:
    det = StallDetector(window=4)
    det.observe(obs(14))
    reports = [det.observe(obs(571 if i % 2 == 0 else 14)) for i in range(5)]
    assert reports[3].stalled


def test_exploration_is_progress() -> None:
    det = StallDetector(window=2)
    det.observe(obs(3, known=[1, 2, 3]))
    r1 = det.observe(obs(19, known=[1, 2, 3, 19]))
    r2 = det.observe(obs(3, known=[1, 2, 3, 19, 571]))
    assert r1.progress and r2.progress


def test_sector68_buy_dump_loop_stalls_under_colonize_intent() -> None:
    det = StallDetector(window=6)
    credits = 40_000
    det.observe(obs(19, credits=credits), Intent("colonize"))
    reports = []
    for _ in range(3):
        credits -= 500  # buy fuel
        reports.append(det.observe(obs(19, credits=credits, fuel=20), Intent("colonize")))
        reports.append(det.observe(obs(19, credits=credits, fuel=20), Intent("colonize")))  # land
        reports.append(det.observe(obs(19, credits=credits), Intent("colonize")))           # dump fuel on planet
        reports.append(det.observe(obs(19, credits=credits), Intent("colonize")))           # liftoff
    assert not any(r.progress for r in reports)
    assert reports[5].stalled


def test_trade_intent_counts_new_credit_highs_not_churn() -> None:
    det = StallDetector(window=3)
    det.observe(obs(2, credits=10_000), Intent("trade"))
    assert not det.observe(obs(2, credits=9_000, fuel=50), Intent("trade")).progress     # buy
    assert det.observe(obs(3, credits=9_000, fuel=50), Intent("trade")).progress is False
    assert det.observe(obs(3, credits=11_000), Intent("trade")).progress                  # profitable sell


def test_day_rollover_growth_is_not_progress() -> None:
    det = StallDetector(window=3)
    det.observe(obs(19, day=1, planet_col=2500))
    r = det.observe(obs(19, day=2, planet_col=2625))  # passive overnight growth
    assert not r.progress


def test_citadel_and_genesis_changes_are_progress() -> None:
    det = StallDetector(window=3)
    det.observe(obs(19, citadel=(1, 1)))
    assert det.observe(obs(19, citadel=(1, 2))).progress
    assert det.observe(obs(1, genesis=1)).progress is True  # bought a genesis (sector known already)


def test_accepts_real_observation_model() -> None:
    u = generate_universe(GameConfig(seed=5, universe_size=40, max_days=2, turns_per_day=20))
    u.players["P1"] = Player(id="P1", name="A", agent_kind="external", sector_id=1)
    u.sectors[1].occupant_ids.append("P1")
    o = build_observation(u, "P1")
    snap = snapshot(o)
    assert snap.sector == 1 and snap.known >= 1
    det = StallDetector()
    assert det.observe(o).progress  # first observation
    assert not det.observe(o).progress
