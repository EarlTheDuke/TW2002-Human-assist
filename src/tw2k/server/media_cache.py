"""Cache headers for files under ``web/media``.

A content-hashed name (``something.<8+ hex>.ext``) is safe to cache for a
year. ``manifest.json`` and every other media file must be revalidated.
Files outside ``media/`` keep Starlette's default headers.
"""

from __future__ import annotations

import re

from starlette.staticfiles import StaticFiles

_HASHED = re.compile(r"\.[0-9a-fA-F]{8,}\.[A-Za-z0-9]+$")
IMMUTABLE = "public, max-age=31536000, immutable"
REVALIDATE = "no-cache"


def media_cache_control(path: str) -> str | None:
    norm = path.replace("\\", "/").lstrip("/")
    if not (norm == "media" or norm.startswith("media/")):
        return None
    name = norm.rsplit("/", 1)[-1]
    if _HASHED.search(name):
        return IMMUTABLE
    return REVALIDATE


class MediaStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        response = await super().get_response(path, scope)
        if getattr(response, "status_code", None) == 200:
            header = media_cache_control(path)
            if header:
                response.headers["Cache-Control"] = header
        return response
