"""OpenTelemetry bridge for CopilotTracer (Phase H6.3).

The existing ``CopilotTracer`` writes flat JSONL events to disk, which is
perfect for grepping but hard to visualise across multiple players or
mixed with backend spans. This module adds an optional OTEL sink:

* One long-lived **session span** per player-copilot lifetime
  (``copilot.session``), tagged with player_id, provider, model.
* Every JSONL event (``chat_utterance``, ``llm_call``,
  ``action_dispatched``, ``standing_order_block``, ``safety_signal``,
  ``escalation``, ``mode_change``, ``memory_update``, ``task_state``)
  becomes an **OTEL span event** attached at the right timestamp on the
  session span — searchable in Jaeger/Weave/Honeycomb by attribute.
* ``action_dispatched`` *also* starts + immediately ends a short child
  span so you get a flamegraph-style view of actions over the session.

Design
------

OTEL is a **soft dependency** — if ``opentelemetry-api`` isn't installed
this module exports a stub ``CopilotOtelBridge`` whose ``emit`` calls
are no-ops. ``build_bridge()`` reads ``TW2K_OTEL_ENDPOINT`` (and the
related OTLP env vars) and returns ``None`` when OTEL is disabled or
not importable, so the tracer stays hot-path fast.

Env toggles
-----------

* ``TW2K_OTEL_ENDPOINT`` — OTLP HTTP endpoint (e.g. http://localhost:4318).
  Setting this enables the bridge. Unset → disabled.
* ``TW2K_OTEL_SERVICE_NAME`` — service name in span resource. Defaults
  to ``tw2k-ai``.
* ``TW2K_OTEL_CONSOLE`` — if truthy, *also* prints spans to **stderr**
  (nice for debugging without an OTLP collector running). Routed to
  stderr rather than stdout so ``tw2k …``, ``--json`` CLI surfaces stay
  parseable when OTEL is globally on in the shell.

All other standard ``OTEL_*`` env vars (``OTEL_EXPORTER_OTLP_HEADERS``,
``OTEL_EXPORTER_OTLP_PROTOCOL``, …) are respected by the SDK directly.
"""

from __future__ import annotations

import logging
import os
import sys
from contextlib import suppress
from typing import Any

ENV_ENDPOINT = "TW2K_OTEL_ENDPOINT"
ENV_SERVICE_NAME = "TW2K_OTEL_SERVICE_NAME"
ENV_CONSOLE = "TW2K_OTEL_CONSOLE"
DEFAULT_SERVICE_NAME = "tw2k-ai"

_log = logging.getLogger(__name__)


def _otel_available() -> bool:
    try:
        import opentelemetry  # noqa: F401
    except ImportError:
        return False
    return True


def _is_truthy(val: str | None) -> bool:
    return (val or "").strip().lower() in ("1", "true", "yes", "on")


# ---------------------------------------------------------------------------
# Tracer-provider bootstrap — process-global, idempotent.
# ---------------------------------------------------------------------------

_PROVIDER_READY = False


def _ensure_tracer_provider() -> Any | None:
    """Install a ``TracerProvider`` once per process. Returns the Tracer.

    Safe to call even without an endpoint configured — we just fall back
    to a no-op tracer so ``start_as_current_span`` et al work.
    """
    global _PROVIDER_READY
    if not _otel_available():
        return None

    from opentelemetry import trace
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import (
        BatchSpanProcessor,
        ConsoleSpanExporter,
    )

    if _PROVIDER_READY:
        return trace.get_tracer("tw2k.copilot")

    service_name = os.environ.get(ENV_SERVICE_NAME, DEFAULT_SERVICE_NAME)
    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)

    endpoint = os.environ.get(ENV_ENDPOINT, "").strip()
    if endpoint:
        with suppress(ImportError):
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
                OTLPSpanExporter,
            )

            provider.add_span_processor(
                BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{endpoint.rstrip('/')}/v1/traces"))
            )

    if _is_truthy(os.environ.get(ENV_CONSOLE)):
        # Route to stderr so JSON-emitting CLIs (e.g. `tw2k human-sim
        # --json`) keep stdout clean when operators leave
        # TW2K_OTEL_CONSOLE=1 in their shell.
        provider.add_span_processor(
            BatchSpanProcessor(ConsoleSpanExporter(out=sys.stderr))
        )

    trace.set_tracer_provider(provider)
    _PROVIDER_READY = True
    return trace.get_tracer("tw2k.copilot")


# ---------------------------------------------------------------------------
# CopilotOtelBridge — one instance per copilot session.
# ---------------------------------------------------------------------------


