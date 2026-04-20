"""Targeted tests for the four memory improvements to `Observation`.

These are the specific fixes for the pathologies observed in the
Grok-vs-Claude 5-day sanity match (saves/20260419-161706-seed42):

  #1 warp_graph          - Grok deadlooped 406<->475 for ~29 turns
  #2 recent_failures     - 4x warp_blocked 406->712 with no escalation signal
  #3 trade_log 25 + summary - 75% haggle-countered rate invisible after 5 trades
  #4 recent_events 30    - 12-event window is <1/2 a real-day slice at 300 tpd

Each improvement gets one positive and one negative assertion where it
makes sense (pattern is present when expected, absent when not).
"""
from __future__ import annotations

from tw2k.engine import (
    Action,
    ActionKind,
    GameConfig,
    Observation,
    apply_action,
    build_observation,
    generate_universe,
)
from tw2k.engine.models import EventKind, Player, Ship


def _make_universe(seed: int = 2026, size: int = 50):
    cfg = GameConfig(seed=seed, universe_size=size, max_days=5)
    u = generate_universe(cfg)
    p = Player(id="A", name="Alice", ship=Ship(holds=20), sector_id=1)
    u.players["A"] = p
    u.sectors[1].occupant_ids.append("A")
    p.known_sectors.add(1)
    # Seed starting-sector warp graph (mirrors the production spawn path).
    p.known_warps[1] = list(u.sectors[1].warps)
    return u, p


# ---------------------------------------------------------------------------
# #1 — warp_graph / known_warps
# ---------------------------------------------------------------------------


class TestKnownWarps:
    def test_spawn_seeds_home_warps(self):
        u, p = _make_universe()
        obs = build_observation(u, "A")
        # Dict keys are stringified for JSON safety in the observation
        assert "1" in obs.known_warps
        assert obs.known_warps["1"] == list(u.sectors[1].warps)

    def test_warp_records_destination_graph(self):
        u, p = _make_universe()
        # Warp to the first adjacent sector; it should learn THAT sector's warps.
        target = u.sectors[1].warps[0]
        res = apply_action(u, "A", Action(kind=ActionKind.WARP, args={"target": target}))
        assert res.ok, res.error
        obs = build_observation(u, "A")
        assert str(target) in obs.known_warps
        assert obs.known_warps[str(target)] == list(u.sectors[target].warps)

    def test_scan_records_current_sector_but_not_neighbor_topology(self):
        u, p = _make_universe()
        # Move to an arbitrary neighbor, then scan — scan should record
        # the NEW sector's warps in the graph, and should NOT learn the
        # 2-hop neighbors' warps (fog of war on topology).
        nbr = u.sectors[1].warps[0]
        apply_action(u, "A", Action(kind=ActionKind.WARP, args={"target": nbr}))
        p.known_warps.pop(str(nbr), None)  # simulate fresh scanner
        p.known_warps.pop(nbr, None)
        apply_action(u, "A", Action(kind=ActionKind.SCAN, args={}))
        obs = build_observation(u, "A")
        assert str(nbr) in obs.known_warps
        # A 2-hop sector we haven't visited should NOT be in known_warps
        # (existence may still be in known_sectors, but warps shouldn't leak).
        two_hop_candidates = [
            w for w in u.sectors[nbr].warps
            if w != 1 and w not in p.known_warps and str(w) not in obs.known_warps
        ]
        assert two_hop_candidates, "expected at least one 2-hop sector unknown to player"

    def test_probe_records_target_warp_graph(self):
        u, p = _make_universe()
        p.ship.ether_probes = 1
        # Pick any non-adjacent sector with at least one warp.
        target = next(
            sid for sid in u.sectors
            if sid != 1 and sid not in u.sectors[1].warps and u.sectors[sid].warps
        )
        res = apply_action(
            u, "A", Action(kind=ActionKind.PROBE, args={"target": target})
        )
        assert res.ok, res.error
        obs = build_observation(u, "A")
        assert str(target) in obs.known_warps
        assert obs.known_warps[str(target)] == list(u.sectors[target].warps)


# ---------------------------------------------------------------------------
# #2 — recent_failures (grouped failure counter)
# ---------------------------------------------------------------------------


class TestRecentFailures:
    def test_empty_when_no_failures(self):
        u, p = _make_universe()
        obs = build_observation(u, "A")
        assert obs.recent_failures == []

    def test_repeated_warp_blocked_surfaces_with_count(self):
        u, p = _make_universe()
        # Emit the canonical Grok pathology: 4× warp_blocked 406->712.
        # We don't need to actually be in 406 — we just need the events
        # to exist as the agent's actor_id'd failures.
        for _ in range(4):
            u.emit(
                EventKind.WARP_BLOCKED,
                actor_id="A",
                sector_id=1,
                payload={"target": 712, "from": 406},
                summary="Alice: no route from 406 to 712",
            )
        obs = build_observation(u, "A")
        assert len(obs.recent_failures) == 1
        row = obs.recent_failures[0]
        assert row["kind"] == "warp_blocked"
        assert row["count"] == 4
        assert "712" in row["target_label"]
        # Hint stream should include the "REPEATED FAILURES" prefix so the
        # LLM sees it even if it ignores the structured field.
        assert "REPEATED FAILURES" in obs.action_hint
        assert "x4" in obs.action_hint

    def test_single_failure_is_not_surfaced(self):
        u, p = _make_universe()
        u.emit(
            EventKind.WARP_BLOCKED,
            actor_id="A",
            sector_id=1,
            payload={"target": 712},
            summary="Alice: no route from 406 to 712",
        )
        obs = build_observation(u, "A")
        # Threshold is >=2 — one-off failures are noise, not a pattern.
        assert obs.recent_failures == []

    def test_different_targets_bucket_separately(self):
        u, p = _make_universe()
        for _ in range(3):
            u.emit(
                EventKind.WARP_BLOCKED,
                actor_id="A",
                payload={"target": 712},
                summary="blocked 712",
            )
        for _ in range(2):
            u.emit(
                EventKind.WARP_BLOCKED,
                actor_id="A",
                payload={"target": 999},
                summary="blocked 999",
            )
        obs = build_observation(u, "A")
        assert len(obs.recent_failures) == 2
        counts = {row["count"] for row in obs.recent_failures}
        assert counts == {3, 2}


