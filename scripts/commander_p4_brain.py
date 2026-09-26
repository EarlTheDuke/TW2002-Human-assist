#!/usr/bin/env python3
"""Commander P4 brain = the S3 SeatBrain on seat P4 (mailbox mode).

Thin wrapper kept so existing runbooks (`python scripts/commander_p4_brain.py`)
keep working. The old hand-patched ladder lives on only as a local reference
copy (scripts/commander_p4_brain_legacy.py, not committed).

  python scripts/grokbot_seat_client.py --seat P4 --policy mailbox   # harness <-> mailbox files
  python scripts/commander_p4_brain.py [--log-dir docs/playtests/<match>]
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from seat_brain_v2 import main

if __name__ == "__main__":
    if "--seat" not in sys.argv:
        sys.argv[1:1] = ["--seat", "P4"]
    raise SystemExit(main())
