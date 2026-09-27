"""Write (or refresh) per-seat claim links in .tw2k/seat_links/<SEAT>.txt (grokbot-player G3).

`tw2k serve` writes them at match start. Quick-tunnel URLs change, so run
this after (re-)exposing the host to point the links at the new base:

    python scripts/write_seat_links.py                       # base from TW2K_PUBLIC_BASE_URL / .tw2k/public_base_url.txt
    python scripts/write_seat_links.py --base https://x.lhr.life --seats P3,P6

Prints paths and masked tokens only; the links themselves stay in the
gitignored files.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tw2k.server import harness_tokens as ht
from tw2k.server import seat_links


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--base", default=None, help="public base URL (default: seat_links.base_url() chain)")
    ap.add_argument("--seats", default="", help="comma-separated seats (default: every seat in the tokens file)")
    ap.add_argument("--tokens-file", default=None, help="tokens JSON (default .tw2k/external_tokens.json)")
    ap.add_argument("--dir", default=None, help="output directory (default .tw2k/seat_links)")
    args = ap.parse_args(argv)

    on_disk = ht.load_tokens_file(ht.tokens_file_path(args.tokens_file))
    wanted = [s.strip().upper() for s in args.seats.split(",") if s.strip()] or sorted(on_disk)
    tokens = {s: on_disk[s] for s in wanted if s in on_disk}
    missing = [s for s in wanted if s not in on_disk]
    if not tokens:
        print("no seat tokens found (run scripts/gen_external_tokens.py first)", file=sys.stderr)
        return 1
    base = args.base or seat_links.base_url()
    written = seat_links.write_seat_links(tokens, base=base, directory=args.dir)
    print(f"base {base}")
    for seat, path in written.items():
        print(f"  {seat} token {ht.mask(tokens[seat])} -> {path}")
    if missing:
        print(f"  no token for: {', '.join(missing)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
