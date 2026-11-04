# Copyright (c) 2022-2026, The Isaac Lab Project Developers (https://github.com/isaac-sim/IsaacLab/blob/main/CONTRIBUTORS.md).
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""The skills a model agent may name: PhyGS's skills under their own names, with a pixel in place of
a point.

A model points: a skill that acts on something takes a camera and a pixel (``u`` column from the
left, ``v`` row from the top) in the images it was just shown, and :mod:`.perception` (the
estimator) turns the pixel into what the PhyGS skill takes: a world point, an object's box, a
drawer's part. That conversion, handing a later stow or look the box the pick measured, handing a
pick the drawer the harness opened when the object lies in it, and pushing that drawer back as far as
it was pulled, is all this module adds; the motions are PhyGS's (the session's ``navigate_to``,
``explore``, ``command_velocity``, ``look_at`` and ``stow``; the composite ``pick``, ``open_drawer``
and ``close_drawer``), and ``done`` ends the episode. Nothing here is privileged: no object names,
boxes or drawer parts.

Each skill returns (status, reason): the session's own status, ``refused`` when the arguments could
not be used (a pixel without depth, a skill the track does not allow), or ``done``.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field, replace
from typing import Any

import numpy as np
from phygs.composite import CompositeSkills
from phygs.session import AgentFailed, ArticulatedPart, PointTarget

from foragebench.agents.model import perception
from foragebench.agents.model.perception import PointingError

# navigate_to at a pixel: stand this far [m] from the point, facing it (Spot reaches 0.80-1.13 m ahead
# of its base; a pick then walks the last bit itself). Nearer, Nav2's fine approach took 25 moves
# (70 s) to a stance 0.95 m from a box on a table's far side (2026-10-30).
STANDOFF_M = 1.05
# close_drawer on a drawer the harness did not open: push length [m] (the depth shows no opening).
# open_drawer pulls as far as the arm reaches from its stance: the depth shows no slide's travel.
PUSH_M = 0.25
HANDLE_RADIUS_M = 0.01  # A handle bar's radius [m]: the depth return is its front, the bar axis behind.
UP = np.array([0.0, 0.0, 1.0])
# An object lies in the drawer the harness opened when it is at most this far behind the handle, to its
# side and from its height [m]: the house and grid drawers are 0.6 m deep, 0.5 to 1.6 m wide (the
# kitchen island's), and 0.2 to 0.4 m high.
DRAWER_DEPTH_M, DRAWER_HALF_WIDTH_M, DRAWER_HEIGHT_M = 0.6, 0.8, 0.25
# A measured handle is the opened drawer's when it is within this [m] of it in depth and height (the
# drawers above and below are 0.31 m or more away), anywhere along its width.
SAME_HANDLE_M = 0.05


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
    or_args: tuple[str, ...] = ()  # The arguments the skill takes instead, if any (navigate_to: x, y).


def guarded(skill: Callable[..., tuple[str, str]]) -> Callable[..., tuple[str, str]]:
    """A pixel that cannot be used is ``refused``; a composite skill that gives up is ``failed``."""

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
    return feedback.status, getattr(feedback, "reason", "") or getattr(feedback, "step", "") or ""


def _base_xy(seen) -> np.ndarray:
    """The base's world position [m] in the observation."""
    localization = getattr(seen, "localization", None)
    if localization is None or not localization.valid:
        raise PointingError("this needs the robot's pose, which this track does not give")
    return perception.array(localization.pose.matrix).astype(float)[:2, 3]


# The composite skills per session: they keep the object a pick estimated from depth, which the
# arm's later plans (stow) carry while the gripper holds it.
_COMPOSITE: dict[int, CompositeSkills] = {}


def composite(session) -> CompositeSkills:
    """The session's composite skills (one per session)."""
    if id(session) not in _COMPOSITE:
        _COMPOSITE[id(session)] = CompositeSkills(session)
    return _COMPOSITE[id(session)]


