"""Pre-generate bearer tokens for external (Grok Bot) seats.

Writes/updates the gitignored tokens file (default `.tw2k/external_tokens.json`,
override with TW2K_EXTERNAL_TOKENS_FILE or --file). Existing seats keep their
token unless --rotate is given. Full secrets are never printed; use --show
to emit `TW2K_HARNESS_TOKEN=...` lines for copy/paste into a bot's env, or
read the file directly.

Usage:
  python scripts/gen_external_tokens.py                  # P3..P6, masked summary
  python scripts/gen_external_tokens.py --seats P2,P3    # custom seat list
  python scripts/gen_external_tokens.py --rotate         # new tokens for listed seats
  python scripts/gen_external_tokens.py --show           # print unmasked env lines (careful)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from tw2k.server import harness_tokens as ht  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seats", default="P3,P4,P5,P6", help="comma-separated player ids")
    ap.add_argument("--file", default=None, help="tokens file path (default .tw2k/external_tokens.json)")
    ap.add_argument("--rotate", action="store_true", help="replace existing tokens for the listed seats")
    ap.add_argument("--show", action="store_true", help="print full tokens as TW2K_HARNESS_TOKEN lines")
    args = ap.parse_args()

    seats = [s.strip().upper() for s in args.seats.split(",") if s.strip()]
    bad = [s for s in seats if not (s.startswith("P") and s[1:].isdigit())]
    if bad:
        print(f"bad seat ids: {bad}", file=sys.stderr)
        return 2

    path = ht.tokens_file_path(args.file)
    on_disk = ht.load_tokens_file(path)
    changed = False
    for pid in seats:
        if args.rotate or not on_disk.get(pid):
            on_disk[pid] = ht.generate_token()
            changed = True
    if changed:
        ht.save_tokens_file(path, on_disk)

    print(f"tokens file: {path}  ({'updated' if changed else 'unchanged'})")
    for pid in seats:
        print(f"  {pid}: {ht.mask(on_disk[pid])}")
    if args.show:
        print("\n# per-seat env (do not commit):")
        for pid in seats:
            print(f"# {pid}\nTW2K_HARNESS_PLAYER={pid}\nTW2K_HARNESS_TOKEN={on_disk[pid]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
