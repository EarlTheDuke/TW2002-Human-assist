"""Phase 1 regression tests (Match 5 prep).

Covers:
- M3-1 proper fix:  `_coalesce_message_text` falls back to `message.reasoning`
  when `message.content` is empty, surfaces diagnostics on bare failure,
  and exposes finish_reason=length so we can tell a truncated response
  from a genuinely empty one.
- M4-12:  observation exposes `sector.warps_count` as a first-class field,
  and adds a MAP COVERAGE / DEAD-END POCKET hint when the agent is in a
  1-warp pocket — so Qwen3.5-class reasoning models stop broadcasting
  false "trapped" rescue bounties (Match 4 P2 behaviour).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# ---------------------------------------------------------------------------
# Fake OpenAI-shape chat-completion responses for _coalesce_message_text tests.
# ---------------------------------------------------------------------------


@dataclass
class _FakeMsg:
    content: str | None = None
    reasoning: str | None = None


@dataclass
class _FakeChoice:
    message: _FakeMsg
    finish_reason: str = "stop"


@dataclass
class _FakeResp:
    choices: list[_FakeChoice]


def _mk(
    content: str | None = None,
    reasoning: str | None = None,
    finish_reason: str = "stop",
) -> _FakeResp:
    return _FakeResp(
        choices=[_FakeChoice(_FakeMsg(content=content, reasoning=reasoning), finish_reason)]
    )


VALID_JSON = '{"thought":"ok","action":{"kind":"scan","args":{}}}'


# ---------------------------------------------------------------------------
# M3-1 — coalesce helper
# ---------------------------------------------------------------------------


class TestM31CoalesceMessageText:
    def test_prefers_content_when_both_populated(self):
        from tw2k.agents.llm import _coalesce_message_text

        resp = _mk(content=VALID_JSON, reasoning='{"not":"this"}')
        text, diag = _coalesce_message_text(resp)
        assert text == VALID_JSON
        assert diag.source == "content"
        assert diag.content_len == len(VALID_JSON)
        assert diag.reasoning_len > 0  # still recorded for diagnostics

    def test_falls_back_to_reasoning_when_content_empty(self):
        """Core M3-1 regression. OWUI+Ollama with reasoning models under
        response_format=json_object routinely returns content='' and the
        JSON ends up in message.reasoning. Previously we dropped those
        turns; now we use them.
        """
        from tw2k.agents.llm import _coalesce_message_text

        resp = _mk(content="", reasoning=VALID_JSON)
        text, diag = _coalesce_message_text(resp)
        assert text == VALID_JSON
        assert diag.source == "reasoning"
        assert diag.content_len == 0
        assert diag.reasoning_len == len(VALID_JSON)

    def test_empty_source_when_both_missing(self):
        from tw2k.agents.llm import _coalesce_message_text

        resp = _mk(content="", reasoning="", finish_reason="length")
        text, diag = _coalesce_message_text(resp)
        assert text == ""
        assert diag.source == "empty"
        assert diag.finish_reason == "length"
        # diag.short() must be a useful single-line description so the
        # parse-error thought is greppable in the event feed.
        assert "finish=length" in diag.short()
        assert "src=empty" in diag.short()

    def test_prefer_reasoning_flag(self):
        from tw2k.agents.llm import _coalesce_message_text

        resp = _mk(content=VALID_JSON, reasoning='{"pref":"reasoning"}')
        text, diag = _coalesce_message_text(resp, prefer="reasoning")
        assert text == '{"pref":"reasoning"}'
        assert diag.source == "reasoning"

    def test_reasoning_fallback_round_trips_through_parser(self):
        """End-to-end: coalesce returns JSON from reasoning → _parse_response
        produces a valid Action. Guards against an 'empty content =>
        diagnostic-only' regression that would still WAIT the turn."""
        from tw2k.agents.llm import _coalesce_message_text, _parse_response

        resp = _mk(
            content="",
            reasoning='{"thought":"go","action":{"kind":"warp","args":{"target":5}}}',
        )
        text, _diag = _coalesce_message_text(resp)
        action = _parse_response(text)
        assert action is not None, "empty-content fallback must still parse"
        assert action.kind.value == "warp"
        assert action.args.get("target") == 5


