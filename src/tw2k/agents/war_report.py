"""Count war verbs a match already took. No decisions, no engine calls."""

from __future__ import annotations

from typing import Any


def _kind(ev: Any) -> str:
    if isinstance(ev, dict):
        return str(ev.get("kind") or "")
    kind = getattr(ev, "kind", "")
    return str(getattr(kind, "value", kind))


def _payload(ev: Any) -> dict[str, Any]:
    raw = ev.get("payload") if isinstance(ev, dict) else getattr(ev, "payload", None)
    return raw if isinstance(raw, dict) else {}


def _actor(ev: Any) -> str:
    if isinstance(ev, dict):
        return str(ev.get("actor") or ev.get("actor_id") or "")
    return str(getattr(ev, "actor_id", "") or "")


def counts_from_events(events: list[Any]) -> dict[str, dict[str, int]]:
    """Per seat. Quantities are summed. A missing actor is skipped."""
    out: dict[str, dict[str, int]] = {}

    def bump(actor: str, key: str, qty: int = 1) -> None:
        row = out.setdefault(actor, {})
        row[key] = int(row.get(key) or 0) + int(qty)

    for ev in events:
        actor = _actor(ev)
        if not actor:
            continue
        kind = _kind(ev)
        payload = _payload(ev)
        qty = int(payload.get("qty") or 1)
        if kind == "deploy_mines":
            mine = str(payload.get("kind") or "armid")
            who = "corporate" if payload.get("ownership") == "corporate" else "personal"
            bump(actor, f"mines_{mine}_{who}", qty)
        elif kind == "deploy_fighters":
            mode = str(payload.get("mode") or "defensive")
            who = "corporate" if payload.get("ownership") == "corporate" else "personal"
            bump(actor, f"fighters_{mode}_{who}", qty)
        elif kind == "deposit_planet_defense":
            bump(actor, f"deposit_{payload.get('kind') or 'fighters'}", qty)
        elif kind == "set_military_reaction":
            bump(actor, "reaction")
        elif kind == "set_quasar_sector":
            bump(actor, "quasar_sector")
        elif kind == "set_quasar_atm":
            bump(actor, "quasar_atm")
        elif kind in ("land_planet", "scan", "launch_probe", "ship_destroyed"):
            bump(actor, kind)
    return out
