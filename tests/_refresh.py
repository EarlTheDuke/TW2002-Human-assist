"""Wait for the redesign cockpit's own refresh counter.

A fixed sleep guesses how long three 2-second refreshes take. The page
already counts them on window.__tw2kTest.refreshCount.
"""

from __future__ import annotations


def wait_refreshes(page, n: int = 3, timeout: int = 20_000) -> None:
    start = page.evaluate(
        "() => (window.__tw2kTest && window.__tw2kTest.refreshCount && window.__tw2kTest.refreshCount()) || 0"
    )
    page.wait_for_function(
        """([start, n]) => {
          const api = window.__tw2kTest;
          return !!(api && api.refreshCount && api.refreshCount() >= start + n);
        }""",
        arg=[int(start), int(n)],
        timeout=timeout,
    )
