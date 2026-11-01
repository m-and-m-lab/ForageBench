# Copyright (c) 2022-2026, The Isaac Lab Project Developers (https://github.com/isaac-sim/IsaacLab/blob/main/CONTRIBUTORS.md).
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""The skills a model agent may name, each mapped onto a few session calls.

A model points: most skills take a camera and a pixel (``u`` column from the left, ``v`` row from
the top) in the images it was just shown, and :mod:`.perception` turns the pixel into a world point
with that capture's depth. Nothing here is privileged: no object names, boxes or drawer parts. The
motions are PhyGS's composite skills (``phygs.composite``: stances, picks, drawer strokes), given
the affordances the robot's cameras measured (:mod:`.perception`, the estimator) instead of what
the scene knows.

Each skill returns (status, reason): the session's own status, ``refused`` when the arguments could
not be used (a pixel without depth, a skill the track does not allow), or ``done``.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from phygs.composite import CompositeSkills
from phygs.session import AgentFailed, ArticulatedPart

from foragebench.agents.model import perception
from foragebench.agents.model.perception import PointingError

# go_to: stand this far [m] from the point (Spot reaches 0.80-1.13 m ahead of its base). Nearer, Nav2's
# fine approach took 25 moves (70 s) to a stance 0.95 m from a box on a table's far side (2026-10-30);
# pick steps the last bit itself.
STANDOFF_M = 1.05
STEP_M = 0.6  # pick: steps at most this far [m] to stand where the object is in reach.
PULL_M = 0.25  # open_drawer / close_drawer: stroke length [m], shortened to stay within reach.
HANDLE_RADIUS_M = 0.01  # A handle bar's radius [m]: the depth return is its front, the bar axis behind.
UP = np.array([0.0, 0.0, 1.0])


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
    run: Callable[..., tuple[str, str]] = field(repr=False)  # (session, seen packet, **args) -> (status, reason)


def guarded(skill: Callable[..., tuple[str, str]]) -> Callable[..., tuple[str, str]]:
    """A pixel that cannot be used is ``refused``; a routine that gives up is ``failed``."""

    def run(session, seen, **args) -> tuple[str, str]:
        try:
            return skill(session, seen, **args)
        except PointingError as error:
            return "refused", str(error)
        except AgentFailed as error:
            return "failed", str(error)

    return run


def _wait(session, command) -> tuple[str, str]:
    feedback = session.wait(command)
    return feedback.status, getattr(feedback, "reason", "") or ""


def _base_pose(seen) -> np.ndarray:
    """The base's world pose (4x4) in the observation."""
    localization = getattr(seen, "localization", None)
    if localization is None or not localization.valid:
        raise PointingError("this needs the robot's pose, which this track does not give")
    return perception.array(localization.pose.matrix).astype(float)


def _base_xy(seen) -> np.ndarray:
    return _base_pose(seen)[:2, 3]


# The composite skills per session: they keep the object a pick estimated from depth, which the
# arm's later plans (stow, look_at) carry as part of the robot while the gripper holds it.
_COMPOSITE: dict[int, CompositeSkills] = {}


def composite(session) -> CompositeSkills:
    """The session's composite skills (one per session)."""
    if id(session) not in _COMPOSITE:
        _COMPOSITE[id(session)] = CompositeSkills(session)
    return _COMPOSITE[id(session)]


def _stow_to_walk(session) -> None:
    """Stow the arm (holding or not) unless it is stowed: the base walks with the arm folded."""
    skills = composite(session)
    if not skills.stowed():
        skills.stow()


def _walk_near(session, seen, point, standoff: float, facing=None) -> tuple[str, str]:
    """Stow, then walk to ``standoff`` [m] from a world point, facing it: out along ``facing`` (the
    level outward direction of the surface there) when given, else short of it along the line from
    the base."""
    if session.navigation is None:
        return "refused", "this track has no navigation client"
    here = _base_xy(seen)
    _stow_to_walk(session)
    offset = np.asarray(point[:2], dtype=float) - here
    distance = float(np.linalg.norm(offset))
    if facing is not None:
        goal = np.asarray(point[:2], dtype=float) + np.asarray(facing[:2], dtype=float) * standoff
    else:
        goal = here if distance <= standoff else here + offset / distance * (distance - standoff)
    heading = perception.heading_to(goal, point)
    return _wait(session, session.navigation.navigate_to(float(goal[0]), float(goal[1]), heading))


