# Copyright (c) 2022-2026, The Isaac Lab Project Developers (https://github.com/isaac-sim/IsaacLab/blob/main/CONTRIBUTORS.md).
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""Orchestrators: a model picks the next skill from the cameras, the brief and the history.

Carried over from the May beta (prompt template, argument-checked skill calls) and re-targeted at
PhyGS's session: a skill here is one of :mod:`.skills`, each a few session calls. The orchestrator
never touches the session itself; :mod:`.loop` runs it.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from string import Template
from typing import Any

from foragebench.agents.model.skills import SKILLS, SkillResult

PROMPTS = Path(__file__).resolve().parent / "prompts"


@dataclass(frozen=True)
class SkillCall:
    """One chosen skill with its arguments, as the model named them."""

    name: str
    args: dict[str, Any] = field(default_factory=dict)


@dataclass
class OrchestratorConfig:
    model: str | None = None
    affordance_prior: bool = True  # Add the prior on where household objects are kept to the prompt.
    max_new_tokens: int = 512
    history: int = 8  # How many past results the model sees.


@dataclass
class Observation:
    """What the model is shown each turn: images by camera name (HxWx3 uint8), the robot's planar
    pose (x, y, heading) when the track grants it, and the latest skill results."""

    images: dict[str, Any]
    pose: tuple[float, float, float] | None
    history: list[SkillResult] = field(default_factory=list)


class Orchestrator(ABC):
    """Picks the next skill; subclasses talk to a model."""

    def __init__(self, config: OrchestratorConfig | None = None) -> None:
        self.config = config or OrchestratorConfig()
        self.system_prompt = ""

    def reset(self, brief: str, target_position: tuple[float, float, float] | None = None) -> None:
        """Start an episode: ``brief`` is the task's public description; ``target_position`` is
        given only on a track that grants the target's position."""
        self.system_prompt = build_system_prompt(brief, target_position, self.config.affordance_prior)

    @abstractmethod
    def act(self, observation: Observation) -> SkillCall:
        """Choose the next skill."""


def skill_list() -> str:
    return "\n".join(f"- {name}({', '.join(skill.args)}): {skill.doc}" for name, skill in SKILLS.items())


def build_system_prompt(brief: str, target_position: tuple[float, float, float] | None, affordance_prior: bool) -> str:
    location = (
        "The target's location is unknown."
        if target_position is None
        else f"The target is at world coordinates {[round(v, 3) for v in target_position]}."
    )
    prior = (PROMPTS / "affordance_prior.md").read_text() if affordance_prior else ""
    return Template((PROMPTS / "system.md").read_text()).substitute(
        goal=brief, skills=skill_list(), target_location=location, affordance_prior=prior
    )


def parse_skill_call(text: str) -> SkillCall:
    """The JSON object ``{"skill": ..., "args": {...}}`` in a model reply (fences and prose around it
    are ignored). Raises ``ValueError`` when there is none, the skill is unknown, or the arguments
    do not match the skill's."""
    try:
        data = json.loads(text[text.find("{") : text.rfind("}") + 1])
        name = str(data["skill"])
        args = dict(data.get("args") or {})
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(f"Could not parse a skill call from {text!r}") from error
    if name not in SKILLS:
        raise ValueError(f"Unknown skill {name!r}; the skills are {sorted(SKILLS)}")
    expected = tuple(SKILLS[name].args)
    if tuple(sorted(args)) != tuple(sorted(expected)):
        raise ValueError(f"{name} expects arguments {expected}, got {tuple(args)}")
    return SkillCall(name, args)


def history_text(history: list[SkillResult], limit: int) -> str:
    """The last ``limit`` results as lines the model can read."""
    return "\n".join(f"{r.call.name}({r.call.args}) -> {r.status}: {r.reason}" for r in history[-limit:]) or "(none)"
