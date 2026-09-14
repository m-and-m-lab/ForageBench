"""Base class for VLM orchestrators that pick the next skill from observations and a language goal."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from string import Template

from agent.interface.perception import ImageResponse
from agent.interface.skills import SKILL_ARGS, SkillCall, SkillName, SkillResult

PROMPTS_DIR = Path(__file__).parent / "prompts"


@dataclass
class OrchestratorConfig:
    model: str | None
    affordance_prior: bool = True
    """Include the receptacle affordance prior in the prompt."""
    max_new_tokens: int = 512


@dataclass
class Observation:
    images: list[ImageResponse]
    history: list[SkillResult] = field(default_factory=list)


class Orchestrator(ABC):
    def __init__(self, config: OrchestratorConfig):
        self.config = config
        self.system_prompt = ""

    def reset(self, goal: str, target_position: tuple[float, float, float] | None = None) -> None:
        """Start a new episode.

        `target_position` is given only under the known-target-location condition.
        """
        self.system_prompt = build_system_prompt(
            goal, target_position, self.config.affordance_prior
        )

    @abstractmethod
    def act(self, observation: Observation) -> SkillCall:
        """Choose the next skill to execute."""


def build_system_prompt(
    goal: str, target_position: tuple[float, float, float] | None, affordance_prior: bool
) -> str:
    skills = "\n".join(f"- {name}({', '.join(args)})" for name, args in SKILL_ARGS.items())
    if target_position is None:
        target_location = "The target's location is unknown."
    else:
        target_location = f"The target is at world coordinates {list(target_position)}."
    prior = (PROMPTS_DIR / "affordance_prior.md").read_text() if affordance_prior else ""
    return Template((PROMPTS_DIR / "system.md").read_text()).substitute(
        goal=goal, skills=skills, target_location=target_location, affordance_prior=prior
    )


def parse_skill_call(text: str) -> SkillCall:
    """Parse a model response containing a JSON object `{"skill": ..., "args": {...}}`.

    Text around the JSON object, such as a markdown code fence, is ignored. Raises ValueError if
    no valid call is found, the skill is unknown, or the arguments do not match the skill.
    """
    try:
        data = json.loads(text[text.find("{") : text.rfind("}") + 1])
        name = SkillName(data["skill"])
        args = dict(data.get("args", {}))
    except (KeyError, TypeError, ValueError) as e:
        raise ValueError(f"Could not parse a skill call from {text!r}") from e
    if set(args) != set(SKILL_ARGS[name]):
        raise ValueError(f"{name} expects arguments {SKILL_ARGS[name]}, got {tuple(args)}")
    return SkillCall(name, args)
