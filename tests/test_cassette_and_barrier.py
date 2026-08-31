"""Reproducibility and the information barrier -- the two claims the README leans on."""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from blindspot.agents.cartographer import (
    BarrierViolation,
    attest_barrier,
    run_cartographer,
    verify_quotes,
)
from blindspot.config import RunConfig
from blindspot.llm.base import CassetteMiss, LLMRequest, LLMResponse
from blindspot.llm.cassette import CassetteStore
from blindspot.llm.mock import MockProvider
from blindspot.llm.router import LLMRouter, extract_json
from blindspot.trace.recorder import NullRecorder
from blindspot.types import Obligation, ObligationGraph

# --------------------------------------------------------------------------- #
# Cassettes
# --------------------------------------------------------------------------- #


def _request(user: str = "hello", nonce: int = 0) -> LLMRequest:
    return LLMRequest(system="sys", user=user, model="m", purpose="test", nonce=nonce)


def test_record_then_replay_is_byte_identical(tmp_path: Path):
    store = CassetteStore(tmp_path)
    original = LLMResponse(
        text="the answer", model="m", provider="p", input_tokens=3, output_tokens=2
    )
    store.record(_request(), original)

    replayed = CassetteStore(tmp_path).lookup(_request())
    assert replayed.text == original.text
    assert replayed.input_tokens == original.input_tokens
    assert replayed.meta["replayed"] is True


def test_a_changed_prompt_misses_loudly(tmp_path: Path):
    store = CassetteStore(tmp_path)
    store.record(_request("hello"), LLMResponse(text="x", model="m", provider="p"))
    with pytest.raises(CassetteMiss) as excinfo:
        CassetteStore(tmp_path).lookup(_request("hello, world"))
    assert "make record" in str(excinfo.value)


def test_repeat_calls_replay_in_recorded_order(tmp_path: Path):
    store = CassetteStore(tmp_path)
    store.record(_request(), LLMResponse(text="first", model="m", provider="p"))
    store.record(_request(), LLMResponse(text="second", model="m", provider="p"))

    replay = CassetteStore(tmp_path)
    assert replay.lookup(_request()).text == "first"
    assert replay.lookup(_request()).text == "second"
    # A replay that asks for more repeats than were recorded clamps rather than
    # exploding, so a slightly different path still completes.
    assert replay.lookup(_request()).text == "second"


def test_replay_is_order_independent_under_concurrency(tmp_path: Path):
    """Each stage's prompt is unique, so thread scheduling cannot change a result.

    This is what makes the parallel sweep safe to publish: the same cassettes
    replay to the same answers regardless of how the threads interleave.
    """
    store = CassetteStore(tmp_path)
    for index in range(12):
        store.record(
            _request(f"prompt-{index}"), LLMResponse(text=f"reply-{index}", model="m", provider="p")
        )

    replay = CassetteStore(tmp_path)
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda i: replay.lookup(_request(f"prompt-{i}")).text, range(12)))
    assert results == [f"reply-{i}" for i in range(12)]


def test_router_records_and_then_replays(tmp_path: Path):
    config = RunConfig(provider="mock", model_family="mock", cassette_dir=tmp_path, record=True)
    live = LLMRouter(config, provider=MockProvider())
    first = live.complete(purpose="cartographer", system="s", user="must do a thing properly")

    offline = LLMRouter(RunConfig(provider="replay", model_family="mock", cassette_dir=tmp_path))
    assert offline.is_replay
    assert (
        offline.complete(purpose="cartographer", system="s", user="must do a thing properly").text
        == first.text
    )


def test_manifest_counts_recordings(tmp_path: Path):
    store = CassetteStore(tmp_path)
    store.record(_request("a"), LLMResponse(text="1", model="m", provider="p", input_tokens=5))
    store.record(_request("b"), LLMResponse(text="2", model="m", provider="p", input_tokens=7))
    manifest = store.manifest()
    assert manifest["recordings"] == 2
    assert manifest["input_tokens"] == 12


