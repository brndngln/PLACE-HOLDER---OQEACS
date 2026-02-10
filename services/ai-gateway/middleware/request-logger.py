# ===========================================================================
# SYSTEM 3 -- AI GATEWAY: LiteLLM Callback Handler
# Omni Quantum Elite AI Coding System -- Request Logging & Observability
#
# Custom LiteLLM callback class that batches events and ships them to
# Langfuse for full request/response tracing, cost attribution, and
# failure tracking.
# ===========================================================================

import os
import time
import json
import uuid
import threading
from collections import deque
from datetime import datetime, timezone
from typing import Any, Optional

import httpx
import structlog

logger = structlog.get_logger("litellm-callback")

# ──────────────────────────────────────────────────────────
# Cost-per-token estimates for local Ollama models (USD)
# These approximate the compute cost of running each model
# locally, normalized per 1M tokens for readability.
# ──────────────────────────────────────────────────────────
COST_PER_MILLION_TOKENS = {
    "ollama/devstral-2-123b": {"input": 0.60, "output": 1.80},
    "ollama/deepseek-v3.2": {"input": 0.30, "output": 0.90},
    "ollama/qwen3-coder-30b": {"input": 0.15, "output": 0.45},
    "ollama/kimi-dev-72b": {"input": 0.40, "output": 1.20},
}

DEFAULT_COST_PER_MILLION = {"input": 0.25, "output": 0.75}


