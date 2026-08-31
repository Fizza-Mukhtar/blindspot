"""Build the archetype taxonomy from the development split.

What is actually learned
------------------------
Not "task X has bug Y".  The input is the set of *observed* forge outcomes on
dev-split tasks -- real implementations a model wrote, and the concrete inputs
on which they diverged from the reference -- and the output is a generalisation:
a named failure shape, the kinds of obligation it applies to, the words in a
clause that predict it, and the shape of test that catches it.

The contract is enforced, not merely intended:

* only dev-split cases are read;
* the generaliser is explicitly forbidden from naming a task, a function, a
  domain or a literal value, and its output is checked against the test-split
  task ids afterwards (``blindspot learn`` exits non-zero on a match);
* the result is a committed YAML file, so what the agent "remembers" shows up
  in a diff instead of hiding in an opaque store.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from ..corpus import Task, load_cases
from ..llm.router import LLMRouter
from ..prompts import load as load_prompt
from ..trace.recorder import TrajectoryRecorder
from .memory import Archetype, ArchetypeMemory


class _ArchetypeSpec(BaseModel):
    id: str
    name: str
    applies_to: list[str] = Field(default_factory=list)
    triggers: list[str] = Field(default_factory=list)
    pattern: str
    probe_recipe: str


class _LearnPayload(BaseModel):
    archetypes: list[_ArchetypeSpec] = Field(default_factory=list)


def learn_archetypes(
    dev_tasks: list[Task],
    *,
    router: LLMRouter,
    recorder: TrajectoryRecorder,
) -> ArchetypeMemory:
    recorder.stage_start("learn", f"{len(dev_tasks)} dev task(s)")
    dev_ids = {t.task_id for t in dev_tasks}
    observations: list[str] = []

    for case in load_cases(defective_only=True):
        if case.meta.task_id not in dev_ids:
            continue
        observations.append(
            "\n".join(
                [
                    "## An observed divergence",
                    f"- obligation shape: {case.task.trap_class or 'unclassified'}",
                    f"- what the specification required: {case.task.trap}",
                    f"- why implementations miss it: {case.task.why_models_miss_it}",
                    f"- the input that exposed it: {case.meta.witness_input}",
                    f"- observed difference: {case.meta.notes}",
                    "- the implementation's own test suite was green on this code",
                ]
            )
        )

    if not observations:
        # Falling back to the declared traps of the dev tasks keeps `learn`
        # useful before any forging has happened, and is recorded as such.
        for task in dev_tasks:
            observations.append(
                "\n".join(
                    [
                        "## A declared trap (no forged case yet)",
                        f"- obligation shape: {task.trap_class}",
                        f"- what the specification required: {task.trap}",
                        f"- why implementations miss it: {task.why_models_miss_it}",
                    ]
                )
            )
        recorder.note("no forged dev cases available; generalising from declared dev traps")

    payload = router.structured(
        purpose="learn",
        system=load_prompt("learn"),
        user="# Observations from the development split\n\n" + "\n\n".join(observations),
        schema=_LearnPayload,
        role="smart",
        max_tokens=6000,
    )

    archetypes = [
        Archetype(
            id=spec.id,
            name=spec.name,
            applies_to=spec.applies_to,
            triggers=[t.lower() for t in spec.triggers],
            pattern=spec.pattern,
            probe_recipe=spec.probe_recipe,
            learned_from="dev",
        )
        for spec in payload.archetypes
    ]
    recorder.stage_end("learn", {"archetypes": len(archetypes)})
    return ArchetypeMemory(archetypes)