# ---------------------------------------------------------------------------
# M4-12 — observation: warps_count + coverage hint
# ---------------------------------------------------------------------------


def _mini_universe(seed: int = 17, size: int = 200) -> Any:
    from tw2k.engine import GameConfig, generate_universe
    from tw2k.engine.models import Player, Ship

    cfg = GameConfig(seed=seed, universe_size=size, max_days=3)
    u = generate_universe(cfg)
    p = Player(id="P1", name="TestPilot", ship=Ship())
    u.players["P1"] = p
    u.sectors[1].occupant_ids.append("P1")
    p.known_sectors.add(1)
    p.known_warps[1] = list(u.sectors[1].warps)
    return u


class TestM412ObservationCoverage:
    def test_sector_exposes_warps_count_as_first_class_field(self):
        from tw2k.engine.observation import build_observation

        u = _mini_universe()
        obs = build_observation(u, "P1")
        assert "warps_count" in obs.sector, (
            "observation.sector must surface `warps_count` so reasoning "
            "models see the total out-warps, not just their known subset"
        )
        assert obs.sector["warps_count"] == len(obs.sector["warps_out"])

    def test_warps_count_never_less_than_known_warps_for_current_sector(self):
        """known_warps[current_sector] is populated from sector.warps on
        entry, so count must equal the known-warps list length for the
        current sector.
        """
        from tw2k.engine.observation import build_observation

        u = _mini_universe()
        obs = build_observation(u, "P1")
        sid_str = str(u.players["P1"].sector_id)
        assert obs.sector["warps_count"] >= len(obs.known_warps.get(sid_str, []))

    def test_low_coverage_nudges_map_hint(self):
        """When the agent knows only a tiny slice of the universe, the
        action_hint must include a MAP COVERAGE nudge so reasoning models
        stop assuming they've seen the whole galaxy.
        """
        from tw2k.engine.observation import build_observation

        u = _mini_universe(size=1000)  # big universe, known_warps has 1 entry
        obs = build_observation(u, "P1")
        # Threshold in _action_hint is known < max(8, total // 50) == max(8, 20) == 20.
        # We only know sector 1, so coverage is 1/1000 — must trigger.
        assert "MAP COVERAGE" in obs.action_hint, (
            f"low-coverage hint missing from action_hint:\n{obs.action_hint}"
        )

    def test_dead_end_pocket_detection(self):
        """Put the player in an artificial 2-sector pocket and verify the
        action_hint flags it — preventing false 'trapped, send rescue'
        broadcasts like Match 4 P2.
        """
        from tw2k.engine.observation import build_observation

        u = _mini_universe(size=30)
        # Build a true pocket: sector 2 <-> sector 3 only. Strip any other
        # warp they happened to have in the generated universe, and put P1
        # in sector 2.
        s2 = u.sectors[2]
        s3 = u.sectors[3]
        s2.warps = [3]
        s3.warps = [2]
        u.players["P1"].sector_id = 2
        u.players["P1"].known_warps[2] = [3]
        u.players["P1"].known_warps[3] = [2]
        u.players["P1"].known_sectors.update({2, 3})
        # Remove P1 from its old sector occupant list and add to new one.
        if "P1" in u.sectors[1].occupant_ids:
            u.sectors[1].occupant_ids.remove("P1")
        u.sectors[2].occupant_ids.append("P1")

        obs = build_observation(u, "P1")
        assert "DEAD-END POCKET" in obs.action_hint, (
            f"dead-end pocket hint missing:\n{obs.action_hint}"
        )
        assert "Citadel L4" in obs.action_hint, (
            "dead-end hint must name Citadel L4 transwarp as the exit"
        )
