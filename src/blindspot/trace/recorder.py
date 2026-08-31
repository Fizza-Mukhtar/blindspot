"""Agent trajectory recording.

One JSONL file per (case, system) run.  Every event is append-only and
self-describing, so a trajectory can be read top-to-bottom as a narrative:

    run.start -> stage.start -> llm.call -> tool.call -> verify.retry
              -> human.checkpoint -> stage.end -> run.end

This is simultaneously:

* the "Agent trajectories" submission deliverable,
* the debugging surface used while building the system, and
* the input to ``blindspot trace render``, which produces a single-file HTML
  viewer that needs no server and no dependencies.

Field naming follows the OpenTelemetry GenAI semantic conventions where they
apply (``gen_ai.request.model``, ``gen_ai.usage.*``) so the files can be
ingested by standard tooling, but the format stays plain JSONL on purpose:
a judge can read it with ``head``.
"""

from __future__ import annotations

import json
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

TRACE_FORMAT = 1


def _truncate(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    return value[:limit] + f"\n... [{len(value) - limit} more characters truncated]"


def _resilient(action: Callable[[], object], *, attempts: int = 5) -> bool:
    """Run a trajectory write, tolerating a transient file lock.

    Trajectories are written into the working tree, and on Windows a sync
    client (OneDrive, Dropbox) or a virus scanner can hold a handle open for a
    fraction of a second.  The result was ``PermissionError`` propagating out of
    the *logger* and failing three otherwise-fine evaluation runs, which then
    showed up as unexplained variance between two replays of the same cassettes.

    A dropped log line is a cosmetic loss; a killed run is a corrupted result.
    So this retries briefly, then gives up quietly and counts the loss in
    ``TrajectoryRecorder.dropped`` rather than raising.
    """
    for attempt in range(attempts):
        try:
            action()
            return True
        except OSError:
            if attempt == attempts - 1:
                return False
            time.sleep(0.05 * (attempt + 1))
    return False


class TrajectoryRecorder:
    """Append-only JSONL writer with a monotonically increasing step counter."""

    def __init__(
        self,
        path: Path,
        *,
        run_id: str,
        case_id: str,
        system: str,
        max_field_chars: int = 24_000,
        enabled: bool = True,
    ) -> None:
        self.path = Path(path)
        self.run_id = run_id
        self.case_id = case_id
        self.system = system
        self.max_field_chars = max_field_chars
        self.enabled = enabled
        self._step = 0
        self._lock = threading.Lock()
        self._stage = "init"
        self.dropped = 0
        if self.enabled:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            _resilient(lambda: self.path.write_text("", encoding="utf-8"))

    # ------------------------------------------------------------------ #

    def _emit(self, event: str, payload: dict[str, Any]) -> None:
        if not self.enabled:
            return
        with self._lock:
            self._step += 1
            record = {
                "format": TRACE_FORMAT,
                "step": self._step,
                "event": event,
                "run_id": self.run_id,
                "case_id": self.case_id,
                "system": self.system,
                "stage": self._stage,
                **payload,
            }
            line = json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n"

            def _append() -> None:
                with self.path.open("a", encoding="utf-8") as handle:
                    handle.write(line)

            if not _resilient(_append):
                # Observability must not be able to fail the thing it observes.
                self.dropped += 1

    # ------------------------------------------------------------------ #
    # Public event API
    # ------------------------------------------------------------------ #

    def run_start(self, *, config: dict[str, Any], inputs: dict[str, Any]) -> None:
        self._emit("run.start", {"config": config, "inputs": inputs})

    def run_end(self, *, verdict: str, findings: int, cost: dict[str, Any]) -> None:
        self._stage = "done"
        self._emit("run.end", {"verdict": verdict, "findings": findings, "cost": cost})

    def stage_start(self, stage: str, note: str = "") -> None:
        self._stage = stage
        self._emit("stage.start", {"note": note})

    def stage_end(self, stage: str, summary: dict[str, Any]) -> None:
        self._stage = stage
        self._emit("stage.end", {"summary": summary})

    def llm_call(
        self,
        *,
        purpose: str,
        model: str,
        system_prompt: str,
        user_prompt: str,
        response_text: str,
        input_tokens: int,
        output_tokens: int,
        cassette: str | None,
        attempt: int = 1,
    ) -> None:
        self._emit(
            "llm.call",
            {
                "gen_ai.operation.name": purpose,
                "gen_ai.request.model": model,
                "gen_ai.usage.input_tokens": input_tokens,
                "gen_ai.usage.output_tokens": output_tokens,
                "attempt": attempt,
                "cassette": cassette,
                "prompt.system": _truncate(system_prompt, self.max_field_chars),
                "prompt.user": _truncate(user_prompt, self.max_field_chars),
                "completion": _truncate(response_text, self.max_field_chars),
            },
        )

    def tool_call(self, *, tool: str, args: dict[str, Any], result: dict[str, Any]) -> None:
        """A deterministic, non-model action: sandbox execution, AST parse, quote check."""
        self._emit(
            "tool.call",
            {
                "tool.name": tool,
                "tool.arguments": {
                    k: _truncate(v, 6_000) if isinstance(v, str) else v for k, v in args.items()
                },
                "tool.result": {
                    k: _truncate(v, 8_000) if isinstance(v, str) else v for k, v in result.items()
                },
            },
        )

    def retry(self, *, reason: str, attempt: int, detail: str = "") -> None:
        """Feedback that changed the agent's next step -- the interesting part of a trace."""
        self._emit(
            "verify.retry",
            {"reason": reason, "attempt": attempt, "detail": _truncate(detail, 4_000)},
        )

    def human_checkpoint(
        self, *, question: str, options: list[str], resolution: str | None, resolved_by: str
    ) -> None:
        self._emit(
            "human.checkpoint",
            {
                "question": question,
                "options": options,
                "resolution": resolution,
                "resolved_by": resolved_by,
            },
        )

    def decision(self, *, what: str, why: str, data: dict[str, Any] | None = None) -> None:
        self._emit("agent.decision", {"what": what, "why": why, "data": data or {}})

    def note(self, message: str) -> None:
        self._emit("note", {"message": message})


class NullRecorder(TrajectoryRecorder):
    """No-op recorder used by unit tests and by nested/forge runs."""

    def __init__(self) -> None:
        super().__init__(Path("."), run_id="null", case_id="null", system="null", enabled=False)
