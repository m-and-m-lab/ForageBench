# Copyright (c) 2022-2026, The Isaac Lab Project Developers (https://github.com/isaac-sim/IsaacLab/blob/main/CONTRIBUTORS.md).
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""The skills a model agent may name, each mapped onto a few session calls.

The list is deliberately small and honest: every skill is something the session does with the
arguments the model can give from images and its own pose (world coordinates in metres), with no
privileged information. Each returns a :class:`SkillResult` with the session's own status and
reason, so the model sees why a call failed. ``done`` ends the episode.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from phygs.episodes.session import PointTarget


@dataclass(frozen=True)
class SkillResult:
    call: Any  # The SkillCall that produced it.
    status: str  # The session's status (succeeded, done, failed, ...), refused, or done for the done skill.
    reason: str = ""

    @property
    def ok(self) -> bool:
        return self.status in ("succeeded", "done")


@dataclass(frozen=True)
class Skill:
    args: tuple[str, ...]
    doc: str
    run: Callable[..., tuple[str, str]] = field(repr=False)  # (session, **args) -> (status, reason)


def _wait(session, command) -> tuple[str, str]:
    feedback = session.wait(command)
    return feedback.status, getattr(feedback, "reason", "") or ""


def navigate(session, x: float, y: float, heading: float) -> tuple[str, str]:
    if session.navigation is None:
        return "refused", "this track has no navigation client"
    return _wait(session, session.navigation.navigate_to(float(x), float(y), float(heading)))


def explore(session, seconds: float) -> tuple[str, str]:
    if session.navigation is None:
        return "refused", "this track has no navigation client"
    return _wait(session, session.navigation.explore(timeout=float(seconds)))


def turn(session, yaw_rate: float, seconds: float) -> tuple[str, str]:
    if session.locomotion is None:
        return "refused", "this track has no locomotion client"
    return _wait(session, session.locomotion.command_velocity(0.0, 0.0, float(yaw_rate), duration=float(seconds)))


def look_at(session, x: float, y: float, z: float) -> tuple[str, str]:
    target = PointTarget((float(x), float(y), float(z)))
    return _wait(session, session.manipulation.look_at(target))


def move_hand_to(session, x: float, y: float, z: float) -> tuple[str, str]:
    """The hand to a world point, pointing down (a top grasp or a handle from above)."""
    pose = (float(x), float(y), float(z), 0.0, 0.7071068, 0.0, 0.7071068)
    return _wait(session, session.manipulation.move_to_pose(pose))


def open_gripper(session) -> tuple[str, str]:
    return _wait(session, session.manipulation.open_gripper())


def close_gripper(session) -> tuple[str, str]:
    status, reason = _wait(session, session.manipulation.close_gripper())
    if status == "succeeded" and not session.manipulation.holding:
        return "failed", "the gripper closed on nothing"
    return status, reason


def stow(session) -> tuple[str, str]:
    return _wait(session, session.manipulation.stow())


def done(session) -> tuple[str, str]:
    return "done", "the agent declared it is done"


SKILLS: dict[str, Skill] = {
    "navigate": Skill(("x", "y", "heading"), "walk to a world position [m] and heading [rad]", navigate),
    "explore": Skill(("seconds",), "walk to unexplored space for up to this long [s]", explore),
    "turn": Skill(("yaw_rate", "seconds"), "turn in place [rad/s] for this long [s]", turn),
    "look_at": Skill(("x", "y", "z"), "point the hand camera at a world point [m]", look_at),
    "move_hand_to": Skill(("x", "y", "z"), "move the open hand to a world point [m], pointing down", move_hand_to),
    "open_gripper": Skill((), "open the gripper", open_gripper),
    "close_gripper": Skill((), "close the gripper; fails if it holds nothing", close_gripper),
    "stow": Skill((), "fold the arm (also while holding something)", stow),
    "done": Skill((), "end the episode: the target is in the hand and the arm is stowed", done),
}
