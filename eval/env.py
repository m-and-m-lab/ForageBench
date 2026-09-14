"""PhyGS / IsaacLab environment for ForageBench episodes.

Import this only after the Isaac Sim app has been launched (see `run_benchmark.py`).
"""

from collections.abc import Sequence
from typing import Any

from agent.interface.perception import ImageResponse
from agent.interface.skills import SkillResult
from eval.metrics import EpisodeOutcome
from eval.termination import TerminationReason
from tasks.episode import Episode


class ForageBenchEnv:
    def __init__(self, physics_hz: int = 60, traversal_tolerance_m: float = 0.6):
        self.physics_hz = physics_hz
        self.traversal_tolerance_m = traversal_tolerance_m
        self.robot: Any = None
        """PhyGS Spot hardware-abstraction handle, passed to the skill API."""

    def reset(self, episode: Episode) -> None:
        """Load the episode's scene, spawn Spot at the start pose, and close all articulations."""
        # TODO: load scenes.registry.scene_usd_path(episode.scene_id) through PhyGS.
        raise NotImplementedError

    def observe(self) -> list[ImageResponse]:
        """Current onboard RGB-D observations."""
        raise NotImplementedError

    def check_termination(self) -> TerminationReason | None:
        """Sim-state termination: collision or leaving the house bounds.

        TODO: these must be monitored while skills execute, not only between skill calls.
        """
        raise NotImplementedError

    def evaluate(
        self, episode: Episode, results: Sequence[SkillResult], termination: TerminationReason
    ) -> EpisodeOutcome:
        """Score the finished episode from final sim state and the skill history."""
        raise NotImplementedError

    def close(self) -> None:
        pass