# --------------------------------------------------------------------------- #
# JSON extraction
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "text",
    [
        '{"a": 1}',
        'Here you go:\n```json\n{"a": 1}\n```\nHope that helps.',
        '```\n{"a": 1}\n```',
        'prose before {"a": 1} prose after',
    ],
)
def test_extract_json_survives_model_packaging(text):
    assert extract_json(text) == {"a": 1}


def test_extract_json_raises_when_there_is_none():
    with pytest.raises(ValueError):
        extract_json("no json here at all")


# --------------------------------------------------------------------------- #
# The information barrier
# --------------------------------------------------------------------------- #

IMPL = '''\
def sort_versions(tags):
    """Sort tags."""
    parsed = [(tag, tag.split(".")) for tag in tags]
    return [tag for tag, _ in sorted(parsed, key=lambda pair: pair[1])]
'''


def test_attestation_is_clean_for_a_spec_only_context():
    attestation = attest_barrier("The function must sort tags by precedence.", IMPL)
    assert attestation.clean
    assert attestation.impl_lines_checked >= 1
    assert attestation.leaked_lines == []


def test_attestation_detects_leaked_implementation_text():
    context = "The spec says...\n" + IMPL
    attestation = attest_barrier(context, IMPL)
    assert not attestation.clean
    assert attestation.leaked_lines


def test_attestation_ignores_trivial_lines():
    """Short or boilerplate lines coincide by chance and must not count as leaks."""
    impl = "import re\nx = 1\nreturn None\n"
    assert attest_barrier("import re and also x = 1 and return None", impl).clean


def test_cartographer_aborts_on_a_barrier_violation(mock_config, monkeypatch):
    """A leak must fail the run, not warn."""
    from blindspot.agents import cartographer as module

    monkeypatch.setattr(module, "attest_barrier", lambda ctx, impl, **kw: _dirty())
    router = LLMRouter(mock_config, provider=MockProvider())
    with pytest.raises(BarrierViolation):
        run_cartographer(spec="anything", router=router, recorder=NullRecorder(), impl_src=IMPL)


def _dirty():
    from blindspot.agents.cartographer import BarrierAttestation

    return BarrierAttestation(
        context_sha256="x",
        context_chars=1,
        impl_sha256="y",
        impl_lines_checked=1,
        impl_lines_published_by_spec=0,
        leaked_lines=["def sort_versions(tags):"],
    )


# --------------------------------------------------------------------------- #
# Quote verification
# --------------------------------------------------------------------------- #


def test_verified_quotes_survive_and_invented_ones_do_not():
    spec = "The result must be sorted ascending.  Ties keep their input order."
    graph = ObligationGraph(
        obligations=[
            Obligation(
                id="OB-001", kind="MUST", statement="sort ascending", quote="sorted ascending"
            ),
            Obligation(id="OB-002", kind="MUST", statement="invented", quote="must be reversed"),
            Obligation(
                id="OB-003",
                kind="MUST",
                statement="whitespace differs",
                quote="Ties keep  their input order",
            ),
        ]
    )
    bad = verify_quotes(spec, graph)
    assert bad == ["OB-002"]
    assert graph.obligations[0].quote_verified is True
    assert graph.obligations[2].quote_verified is True  # normalised whitespace still matches


def test_obligations_blocked_on_an_unresolved_ambiguity_are_withheld():
    graph = ObligationGraph(
        obligations=[
            Obligation(
                id="OB-001",
                kind="MUST",
                statement="settled thing",
                quote="a settled clause",
                quote_verified=True,
            ),
            Obligation(
                id="OB-002",
                kind="MUST",
                statement="unsettled thing",
                quote="an unsettled clause",
                quote_verified=True,
                depends_on_ambiguity=["AM-001"],
            ),
        ],
        ambiguities=[{"id": "AM-001", "question": "which is it?", "options": ["a", "b"]}],  # type: ignore[list-item]
    )
    assert [o.id for o in graph.resolved_obligations()] == ["OB-001"]

    graph.ambiguities[0].resolution = "a"
    graph.ambiguities[0].resolved_by = "human"
    assert [o.id for o in graph.resolved_obligations()] == ["OB-001", "OB-002"]


