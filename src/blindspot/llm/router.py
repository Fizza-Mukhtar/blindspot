"""The single door through which every model call passes.

Responsibilities, in order of importance to the project:

1. **Determinism.**  Record/replay via :mod:`blindspot.llm.cassette`, so the
   published numbers can be regenerated offline with no credentials.
2. **Schema discipline.**  ``structured()`` parses, validates and *repairs*
   model output against a Pydantic model with a bounded retry loop.  A stage
   never receives a half-parsed dict.
3. **Observability.**  Every call, retry and repair is written to the
   trajectory.
4. **Accounting.**  Tokens, USD and wall-clock are attributed per stage.
"""

from __future__ import annotations

import json
import random
import re
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from ..config import RunConfig
from ..trace.recorder import NullRecorder, TrajectoryRecorder
from ..types import CostRecord, estimate_tokens
from .base import BaseProvider, CassetteMiss, LLMRequest, LLMResponse, ProviderError
from .cassette import CassetteStore

T = TypeVar("T", bound=BaseModel)

_FENCE = re.compile(r"```(?:json|JSON)?\s*(.*?)```", re.S)


class SchemaRepairFailed(RuntimeError):
    """Raised when a model could not be coaxed into the required schema."""


# --------------------------------------------------------------------------- #
# Process-wide in-flight limit
# --------------------------------------------------------------------------- #

_inflight_lock = threading.Lock()
_inflight_sem: threading.Semaphore | None = None
_inflight_limit = 0


def set_inflight_limit(limit: int) -> None:
    """Bound how many model calls may be in flight process-wide.

    The evaluation nests thread pools: one over ``(system, case)`` jobs, and a
    second inside each audit over obligations.  Worker counts therefore
    *multiply*, so ``--concurrency 6`` was really up to 36 simultaneous calls.
    For the Claude Code CLI backend each of those is its own subprocess, which
    thrashes the machine long before it saturates the API -- that is what made
    individual calls take minutes rather than seconds.

    One semaphore at the only place every call passes through makes throughput
    a function of a single number instead of the product of two, and keeps the
    knob meaningful for every backend.
    """
    global _inflight_sem, _inflight_limit
    with _inflight_lock:
        if limit <= 0:
            _inflight_sem, _inflight_limit = None, 0
        else:
            _inflight_sem, _inflight_limit = threading.Semaphore(limit), limit


def inflight_limit() -> int:
    return _inflight_limit


@contextmanager
def _inflight_slot() -> Iterator[None]:
    semaphore = _inflight_sem
    if semaphore is None:
        yield
        return
    semaphore.acquire()
    try:
        yield
    finally:
        semaphore.release()


def build_provider(config: RunConfig) -> BaseProvider | None:
    """Construct the live provider, or ``None`` for pure replay."""
    if config.provider == "replay":
        return None
    if config.provider == "mock":
        from .mock import MockProvider

        return MockProvider()
    if config.provider == "claude_cli":
        from .claude_cli import ClaudeCLIProvider

        return ClaudeCLIProvider()
    if config.provider == "anthropic":
        from .http_providers import AnthropicProvider

        return AnthropicProvider()
    if config.provider == "openai":
        from .http_providers import OpenAIProvider

        return OpenAIProvider()
    raise ValueError(f"unknown provider {config.provider!r}")


def extract_json(text: str) -> Any:
    """Pull a JSON document out of a model response.

    Models wrap JSON in prose and fences with depressing creativity, so we try,
    in order: the whole string, every fenced block, then the outermost brace or
    bracket span.  Raises ``ValueError`` if nothing parses.
    """
    candidates: list[str] = [text.strip()]
    candidates.extend(m.strip() for m in _FENCE.findall(text))
    for opener, closer in (("{", "}"), ("[", "]")):
        start = text.find(opener)
        end = text.rfind(closer)
        if start != -1 and end > start:
            candidates.append(text[start : end + 1])
    for candidate in candidates:
        if not candidate:
            continue
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue
    raise ValueError("no parsable JSON found in model output")