def _held(session):
    """The object the pick measured, while the gripper holds it (the arm's plans carry it)."""
    return composite(session).held if session.manipulation.holding else None


# The drawer each session's last open_drawer pulled, its handle where the pull left it; a close forgets it.
_OPENED: dict[int, ArticulatedPart] = {}


def _from_handle(part: ArticulatedPart, point) -> tuple[float, float, float]:
    """How far ``point`` [m] lies behind ``part``'s handle (into the drawer), to its side and above it."""
    offset = np.asarray(point, dtype=float) - np.asarray(part.handle_center, dtype=float)
    out = np.asarray(part.direction, dtype=float)[:2]
    behind = -float(offset[:2] @ out)
    return behind, float(np.linalg.norm(offset[:2] + behind * out)), float(offset[2])


def _drawer_around(session, center) -> ArticulatedPart | None:
    """The drawer the harness opened, when ``center`` [m] lies in it (``DRAWER_*``): the composite pick
    then stands square to it, and first where the body is clear of it (a costmap marks it occupied)."""
    part = _OPENED.get(id(session))
    if part is None:
        return None
    behind, side, up = _from_handle(part, center)
    inside = 0.0 <= behind <= DRAWER_DEPTH_M and side <= DRAWER_HALF_WIDTH_M and abs(up) <= DRAWER_HEIGHT_M
    return part if inside else None


def navigate_to(session, seen, camera=None, u=None, v=None, x=None, y=None) -> tuple[str, str]:
    """``navigate_to`` at a pixel: ``STANDOFF_M`` in front of a vertical surface there (a drawer
    front, a cabinet door), facing it; else (a table top, an object's top, the floor) short of the
    point along the line of sight. At a world position (x, y) [m]: there, as PhyGS's ``navigate_to``."""
    if session.navigation is None:
        return "refused", "this track has no navigation client"
    if camera is None:
        return _wait(session, session.navigation.navigate_to(float(x), float(y)))
    point = perception.world_point(seen, camera, u, v)
    here = _base_xy(seen)
    try:
        goal = point[:2] + perception.facing_normal(seen, camera, u, v)[:2] * STANDOFF_M
    except PointingError:  # Not a vertical surface.
        offset = point[:2] - here
        distance = float(np.linalg.norm(offset))
        goal = here if distance <= STANDOFF_M else here + offset / distance * (distance - STANDOFF_M)
    heading = perception.heading_to(goal, point)
    return _wait(session, session.navigation.navigate_to(float(goal[0]), float(goal[1]), heading))


def explore(session, seen, timeout: float) -> tuple[str, str]:
    if session.navigation is None:
        return "refused", "this track has no navigation client"
    return _wait(session, session.navigation.explore(timeout=float(timeout)))


def command_velocity(session, seen, v_x: float, v_y: float, v_rot: float, duration: float) -> tuple[str, str]:
    if session.locomotion is None:
        return "refused", "this track has no locomotion client"
    command = session.locomotion.command_velocity(float(v_x), float(v_y), float(v_rot), duration=float(duration))
    return _wait(session, command)


def look_at(session, seen, camera: str, u: float, v: float) -> tuple[str, str]:
    """``look_at`` the pixel's world point, from look_at's own views."""
    point = PointTarget(tuple(map(float, perception.world_point(seen, camera, u, v))))
    return _wait(session, session.manipulation.look_at(point, held=_held(session)))