def _estimate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Estimate the USD cost for a request based on token counts and model."""
    rates = COST_PER_MILLION_TOKENS.get(model, DEFAULT_COST_PER_MILLION)
    input_cost = (prompt_tokens / 1_000_000) * rates["input"]
    output_cost = (completion_tokens / 1_000_000) * rates["output"]
    return round(input_cost + output_cost, 8)


def _utc_iso() -> str:
    """Return current UTC timestamp in ISO-8601 format."""
    return datetime.now(timezone.utc).isoformat()


class LangfuseRequestLogger:
    """LiteLLM callback handler that logs to Langfuse with batching.

    Events are buffered in a thread-safe deque and flushed to the
    Langfuse ingestion API either every ``flush_interval`` seconds or
    when the buffer reaches ``flush_size`` events -- whichever comes
    first.
    """

    def __init__(self) -> None:
        self.langfuse_url = os.getenv("LANGFUSE_HOST", "http://omni-langfuse:3000")
        self.public_key = os.getenv("LANGFUSE_PUBLIC_KEY", "")
        self.secret_key = os.getenv("LANGFUSE_SECRET_KEY", "")
        self.buffer: deque = deque(maxlen=1000)
        self.flush_interval: int = 10
        self.flush_size: int = 100
        self._lock = threading.Lock()
        self._client = httpx.Client(timeout=15.0)
        self._start_flush_thread()

        logger.info(
            "langfuse_callback_initialized",
            langfuse_url=self.langfuse_url,
            flush_interval=self.flush_interval,
            flush_size=self.flush_size,
        )

    # ──────────────────────────────────────────────────────
    # Background flush thread
    # ──────────────────────────────────────────────────────

    def _start_flush_thread(self) -> None:
        """Launch a daemon thread that periodically flushes the buffer."""
        thread = threading.Thread(target=self._periodic_flush, daemon=True)
        thread.start()
        logger.debug("flush_thread_started", interval_seconds=self.flush_interval)

    def _periodic_flush(self) -> None:
        """Run an infinite loop, flushing the buffer every ``flush_interval`` seconds."""
        while True:
            time.sleep(self.flush_interval)
            try:
                self._flush_buffer()
            except Exception as exc:
                logger.error("periodic_flush_error", error=str(exc), exc_info=True)

    def _flush_buffer(self) -> None:
        """Drain up to ``flush_size`` events from the buffer and POST them to Langfuse."""
        events: list[dict] = []
        with self._lock:
            while self.buffer and len(events) < self.flush_size:
                events.append(self.buffer.popleft())

        if not events:
            return

        logger.info("flushing_events", count=len(events))

        payload = {"batch": events, "metadata": {"sdk": "omni-quantum-litellm-callback", "version": "1.0.0"}}

        try:
            response = self._client.post(
                f"{self.langfuse_url}/api/public/ingestion",
                json=payload,
                auth=(self.public_key, self.secret_key),
                headers={"Content-Type": "application/json"},
            )
            if response.status_code >= 400:
                logger.warning(
                    "langfuse_flush_http_error",
                    status_code=response.status_code,
                    body=response.text[:500],
                    event_count=len(events),
                )
            else:
                logger.debug("langfuse_flush_ok", status_code=response.status_code, event_count=len(events))
        except httpx.HTTPError as exc:
            logger.error("langfuse_flush_network_error", error=str(exc), event_count=len(events))
            # Re-queue events that failed to send (drop if buffer is full)
            with self._lock:
                for event in reversed(events):
                    if len(self.buffer) < self.buffer.maxlen:
                        self.buffer.appendleft(event)

    def _enqueue(self, event: dict) -> None:
        """Add an event to the buffer and trigger a flush if the threshold is reached."""
        with self._lock:
            self.buffer.append(event)
            should_flush = len(self.buffer) >= self.flush_size

        if should_flush:
            threading.Thread(target=self._flush_buffer, daemon=True).start()

    # ──────────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────────

    def _extract_metadata(self, kwargs: dict) -> dict:
        """Pull commonly-used metadata out of the litellm kwargs dict."""
        litellm_params = kwargs.get("litellm_params", {}) or {}
        metadata = litellm_params.get("metadata", {}) or {}
        return {
            "model": kwargs.get("model", "unknown"),
            "call_type": kwargs.get("call_type", "unknown"),
            "api_base": litellm_params.get("api_base", ""),
            "user": metadata.get("user", "anonymous"),
            "service": metadata.get("service", "unknown"),
            "trace_id": metadata.get("trace_id", str(uuid.uuid4())),
            "tags": litellm_params.get("tags", []),
        }

    def _build_usage_dict(self, response_obj: Any) -> dict:
        """Safely extract token-usage data from a litellm response object."""
        usage = {}
        if hasattr(response_obj, "usage") and response_obj.usage is not None:
            usage_obj = response_obj.usage
            usage["prompt_tokens"] = getattr(usage_obj, "prompt_tokens", 0) or 0
            usage["completion_tokens"] = getattr(usage_obj, "completion_tokens", 0) or 0
            usage["total_tokens"] = getattr(usage_obj, "total_tokens", 0) or 0
        return usage

    # ──────────────────────────────────────────────────────
    # Pre-call hook
    # ──────────────────────────────────────────────────────

    def log_pre_api_call(self, model: str, messages: list, kwargs: dict) -> None:
        """Called by LiteLLM before the request is sent to the provider.

        We log a lightweight span-start event so Langfuse can show
        latency even when the downstream call never completes.
        """
        meta = self._extract_metadata(kwargs)
        message_count = len(messages) if isinstance(messages, list) else 0
        estimated_input_tokens = sum(len(str(m.get("content", ""))) // 4 for m in messages) if isinstance(messages, list) else 0

        event = {
            "id": str(uuid.uuid4()),
            "type": "span-create",
            "timestamp": _utc_iso(),
            "body": {
                "traceId": meta["trace_id"],
                "name": f"litellm-pre-call-{model}",
                "startTime": _utc_iso(),
                "metadata": {
                    "model": model,
                    "call_type": meta["call_type"],
                    "api_base": meta["api_base"],
                    "service": meta["service"],
                    "user": meta["user"],
                    "message_count": message_count,
                    "estimated_input_tokens": estimated_input_tokens,
                    "tags": meta["tags"],
                },
                "input": {
                    "message_count": message_count,
                    "first_message_role": messages[0].get("role", "unknown") if messages and isinstance(messages, list) else "none",
                },
            },
        }
        self._enqueue(event)
        logger.debug(
            "pre_api_call_logged",
            model=model,
            trace_id=meta["trace_id"],
            message_count=message_count,
        )

    # ──────────────────────────────────────────────────────
    # Success handler (async)
    # ──────────────────────────────────────────────────────

    async def async_log_success_event(self, kwargs: dict, response_obj: Any, start_time: float, end_time: float) -> None:
        """Called by LiteLLM after a successful API call.

        Builds a Langfuse generation event with full usage, cost, and
        latency data, then enqueues it for the next batch flush.
        """
        meta = self._extract_metadata(kwargs)
        usage = self._build_usage_dict(response_obj)
        duration_s = round(end_time - start_time, 4)

        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        cost = _estimate_cost(meta["model"], prompt_tokens, completion_tokens)

        # Extract the actual response text
        response_text = ""
        if hasattr(response_obj, "choices") and response_obj.choices:
            first_choice = response_obj.choices[0]
            if hasattr(first_choice, "message") and first_choice.message:
                response_text = getattr(first_choice.message, "content", "") or ""
            elif hasattr(first_choice, "delta") and first_choice.delta:
                response_text = getattr(first_choice.delta, "content", "") or ""

        event = {
            "id": str(uuid.uuid4()),
            "type": "generation-create",
            "timestamp": _utc_iso(),
            "body": {
                "traceId": meta["trace_id"],
                "name": f"litellm-{meta['model']}",
                "startTime": datetime.fromtimestamp(start_time, tz=timezone.utc).isoformat(),
                "endTime": datetime.fromtimestamp(end_time, tz=timezone.utc).isoformat(),
                "model": meta["model"],
                "modelParameters": {
                    "max_tokens": str(kwargs.get("max_tokens", "")),
                    "temperature": str(kwargs.get("temperature", "")),
                    "stream": str(kwargs.get("stream", False)),
                },
                "usage": {
                    "input": prompt_tokens,
                    "output": completion_tokens,
                    "total": usage.get("total_tokens", prompt_tokens + completion_tokens),
                    "unit": "TOKENS",
                },
                "metadata": {
                    "service": meta["service"],
                    "user": meta["user"],
                    "api_base": meta["api_base"],
                    "call_type": meta["call_type"],
                    "duration_seconds": duration_s,
                    "cost_usd": cost,
                    "tags": meta["tags"],
                    "status": "success",
                },
                "output": {
                    "content": response_text[:2000],  # Truncate to keep payload size reasonable
                },
                "level": "DEFAULT",
                "statusMessage": "success",
            },
        }
        self._enqueue(event)

        logger.info(
            "success_event_logged",
            model=meta["model"],
            trace_id=meta["trace_id"],
            duration_s=duration_s,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_usd=cost,
            service=meta["service"],
        )

    # ──────────────────────────────────────────────────────
    # Failure handler (async)
    # ──────────────────────────────────────────────────────

    async def async_log_failure_event(self, kwargs: dict, response_obj: Any, start_time: float, end_time: float) -> None:
        """Called by LiteLLM when an API call fails.

        Logs the error details to Langfuse so failures are visible in
        traces and can trigger alerting rules.
        """
        meta = self._extract_metadata(kwargs)
        duration_s = round(end_time - start_time, 4)

        # Try to extract error information
        exception = kwargs.get("exception", None)
        error_message = str(exception) if exception else "Unknown error"
        error_type = type(exception).__name__ if exception else "UnknownError"

        # Attempt to get any partial usage data
        usage = self._build_usage_dict(response_obj) if response_obj else {}
        prompt_tokens = usage.get("prompt_tokens", 0)

        event = {
            "id": str(uuid.uuid4()),
            "type": "generation-create",
            "timestamp": _utc_iso(),
            "body": {
                "traceId": meta["trace_id"],
                "name": f"litellm-{meta['model']}-error",
                "startTime": datetime.fromtimestamp(start_time, tz=timezone.utc).isoformat(),
                "endTime": datetime.fromtimestamp(end_time, tz=timezone.utc).isoformat(),
                "model": meta["model"],
                "modelParameters": {
                    "max_tokens": str(kwargs.get("max_tokens", "")),
                    "temperature": str(kwargs.get("temperature", "")),
                    "stream": str(kwargs.get("stream", False)),
                },
                "usage": {
                    "input": prompt_tokens,
                    "output": 0,
                    "total": prompt_tokens,
                    "unit": "TOKENS",
                },
                "metadata": {
                    "service": meta["service"],
                    "user": meta["user"],
                    "api_base": meta["api_base"],
                    "call_type": meta["call_type"],
                    "duration_seconds": duration_s,
                    "error_type": error_type,
                    "error_message": error_message[:1000],
                    "tags": meta["tags"],
                    "status": "error",
                },
                "output": {
                    "error": error_message[:2000],
                },
                "level": "ERROR",
                "statusMessage": f"Failed: {error_type}",
            },
        }
        self._enqueue(event)

        logger.error(
            "failure_event_logged",
            model=meta["model"],
            trace_id=meta["trace_id"],
            duration_s=duration_s,
            error_type=error_type,
            error_message=error_message[:200],
            service=meta["service"],
        )

    # ──────────────────────────────────────────────────────
    # Streaming support
    # ──────────────────────────────────────────────────────

    async def async_log_stream_event(self, kwargs: dict, response_obj: Any, start_time: float, end_time: float) -> None:
        """Handle streaming success events identically to non-streaming ones."""
        await self.async_log_success_event(kwargs, response_obj, start_time, end_time)

    # ──────────────────────────────────────────────────────
    # Synchronous fallbacks
    # ──────────────────────────────────────────────────────

    def log_success_event(self, kwargs: dict, response_obj: Any, start_time: float, end_time: float) -> None:
        """Synchronous wrapper for environments that do not use async callbacks."""
        import asyncio

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.async_log_success_event(kwargs, response_obj, start_time, end_time))
        except RuntimeError:
            asyncio.run(self.async_log_success_event(kwargs, response_obj, start_time, end_time))

    def log_failure_event(self, kwargs: dict, response_obj: Any, start_time: float, end_time: float) -> None:
        """Synchronous wrapper for environments that do not use async callbacks."""
        import asyncio

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.async_log_failure_event(kwargs, response_obj, start_time, end_time))
        except RuntimeError:
            asyncio.run(self.async_log_failure_event(kwargs, response_obj, start_time, end_time))

    # ──────────────────────────────────────────────────────
    # Shutdown
    # ──────────────────────────────────────────────────────

    def shutdown(self) -> None:
        """Flush remaining events and close the HTTP client."""
        logger.info("callback_shutting_down", remaining_events=len(self.buffer))
        try:
            self._flush_buffer()
            # Drain anything left after the first flush
            while self.buffer:
                self._flush_buffer()
        except Exception as exc:
            logger.error("shutdown_flush_error", error=str(exc))
        finally:
            self._client.close()
            logger.info("callback_shutdown_complete")