class CopilotOtelBridge:
    """Long-lived OTEL session span + per-event bridge.

    Created by ``build_bridge()`` when OTEL is enabled; otherwise the
    tracer holds ``None`` and every call becomes a no-op.
    """

    __slots__ = ("_scope", "_session_span", "_tracer", "player_id")

    def __init__(self, *, player_id: str, attributes: dict[str, Any] | None = None) -> None:
        self.player_id = player_id
        self._tracer = _ensure_tracer_provider()
        self._session_span: Any | None = None
        self._scope: Any | None = None
        if self._tracer is None:
            return
        try:
            self._session_span = self._tracer.start_span(
                "copilot.session",
                attributes={
                    "tw2k.player_id": player_id,
                    **_safe_attrs(attributes or {}),
                },
            )
            # Make the session span the active parent for any spans
            # created by child code (LLM libs, httpx, etc.) that honour
            # OTEL context.
            from opentelemetry import trace

            self._scope = trace.use_span(self._session_span, end_on_exit=False)
            self._scope.__enter__()
        except Exception:  # pragma: no cover - defensive
            _log.exception("Failed to start copilot.session span")
            self._session_span = None
            self._scope = None

    @property
    def enabled(self) -> bool:
        return self._session_span is not None

    def shutdown(self) -> None:
        """End the session span. Safe to call repeatedly."""
        if self._scope is not None:
            with suppress(Exception):
                self._scope.__exit__(None, None, None)
            self._scope = None
        if self._session_span is not None:
            with suppress(Exception):
                self._session_span.end()
            self._session_span = None

    # -- Event emission -----------------------------------------------------

    def emit_event(
        self,
        event: str,
        payload: dict[str, Any] | None = None,
        *,
        level: str = "info",
    ) -> None:
        """Attach a span event to the session span.

        Mirrors the shape of ``CopilotTracer.emit`` so the JSONL sink and
        OTEL sink carry the same information. Defensive: any exception
        from the OTEL SDK is swallowed (tracing must never break the hot
        path).
        """
        if self._session_span is None:
            return
        try:
            attrs = {"tw2k.level": level, **_safe_attrs(payload or {})}
            self._session_span.add_event(event, attributes=attrs)
        except Exception:  # pragma: no cover - defensive
            _log.debug("otel emit_event failed", exc_info=True)

    def emit_action_span(
        self,
        tool: str,
        args: dict[str, Any],
        ok: bool,
        reason: str,
    ) -> None:
        """Record an ``action_dispatched`` as a discrete child span.

        Duration is effectively zero (we don't own the engine's action
        lifecycle) but the span's presence gives flamegraph-style UIs a
        point to hang a click-to-details interaction on.
        """
        if self._tracer is None or self._session_span is None:
            return
        try:
            from opentelemetry import trace

            with trace.use_span(self._session_span, end_on_exit=False), self._tracer.start_as_current_span(
                f"copilot.action.{tool}",
                attributes={
                    "tw2k.tool": tool,
                    "tw2k.ok": bool(ok),
                    "tw2k.reason": str(reason)[:200],
                    **_safe_attrs({f"tw2k.arg.{k}": v for k, v in args.items()}),
                },
            ):
                pass
        except Exception:  # pragma: no cover - defensive
            _log.debug("otel emit_action_span failed", exc_info=True)


def _safe_attrs(payload: dict[str, Any]) -> dict[str, Any]:
    """Coerce payload values into OTEL-legal attribute types.

    OTEL only accepts str / bool / int / float (and homogeneous sequences
    of those). Everything else gets ``str()``-ified. Keys longer than 64
    chars are truncated — some collectors enforce that limit.
    """
    out: dict[str, Any] = {}
    for k, v in payload.items():
        if not isinstance(k, str):
            k = str(k)
        k = k[:64]
        if isinstance(v, (str, bool, int, float)):
            out[k] = v
        elif isinstance(v, (list, tuple)) and all(
            isinstance(x, (str, bool, int, float)) for x in v
        ):
            out[k] = list(v)
        else:
            try:
                out[k] = str(v)[:400]
            except Exception:
                out[k] = "<unserialisable>"
    return out


def build_bridge(
    *,
    player_id: str,
    attributes: dict[str, Any] | None = None,
    force: bool | None = None,
) -> CopilotOtelBridge | None:
    """Construct a bridge iff OTEL is configured AND the SDK is available.

    ``force=True`` bypasses the endpoint check (useful for tests that
    install an in-memory exporter manually). ``force=False`` disables
    unconditionally. ``force=None`` (default) follows the env.
    """
    if force is False:
        return None
    if force is None:
        endpoint = os.environ.get(ENV_ENDPOINT, "").strip()
        console = _is_truthy(os.environ.get(ENV_CONSOLE))
        if not endpoint and not console:
            return None
    if not _otel_available():
        return None
    bridge = CopilotOtelBridge(player_id=player_id, attributes=attributes)
    return bridge if bridge.enabled else None


__all__ = [
    "DEFAULT_SERVICE_NAME",
    "ENV_CONSOLE",
    "ENV_ENDPOINT",
    "ENV_SERVICE_NAME",
    "CopilotOtelBridge",
    "build_bridge",
]
