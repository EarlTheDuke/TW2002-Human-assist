import os

# A test that leaves a watched engine global changed fails with its node id.
# Module fixtures that put the value back when the module ends stay quiet.
# TW2K_LEAK_GUARD=warn prints the line and lets the test pass.
# TW2K_LEAK_GUARD=off skips the check.
if "TW2K_LEAK_GUARD" not in os.environ:
    os.environ["TW2K_LEAK_GUARD"] = "fail"

pytest_plugins = ["tests.leak_guard_plugin"]

from tests._cu_host import browser  # noqa: F401, E402  (Playwright fixture for the /bot browser tests)
