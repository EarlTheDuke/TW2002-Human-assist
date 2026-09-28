"""Stand-in clips, manifest wiring, swap, and approve/unapprove.

The live manifest lists a ffmpeg stand-in first (approved_by null) and any real
takes after it. The player plays the first approved take, otherwise the stand-in.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MEDIA = ROOT / "web" / "media"
MANIFEST = MEDIA / "manifest.json"
CATALOG = MEDIA / "clips" / "v3-pilot" / "clips_manifest_v3.json"
PLACEHOLDER = "clips/placeholder"
STANDIN_TOOL = "placeholder-ffmpeg-from-still"
BAKED_FRAME_IDS = frozenset({"dock_port_std_b", "dock_port_std_c", "warp_out_c"})
_TS = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}")
_HASH = re.compile(r"\.([a-f0-9]{8})\.(?:webm|mp4|webp)$")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def save_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _media_paths(variant: dict[str, Any]) -> list[str]:
    return [str(variant.get(role) or "") for role in ("webm", "mp4", "poster")]


def is_standin(variant: dict[str, Any]) -> bool:
    """Ffmpeg stand-ins, files under clips/placeholder/, and old poster-only placeholders."""
    vid = str(variant.get("id") or "")
    tool = str((variant.get("provenance") or {}).get("tool") or "")
    paths = " ".join(_media_paths(variant))
    return (vid.startswith("ph_") or "placeholder" in vid or tool == STANDIN_TOOL or "clips/placeholder/" in paths)


def is_real_take(variant: dict[str, Any]) -> bool:
    """A generated pilot take: a clips/v3-pilot file plus real provenance. Nothing else can be approved."""
    if is_standin(variant):
        return False
    prov = variant.get("provenance")
    tool = str((prov or {}).get("tool") or "") if isinstance(prov, dict) else ""
    if not tool:
        return False
    return any(path.startswith("clips/v3-pilot/") for path in _media_paths(variant))


def still_for(variant_id: str) -> str:
    if variant_id.startswith(("amb_deep", "warp_out")):
        return "stills/move_warp.png"
    if variant_id.startswith(("amb_port", "dock_port")):
        return "stills/trade_port.png"
    if variant_id.startswith("combat_hit"):
        return "stills/combat_photon.png"
    return "stills/combat_alert.png"


def _entry(manifest: dict[str, Any], key: str) -> dict[str, Any]:
    if key.startswith("ambient."):
        name = key.split(".", 1)[1]
        return manifest.setdefault("ambient", {}).setdefault(name, {"variants": []})
    clip = manifest.setdefault("clips", {}).get(key)
    if clip is None:
        raise SystemExit(f"no clip {key} in the manifest")
    return clip


def _run(cmd: list[str]) -> None:
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120, check=False)
    if r.returncode != 0:
        tail = (r.stderr or r.stdout or "")[-400:]
        raise RuntimeError(f"ffmpeg failed ({r.returncode}): {tail}")


def render_standin(media: Path, variant_id: str) -> dict[str, str]:
    """Write a 2s silent pan of an existing still. Skip when the files are already there."""
    sid = f"ph_{variant_id}"
    rel = {
        "webm": f"{PLACEHOLDER}/{sid}.webm",
        "mp4": f"{PLACEHOLDER}/{sid}.mp4",
        "poster": f"{PLACEHOLDER}/{sid}.webp",
    }
    paths = {role: media / rel[role] for role in rel}
    if all(p.is_file() and p.stat().st_size > 500 for p in paths.values()):
        return rel
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg is not on PATH")
    still = media / still_for(variant_id)
    paths["webm"].parent.mkdir(parents=True, exist_ok=True)
    vf = "scale=640:360:force_original_aspect_ratio=increase,crop=480:270:(in_w-out_w)*t/2:(in_h-out_h)*t/2,fps=12"
    _run(["ffmpeg", "-y", "-loop", "1", "-i", str(still), "-t", "2", "-an", "-vf", vf,
          "-c:v", "libvpx-vp9", "-pix_fmt", "yuv420p", "-crf", "45", "-b:v", "0",
          "-deadline", "realtime", "-cpu-used", "8", str(paths["webm"])])
    _run(["ffmpeg", "-y", "-loop", "1", "-i", str(still), "-t", "2", "-an", "-vf", vf,
          "-c:v", "libx264", "-crf", "36", "-preset", "veryfast", "-pix_fmt", "yuv420p",
          "-movflags", "+faststart", str(paths["mp4"])])
    _run(["ffmpeg", "-y", "-i", str(paths["webm"]), "-frames:v", "1",
          "-c:v", "libwebp", "-quality", "50", str(paths["poster"])])
    return rel


def _standin_variant(variant_id: str, rel: dict[str, str], media: Path, *, ambient: bool) -> dict[str, Any]:
    sid = f"ph_{variant_id}"
    row: dict[str, Any] = {
        "id": sid,
        "webm": rel["webm"],
        "mp4": rel["mp4"],
        "poster": rel["poster"],
        "duration_ms": 2000,
        "bytes": (media / rel["webm"]).stat().st_size,
        "provenance": {"tool": STANDIN_TOOL, "shot_id": sid, "take": 1, "approved_by": None},
    }
    if ambient:
        row["loop"] = True
    return row


def _real_variant(row: dict[str, Any], media: Path) -> dict[str, Any]:
    base = "clips/v3-pilot"
    webm = f"{base}/{row['webm']}"
    who = row.get("approved_by")
    found = _TS.search(who) if isinstance(who, str) else None
    hashed = _HASH.search(row["webm"])
    provenance: dict[str, Any] = {
        "tool": (row.get("provenance") or {}).get("service") or "xai grok-imagine-video",
        "shot_id": row["variant"],
        "take": int(row.get("take") or 1),
        "approved_by": who if isinstance(who, str) and who.strip() else None,
    }
    model = (row.get("provenance") or {}).get("model")
    if model:
        provenance["model"] = model
    if found:
        provenance["approved_at"] = found.group(0)
    if hashed:
        provenance["hash"] = hashed.group(1)
    out: dict[str, Any] = {
        "id": row["variant"],
        "webm": webm,
        "mp4": f"{base}/{row['mp4']}",
        "poster": f"{base}/{row['poster']}",
        "duration_ms": round(float(row["duration_s"]) * 1000),
        "bytes": (media / webm).stat().st_size,
        "provenance": provenance,
    }
    if row.get("loop"):
        out["loop"] = True
    if row["variant"] in BAKED_FRAME_IDS:
        out["baked_frame"] = True
    review = row.get("review") or {}
    kept = {k: review[k] for k in ("reviewer", "result", "notes") if review.get(k)}
    if kept:
        out["review"] = kept
    return out


def wire_pilot(manifest: dict[str, Any], rows: list[dict[str, Any]], media: Path = MEDIA) -> None:
    """Put a stand-in first and the catalog takes after it. Leaves every other clip alone."""
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(row["key"], []).append(row)
    for key, group in grouped.items():
        ambient = key.startswith("ambient.")
        standins, reals = [], []
        for row in group:
            rel = render_standin(media, row["variant"])
            standins.append(_standin_variant(row["variant"], rel, media, ambient=ambient))
            reals.append(_real_variant(row, media))
        _entry(manifest, key)["variants"] = standins + reals


def _refuse(variant: dict[str, Any]) -> None:
    vid = variant.get("id") or "?"
    raise SystemExit(
        f"refusing {vid}: only clips/v3-pilot takes with provenance can be approved; "
        "stand-ins, placeholders, and takes with no provenance stay unapproved"
    )


def find_variant(entry: dict[str, Any], spec: str) -> dict[str, Any]:
    variants = entry.get("variants") or []
    if spec.isdigit():
        reals = [v for v in variants if is_real_take(v)]
        idx = int(spec) - 1
        if idx < 0 or idx >= len(reals):
            raise SystemExit(f"variant {spec} is out of range ({len(reals)} real takes)")
        return reals[idx]
    for variant in variants:
        if variant.get("id") == spec:
            if not is_real_take(variant):
                _refuse(variant)
            return variant
    raise SystemExit(f"no variant {spec}")


def set_approval(variant: dict[str, Any], by: str | None, when: str | None = None) -> None:
    provenance = variant.setdefault("provenance", {})
    if by:
        provenance["approved_by"] = by
        provenance["approved_at"] = when or datetime.now().astimezone().isoformat(timespec="seconds")
    else:
        provenance["approved_by"] = None
        provenance["approved_at"] = None


def iter_variants(manifest: dict[str, Any]):
    for amb in (manifest.get("ambient") or {}).values():
        yield from amb.get("variants") or []
    for clip in (manifest.get("clips") or {}).values():
        yield from clip.get("variants") or []


def sync_catalog_approvals(catalog: dict[str, Any], manifest: dict[str, Any]) -> int:
    """Copy each real take's approved_by onto clips_manifest_v3.json.

    ``--wire-pilot`` rebuilds the manifest from that catalog, so the catalog has to
    move with every approve or clear. Otherwise a rewire would put the old approval back.
    """
    by_id = {v["id"]: (v.get("provenance") or {}).get("approved_by") for v in iter_variants(manifest) if is_real_take(v)}
    n = 0
    for row in catalog.get("clips") or []:
        vid = row.get("variant")
        if vid in by_id and row.get("approved_by") != by_id[vid]:
            row["approved_by"] = by_id[vid]
            n += 1
    return n


def approve_pending(manifest: dict[str, Any], by: str, *, clear: bool = False) -> int:
    """Approve (or unapprove) every real pilot take. Stand-ins and placeholders are skipped."""
    n = 0
    for variant in iter_variants(manifest):
        if not is_real_take(variant):
            continue
        who = (variant.get("provenance") or {}).get("approved_by")
        if clear:
            if isinstance(who, str) and who.strip():
                set_approval(variant, None)
                n += 1
        elif not (isinstance(who, str) and who.strip()):
            set_approval(variant, by)
            n += 1
    return n


def _place(src: Path, media_root: Path, dest_dir: Path, name: str) -> str:
    src = src.resolve()
    try:
        rel = src.relative_to(media_root.resolve()).as_posix()
        if (media_root / rel).is_file():
            return rel
    except ValueError:
        pass
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / name
    shutil.copyfile(src, dest)
    return dest.relative_to(media_root).as_posix()


def swap_variant(manifest: dict[str, Any], key: str, variant_id: str, *,
                 webm: Path | None = None, mp4: Path | None = None, poster: Path | None = None,
                 media_root: Path = MEDIA) -> dict[str, Any]:
    """Point a variant at new files. Adds the variant when the id is new. No player code changes."""
    entry = _entry(manifest, key)
    variant = next((v for v in entry.get("variants") or [] if v.get("id") == variant_id), None)
    if variant is None:
        variant = {"id": variant_id, "duration_ms": 2000, "provenance": {"approved_by": None}}
        entry.setdefault("variants", []).append(variant)
    dest_dir = media_root / "clips" / "swapped"
    ext = {"webm": "webm", "mp4": "mp4", "poster": "webp"}
    for role, src in (("webm", webm), ("mp4", mp4), ("poster", poster)):
        if src is None:
            continue
        variant[role] = _place(Path(src), media_root, dest_dir, f"{variant_id}.{ext[role]}")
    primary = variant.get("webm") or variant.get("mp4")
    if primary and (media_root / primary).is_file():
        variant["bytes"] = (media_root / primary).stat().st_size
    return variant
