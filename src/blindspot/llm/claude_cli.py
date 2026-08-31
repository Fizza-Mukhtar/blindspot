"""Claude Code CLI as a model provider.

This backend drives the Claude Code binary in headless single-turn mode, which
means a Claude Pro/Max **subscription** can power the whole benchmark with no
pay-as-you-go API key.  It is also the most honest backend for this
competition: the entry is judged on agentic work, and the model calls are
served by an actual coding agent, whose transcripts are what we ship as
trajectories.

The CLI is invoked with every agentic affordance switched off -- no tools, no
MCP servers, no slash commands, no project settings, no ``CLAUDE.md`` discovery
-- so it behaves as a plain completion endpoint and the run stays a pure
function of the prompt.

Authentication (choose one):
    claude setup-token            -> CLAUDE_CODE_OAUTH_TOKEN in .env
    claude auth login             -> OS credential store
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from .base import BaseProvider, LLMRequest, LLMResponse, ProviderError

# Tools are disabled by name as well as by --max-turns so that a model which
# tries to reach for one degrades to plain text instead of stalling.
_DISABLED_TOOLS = [
    "Bash",
    "Edit",
    "Write",
    "Read",
    "Glob",
    "Grep",
    "WebFetch",
    "WebSearch",
    "Task",
    "Agent",
    "NotebookEdit",
    "TodoWrite",
    "SlashCommand",
    "Skill",
]


def _discover_executable() -> str | None:
    explicit = os.environ.get("CLAUDE_CODE_PATH")
    if explicit and Path(explicit).exists():
        return explicit
    found = shutil.which("claude")
    if found:
        return found
    exec_path = os.environ.get("CLAUDE_CODE_EXECPATH")
    if exec_path and Path(exec_path).exists():
        return exec_path
    # Windows desktop-app install location.
    local = Path(os.path.expanduser("~")) / "AppData/Local/Packages"
    if local.is_dir():
        candidates = sorted(
            local.glob("Claude_*/LocalCache/Roaming/Claude/claude-code/*/claude.exe")
        )
        if candidates:
            return str(candidates[-1])
    return None


class ClaudeCLIProvider(BaseProvider):
    name = "claude_cli"

    executable: str

    def __init__(self, executable: str | None = None) -> None:
        found = executable or _discover_executable()
        if not found:
            raise ProviderError(
                "Claude Code CLI not found. Install it, or set CLAUDE_CODE_PATH in .env.",
                retryable=False,
            )
        self.executable = found
        # An empty working directory keeps CLAUDE.md / settings discovery from
        # leaking machine-specific context into the prompt.
        self._workdir = Path(tempfile.mkdtemp(prefix="blindspot-cli-"))

    def _argv(self, request: LLMRequest) -> list[str]:
        return [
            self.executable,
            "--print",
            "--model",
            request.model,
            "--system-prompt",
            request.system,
            # Not 1.  Every tool is disallowed, but a model that reaches for
            # one anyway spends a turn discovering that, and with a budget of a
            # single turn the CLI aborts with `error_max_turns` and an *empty*
            # result instead of answering.  That silently zeroed the ReAct
            # baseline -- whose prompt talks about "tools" -- on every case.
            # A few turns let a refused tool call be followed by the answer.
            "--max-turns",
            "4",
            "--output-format",
            "json",
            "--disallowedTools",
            *_DISABLED_TOOLS,
            "--disable-slash-commands",
            "--strict-mcp-config",
            "--mcp-config",
            '{"mcpServers":{}}',
            "--settings",
            "{}",
        ]

    def complete(self, request: LLMRequest, *, timeout_s: float) -> LLMResponse:
        argv = self._argv(request)
        env = dict(os.environ)
        env.pop("ANTHROPIC_API_KEY", None)  # force subscription auth path
        env["CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC"] = "1"

        started = time.monotonic()
        try:
            proc = subprocess.run(
                argv,
                input=request.user,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout_s,
                cwd=str(self._workdir),
                env=env,
            )
        except subprocess.TimeoutExpired as exc:
            raise ProviderError(f"claude CLI timed out after {timeout_s}s") from exc
        latency_ms = int((time.monotonic() - started) * 1000)

        if not proc.stdout.strip():
            raise ProviderError(
                f"claude CLI produced no output (exit {proc.returncode}): "
                f"{proc.stderr.strip()[:400]}"
            )
        try:
            payload = json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            raise ProviderError(f"claude CLI returned non-JSON: {proc.stdout[:400]}") from exc

        # A run that exhausted its turns but still produced text is usable: the
        # text is the answer, the turn budget merely stopped further tool
        # attempts.  Only an error with nothing to show is a failure.
        if payload.get("is_error") and not str(payload.get("result") or "").strip():
            # `result` is often empty on transport failures, so the useful
            # diagnosis lives in the sibling fields.  Surfacing them turns
            # "unknown error" -- which is what a rate limit looked like on the
            # first long run -- into something actionable.
            message = str(payload.get("result") or "").strip()
            detail = {
                key: payload.get(key)
                for key in ("subtype", "terminal_reason", "api_error_status", "stop_reason")
                if payload.get(key)
            }
            stderr_tail = proc.stderr.strip()[-300:]
            rendered = message or "unknown error"
            if detail:
                rendered += f" [{', '.join(f'{k}={v}' for k, v in detail.items())}]"
            if stderr_tail:
                rendered += f" | stderr: {stderr_tail}"

            lowered = f"{message} {detail}".lower()
            not_logged_in = "not logged in" in lowered or "/login" in lowered
            hint = ""
            if not_logged_in:
                hint = (
                    "\nRun `claude setup-token` and put the token in .env as "
                    "CLAUDE_CODE_OAUTH_TOKEN, or run `claude auth login`."
                )
            elif "rate" in lowered or "limit" in lowered or "429" in lowered:
                hint = (
                    "\nThis looks like a usage limit. Forging and recording are both "
                    "idempotent -- re-run the same command later and it resumes from the "
                    "cassettes already written."
                )
            raise ProviderError(f"claude CLI error: {rendered}{hint}", retryable=not not_logged_in)

        usage = payload.get("usage") or {}
        text = str(payload.get("result", ""))
        if not text.strip():
            raise ProviderError("claude CLI returned an empty completion")

        return LLMResponse(
            text=text,
            model=request.model,
            provider=self.name,
            input_tokens=int(usage.get("input_tokens", 0))
            + int(usage.get("cache_read_input_tokens", 0))
            + int(usage.get("cache_creation_input_tokens", 0)),
            output_tokens=int(usage.get("output_tokens", 0)),
            latency_ms=latency_ms,
            stop_reason=str(payload.get("stop_reason") or payload.get("subtype") or ""),
            meta={"session_id": payload.get("session_id", "")},
        )

    def close(self) -> None:
        shutil.rmtree(self._workdir, ignore_errors=True)