# --------------------------------------------------------------------------- #
# Resumable recording
#
# A live recording run is long and can die half way -- a usage limit, a dropped
# connection.  Re-running the same command must replay what was already
# captured and pay only for the calls that were never reached, otherwise an
# interrupted recording re-buys the entire sweep.
# --------------------------------------------------------------------------- #


class _CountingProvider:
    """Provider stub that records how many live calls it actually served."""

    name = "counting"

    def __init__(self, fail_after: int | None = None) -> None:
        self.calls = 0
        self.fail_after = fail_after

    def complete(self, request: LLMRequest, *, timeout_s: float) -> LLMResponse:
        if self.fail_after is not None and self.calls >= self.fail_after:
            raise RuntimeError("simulated usage limit")
        self.calls += 1
        return LLMResponse(text=f"answer-{request.user}", model=request.model, provider=self.name)

    def close(self) -> None:  # pragma: no cover - nothing to release
        pass


def _recording_router(tmp_path: Path, provider: _CountingProvider) -> LLMRouter:
    config = RunConfig(provider="mock", record=True, cassette_dir=tmp_path, llm_retries=1)
    return LLMRouter(
        config,
        recorder=NullRecorder(),
        store=CassetteStore(tmp_path),
        provider=provider,  # type: ignore[arg-type]
    )


def test_recording_replays_an_existing_cassette_instead_of_paying_again(tmp_path: Path):
    first = _CountingProvider()
    router = _recording_router(tmp_path, first)
    router.complete(purpose="p", system="sys", user="question")
    assert first.calls == 1

    # A fresh process, same command, same prompt: nothing should be bought.
    second = _CountingProvider()
    resumed = _recording_router(tmp_path, second)
    response = resumed.complete(purpose="p", system="sys", user="question")
    assert second.calls == 0
    assert response.text == "answer-question"
    assert response.meta["replayed"] is True


def test_an_interrupted_recording_resumes_from_where_it_stopped(tmp_path: Path):
    prompts = ["a", "b", "c", "d"]

    # First attempt dies after two calls, the way a usage limit ends a run.
    dying = _CountingProvider(fail_after=2)
    router = _recording_router(tmp_path, dying)
    completed = 0
    for prompt in prompts:
        try:
            router.complete(purpose="p", system="sys", user=prompt)
        except Exception:
            break
        completed += 1
    assert completed == 2

    # Re-running the identical command buys only the remaining two.
    resumed_provider = _CountingProvider()
    resumed = _recording_router(tmp_path, resumed_provider)
    texts = [resumed.complete(purpose="p", system="sys", user=p).text for p in prompts]
    assert resumed_provider.calls == 2
    assert texts == [f"answer-{p}" for p in prompts]


def test_repeated_identical_prompts_keep_distinct_recordings(tmp_path: Path):
    """A prompt issued twice in one run must not collapse to one cassette."""
    provider = _CountingProvider()
    router = _recording_router(tmp_path, provider)
    router.complete(purpose="p", system="sys", user="same")
    router.complete(purpose="p", system="sys", user="same")
    assert provider.calls == 2
    assert len(list(tmp_path.glob("*/*.json"))) == 2


# --------------------------------------------------------------------------- #
# In-flight limit
# --------------------------------------------------------------------------- #


def test_the_inflight_limit_bounds_nested_thread_pools(tmp_path: Path):
    """The evaluation nests pools, so worker counts multiply.

    Without a cap at the router, `--concurrency 6` meant up to 36 simultaneous
    subprocesses for the CLI backend.  This asserts the ceiling holds no matter
    how many threads call in.
    """
    import threading

    from blindspot.llm.router import set_inflight_limit

    peak = 0
    live = 0
    lock = threading.Lock()

    class _Tracking:
        name = "tracking"

        def complete(self, request: LLMRequest, *, timeout_s: float) -> LLMResponse:
            nonlocal peak, live
            with lock:
                live += 1
                peak = max(peak, live)
            time.sleep(0.02)
            with lock:
                live -= 1
            return LLMResponse(text="ok", model=request.model, provider=self.name)

        def close(self) -> None:
            pass

    config = RunConfig(provider="mock", record=True, cassette_dir=tmp_path, llm_retries=1)
    router = LLMRouter(
        config,
        recorder=NullRecorder(),
        store=CassetteStore(tmp_path),
        provider=_Tracking(),  # type: ignore[arg-type]
    )
    set_inflight_limit(3)
    try:
        with ThreadPoolExecutor(max_workers=16) as pool:
            list(
                pool.map(
                    lambda i: router.complete(purpose="p", system="s", user=f"q{i}"), range(32)
                )
            )
    finally:
        set_inflight_limit(0)

    assert peak <= 3, f"in-flight ceiling breached: peak={peak}"
    assert peak > 1, "the limiter serialised everything; concurrency was lost"


