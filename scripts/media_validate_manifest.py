"""Validate a media manifest (v1 stills HUD or v2 viewport) - video cockpit V0.

    python scripts/media_validate_manifest.py                                  # web/media/manifest.json
    python scripts/media_validate_manifest.py --manifest web/media/examples/manifest.v2.example.json
    python scripts/media_validate_manifest.py --probe                          # also ffprobe clip durations

Checks: JSON Schema (web/media/manifest.schema.json; needs `jsonschema`, in the
dev extra), every referenced file exists, trigger rules use only the named
predicates, triggers point at existing clip keys and real EventKinds, triggers
on public-only kinds are local to the seat (no first-person clip for events
far away), declared `bytes` match the files and stay inside the size budget,
and (with --probe) declared durations match. Exit 1 on any problem.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MEDIA = ROOT / "web" / "media"
MANIFEST = MEDIA / "manifest.json"
SCHEMA = MEDIA / "manifest.schema.json"
sys.path.insert(0, str(ROOT / "src"))

# Named predicates the V2 resolver implements (phase plan section 4.1 / 4.2). No eval.
PREDICATES = frozenset({
    "self", "self_attacker", "self_defender", "self_victim", "first_in_visit", "outcome_hit", "witnessed_in_my_sector",
})
# A trigger on a public-only kind must require one of these (the event happened at the seat's own ship).
LOCAL_PREDICATES = frozenset({"self", "self_attacker", "self_defender", "self_victim", "witnessed_in_my_sector"})
RULE_RE = re.compile(r"^!?[a-z_]+( && !?[a-z_]+)*$")
EVENT_CLIP_MAX_BYTES = 600_000   # hard cap per event clip file (budget section 6)
AMBIENT_MAX_BYTES = 900_000
EVENT_CLIP_MAX_MS = 5_000


def _event_kinds() -> tuple[set[str], set[str]]:
    from tw2k.engine.models import EventKind
    from tw2k.engine.observation import _PUBLIC_EVENTS

    return {k.value for k in EventKind}, {k.value for k in _PUBLIC_EVENTS}


def _media_paths(data: dict[str, Any]) -> list[tuple[str, str, dict | None, str]]:
    """(where, path, owning variant or None, role) for every file the manifest references."""
    out: list[tuple[str, str, dict | None, str]] = []
    for block_name in ("groups", "kinds"):
        for key, entry in (data.get(block_name) or {}).items():
            for role in ("still", "clip"):
                if entry.get(role):
                    out.append((f"{block_name}.{key}.{role}", entry[role], None, "v1"))
    for key, amb in (data.get("ambient") or {}).items():
        for v in amb.get("variants") or []:
            for role in ("webm", "mp4", "poster"):
                if v.get(role):
                    out.append((f"ambient.{key}.{v.get('id')}.{role}", v[role], v, "ambient"))
    for key, clip in (data.get("clips") or {}).items():
        if clip.get("fallback_still"):
            out.append((f"clips.{key}.fallback_still", clip["fallback_still"], None, "still"))
        for v in clip.get("variants") or []:
            for role in ("webm", "mp4", "poster"):
                if v.get(role):
                    out.append((f"clips.{key}.{v.get('id')}.{role}", v[role], v, "clip"))
    return out


def _probe_ms(path: Path) -> int | None:
    exe = shutil.which("ffprobe")
    if not exe:
        return None
    r = subprocess.run([exe, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                       capture_output=True, text=True, timeout=30, check=False)
    try:
        return round(float(r.stdout.strip()) * 1000)
    except ValueError:
        return None


def validate(data: dict[str, Any], media_root: Path = MEDIA, *, probe: bool = False) -> tuple[list[str], dict[str, Any]]:
    """Return (errors, report). `report` lists present/missing assets for the CLI."""
    errors: list[str] = []
    try:
        import jsonschema

        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        for err in sorted(jsonschema.Draft202012Validator(schema).iter_errors(data), key=lambda e: list(e.path)):
            where = "/".join(str(p) for p in err.path) or "(root)"
            errors.append(f"schema: {where}: {err.message}")
    except ImportError:
        errors.append("schema: jsonschema is not installed (pip install 'tw2k-ai[dev]')")

    kinds, public = _event_kinds()
    clips = data.get("clips") or {}
    for i, t in enumerate(data.get("triggers") or []):
        where = f"triggers[{i}] ({t.get('kind')} -> {t.get('clip')})"
        rule = str(t.get("rule") or "")
        if not RULE_RE.match(rule):
            errors.append(f"{where}: rule {rule!r} is not 'pred && !pred ...'")
            names: list[str] = []
        else:
            names = [p.lstrip("!") for p in rule.split(" && ")]
        unknown = sorted(set(names) - PREDICATES)
        if unknown:
            errors.append(f"{where}: unknown predicate(s) {unknown}; known: {sorted(PREDICATES)}")
        if t.get("kind") not in kinds:
            errors.append(f"{where}: {t.get('kind')!r} is not an EventKind")
        if t.get("coalesce") and t["coalesce"] not in kinds:
            errors.append(f"{where}: coalesce {t['coalesce']!r} is not an EventKind")
        if t.get("clip") not in clips:
            errors.append(f"{where}: clip key {t.get('clip')!r} is not defined in clips")
        positive = {p for p in rule.split(" && ") if p and not p.startswith("!")}
        if t.get("kind") in public and not (positive & LOCAL_PREDICATES):
            errors.append(f"{where}: {t['kind']!r} is public (seen galaxy-wide); a first-person clip needs one of "
                          f"{sorted(LOCAL_PREDICATES)}")

    present, missing = [], []
    for where, rel, variant, role in _media_paths(data):
        f = media_root / rel
        if not f.is_file():
            missing.append(rel)
            errors.append(f"{where}: missing file {rel}")
            continue
        present.append(rel)
        if variant is None or role not in ("clip", "ambient") or not rel.endswith((".webm", ".mp4")):
            continue
        primary = variant.get("webm") or variant.get("mp4")
        size = f.stat().st_size
        if rel == primary and variant.get("bytes") is not None and variant["bytes"] != size:
            errors.append(f"{where}: bytes says {variant['bytes']} but the file is {size}")
        cap = AMBIENT_MAX_BYTES if role == "ambient" else EVENT_CLIP_MAX_BYTES
        if size > cap:
            errors.append(f"{where}: {size} bytes is over the {cap} budget")
        if probe and variant.get("duration_ms") is not None:
            ms = _probe_ms(f)
            if ms is not None and abs(ms - variant["duration_ms"]) > 150:
                errors.append(f"{where}: duration_ms {variant['duration_ms']} but ffprobe says {ms}")
            if role == "clip" and ms is not None and ms > EVENT_CLIP_MAX_MS:
                errors.append(f"{where}: {ms} ms is over the {EVENT_CLIP_MAX_MS} ms event clip cap")
    return errors, {"present": sorted(set(present)), "missing": sorted(set(missing))}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--manifest", default=str(MANIFEST))
    ap.add_argument("--media-root", default=None, help="directory paths are relative to (default: web/media)")
    ap.add_argument("--probe", action="store_true", help="check clip durations with ffprobe")
    args = ap.parse_args(argv)
    path = Path(args.manifest)
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    errors, report = validate(data, Path(args.media_root) if args.media_root else MEDIA, probe=args.probe)
    print(f"manifest: {path.name} (version {data.get('version')})")
    print(f"manifest assets: {len(report['present']) + len(report['missing'])} unique")
    print(f"present: {len(report['present'])}")
    print(f"missing: {len(report['missing'])}")
    for p in report["missing"]:
        print(f"  MISSING  {p}")
    for p in report["present"]:
        print(f"  ok       {p}")
    for e in errors:
        print(f"ERROR  {e}")
    print("OK" if not errors else f"{len(errors)} problem(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
