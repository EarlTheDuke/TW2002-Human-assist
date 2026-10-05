"""QC legacy golden for fedspace-police-v1: digest of a short scripted FED_MODE legacy run.

Hashes every observation JSON, prompt text, action + result, event and end-of-day universe state.
Runs on the pre-slice commit (no FED_MODE) and on later commits (FED_MODE forced to legacy).
"""

import hashlib
import importlib.util
import json
from pathlib import Path

NEW_UNIVERSE_KEYS = ("federals", "posted_rewards", "pending_rewards")
NEW_PLAYER_KEYS = ("commission_used", "fed_hail_sent")


def legacy_run_digest(root: Path, seats: str = "N3,H", days: int = 2, seed: int = 250925) -> str:
    import tw2k.engine as E
    import tw2k.engine.constants as K
    from tw2k.agents import prompts as P

    # Every tw2002 switch to legacy (FED_MODE included when present): later slices may retune tw2002
    # play, but an all-legacy run must stay what it was before this slice.
    for name in dir(K):
        if name.endswith("_MODE") and getattr(K, name) == "tw2002":
            setattr(K, name, "legacy")
    spec = importlib.util.spec_from_file_location("rsm_qc", root / "scripts" / "run_scripted_match.py")
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

    def td(u):
        td0(u)
        h.update(_state(u).encode())

    E.generate_universe, E.build_observation, E.apply_action, E.tick_day = gen, bo, aa, td
    try:
        res = rsm.run_match(rsm.parse_seats(seats), seed=seed, days=days)
    finally:
        E.generate_universe, E.build_observation, E.apply_action, E.tick_day = gen0, bo0, aa0, td0
    h.update(json.dumps(res, sort_keys=True).encode())
    for ev in holder["u"].events:
        h.update(ev.model_dump_json().encode())
    h.update(_state(holder["u"]).encode())
    return h.hexdigest()[:24]


def _state(u) -> str:
    dump = json.loads(u.model_dump_json())
    for k in NEW_UNIVERSE_KEYS:
        dump.pop(k, None)
    for p in dump.get("players", {}).values():
        for k in NEW_PLAYER_KEYS:
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
