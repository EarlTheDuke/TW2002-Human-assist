"""Validate web/media/manifest.json paths exist (or list missing for generation)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MEDIA = ROOT / "web" / "media"
MANIFEST = MEDIA / "manifest.json"


def main() -> int:
    data = json.loads(MANIFEST.read_text(encoding="utf-8-sig"))
    paths: set[str] = set()
    for block in (data.get("groups") or {}).values():
        for key in ("still", "clip"):
            if block.get(key):
                paths.add(block[key])
    for block in (data.get("kinds") or {}).values():
        for key in ("still", "clip"):
            if block.get(key):
                paths.add(block[key])
    missing = sorted(p for p in paths if not (MEDIA / p).is_file())
    present = sorted(p for p in paths if (MEDIA / p).is_file())
    print(f"manifest assets: {len(paths)} unique")
    print(f"present: {len(present)}")
    print(f"missing: {len(missing)}")
    for p in missing:
        print(f"  MISSING  {p}")
    for p in present:
        print(f"  ok       {p}")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
