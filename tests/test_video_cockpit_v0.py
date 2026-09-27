"""Video cockpit V0 - spec lock: manifest v2 schema + validator, event fixtures, resolver table.

V2 points the live manifest at the placeholder v2 set. This file still checks the schema,
the validator, and that the recorded fixtures match the engine.
"""

from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import media_validate_manifest as mv  # noqa: E402

MEDIA = ROOT / "web" / "media"
V1 = json.loads((MEDIA / "manifest.json").read_text(encoding="utf-8-sig"))
V2 = json.loads((MEDIA / "examples" / "manifest.v2.example.json").read_text(encoding="utf-8"))
FIXTURES = ROOT / "tests" / "fixtures" / "media_events"
DOC = (ROOT / "docs" / "plans" / "2026-09-26-video-cockpit-v0-fixtures.md").read_text(encoding="utf-8")
REQUIRED = ("single_warp", "autopilot_burst", "trade_burst", "trade_failed", "self_attack_win", "self_attack_lose",
            "ferrengi_attack", "witnessed_combat", "far_port_destroyed")
jsonschema = pytest.importorskip("jsonschema")


def _errors(data: dict, root: Path = MEDIA) -> list[str]:
    return mv.validate(data, root)[0]


# ------------------------------------------------------------------ schema + validator
def test_schema_is_valid_2020_12() -> None:
    jsonschema.Draft202012Validator.check_schema(json.loads((MEDIA / "manifest.schema.json").read_text(encoding="utf-8")))


def test_live_v1_manifest_and_v2_example_validate() -> None:
    assert V1["version"] == 2 and "warp" in V1["kinds"] and "dock.port" in V1["clips"]
    assert _errors(V1) == []
    assert _errors(V2) == []


@pytest.mark.parametrize("mutate, needle", [
    (lambda m: m["triggers"][0].update(rule="self && outcome_bribe"), "unknown predicate"),
    (lambda m: m["triggers"][0].update(rule="self || first_in_visit"), "is not 'pred && !pred"),
    (lambda m: m["triggers"][0].update(clip="dock.stardock"), "not defined in clips"),
    (lambda m: m["triggers"][0].update(kind="teleport"), "is not an EventKind"),
    (lambda m: m["triggers"].append({"kind": "port_destroyed", "rule": "outcome_hit", "clip": "combat.hit"}), "is public"),
    (lambda m: m["clips"]["warp.out"]["variants"][0].update(poster="stills/nope.png"), "missing file stills/nope.png"),
    (lambda m: m["clips"]["warp.out"].update(fallback_still="stills/gone.png"), "missing file stills/gone.png"),
    (lambda m: m["clips"]["warp.out"]["variants"][0].update(duration_ms=9000), "schema"),
    (lambda m: m.pop("triggers"), "schema"),
])
def test_validator_rejects_bad_manifests(mutate, needle: str) -> None:
    bad = copy.deepcopy(V2)
    mutate(bad)
    errs = _errors(bad)
    assert any(needle in e for e in errs), errs


def test_public_kind_is_fine_when_local_and_v1_cannot_carry_v2_blocks() -> None:
    ok = copy.deepcopy(V2)
    ok["triggers"].append({"kind": "port_destroyed", "rule": "witnessed_in_my_sector", "clip": "combat.witnessed"})
    assert _errors(ok) == []
    v1_bad = {"version": 1, "defaults": {"duration_ms": 2400, "muted": True, "fit": "cover"},
              "kinds": {"warp": {"still": "stills/move_warp.png", "caption": "Warp"}}, "triggers": []}
    assert any(e.startswith("schema") for e in _errors(v1_bad))


def test_bytes_and_budget_checks(tmp_path: Path) -> None:
    (tmp_path / "clips").mkdir()
    (tmp_path / "stills").mkdir()
    (tmp_path / "stills" / "p.png").write_bytes(b"x")
    (tmp_path / "clips" / "warp_out_a.1234abcd.webm").write_bytes(b"\0" * 1000)
    (tmp_path / "clips" / "big.1234abcd.webm").write_bytes(b"\0" * 700_000)
    m = {"version": 2, "defaults": {"duration_ms": 2400, "muted": True},
         "clips": {"warp.out": {"priority": 2, "caption": "Warp", "variants": [
             {"id": "a", "webm": "clips/warp_out_a.1234abcd.webm", "bytes": 999},
             {"id": "b", "webm": "clips/big.1234abcd.webm", "poster": "stills/p.png"}]}},
         "triggers": [{"kind": "warp", "rule": "self", "clip": "warp.out"}]}
    errs = _errors(m, tmp_path)
    assert any("bytes says 999 but the file is 1000" in e for e in errs)
    assert any("over the 600000 budget" in e for e in errs)


