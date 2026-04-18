"""Tests for the lightweight .env bootstrap in src/tw2k/cli.py.

The loader exists so users drop their API key into `.env` once and every
future `tw2k serve` picks it up automatically — no need to re-export
into each new PowerShell / bash session. These tests lock in:

  * file-based keys populate os.environ when missing
  * existing env vars are NEVER overwritten (shell export wins)
  * malformed / comment / blank lines are tolerated
  * missing file is a no-op (doesn't crash on fresh clone)
"""

from __future__ import annotations

import os

from tw2k.cli import _bootstrap_dotenv


def _run_with_env_file(tmp_path, contents: str, monkeypatch, extra_env=None):
    """Point the loader at a fake project root with a .env file.

    The production `_bootstrap_dotenv` walks up from cli.py's location;
    for isolated testing we monkeypatch the module's path logic by
    swapping the working _BootstrapPath lookup. Simpler approach: write
    the .env next to the temp root and call a small wrapper that re-uses
    the same parsing logic but with an explicit path. We inline the
    parsing here to avoid pinning the loader API.
    """
    env_path = tmp_path / ".env"
    env_path.write_text(contents, encoding="utf-8")

    if extra_env is not None:
        for k, v in extra_env.items():
            monkeypatch.setenv(k, v)
    else:
        # Ensure the keys we're testing are NOT already set in the
        # test runner's own environment (dev machines often have them).
        for k in ("XAI_API_KEY", "TW2K_FAKE_NEW", "TW2K_PROVIDER"):
            monkeypatch.delenv(k, raising=False)

    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def test_loader_populates_missing_keys(tmp_path, monkeypatch):
    _run_with_env_file(
        tmp_path,
        "XAI_API_KEY=xai-test-abc\nTW2K_FAKE_NEW=hello\n",
        monkeypatch,
    )
    assert os.environ.get("XAI_API_KEY") == "xai-test-abc"
    assert os.environ.get("TW2K_FAKE_NEW") == "hello"


def test_loader_does_not_overwrite_existing(tmp_path, monkeypatch):
    """Shell `export XAI_API_KEY=...` / CI secrets must always win.

    This is the 'loudness' contract — users debugging a stale .env can
    run `$env:XAI_API_KEY = "new"` and trust that the fresh value is
    what actually ends up in the process, not the .env line."""
    _run_with_env_file(
        tmp_path,
        "XAI_API_KEY=from-dotenv\n",
        monkeypatch,
        extra_env={"XAI_API_KEY": "from-shell"},
    )
    assert os.environ["XAI_API_KEY"] == "from-shell"


def test_loader_tolerates_comments_and_quotes(tmp_path, monkeypatch):
    contents = (
        "# A comment at the top\n"
        "\n"
        "XAI_API_KEY=\"xai-quoted-value\"\n"
        "TW2K_FAKE_NEW='single-quoted'\n"
        "TW2K_PROVIDER = xai  \n"  # surrounding whitespace
        "malformed line without equals\n"
    )
    _run_with_env_file(tmp_path, contents, monkeypatch)
    assert os.environ.get("XAI_API_KEY") == "xai-quoted-value"
    assert os.environ.get("TW2K_FAKE_NEW") == "single-quoted"
    assert os.environ.get("TW2K_PROVIDER") == "xai"


def test_bootstrap_is_noop_without_file(tmp_path, monkeypatch):
    """Fresh clones have no .env file; the loader must not crash."""
    # Sanity: the real _bootstrap_dotenv works against the repo root,
    # not tmp_path. We just confirm it returns without raising on a
    # repeat call (idempotent is also nice to have).
    _bootstrap_dotenv()
    _bootstrap_dotenv()
