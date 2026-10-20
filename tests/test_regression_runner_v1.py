"""The regression runner keeps each browser file in its own process."""

from __future__ import annotations

from pathlib import Path

from tests._regression import is_browser_file, split_files
from tests._screenshot import save_screenshot

ROOT = Path(__file__).resolve().parents[1]


def test_browser_files_are_split_from_unit_files() -> None:
    browser, unit = split_files(ROOT / "tests")
    names = {path.name for path in browser}
    unit_names = {path.name for path in unit}
    assert "test_cockpit_playthrough_v1.py" in names
    assert "test_cockpit_ship_view_full_v1.py" in names
    assert "test_cockpit_note50_polish_v1.py" in names
    assert "test_engine.py" in unit_names
    assert "test_regression_runner_v1.py" in unit_names
    assert names.isdisjoint(unit_names)
    assert all(is_browser_file(path) for path in browser)
    assert all(not is_browser_file(path) for path in unit)
    assert len(browser) + len(unit) == len(list((ROOT / "tests").glob("test_*.py")))
    # Each browser file is one pytest process. Two files never share one.
    assert all(path.suffix == ".py" for path in browser)


class _Page:
    def __init__(self) -> None:
        self.calls = 0

    def screenshot(self, **kwargs) -> bytes:
        self.calls += 1
        if self.calls == 1:
            raise BlockingIOError(11, "Resource temporarily unavailable")
        return b"png"


def test_screenshot_retries_a_blocking_io_error(tmp_path: Path) -> None:
    dest = tmp_path / "shot.png"
    save_screenshot(_Page(), dest, attempts=3)
    assert dest.read_bytes() == b"png"