# ---------------------------------------------------------------------------
# #3 — trade_log (25 entries) + trade_summary aggregate
# ---------------------------------------------------------------------------


class TestTradeLogAndSummary:
    def _synth_trade(
        self, *, commodity: str, qty: int, unit: int, side: str,
        realized_profit: int | None = None, note: str = "",
    ) -> dict:
        return {
            "day": 1, "tick": 1, "sector_id": 7,
            "commodity": commodity, "qty": qty, "side": side,
            "unit": unit, "total": qty * unit, "note": note,
            "realized_profit": realized_profit,
        }

    def test_trade_log_slice_is_25(self):
        u, p = _make_universe()
        for i in range(30):
            p.trade_log.append(self._synth_trade(
                commodity="organics", qty=20, unit=25, side="buy"
            ))
        obs = build_observation(u, "A")
        # Up from the previous cap of 5; 25 is the new LLM-visible window.
        assert len(obs.trade_log) == 25

    def test_summary_empty_ledger(self):
        u, p = _make_universe()
        obs = build_observation(u, "A")
        assert obs.trade_summary["total_trades"] == 0
        assert obs.trade_summary["total_profit_cr"] == 0
        assert obs.trade_summary["best_pair"] is None

    def test_summary_aggregates_profit_and_margin(self):
        u, p = _make_universe()
        # 2 buys at 20cr, 2 sells at 25cr — realized profit should match
        # (unit - basis) * qty on each sell.
        p.trade_log.append(self._synth_trade(
            commodity="organics", qty=20, unit=20, side="buy"
        ))
        p.trade_log.append(self._synth_trade(
            commodity="organics", qty=20, unit=25, side="sell",
            realized_profit=100, note="haggle countered",
        ))
        p.trade_log.append(self._synth_trade(
            commodity="fuel_ore", qty=20, unit=14, side="buy"
        ))
        p.trade_log.append(self._synth_trade(
            commodity="fuel_ore", qty=20, unit=20, side="sell",
            realized_profit=120, note="",
        ))
        obs = build_observation(u, "A")
        s = obs.trade_summary
        assert s["total_trades"] == 4
        assert s["sells"] == 2
        assert s["total_profit_cr"] == 220
        assert s["haggle_win_rate_pct"] == 75.0  # 3 of 4 not countered
        # fuel_ore earned more than organics so it's best_pair
        assert s["best_pair"]["commodity"] == "fuel_ore"
        assert s["worst_pair"]["commodity"] == "organics"

    def test_summary_detects_negative_margin(self):
        u, p = _make_universe()
        # Bought at 30, sold at 20 — a loss.
        p.trade_log.append(self._synth_trade(
            commodity="equipment", qty=10, unit=30, side="buy"
        ))
        p.trade_log.append(self._synth_trade(
            commodity="equipment", qty=10, unit=20, side="sell",
            realized_profit=-100,
        ))
        obs = build_observation(u, "A")
        assert obs.trade_summary["total_profit_cr"] == -100
        assert obs.trade_summary["avg_margin_pct"] < 0


# ---------------------------------------------------------------------------
# #4 — recent_events window bumped 12 → 30
# ---------------------------------------------------------------------------


class TestRecentEventsWindow:
    def test_observation_event_history_default(self):
        u, p = _make_universe()
        # Emit 25 visible-to-A events; default event_history=40 means
        # they should all appear in the observation.
        for i in range(25):
            u.emit(
                EventKind.AGENT_THOUGHT,
                actor_id="A",
                sector_id=1,
                payload={"text": f"thought-{i}"},
                summary=f"Alice thought {i}",
            )
        obs = build_observation(u, "A")
        assert len(obs.recent_events) >= 25

    def test_format_observation_uses_30_events(self):
        """format_observation (prompts.py) slices to the last 30 events."""
        from tw2k.agents.prompts import format_observation

        u, p = _make_universe()
        for i in range(50):
            u.emit(
                EventKind.AGENT_THOUGHT,
                actor_id="A",
                sector_id=1,
                payload={"text": f"t{i}"},
                summary=f"Alice thought {i}",
            )
        obs = build_observation(u, "A")
        payload = format_observation(obs)
        # Coarse assertion: count the distinct thought markers. The
        # per-entry summary is unique so we can cheaply count.
        marker = '"Alice thought '
        n_in_payload = payload.count(marker)
        assert 25 <= n_in_payload <= 30


# ---------------------------------------------------------------------------
# End-to-end — observation shape smoke
# ---------------------------------------------------------------------------


def test_observation_model_fields_present():
    u, p = _make_universe()
    obs = build_observation(u, "A")
    assert isinstance(obs, Observation)
    assert isinstance(obs.known_warps, dict)
    assert isinstance(obs.trade_summary, dict)
    assert isinstance(obs.recent_failures, list)
    # known_warps is keyed by str(sector_id) for JSON compatibility
    assert all(isinstance(k, str) for k in obs.known_warps)
    assert all(isinstance(v, list) for v in obs.known_warps.values())
