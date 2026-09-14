"""Door and drawer skills.

Handle grasps come from AO-Grasp (`third_party/ao-grasp`), and arm motion is planned with cuRobo
(`third_party/curobo`). Cabinets, ovens, and dishwashers are opened with the door skills.
"""

from typing import Any

from agent.interface.skills import SkillStatus


def open_door(robot: Any, reference: str) -> SkillStatus:
    """Grasp the handle of the hinged articulation `reference` and swing it open."""
    raise NotImplementedError


def close_door(robot: Any, reference: str) -> SkillStatus:
    """Push the hinged articulation `reference` closed."""
    raise NotImplementedError


def open_drawer(robot: Any, reference: str) -> SkillStatus:
    """Grasp the handle of drawer `reference` and pull it open."""
    raise NotImplementedError


def close_drawer(robot: Any, reference: str) -> SkillStatus:
    """Push drawer `reference` closed."""
    raise NotImplementedError
