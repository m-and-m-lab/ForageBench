"""Base navigation skill."""

from typing import Any

from agent.interface.skills import SkillStatus


def navigate(robot: Any, target: str) -> SkillStatus:
    """Drive the base to `target`, a semantic reference to a room, receptacle, or object.

    Returns SUCCESS once the base reaches a collision-free pose facing the target.
    """
    # TODO: resolve target to a goal pose, plan a base path, and command the Spot HAL.
    raise NotImplementedError