def test_a_caller_supplied_nonce_separates_repeat_samples(tmp_path: Path):
    """The forge asks for several implementations of one ticket.

    Without a caller nonce those requests shared a cache key, so every variant
    after the first replayed the same recorded implementation and
    `--variants 12` silently meant four.
    """
    from pydantic import BaseModel

    class _Payload(BaseModel):
        code: str = "x = 1"

    class _Json:
        name = "json"

        def __init__(self) -> None:
            self.calls = 0

        def complete(self, request: LLMRequest, *, timeout_s: float) -> LLMResponse:
            self.calls += 1
            return LLMResponse(
                text='{"code": "x = ' + str(self.calls) + '"}',
                model=request.model,
                provider=self.name,
            )

        def close(self) -> None:
            pass

    provider = _Json()
    config = RunConfig(provider="mock", record=True, cassette_dir=tmp_path, repair_attempts=0)
    router = LLMRouter(
        config,
        recorder=NullRecorder(),
        store=CassetteStore(tmp_path),
        provider=provider,  # type: ignore[arg-type]
    )
    first = router.structured(
        purpose="forge_impl", system="s", user="same ticket", schema=_Payload, nonce=0
    )
    second = router.structured(
        purpose="forge_impl", system="s", user="same ticket", schema=_Payload, nonce=1
    )
    assert provider.calls == 2, "the second variant replayed instead of being sampled"
    assert first.code != second.code

    # ...and the same nonce still replays, so recording stays resumable.
    again = LLMRouter(
        config,
        recorder=NullRecorder(),
        store=CassetteStore(tmp_path),
        provider=provider,  # type: ignore[arg-type]
    ).structured(purpose="forge_impl", system="s", user="same ticket", schema=_Payload, nonce=0)
    assert provider.calls == 2
    assert again.code == first.code


def test_concurrent_runs_do_not_renumber_each_others_cassettes(tmp_path: Path):
    """Two runs sharing one store must not disturb each other's sequence.

    The sweep executes many runs concurrently against a single CassetteStore.
    The store used to keep one global occurrence counter and clear it at the
    start of each run, so a reset from one job silently renumbered another
    job's in-flight lookups. The symptom was a replay taking a *different path*
    from the run it was replaying -- precisely what a reproduction guarantee
    exists to exclude.
    """
    store = CassetteStore(tmp_path)
    request = _request("same prompt")
    store.record(request, LLMResponse(text="first", model="m", provider="p"))
    store.record(request, LLMResponse(text="second", model="m", provider="p"))

    fresh = CassetteStore(tmp_path)
    # Run A takes its first occurrence.
    assert fresh.take(_request("same prompt"), "run-A")[2].text == "first"
    # Run B starts independently and must also see *its* first occurrence.
    assert fresh.take(_request("same prompt"), "run-B")[2].text == "first"
    # Run A continues to its second, unaffected by B.
    assert fresh.take(_request("same prompt"), "run-A")[2].text == "second"
    assert fresh.take(_request("same prompt"), "run-B")[2].text == "second"


def test_scoped_counters_survive_parallel_access(tmp_path: Path):
    store = CassetteStore(tmp_path)
    for index in range(4):
        store.record(_request("shared"), LLMResponse(text=f"r{index}", model="m", provider="p"))

    replay = CassetteStore(tmp_path)

    def drain(scope: str) -> list[str]:
        return [replay.take(_request("shared"), scope)[2].text for _ in range(4)]

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(drain, [f"run-{i}" for i in range(8)]))

    assert all(r == ["r0", "r1", "r2", "r3"] for r in results), (
        "every run must see the full recorded sequence, in order"
    )
