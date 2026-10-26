"""The quick set keeps its slow list honest and never drops the pins."""

from __future__ import annotations

from pathlib import Path

from tests._regression import split_files
from tests._tiers import SLOW_UNIT_FILES, is_pin_file, quick_files

TESTS = Path(__file__).resolve().parent


def test_every_slow_name_is_a_unit_file_that_exists() -> None:
    _browser, unit = split_files(TESTS)
    unit_names = {path.name for path in unit}
    assert sorted(SLOW_UNIT_FILES - unit_names) == []


def test_quick_set_has_no_browser_file_and_no_slow_file() -> None:
    browser, _unit = split_files(TESTS)
    quick = {path.name for path in quick_files(TESTS)}
    assert quick.isdisjoint(path.name for path in browser)
    assert quick.isdisjoint(SLOW_UNIT_FILES)


def test_every_pin_is_in_the_quick_set() -> None:
    pins = {path.name for path in TESTS.glob("test_*.py") if is_pin_file(path)}
    assert pins, "no legacy pins found"
    assert pins <= {path.name for path in quick_files(TESTS)}
