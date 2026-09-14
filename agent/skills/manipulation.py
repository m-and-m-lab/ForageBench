"""Object manipulation skills: grasping, placing, and reporting the target."""

from typing import Any

from agent.interface.skills import SkillStatus


def grasp(robot: Any, obj: str) -> SkillStatus:
    """Pick up `obj` using Contact-GraspNet grasp candidates and cuRobo arm planning.

    The paper's orchestrator skill set has no standalone pick, but IOSS requires a successful pick
    before `report_found`, and tier 4 requires moving occluders.
    TODO: reconcile with the subskills defined in the paper supplement.
    """
    raise NotImplementedError


def place(robot: Any, receptacle: str) -> SkillStatus:
    """Place the held object on or in `receptacle`."""
    raise NotImplementedError


def report_found(robot: Any, object: str) -> SkillStatus:
    """Signal that `object` has been found and retrieved. Ends the episode.

    The evaluator checks `object` against the episode target; reporting the wrong object fails
    the episode.
    """
    return SkillStatus.SUCCESS