def pick(session, seen, camera: str, u: float, v: float) -> tuple[str, str]:
    """The composite pick on the object at the pixel as the depth measures it (a box from its top
    down to the surface it stands on): it walks to where the arm reaches it, looks at it, then tries
    each approach and grasp yaw in turn."""
    if session.manipulation.holding:
        return "refused", "the gripper already holds something"
    center, size = perception.object_box(seen, camera, u, v)
    composite(session).pick(center, size, part=_drawer_around(session, center))
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
    """The composite drawer stroke on the measured drawer: it stands in front of it, then pulls it as
    far as the arm reaches from there (open, as the oracle's), or pushes it (close) back as far as the
    harness pulled it when it is the drawer the harness opened, else ``PUSH_M``."""
    if session.navigation is None:
        raise PointingError("this track has no navigation client to stand at the drawer")
    skills, opened = composite(session), _OPENED.pop(id(session), None)
    if kind == "open":
        moved = skills.open_drawer(part).measured["moved_m"]
        handle = np.asarray(part.handle_center) + np.asarray(part.direction) * moved
        _OPENED[id(session)] = replace(part, handle_center=tuple(map(float, handle)), opening=float(moved))
    elif opened is not None and _same_handle(opened, part):
        moved = skills.close_drawer(replace(part, opening=opened.opening)).measured["moved_m"]
    else:
        moved = skills.close_drawer(part, distance=PUSH_M).measured["moved_m"]
    return "succeeded", f"moved the drawer {moved:.2f} m"


def _same_handle(opened: ArticulatedPart, part: ArticulatedPart) -> bool:
    """Whether ``part``'s measured handle is the handle of the drawer the harness ``opened``."""
    behind, side, up = _from_handle(opened, part.handle_center)
    return abs(behind) <= SAME_HANDLE_M and side <= DRAWER_HALF_WIDTH_M and abs(up) <= SAME_HANDLE_M


def open_drawer(session, seen, camera: str, u: float, v: float) -> tuple[str, str]:
    if session.manipulation.holding:
        return "refused", "the gripper holds something: stow or put it down first"
    return _stroke(session, _drawer_part(seen, camera, u, v), "open")


def close_drawer(session, seen, camera: str, u: float, v: float) -> tuple[str, str]:
    if session.manipulation.holding:
        return "refused", "the gripper holds something: it pushes with the closed, empty gripper"
    return _stroke(session, _drawer_part(seen, camera, u, v), "close")


def stow(session, seen) -> tuple[str, str]:
    """``stow``, carrying the object the pick measured while the gripper holds it."""
    return _wait(session, session.manipulation.stow(held=_held(session)))


def done(session, seen) -> tuple[str, str]:
    return "done", "the agent declared it is done"


PIXEL = ("camera", "u", "v")
SKILLS: dict[str, Skill] = {
    "navigate_to": Skill(
        PIXEL,
        "walk to about 1 m from what the pixel shows, facing it (in front of it when it is a drawer front"
        " or another upright surface); or, given x and y, to that world position [m]. The arm must be"
        " stowed",
        guarded(navigate_to),
        or_args=("x", "y"),
    ),
    "explore": Skill(
        ("timeout",), "walk to unexplored space for up to timeout [s]; the arm must be stowed", guarded(explore)
    ),
    "command_velocity": Skill(
        ("v_x", "v_y", "v_rot", "duration"),
        "walk at a body velocity [m/s, m/s, rad/s] for duration [s] (0, 0, v_rot turns in place; all 0 stops)",
        guarded(command_velocity),
    ),
    "look_at": Skill(PIXEL, "point the hand camera at what the pixel shows", guarded(look_at)),
    "open_drawer": Skill(
        PIXEL,
        "step in front of the drawer whose handle is at the pixel, take the handle, pull it open, fold the arm",
        guarded(open_drawer),
    ),
    "close_drawer": Skill(
        PIXEL,
        "step in front of the drawer whose handle is at the pixel, push it shut, fold the arm",
        guarded(close_drawer),
    ),
    "pick": Skill(PIXEL, "walk to within reach of the object at the pixel, grasp it and lift it", guarded(pick)),
    "stow": Skill((), "fold the arm (also while holding something)", guarded(stow)),
    "done": Skill((), "end the episode: the target is in the hand and the arm is stowed", done),
}