def go_to(session, seen, camera: str, u: float, v: float) -> tuple[str, str]:
    """In front of a vertical surface at the pixel (a drawer front, a cabinet door), facing it;
    else (a table top, an object's top, the floor) short of the point along the line of sight."""
    point = perception.world_point(seen, camera, u, v)
    try:
        facing = perception.facing_normal(seen, camera, u, v)
    except PointingError:  # Not a vertical surface.
        facing = None
    return _walk_near(session, seen, point, STANDOFF_M, facing)


def go_near(session, seen, x: float, y: float) -> tuple[str, str]:
    return _walk_near(session, seen, (float(x), float(y)), STANDOFF_M)


def explore(session, seen, seconds: float) -> tuple[str, str]:
    if session.navigation is None:
        return "refused", "this track has no navigation client"
    _stow_to_walk(session)
    return _wait(session, session.navigation.explore(timeout=float(seconds)))


def turn(session, seen, yaw_rate: float, seconds: float) -> tuple[str, str]:
    if session.locomotion is None:
        return "refused", "this track has no locomotion client"
    return _wait(session, session.locomotion.command_velocity(0.0, 0.0, float(yaw_rate), duration=float(seconds)))


def look_at(session, seen, camera: str, u: float, v: float) -> tuple[str, str]:
    """Aim the hand camera at the pixel's world point from the composite skills' views, in turn,
    until one is reachable from where the base stands."""
    looked = composite(session).look_at(perception.world_point(seen, camera, u, v), "target")
    if looked.succeeded:
        return "succeeded", f"looking from {looked.option['distance_m']} m at {looked.option['elevation_deg']} deg"
    return "failed", f"{looked.reason}; move the base"


def _step_to_reach(session, seen, point) -> None:
    """Stand with ``point`` the composite skills' ``reach_ahead_m`` straight ahead of the base centre
    (where their picks work, on tables and in drawers): keeping the heading when it faces the point
    within 45 deg (square to an open drawer), else turning to face it. Steps at most ``STEP_M``."""
    skills = composite(session)
    pose = _base_pose(seen)
    here, forward = pose[:2, 3], pose[:2, 0] / np.linalg.norm(pose[:2, 0])
    offset = np.asarray(point[:2], dtype=float) - here
    ahead, side = float(offset @ forward), float(forward[0] * offset[1] - forward[1] * offset[0])
    reach, tolerance = skills.tuning.reach_ahead_m, skills.tuning.goal_tolerance[0] + 0.01
    if abs(ahead - reach) <= tolerance and abs(side) <= tolerance:
        return
    if ahead < np.linalg.norm(offset) * np.cos(np.radians(45.0)):
        forward = offset / np.linalg.norm(offset)
    stance = skills.reach_stances(point, facing=forward)[-1]
    if np.linalg.norm(np.asarray(stance[:2]) - here) > STEP_M:
        away = np.linalg.norm(np.asarray(stance[:2]) - here)
        raise PointingError(f"it is {away:.1f} m from where it can be reached: go_to it first")
    skills.walk(stance)


def _look_down_at(session, point) -> bool:
    """Aim the look camera at a point from the steepest of the composite skills' target views that is
    reachable (from above, a drawer's front hides less of what is inside)."""
    skills = composite(session)
    views = sorted(skills.tuning.look_views["target"], key=lambda view: -view[1])
    try:
        return skills.look_at(point, views).succeeded
    except AgentFailed:  # Failed while moving: keep the first measurement.
        return False


