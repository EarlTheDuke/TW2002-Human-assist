"""The port reservation has to import on Windows, where fcntl does not exist."""

from __future__ import annotations

import multiprocessing as mp
import subprocess
import sys
import tempfile
from pathlib import Path

from tests._port_lock import _DIR, claim_ports, release_ports

ROOT = Path(__file__).resolve().parents[1]


def test_the_book_lives_in_the_system_temp_dir() -> None:
    text = (ROOT / "tests" / "_port_lock.py").read_text(encoding="utf-8")
    assert 'Path("/tmp' not in text and "tempfile.gettempdir()" in text
    assert Path(tempfile.gettempdir()) == _DIR
    # fcntl is loaded only when a POSIX process takes the lock, never at import.
    assert "\nimport fcntl\n" not in text


def test_import_does_not_need_fcntl() -> None:
    """Ben's PC: `import fcntl` at module scope is `No module named fcntl`."""
    code = (
        "import sys\n"
        "class _Block:\n"
        "    def find_spec(self, name, path, target=None):\n"
        "        if name == 'fcntl':\n"
        "            raise ModuleNotFoundError('No module named fcntl')\n"
        "        return None\n"
        "sys.meta_path.insert(0, _Block())\n"
        "import tests._port_lock\n"
        "print('imported')\n"
    )
    out = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True, check=False)
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip() == "imported"


def test_two_processes_do_not_claim_the_same_ports() -> None:
    def grab(q):
        base = claim_ports(2, low=47000, high=47200)
        q.put(base)

    queue: mp.Queue = mp.Queue()
    procs = [mp.Process(target=grab, args=(queue,)) for _ in range(6)]
    for proc in procs:
        proc.start()
    for proc in procs:
        proc.join(20)
        assert proc.exitcode == 0
    bases = [queue.get() for _ in procs]
    owned = [port for base in bases for port in range(base, base + 2)]
    assert len(owned) == len(set(owned))
    release_ports(*owned)
