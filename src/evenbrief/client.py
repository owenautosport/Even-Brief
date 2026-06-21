"""Thin Anthropic API wrapper for the Even Brief generation backend.

This module isolates *all* network/SDK use behind ``BriefingClient`` so the rest
of the pipeline can be imported and unit-tested (and ``--dry-run`` can run) with
no ``anthropic`` package and no ``ANTHROPIC_API_KEY`` present.

The ``anthropic`` import is therefore performed **lazily** inside the methods
that actually call the API - never at module import time.

API facts baked in here (authoritative; do not re-verify over the network):
* Models: ``claude-opus-4-8`` ($5/MTok in, $25/MTok out) for verification and
  logic checking; ``claude-sonnet-4-6`` ($3/$15) for high-volume research/writing.
* Server-side web tools (GA, no beta header):
  ``{"type":"web_search_20260209","name":"web_search"}`` and
  ``{"type":"web_fetch_20260209","name":"web_fetch"}``.
* Adaptive thinking via ``thinking={"type":"adaptive"}`` and high effort via
  ``output_config={"effort":"high"}`` on Opus.
* Structured output: ``client.messages.parse(..., output_format=Model)`` returns
  an object whose ``.parsed_output`` is the validated Pydantic instance.
* Server tools run server-side; a research loop must re-send the conversation
  while ``stop_reason == "pause_turn"``.
* Web searches are billed at ~$10 / 1000 searches.
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Any, Optional, Type, TypeVar

from pydantic import BaseModel

# Model identifiers ---------------------------------------------------------- #
MODEL_OPUS = "claude-opus-4-8"        # verification / logic-check
MODEL_SONNET = "claude-sonnet-4-6"    # research / writing

# Per-MTok USD pricing (input, output). ------------------------------------- #
_PRICING = {
    MODEL_OPUS: (5.0, 25.0),
    MODEL_SONNET: (3.0, 15.0),
}
_SEARCH_USD = 10.0 / 1000.0           # $0.01 per web_search call

# Server tool definitions (GA - no beta header needed). --------------------- #
WEB_SEARCH_TOOL = {"type": "web_search_20260209", "name": "web_search"}
WEB_FETCH_TOOL = {"type": "web_fetch_20260209", "name": "web_fetch"}

T = TypeVar("T", bound=BaseModel)


# --------------------------------------------------------------------------- #
# Cost accounting
# --------------------------------------------------------------------------- #
@dataclass
class CostMeter:
    """Accumulates token + web-search usage and estimates the run cost in USD.

    Costs are split per model because Opus and Sonnet are priced differently.
    ``add()`` is fed a ``response.usage`` object (or anything exposing
    ``input_tokens`` / ``output_tokens`` / ``server_tool_use``).
    """
    # model -> [input_tokens, output_tokens]
    tokens: dict[str, list[int]] = field(default_factory=dict)
    searches: int = 0
    fetches: int = 0
    calls: int = 0

    def add(self, model: str, usage: Any) -> None:
        self.calls += 1
        bucket = self.tokens.setdefault(model, [0, 0])
        bucket[0] += int(getattr(usage, "input_tokens", 0) or 0)
        bucket[1] += int(getattr(usage, "output_tokens", 0) or 0)
        # Cache tokens, when present, are billed roughly as input - fold them in.
        bucket[0] += int(getattr(usage, "cache_read_input_tokens", 0) or 0)
        bucket[0] += int(getattr(usage, "cache_creation_input_tokens", 0) or 0)
        stu = getattr(usage, "server_tool_use", None)
        if stu is not None:
            self.searches += int(getattr(stu, "web_search_requests", 0) or 0)
            self.fetches += int(getattr(stu, "web_fetch_requests", 0) or 0)

    def add_searches(self, n: int) -> None:
        self.searches += int(n)

    def usd(self) -> float:
        total = self.searches * _SEARCH_USD
        for model, (ti, to) in self.tokens.items():
            pin, pout = _PRICING.get(model, (0.0, 0.0))
            total += (ti / 1_000_000) * pin + (to / 1_000_000) * pout
        return total

    def summary(self) -> str:
        lines = ["Cost meter:"]
        for model, (ti, to) in sorted(self.tokens.items()):
            lines.append(
                f"  {model}: {ti:,} in / {to:,} out tokens"
            )
        lines.append(f"  web_search: {self.searches} | web_fetch: {self.fetches}")
        lines.append(f"  API calls: {self.calls}")
        lines.append(f"  Estimated cost: ${self.usd():.4f}")
        return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Web-research result container
# --------------------------------------------------------------------------- #
@dataclass
class ResearchResult:
    """The final text of a web-research call plus the sources it gathered."""
    text: str
    sources: list[dict[str, str]] = field(default_factory=list)


# --------------------------------------------------------------------------- #
# Client
# --------------------------------------------------------------------------- #
class BriefingClient:
    """Wraps ``anthropic.Anthropic`` with retries, structured parsing and a
    server-tool research loop. Construction triggers the (lazy) SDK import and
    reads ``ANTHROPIC_API_KEY`` from the environment.
    """

    def __init__(self, meter: Optional[CostMeter] = None, max_retries: int = 4):
        self.meter = meter or CostMeter()
        self.max_retries = max_retries
        # Lazy import: only required when a live client is actually built.
        import anthropic  # noqa: F401  (presence check)

        self._anthropic = anthropic
        key = os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set; live BriefingClient unavailable. "
                "Use --dry-run for an offline edition."
            )
        self._client = anthropic.Anthropic(api_key=key)

    # ----- retry helper ---------------------------------------------------- #
    def _with_retries(self, fn):
        """Run ``fn`` with exponential backoff on rate limits / 5xx errors."""
        anthropic = self._anthropic
        last_exc: Optional[Exception] = None
        for attempt in range(self.max_retries):
            try:
                return fn()
            except anthropic.RateLimitError as exc:  # 429
                last_exc = exc
            except anthropic.APIStatusError as exc:   # other HTTP errors
                if getattr(exc, "status_code", 0) < 500:
                    raise
                last_exc = exc
            except anthropic.APIConnectionError as exc:
                last_exc = exc
            sleep = min(2 ** attempt, 30) + 0.5
            time.sleep(sleep)
        assert last_exc is not None
        raise last_exc

    # ----- structured parse ------------------------------------------------ #
    def parse(
        self,
        *,
        output_format: Type[T],
        prompt: str,
        system: str = "",
        model: str = MODEL_SONNET,
        max_tokens: int = 8000,
        opus_effort: bool = False,
    ) -> T:
        """Make a structured call that parses directly into a Pydantic model.

        Retries on ``RateLimitError`` and ``APIStatusError`` (>=500). Returns the
        validated ``.parsed_output``.
        """
        kwargs: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
            "output_format": output_format,
        }
        if system:
            kwargs["system"] = system
        if model == MODEL_OPUS:
            kwargs["thinking"] = {"type": "adaptive"}
            if opus_effort:
                kwargs["output_config"] = {"effort": "high"}

        def _call():
            return self._client.messages.parse(**kwargs)

        resp = self._with_retries(_call)
        self.meter.add(model, getattr(resp, "usage", None))
        return resp.parsed_output  # type: ignore[attr-defined]

    # ----- web research loop ----------------------------------------------- #
    def research(
        self,
        *,
        prompt: str,
        system: str = "",
        model: str = MODEL_SONNET,
        max_tokens: int = 8000,
        max_searches: int = 8,
        stream: bool = True,
    ) -> ResearchResult:
        """Run a research turn with web_search + web_fetch enabled.

        Server tools execute server-side; whenever the model pauses
        (``stop_reason == "pause_turn"``) we re-send the accumulated message
        content so the model can continue. Returns the final assistant text plus
        any web-search result sources encountered.
        """
        tools = [
            {**WEB_SEARCH_TOOL, "max_uses": max_searches},
            WEB_FETCH_TOOL,
        ]
        messages: list[dict[str, Any]] = [{"role": "user", "content": prompt}]
        collected_sources: list[dict[str, str]] = []
        final_text: list[str] = []

        for _ in range(12):  # hard ceiling on pause/resume rounds
            base: dict[str, Any] = {
                "model": model,
                "max_tokens": max_tokens,
                "messages": messages,
                "tools": tools,
            }
            if system:
                base["system"] = system

            def _call():
                if stream:
                    # Streaming for large outputs; accumulate to a final message.
                    with self._client.messages.stream(**base) as s:
                        return s.get_final_message()
                return self._client.messages.create(**base)

            msg = self._with_retries(_call)
            self.meter.add(model, getattr(msg, "usage", None))

            # Harvest text + web-search source citations from the content blocks.
            for block in msg.content:
                btype = getattr(block, "type", None)
                if btype == "text" and getattr(block, "text", ""):
                    final_text.append(block.text)
                    for cit in getattr(block, "citations", None) or []:
                        url = getattr(cit, "url", None)
                        if url:
                            collected_sources.append(
                                {
                                    "url": url,
                                    "title": getattr(cit, "title", "") or "",
                                }
                            )
                elif btype == "web_search_tool_result":
                    for item in getattr(block, "content", None) or []:
                        url = getattr(item, "url", None)
                        if url:
                            collected_sources.append(
                                {
                                    "url": url,
                                    "title": getattr(item, "title", "") or "",
                                }
                            )

            if getattr(msg, "stop_reason", None) == "pause_turn":
                # Re-send the assistant turn verbatim so server tools resume.
                messages.append({"role": "assistant", "content": msg.content})
                continue
            break

        # De-duplicate sources by URL while preserving order.
        seen: set[str] = set()
        unique: list[dict[str, str]] = []
        for s in collected_sources:
            if s["url"] not in seen:
                seen.add(s["url"])
                unique.append(s)
        return ResearchResult(text="\n".join(final_text).strip(), sources=unique)