class LLMRouter:
    """Facade over a provider plus the cassette store."""

    def __init__(
        self,
        config: RunConfig,
        *,
        recorder: TrajectoryRecorder | None = None,
        store: CassetteStore | None = None,
        provider: BaseProvider | None = None,
        scope: str = "",
    ) -> None:
        self.config = config
        # Identifies this run inside a shared cassette store, so concurrent
        # runs cannot renumber each other's occurrence sequences.
        self.scope = scope
        self.recorder = recorder or NullRecorder()
        self.store = store or CassetteStore(config.cassette_dir, strict=config.strict_replay)
        self._provider = provider if provider is not None else build_provider(config)
        self.cost = CostRecord()
        self._rng = random.Random(config.seed)
        self._lock = threading.Lock()

    # ------------------------------------------------------------------ #
    # Raw completion
    # ------------------------------------------------------------------ #

    def complete(
        self,
        *,
        purpose: str,
        system: str,
        user: str,
        role: str = "fast",
        nonce: int = 0,
        max_tokens: int | None = None,
        attempt: int = 1,
    ) -> LLMResponse:
        model = self.config.resolve(role)  # type: ignore[arg-type]
        request = LLMRequest(
            system=system,
            user=user,
            model=model,
            temperature=self.config.temperature,
            max_tokens=max_tokens or self.config.max_tokens,
            purpose=purpose,
            nonce=nonce,
        )

        started = time.monotonic()
        response = self._dispatch(request)
        elapsed_ms = int((time.monotonic() - started) * 1000)

        # Content tokens are estimated from the text we actually sent and
        # received, so the cost column means the same thing on every backend.
        content_in = estimate_tokens(system) + estimate_tokens(user)
        content_out = estimate_tokens(response.text)
        with self._lock:
            self.cost = self.cost.merge(
                CostRecord(
                    calls=1,
                    input_tokens=content_in,
                    output_tokens=content_out,
                    provider_input_tokens=response.input_tokens,
                    provider_output_tokens=response.output_tokens,
                    usd=self.config.price(model, content_in, content_out),
                    wall_ms=elapsed_ms,
                )
            )
        self.recorder.llm_call(
            purpose=purpose,
            model=model,
            system_prompt=system,
            user_prompt=user,
            response_text=response.text,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            cassette=response.meta.get("cassette"),
            attempt=attempt,
        )
        return response

    def _dispatch(self, request: LLMRequest) -> LLMResponse:
        # Replay-first, *including* during a live recording run.  Recording is
        # then idempotent and resumable: re-running the same command after a
        # usage limit or a crash replays everything already captured and pays
        # only for the calls that were never reached.
        key, seq, cached = self.store.take(request, self.scope)
        if cached is not None:
            return cached
        if self._provider is None:
            # Pure replay.  Fall back to the clamped read so a run that takes
            # one extra retry than the recording did still resolves.
            return self.store.replay(request, key, seq)

        last_error: Exception | None = None
        for attempt in range(1, self.config.llm_retries + 1):
            try:
                with _inflight_slot():
                    response = self._provider.complete(request, timeout_s=self.config.llm_timeout_s)
                if self.config.record:
                    path = self.store.record(request, response, key=key, seq=seq)
                    response.meta["cassette"] = str(path.name)
                return response
            except ProviderError as exc:
                last_error = exc
                if not exc.retryable or attempt == self.config.llm_retries:
                    break
                backoff = min(2**attempt, 30) + self._rng.random()
                self.recorder.retry(reason="provider_error", attempt=attempt, detail=str(exc)[:500])
                time.sleep(backoff)
        if isinstance(last_error, ProviderError):
            raise last_error
        raise ProviderError(str(last_error))

    # ------------------------------------------------------------------ #
    # Schema-validated completion
    # ------------------------------------------------------------------ #

    def structured(
        self,
        *,
        purpose: str,
        system: str,
        user: str,
        schema: type[T],
        role: str = "fast",
        max_tokens: int | None = None,
        extra_validate: Any = None,
        nonce: int = 0,
    ) -> T:
        """Complete, parse JSON and validate against ``schema``.

        On failure the *exact* validation error is fed back to the model, up to
        ``config.repair_attempts`` times.  ``extra_validate`` is an optional
        callable that receives the parsed model and either returns ``None`` or a
        string describing a semantic problem to repair (this is how the
        verbatim-quote check is enforced on the Cartographer).
        """
        prompt = user
        last_error = ""
        for attempt in range(1, self.config.repair_attempts + 2):
            response = self.complete(
                purpose=purpose,
                system=system,
                user=prompt,
                role=role,
                nonce=nonce * 100 + (attempt - 1),
                max_tokens=max_tokens,
                attempt=attempt,
            )
            try:
                payload = extract_json(response.text)
                parsed = schema.model_validate(payload)
            except (ValueError, ValidationError) as exc:
                last_error = str(exc)[:1800]
                self.recorder.retry(reason="schema_violation", attempt=attempt, detail=last_error)
                prompt = (
                    f"{user}\n\n"
                    "--- REPAIR REQUIRED ---\n"
                    "Your previous reply could not be parsed into the required schema.\n"
                    f"Error:\n{last_error}\n\n"
                    "Reply again with ONLY the corrected JSON object. No prose, no code fences."
                )
                continue

            if extra_validate is not None:
                problem = extra_validate(parsed)
                if problem:
                    last_error = str(problem)[:1800]
                    self.recorder.retry(
                        reason="semantic_violation", attempt=attempt, detail=last_error
                    )
                    prompt = (
                        f"{user}\n\n"
                        "--- REPAIR REQUIRED ---\n"
                        f"{last_error}\n\n"
                        "Reply again with ONLY the corrected JSON object. No prose, no code fences."
                    )
                    continue
            return parsed

        raise SchemaRepairFailed(
            f"{purpose}: model did not satisfy the schema after "
            f"{self.config.repair_attempts + 1} attempts. Last error: {last_error}"
        )

    # ------------------------------------------------------------------ #

    def close(self) -> None:
        if self._provider is not None:
            self._provider.close()

    @property
    def is_replay(self) -> bool:
        return self._provider is None


__all__ = [
    "CassetteMiss",
    "LLMRouter",
    "SchemaRepairFailed",
    "build_provider",
    "extract_json",
]
