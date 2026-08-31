"""Provider-independent request/response shapes.

Every Blindspot model call is **single turn**: a system prompt plus exactly one
user message.  That is a deliberate constraint, not a limitation:

* it makes each call independently content-addressable, which is what the
  cassette layer needs to give byte-identical replay;
* it removes hidden conversational state, so a stage's behaviour is a pure
  function of the artefacts fed into it;
* it lets the Claude Code CLI (a subscription-backed coding agent) act as a
  drop-in provider alongside raw HTTP APIs.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Any

from ..types import canonical_json, sha256_text


class ProviderError(RuntimeError):
    """Raised when a provider cannot produce a completion."""

    def __init__(self, message: str, *, retryable: bool = True) -> None:
        super().__init__(message)
        self.retryable = retryable


class CassetteMiss(RuntimeError):
    """Raised in strict replay mode when no recording exists for a request."""


@dataclass(frozen=True)
class LLMRequest:
    system: str
    user: str
    model: str
    temperature: float = 0.0
    max_tokens: int = 4096
    # `purpose` is carried into the cassette key so that two structurally
    # identical prompts issued by different stages never collide.
    purpose: str = "generic"
    # `nonce` distinguishes deliberate re-samples of the *same* prompt
    # (e.g. self-consistency voting) from accidental repeats.
    nonce: int = 0

    def cache_payload(self) -> dict[str, Any]:
        return {
            "system": self.system,
            "user": self.user,
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "purpose": self.purpose,
            "nonce": self.nonce,
        }

    def cache_key(self) -> str:
        return sha256_text(canonical_json(self.cache_payload()))


@dataclass
class LLMResponse:
    text: str
    model: str
    provider: str
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int = 0
    stop_reason: str = ""
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "model": self.model,
            "provider": self.provider,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "stop_reason": self.stop_reason,
            # latency is deliberately NOT persisted: it is machine-dependent
            # and would break byte-identical replay.
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LLMResponse:
        return cls(
            text=data["text"],
            model=data.get("model", ""),
            provider=data.get("provider", ""),
            input_tokens=int(data.get("input_tokens", 0)),
            output_tokens=int(data.get("output_tokens", 0)),
            stop_reason=data.get("stop_reason", ""),
        )


class BaseProvider(abc.ABC):
    """Minimal contract every backend implements."""

    name: str = "base"

    @abc.abstractmethod
    def complete(self, request: LLMRequest, *, timeout_s: float) -> LLMResponse:  # pragma: no cover
        ...

    def close(self) -> None:  # pragma: no cover - most providers are stateless
        return None
