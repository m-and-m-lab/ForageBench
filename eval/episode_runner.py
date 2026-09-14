"""Runs one ForageBench episode: orchestrator → skill → termination check, until the episode ends."""

from dataclasses import dataclass

from agent.interface.skills import SkillAPI, SkillCall, SkillResult
from agent.orchestrators.base import Observation, Orchestrator
from eval.env import ForageBenchEnv
from eval.metrics import EpisodeOutcome
from eval.termination import TerminationReason, check_skill_termination
from tasks.episode import Episode


@dataclass
class RunnerConfig:
    known_target_location: bool = False
    max_repeated_skill: int = 3
    max_steps: int | None = None


def run_episode(
    env: ForageBenchEnv,
    orchestrator: Orchestrator,
    skills: SkillAPI,
    episode: Episode,
    config: RunnerConfig,
) -> EpisodeOutcome:
    env.reset(episode)
    orchestrator.reset(
        goal=episode.target.description,
        target_position=episode.target.position if config.known_target_location else None,
    )

    calls: list[SkillCall] = []
    results: list[SkillResult] = []
    termination: TerminationReason | None = None
    while termination is None:
        if config.max_steps is not None and len(calls) >= config.max_steps:
            termination = TerminationReason.STEP_BUDGET
            break
        # TODO: decide how an unparseable orchestrator reply is scored (incompatible skill?).
        call = orchestrator.act(Observation(images=env.observe(), history=list(results)))
        result = skills.execute(call)
        calls.append(call)
        results.append(result)
        termination = (
            check_skill_termination(
                result, calls, episode.target.prim_path, config.max_repeated_skill
            )
            or env.check_termination()
        )

    return env.evaluate(episode, results, termination)
