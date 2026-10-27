import os

# A test that leaves a watched engine global changed fails with its node id.
# Module fixtures that put the value back when the module ends stay quiet.
# TW2K_LEAK_GUARD=warn prints the line and lets the test pass.
# TW2K_LEAK_GUARD=off skips the check.
if "TW2K_LEAK_GUARD" not in os.environ:
    os.environ["TW2K_LEAK_GUARD"] = "fail"

pytest_plugins = ["tests.leak_guard_plugin"]

import pytest  # noqa: E402

from tests._cu_host import browser  # noqa: F401, E402  (Playwright fixture for the /bot browser tests)

# R-4 (docs/plans/future-stages-v1.md): the stored V311_PROFILE default is "v311".
# A module that pins the legacy rules says so with
#     pytestmark = pytest.mark.legacy_profile
# and runs, module fixtures and collection-time state aside, under V311_PROFILE="legacy".
# Grep for the marker to find the tests that go with each legacy path removal.


def pytest_configure(config):
    config.addinivalue_line("markers", "legacy_profile: run this module under V311_PROFILE='legacy'")


@pytest.fixture(autouse=True, scope="module")
def _legacy_profile_module(request):
    if request.node.get_closest_marker("legacy_profile") is None:
        yield
        return
    import tw2k.engine.constants as K

    saved = K.V311_PROFILE
    K.V311_PROFILE = "legacy"
    try:
        yield
    finally:
        K.V311_PROFILE = saved
