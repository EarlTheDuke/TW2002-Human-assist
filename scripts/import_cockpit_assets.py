"""Copy cockpit pictures the Commander dropped into the reference folder.

The game already names every scene in web/media/manifest.json. Dropped files
are copied under those names. A missing folder is fine: the keys stay, and a
missing picture falls back to the next key, then to a drawn scene.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MEDIA = ROOT / "web" / "media"
MANIFEST = MEDIA / "manifest.json"
DEFAULT_SOURCE = Path(r"C:\Users\sugar\tw2002_reference\cockpit_assets")
STILL_MAX_BYTES = 300_000
# A dropped picture sometimes uses a longer name than the key the cockpit already has.
ALIASES = {
    "genesis_launch": "genesis",
    "planet_citadel_built": "citadel_built",
}


def _to_webp(source: Path, target: Path) -> None:
    """Write a still under 300 KB. The cockpit serves webp, not the camera original."""
    from PIL import Image

    target.parent.mkdir(parents=True, exist_ok=True)
    image = Image.open(source).convert("RGB")
    for quality in (75, 60, 45, 30, 20):
        image.save(target, "WEBP", quality=quality, method=6)
        if target.stat().st_size <= STILL_MAX_BYTES:
            return
    raise RuntimeError(f"{target.name} is still over {STILL_MAX_BYTES} bytes")


def _remember(keys: dict, name: str, file_rel: str) -> None:
    current = keys.get(name) or {}
    keys[name] = {"file": file_rel, "fallback": current.get("fallback") or "canvas"}


def import_assets(source: Path, media: Path = MEDIA, manifest_path: Path = MANIFEST) -> list[str]:
    copied: list[str] = []
    if not source.is_dir():
        return copied
    for folder in ("stills", "clips"):
        src = source / folder
        if not src.is_dir():
            continue
        dest = media / folder
        dest.mkdir(parents=True, exist_ok=True)
        for path in src.rglob("*"):
            if not path.is_file():
                continue
            rel = Path(folder) / path.relative_to(src)
            if path.suffix.lower() in {".jpg", ".jpeg"}:
                rel = rel.with_suffix(".webp")
                _to_webp(path, media / rel)
            else:
                target = media / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, target)
            copied.append(str(rel).replace("\\", "/"))
    additions = source / "manifest_additions.json"
    if additions.is_file() and manifest_path.is_file():
        extra = json.loads(additions.read_text(encoding="utf-8-sig"))
        data = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
        keys = data.setdefault("keys", {})
        for name, entry in (extra.get("keys") or {}).items():
            keys[name] = entry
        for name, entry in (extra.get("contexts") or {}).items():
            still = str(entry.get("still") or "")
            file_rel = str(Path(still).with_suffix(".webp")).replace("\\", "/") if still.lower().endswith((".jpg", ".jpeg")) else still
            if not file_rel or not (media / file_rel).is_file():
                continue
            _remember(keys, name, file_rel)
            alias = ALIASES.get(name)
            if alias:
                _remember(keys, alias, file_rel)
        manifest_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return copied


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--source", default=str(DEFAULT_SOURCE))
    args = ap.parse_args(argv)
    source = Path(args.source)
    if not source.is_dir():
        print(f"no dropped assets at {source}")
        return 0
    copied = import_assets(source)
    print(f"copied {len(copied)} file(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
