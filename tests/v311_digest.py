"""R-4 v3.11 pins: digest of a scripted match played on the stored defaults (V311_PROFILE "v311").

The legacy digest pins guarded "an all-legacy run stays what it was" until Phase 2 removed
legacy paths. These guard the game players now get: removing a legacy code path must leave every digest here
byte-identical, because a v3.11 game never ran that path.

Hashes the system prompt, every observation JSON and its prompt text, every action + result,
the end-of-day universe state after each day, the match result, and every event.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path


def v311_run_digest(root: Path, seats: str = "N3,N2,N1,H", days: int = 3, seed: int = 250925) -> str:
    import tw2k.engine as E
    import tw2k.engine.constants as K
    from tw2k.agents import prompts as P

    saved = K.V311_PROFILE
    K.V311_PROFILE = "v311"
    try:
        spec = importlib.util.spec_from_file_location("rsm_v311", root / "scripts" / "run_scripted_match.py")
        rsm = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(rsm)
        h = hashlib.sha256()
        h.update(P.get_system_prompt().encode())
        holder = {}
        gen0, bo0, aa0, td0 = E.generate_universe, E.build_observation, E.apply_action, E.tick_day

        def gen(cfg):
            holder["u"] = gen0(cfg)
            return holder["u"]

        def bo(u, pid, *a, **k):
            o = bo0(u, pid, *a, **k)
            h.update(o.model_dump_json().encode())
            h.update(P.format_observation(o).encode())
            return o

        def aa(u, pid, act):
            r = aa0(u, pid, act)
            h.update((act.model_dump_json() + r.model_dump_json()).encode())
            return r

        def td(u, *a, **k):
            out = td0(u, *a, **k)
            h.update(_state(u).encode())
            return out

        E.generate_universe, E.build_observation, E.apply_action, E.tick_day = gen, bo, aa, td
        try:
            res = rsm.run_match(rsm.parse_seats(seats), seed=seed, days=days)
        finally:
            E.generate_universe, E.build_observation, E.apply_action, E.tick_day = gen0, bo0, aa0, td0
        h.update(json.dumps(res, sort_keys=True, default=str).encode())
        for ev in holder["u"].events:
            h.update(ev.model_dump_json().encode())
        h.update(_state(holder["u"]).encode())
        return h.hexdigest()[:24]
    finally:
        K.V311_PROFILE = saved


# Wall-clock fields: INACTIVITY_TIMEOUT_MODE stamps each action with time.time().
WALL_CLOCK_PLAYER_KEYS = ("last_action_at",)


def _state(u) -> str:
    dump = json.loads(u.model_dump_json())
    for p in dump.get("players", {}).values():
        for k in WALL_CLOCK_PLAYER_KEYS:
            p.pop(k, None)
    return json.dumps(_round_floats(dump), sort_keys=True)


def _round_floats(obj):
    """Map layout coordinates come from libm trig; the last digit differs between Linux and Windows."""
    if isinstance(obj, float):
        return round(obj, 6)
    if isinstance(obj, dict):
        return {k: _round_floats(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_round_floats(v) for v in obj]
    return obj