def pick(session, seen, camera: str, u: float, v: float) -> tuple[str, str]:
    """The composite pick on the object at the pixel as the depth measures it (a box from its top
    down to the surface it stands on): step to where it is in reach, look down at it and measure it
    again from there, then each approach (straight down first) and grasp yaw in turn, straight in,
    close, straight back out."""
    if session.manipulation.holding:
        return "refused", "the gripper already holds something"
    center, size = perception.object_box(seen, camera, u, v)
    _step_to_reach(session, seen, center)
    top = center + [0.0, 0.0, size[2] / 2]
    look = session.robot.look_camera
    if look is not None and _look_down_at(session, top):
        view = session.observe()
        try:
            pixel = perception.project(view, look, top)
            if pixel is not None:
                center, size = perception.object_box(view, look, *pixel)
        except PointingError:  # Keep the first measurement.
            pass
    composite(session).pick(center, size, look=False)
    return "succeeded", f"holding it (about {size[0]:.2f} x {size[1]:.2f} x {size[2]:.2f} m)"


def _drawer_part(seen, camera: str, u: float, v: float) -> ArticulatedPart:
    """A drawer as the cameras measure it: the handle near the pixel (the point sticking out of the
    front), the level outward direction of the front, a level bar."""
    outward = perception.facing_normal(seen, camera, u, v)
    handle = perception.protruding_point(seen, camera, u, v, outward)
    bar = np.cross(UP, outward)
    return ArticulatedPart(
        handle_center=tuple(map(float, handle - outward * HANDLE_RADIUS_M)),
        handle_axis=tuple(map(float, bar / np.linalg.norm(bar))),
        handle_length=0.1,
        handle_radius=HANDLE_RADIUS_M,
        direction=tuple(map(float, outward)),
        opening=0.0,
        limits=(0.0, 1.0),
    )


def _stroke(session, part: ArticulatedPart, kind: str) -> tuple[str, str]:
    """The composite drawer stroke on the measured drawer: stand in front of it, then pull it (open)
    or push it (close) ``PULL_M``, keeping the handle within the grip range ahead of the base."""
    if session.navigation is None:
        raise PointingError("this track has no navigation client to stand at the drawer")
    skills = composite(session)
    stroke = skills.open_drawer if kind == "open" else skills.close_drawer
    moved = stroke(part, distance=PULL_M)
    return "succeeded", f"moved the drawer {moved.measured['moved_m']:.2f} m"


def open_drawer(session, seen, camera: str, u: float, v: float) -> tuple[str, str]:
    if session.manipulation.holding:
        return "refused", "the gripper holds something: stow or put it down first"
    return _stroke(session, _drawer_part(seen, camera, u, v), "open")


def close_drawer(session, seen, camera: str, u: float, v: float) -> tuple[str, str]:
    if session.manipulation.holding:
        return "refused", "the gripper holds something: it pushes with the closed, empty gripper"
    return _stroke(session, _drawer_part(seen, camera, u, v), "close")


def stow(session, seen) -> tuple[str, str]:
    stowed = composite(session).stow()
    return "succeeded", "stowed" + (" after lifting the hand" if stowed.option["how"] != "stow" else "")


def done(session, seen) -> tuple[str, str]:
    return "done", "the agent declared it is done"


PIXEL = ("camera", "u", "v")
SKILLS: dict[str, Skill] = {
    "go_to": Skill(
        PIXEL,
        "stow the arm and walk to about 1 m from what the pixel shows, facing it (in front of it when it is"
        " a drawer front or another upright surface)",
        guarded(go_to),
    ),
    "go_near": Skill(
        ("x", "y"), "stow the arm and walk to about 1 m from a world position [m], facing it", guarded(go_near)
    ),
    "explore": Skill(("seconds",), "stow the arm and walk to unexplored space for up to [s]", guarded(explore)),
    "turn": Skill(("yaw_rate", "seconds"), "turn in place [rad/s] for this long [s]", guarded(turn)),
    "look_at": Skill(PIXEL, "point the hand camera at what the pixel shows", guarded(look_at)),
    "open_drawer": Skill(
        PIXEL,
        "step in front of the drawer whose handle is at the pixel, take the handle, pull it open",
        guarded(open_drawer),
    ),
    "close_drawer": Skill(
        PIXEL, "step in front of the drawer whose handle is at the pixel and push it shut", guarded(close_drawer)
    ),
    "pick": Skill(
        PIXEL, "step to within reach of the object at the pixel (at most 0.6 m), grasp it and lift it", guarded(pick)
    ),
    "stow": Skill((), "fold the arm (also while holding something)", guarded(stow)),
    "done": Skill((), "end the episode: the target is in the hand and the arm is stowed", done),
}
