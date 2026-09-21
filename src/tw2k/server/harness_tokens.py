"""Per-seat bearer tokens for external (Grok Bot) seats.

Resolution order for a seat ``P3``:

1. explicit token on the AgentSpec / restart body (``agents[i].token``)
2. env ``TW2K_EXTERNAL_TOKEN_P3``
3. tokens file (``TW2K_EXTERNAL_TOKENS_FILE``, default ``.tw2k/external_tokens.json``
   under the repo root) — a flat ``{"P3": "...", "P4": "..."}`` map
4. freshly generated ``secrets.token_urlsafe(32)``, persisted to the tokens
   file so the same token survives ``/control/restart`` and server reboots

Tokens never appear in meta.json, events, snapshots, or unmasked logs.
The tokens file and its directory are gitignored.
"""

from __future__ import annotations

import hmac
import json
import os
import secrets
from pathlib import Path

ENV_TOKENS_FILE = "TW2K_EXTERNAL_TOKENS_FILE"
ENV_TOKEN_PREFIX = "TW2K_EXTERNAL_TOKEN_"
DEFAULT_TOKENS_FILE = Path(".tw2k") / "external_tokens.json"


def _repo_root() -> Path:
    # src/tw2k/server/harness_tokens.py -> up 4 = repo root
    return Path(__file__).resolve().parents[3]


def tokens_file_path(explicit: str | os.PathLike[str] | None = None) -> Path:
    raw = explicit or os.environ.get(ENV_TOKENS_FILE) or ""
    if raw:
        p = Path(raw).expanduser()
        return p if p.is_absolute() else (Path.cwd() / p).resolve()
    return _repo_root() / DEFAULT_TOKENS_FILE


def load_tokens_file(path: Path) -> dict[str, str]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(k): str(v) for k, v in data.items() if isinstance(v, str) and v}


def save_tokens_file(path: Path, tokens: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(tokens, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    try:
        os.chmod(path, 0o600)
    except OSError:
        # Windows ACLs ignore POSIX bits; best effort only.
        pass


def generate_token() -> str:
    return secrets.token_urlsafe(32)


def mask(token: str | None) -> str:
    if not token:
        return "<unset>"
    if len(token) <= 12:
        return "<short>"
    return f"{token[:4]}...{token[-4:]}"


def verify(candidate: str | None, expected: str | None) -> bool:
    if not candidate or not expected:
        return False
    return hmac.compare_digest(candidate.encode("utf-8"), expected.encode("utf-8"))


def resolve_seat_tokens(
    seats: dict[str, str | None],
    *,
    tokens_file: str | os.PathLike[str] | None = None,
    persist: bool = True,
) -> dict[str, str]:
    """Return ``{player_id: token}`` for every seat, generating + persisting as needed.

    ``seats`` maps player_id -> explicit token (or None). Only seats whose
    token had to be *generated* are written back; explicit/env tokens are
    never copied into the file.
    """
    path = tokens_file_path(tokens_file)
    on_disk = load_tokens_file(path)
    out: dict[str, str] = {}
    new_entries: dict[str, str] = {}
    for pid, explicit in seats.items():
        tok = (explicit or "").strip()
        if not tok:
            tok = (os.environ.get(f"{ENV_TOKEN_PREFIX}{pid}") or "").strip()
        if not tok:
            tok = on_disk.get(pid, "")
        if not tok:
            tok = generate_token()
            new_entries[pid] = tok
        out[pid] = tok
    if new_entries and persist:
        on_disk.update(new_entries)
        save_tokens_file(path, on_disk)
    return out
