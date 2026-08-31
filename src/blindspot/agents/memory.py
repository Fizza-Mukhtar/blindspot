"""Cross-case memory: a taxonomy of specification-violation archetypes.

What it is
----------
A small, human-readable YAML file of *defect archetypes* -- recurring shapes of
"the specification says X, implementations do Y" -- each with the obligation
kinds it applies to, trigger keywords, and a probe recipe describing the shape
of test that catches it.

Why it is not leakage
---------------------
This is the part of an agent memory that is easiest to get wrong in a
benchmark, so the rule is strict and mechanical:

* archetypes may be learned **only** from the ``dev`` split;
* an archetype records a *generic pattern*, never a task id, a case id, a
  witness input, or an expected value;
* ``blindspot learn`` refuses to run on the test split, and ``make verify-memory``
  asserts that no archetype text matches any test-split task id.

The archetypes are committed, so what the agent "remembers" is auditable in a
diff rather than hidden in a vector store.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from ..config import MEMORY_PATH
from ..types import Obligation


@dataclass(frozen=True)
class Archetype:
    id: str
    name: str
    applies_to: list[str]  # ObligationKind values
    triggers: list[str]  # lowercase keywords matched against the clause
    pattern: str  # what implementations get wrong
    probe_recipe: str  # the shape of test that catches it
    learned_from: str = "dev"

    def matches(self, obligation: Obligation) -> int:
        """Relevance score for this obligation; 0 means not applicable."""
        if self.applies_to and obligation.kind.value not in self.applies_to:
            return 0
        haystack = f"{obligation.statement} {obligation.quote}".lower()
        hits = sum(1 for trigger in self.triggers if trigger in haystack)
        if hits == 0:
            return 0
        bonus = 1 if obligation.risk.value == "high" else 0
        return hits + bonus


class ArchetypeMemory:
    def __init__(self, archetypes: list[Archetype]) -> None:
        self.archetypes = archetypes

    @classmethod
    def load(cls, path: Path = MEMORY_PATH) -> ArchetypeMemory:
        if not path.is_file():
            return cls([])
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return cls([Archetype(**item) for item in raw.get("archetypes", [])])

    def save(self, path: Path = MEMORY_PATH) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "archetypes": [
                {
                    "id": a.id,
                    "name": a.name,
                    "applies_to": a.applies_to,
                    "triggers": a.triggers,
                    "pattern": a.pattern,
                    "probe_recipe": a.probe_recipe,
                    "learned_from": a.learned_from,
                }
                for a in sorted(self.archetypes, key=lambda a: a.id)
            ]
        }
        path.write_text(
            yaml.safe_dump(payload, sort_keys=False, allow_unicode=True, width=100),
            encoding="utf-8",
        )
        return path

    def retrieve(self, obligation: Obligation, *, top_k: int = 3) -> list[Archetype]:
        scored = [(a.matches(obligation), a) for a in self.archetypes]
        ranked = sorted(
            ((score, a) for score, a in scored if score > 0),
            key=lambda pair: (-pair[0], pair[1].id),
        )
        return [a for _, a in ranked[:top_k]]

    def render_for(self, obligation: Obligation, *, top_k: int = 3) -> str:
        hits = self.retrieve(obligation, top_k=top_k)
        if not hits:
            return ""
        lines = [
            "# Recurring failure patterns for obligations of this shape",
            "",
            "These come from a taxonomy built on a separate development split. They are",
            "hypotheses to test, not facts about this implementation. Ignore any that do",
            "not fit the clause.",
            "",
        ]
        for a in hits:
            lines.append(f"- **{a.name}** ({a.id}): {a.pattern}")
            lines.append(f"  Probe shape: {a.probe_recipe}")
        return "\n".join(lines)

    def leakage_report(self, forbidden_tokens: list[str]) -> list[str]:
        """Ids of archetypes whose text mentions a forbidden (test-split) token."""
        offenders: list[str] = []
        for a in self.archetypes:
            blob = " ".join([a.name, a.pattern, a.probe_recipe, " ".join(a.triggers)]).lower()
            for token in forbidden_tokens:
                needle = token.lower().replace("_", " ")
                if re.search(rf"\b{re.escape(token.lower())}\b", blob) or needle in blob:
                    offenders.append(a.id)
                    break
        return sorted(set(offenders))