def test_cli_exit_codes(tmp_path: Path) -> None:
    run = lambda *a: subprocess.run([sys.executable, str(ROOT / "scripts" / "media_validate_manifest.py"), *a],  # noqa: E731
                                    capture_output=True, text=True, timeout=60)
    assert run().returncode == 0
    assert run("--manifest", str(MEDIA / "examples" / "manifest.v2.example.json")).returncode == 0
    bad = copy.deepcopy(V2)
    bad["triggers"][0]["rule"] = "self && sneaky"
    p = tmp_path / "bad.json"
    p.write_text(json.dumps(bad), encoding="utf-8")
    r = run("--manifest", str(p))
    assert r.returncode == 1 and "unknown predicate" in r.stdout


# ------------------------------------------------------------------ fixtures + resolver table
def _fx(name: str) -> dict:
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


def test_fixtures_cover_every_required_scenario_with_real_event_rows() -> None:
    for name in REQUIRED + ("trade_same_visit", "other_trade_in_sector"):
        fx = _fx(name)
        assert fx["seed"] == 250925 and fx["viewer"] == "P1" and fx["batch"], name
        for row in fx["batch"]:
            assert {"seq", "day", "tick", "kind", "actor_id", "sector_id", "summary", "facts"} <= set(row), (name, row)
        for e in fx["expected"]:
            assert set(e) == {"clip_key", "priority"} and 0 <= e["priority"] <= 4
        assert f"`{name}`" in DOC, f"{name} missing from the resolver table"


def test_fixture_semantics_match_their_scenario() -> None:
    kinds = lambda fx: [r["kind"] for r in fx["batch"]]  # noqa: E731
    ap = _fx("autopilot_burst")
    assert kinds(ap).count("warp") >= 2 and "autopilot" in kinds(ap) and all(r["actor_id"] == "P1" for r in ap["batch"])
    tb = _fx("trade_burst")
    assert kinds(tb).count("trade") >= 2 and len({r["sector_id"] for r in tb["batch"]}) == 1
    assert kinds(_fx("trade_failed")) == ["trade_failed"]
    for name in ("self_attack_win", "self_attack_lose"):
        combat = next(r for r in _fx(name)["batch"] if r["kind"] == "combat")
        assert combat["facts"]["attacker"] == "P1" and combat["facts"]["exchange_kind"] == "ship_vs_ship"
    fe = _fx("ferrengi_attack")
    assert fe["batch"][0]["kind"] == "ferrengi_attack" and fe["batch"][0]["facts"]["victim"] == "P1"
    assert any(r["kind"] == "combat" and r["facts"].get("defender") == "P1" for r in fe["batch"])
    wc = _fx("witnessed_combat")
    combat = next(r for r in wc["batch"] if r["kind"] == "combat")
    assert combat["actor_id"] != "P1" and combat["sector_id"] == wc["obs"]["sector"]["id"]
    fp = _fx("far_port_destroyed")
    assert kinds(fp)[0] == "port_destroyed" and all(r["sector_id"] != fp["obs"]["sector"]["id"] for r in fp["batch"])
    ot = _fx("other_trade_in_sector")
    assert ot["batch"][0]["actor_id"] != "P1" and ot["batch"][0]["sector_id"] == ot["obs"]["sector"]["id"]
    # expected table in fixtures = the documented V2 outcomes
    assert [e["clip_key"] for e in _fx("autopilot_burst")["expected"]] == ["warp.out"]
    assert _fx("far_port_destroyed")["expected"] == [] and _fx("other_trade_in_sector")["expected"] == []
    assert _fx("ferrengi_attack")["expected"] == [{"clip_key": "combat.incoming", "priority": 0}]


def test_fixtures_are_reproducible_from_the_engine(tmp_path: Path) -> None:
    subprocess.run([sys.executable, str(ROOT / "scripts" / "media_record_fixtures.py"), "--out", str(tmp_path)],
                   check=True, capture_output=True, timeout=120)
    for f in FIXTURES.glob("*.json"):
        assert json.loads((tmp_path / f.name).read_text(encoding="utf-8")) == json.loads(f.read_text(encoding="utf-8")), f.name


def test_expected_clip_keys_exist_in_the_v2_example() -> None:
    for f in FIXTURES.glob("*.json"):
        for e in json.loads(f.read_text(encoding="utf-8"))["expected"]:
            assert e["clip_key"] in V2["clips"] and V2["clips"][e["clip_key"]]["priority"] == e["priority"], (f.name, e)


def test_victim_sees_its_own_ship_destroyed() -> None:
    for name in ("self_attack_lose", "ferrengi_attack"):
        fx = _fx(name)
        assert fx["obs"]["sector"]["id"] == 1, "viewer was destroyed and ejected to StarDock"
        assert any(r["kind"] == "ship_destroyed" and r["facts"].get("victim") == "P1" for r in fx["batch"]), name
