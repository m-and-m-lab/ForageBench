"""Episode definitions for ForageBench.

ForageBench has 25 scenes with four episodes each, one per difficulty tier.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path

import yaml

EPISODES_DIR = Path(__file__).parent / "episodes"


class DifficultyTier(IntEnum):
    """Episode difficulty, from easiest to hardest."""

    SEPARATE_ROOM_VISIBLE = 1
    """Target is visible in another room; doors must be opened but receptacles need not be."""
    SAME_ROOM_NOT_PERCEIVABLE = 2
    """Target is inside a receptacle in the starting room."""
    SEPARATE_ROOM_NOT_PERCEIVABLE = 3
    """Target is inside a receptacle in another room."""
    SEPARATE_ROOM_OCCLUDED = 4
    """As tier 3, and non-target objects occluding the target must be moved."""


@dataclass(frozen=True)
class Pose:
    position: tuple[float, float, float]
    yaw: float = 0.0


@dataclass(frozen=True)
class Target:
    description: str
    """Natural-language goal given to the agent, e.g. "a ceramic mug"."""
    prim_path: str
    """USD prim of the target. Each manipuland is unique within its scene."""
    position: tuple[float, float, float]


@dataclass(frozen=True)
class Interaction:
    """A manipulation required on the optimal solution, e.g. opening a door or drawer."""

    skill: str
    reference: str


@dataclass(frozen=True)
class Episode:
    episode_id: str
    scene_id: str
    tier: DifficultyTier
    target: Target
    start_pose: Pose
    required_interactions: tuple[Interaction, ...] = ()
    optimal_path_length: float | None = None

    @classmethod
    def from_dict(cls, data: dict) -> Episode:
        return cls(
            episode_id=data["episode_id"],
            scene_id=data["scene_id"],
            tier=DifficultyTier(data["tier"]),
            target=Target(
                description=data["target"]["description"],
                prim_path=data["target"]["prim_path"],
                position=tuple(data["target"]["position"]),
            ),
            start_pose=Pose(
                position=tuple(data["start_pose"]["position"]),
                yaw=data["start_pose"].get("yaw", 0.0),
            ),
            required_interactions=tuple(
                Interaction(**i) for i in data.get("required_interactions", [])
            ),
            optimal_path_length=data.get("optimal_path_length"),
        )


def load_episode(path: Path) -> Episode:
    return Episode.from_dict(yaml.safe_load(Path(path).read_text()))


def load_episodes(directory: Path = EPISODES_DIR) -> list[Episode]:
    """Load every episode YAML in `directory`, sorted by filename."""
    return [load_episode(p) for p in sorted(Path(directory).glob("*.yaml"))]
