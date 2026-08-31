"""HTTP model backends (Anthropic Messages API, OpenAI-compatible Chat).

These are optional: ``pip install -e ".[live]"``.  The default ``replay``
provider needs neither of them, which is why they are imported lazily.
"""

from __future__ import annotations

import os
import time

from .base import BaseProvider, LLMRequest, LLMResponse, ProviderError


class AnthropicProvider(BaseProvider):
    name = "anthropic"

    def __init__(self) -> None:
        try:
            import anthropic
        except ImportError as exc:  # pragma: no cover
            raise ProviderError(
                'anthropic SDK not installed. Run: pip install -e ".[live]"', retryable=False
            ) from exc
        key = os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise ProviderError(
                "ANTHROPIC_API_KEY is not set. Put it in .env, or use "
                "BLINDSPOT_PROVIDER=claude_cli with a Claude subscription.",
                retryable=False,
            )
        self._client = anthropic.Anthropic(api_key=key)

    def complete(self, request: LLMRequest, *, timeout_s: float) -> LLMResponse:
        started = time.monotonic()
        try:
            msg = self._client.messages.create(
                model=request.model,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                system=request.system,
                messages=[{"role": "user", "content": request.user}],
                timeout=timeout_s,
            )
        except Exception as exc:
            raise ProviderError(f"anthropic API error: {exc}") from exc
        latency_ms = int((time.monotonic() - started) * 1000)
        # The SDK's content union covers a dozen block types; only text blocks
        # carry `.text`, so it is read defensively rather than by isinstance
        # against a list that grows with every SDK release.
        text = "".join(
            str(getattr(block, "text", ""))
            for block in msg.content
            if getattr(block, "type", "") == "text"
        )
        return LLMResponse(
            text=text,
            model=msg.model,
            provider=self.name,
            input_tokens=msg.usage.input_tokens,
            output_tokens=msg.usage.output_tokens,
            latency_ms=latency_ms,
            stop_reason=str(msg.stop_reason or ""),
        )


class OpenAIProvider(BaseProvider):
    name = "openai"

    def __init__(self) -> None:
        try:
            import openai
        except ImportError as exc:  # pragma: no cover
            raise ProviderError(
                'openai SDK not installed. Run: pip install -e ".[live]"', retryable=False
            ) from exc
        key = os.environ.get("OPENAI_API_KEY")
        if not key:
            raise ProviderError("OPENAI_API_KEY is not set.", retryable=False)
        base_url = os.environ.get("OPENAI_BASE_URL") or None
        self._client = openai.OpenAI(api_key=key, base_url=base_url)

    def complete(self, request: LLMRequest, *, timeout_s: float) -> LLMResponse:
        started = time.monotonic()
        try:
            resp = self._client.chat.completions.create(
                model=request.model,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                messages=[
                    {"role": "system", "content": request.system},
                    {"role": "user", "content": request.user},
                ],
                timeout=timeout_s,
            )
        except Exception as exc:
            raise ProviderError(f"openai API error: {exc}") from exc
        latency_ms = int((time.monotonic() - started) * 1000)
        choice = resp.choices[0]
        usage = resp.usage
        return LLMResponse(
            text=choice.message.content or "",
            model=resp.model,
            provider=self.name,
            input_tokens=getattr(usage, "prompt_tokens", 0) if usage else 0,
            output_tokens=getattr(usage, "completion_tokens", 0) if usage else 0,
            latency_ms=latency_ms,
            stop_reason=str(choice.finish_reason or ""),
        )
