"""A deterministic offline stub provider.

Its job is *plumbing verification*, not intelligence.  ``make test`` runs the
entire pipeline end to end against this provider on a clean machine with no
credentials and no cassettes, so a contributor can prove the orchestration,
schema repair, sandboxing and grading all work before spending a single token.

Every response is a pure function of the request, so tests are deterministic.
"""

from __future__ import annotations

import hashlib
import json
import re

from .base import BaseProvider, LLMRequest, LLMResponse

_MODAL = re.compile(
    r"(?m)^\s*[-*]?\s*(.{12,300}?\b(?:must|shall|should|always|never)\b.{0,300})$", re.I
)


def _stable_int(text: str, modulo: int) -> int:
    return int(hashlib.sha256(text.encode()).hexdigest()[:8], 16) % modulo


class MockProvider(BaseProvider):
    name = "mock"

    def complete(self, request: LLMRequest, *, timeout_s: float) -> LLMResponse:
        handler = getattr(self, f"_do_{request.purpose}", None)
        text = handler(request) if handler else self._do_generic(request)
        return LLMResponse(
            text=text,
            model=request.model,
            provider=self.name,
            input_tokens=len(request.system + request.user) // 4,
            output_tokens=len(text) // 4,
            latency_ms=1,
            stop_reason="end_turn",
        )

    # ------------------------------------------------------------------ #

    def _do_generic(self, request: LLMRequest) -> str:
        return json.dumps({"ok": True, "echo": request.purpose})

    def _do_cartographer(self, request: LLMRequest) -> str:
        """Extract modal sentences from the spec as pseudo-obligations."""
        spec = request.user
        sentences: list[str] = []
        for line in spec.splitlines():
            stripped = line.strip().lstrip("-*0123456789. ").strip()
            if 12 <= len(stripped) <= 280 and re.search(
                r"\b(must|shall|always|never)\b", stripped, re.I
            ):
                sentences.append(stripped)
        sentences = sentences[:6] or ["The function must behave as described in the specification."]
        obligations = []
        for i, sentence in enumerate(sentences, start=1):
            quote = sentence if sentence in spec else spec.strip().splitlines()[0][:80]
            obligations.append(
                {
                    "id": f"OB-{i:03d}",
                    "kind": "MUST",
                    "statement": sentence[:300],
                    "quote": quote[:280],
                    "risk": "medium",
                    "inputs_hint": [],
                    "depends_on_ambiguity": [],
                }
            )
        return json.dumps({"obligations": obligations, "ambiguities": [], "vocabulary": {}})

    def _do_adversary(self, request: LLMRequest) -> str:
        entry = "solve"
        match = re.search(r"^def (\w+)\(", request.user, re.M)
        if match:
            entry = match.group(1)
        ob = "OB-001"
        ob_match = re.search(r"OB-\d{3}", request.user)
        if ob_match:
            ob = ob_match.group(0)
        code = f"import impl\n\n\ndef test_mock_probe():\n    assert hasattr(impl, {entry!r})\n"
        return json.dumps(
            {
                "probes": [
                    {
                        "strategy": "example",
                        "rationale": "mock provider smoke probe",
                        "code": code,
                        "obligation_id": ob,
                    }
                ]
            }
        )

    def _do_referee(self, request: LLMRequest) -> str:
        # Deterministically uphold roughly half of triages so both branches of
        # the pipeline are exercised by the test suite.
        upheld = _stable_int(request.user, 2) == 0
        return json.dumps(
            {
                "outcome": "upheld" if upheld else "bad_test",
                "reason": "mock triage",
                "spec_supports_expectation": upheld,
            }
        )

    def _do_reporter(self, request: LLMRequest) -> str:
        return json.dumps({"title": "Mock finding", "severity": "medium"})

    def _do_baseline_direct(self, request: LLMRequest) -> str:
        return json.dumps(
            {
                "tests": [
                    {
                        "name": "test_baseline_mock",
                        "code": "import impl\n\n\ndef test_baseline_mock():\n    assert impl is not None\n",
                    }
                ]
            }
        )

    def _do_forge_impl(self, request: LLMRequest) -> str:
        return json.dumps({"code": "def solve(*args, **kwargs):\n    return None\n"})

    def _do_forge_tests(self, request: LLMRequest) -> str:
        return json.dumps(
            {"code": "import impl\n\n\ndef test_smoke():\n    assert impl is not None\n"}
        )
