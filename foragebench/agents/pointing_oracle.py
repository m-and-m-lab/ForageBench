# Copyright (c) 2022-2026, The Isaac Lab Project Developers (https://github.com/isaac-sim/IsaacLab/blob/main/CONTRIBUTORS.md).
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""The model harness's skills with perfect pointing: what a model could reach with them.

On the privileged track it reads where the target and the drawer handle are, projects them into the
camera images, and calls the skills a model calls (``model/skills.py``) with those pixels:
navigate_to the handle, open the drawer, navigate_to the target (on a table; in a drawer it stays
where it opened it), look at it (the sweep: it points in the first view that sees it), pick it,
stowing the arm before each walk as a model must. A point hidden behind something (the target in a
drawer) is pointed at where it is hidden. While no camera's image holds a point yet it first walks to
the composite skills' stance for it, where a model would explore until it sees it. It points at the
target's top, or at its middle when the top is seen edge-on (a box on a table at the cameras'
height). It checks that the pointing skills work physically; it is the ceiling of the skills (and of
the estimator), not of a method.

    ./isaaclab.sh -p -m foragebench run --episode dev/grid_drawer --track privileged \\
        --agent pointing_oracle --output ...
"""

from __future__ import annotations

import numpy as np
from phygs.session import AgentFailed

from foragebench.agents.model import perception
from foragebench.agents.model.skills import SKILLS, composite, with_views

CAMERAS = ("hand", "frontleft", "frontright")
VISIBLE_M = 0.05  # A point counts as seen when the depth there is within this of its distance [m].


def call(session, name: str, **args) -> None:
    status, reason = SKILLS[name].run(session, with_views(session, session.observe()), **args)
    print(f"pointing oracle: {name}{args} -> {status} {reason}", flush=True)
    if status not in ("succeeded", "done"):
        raise AgentFailed(f"{name}: {reason}")


def pixel_of(session, point, cameras=CAMERAS, occluded: bool = False) -> dict | None:
    """Where a world point is seen: {camera, u, v} in the first camera that sees it unoccluded, or
    with ``occluded`` where it would be behind what hides it (a model points there too)."""
    packet = with_views(session, session.observe())
    for camera in cameras:
        if camera not in packet.cameras or packet.cameras[camera].depth is None:
            continue
        pixel = perception.project(packet, camera, point)
        if pixel is None:
            continue
        try:
            seen = perception.world_point(packet, camera, *pixel)
        except perception.PointingError:  # No depth there: out of the camera's range.
            continue
        eye = perception.world_from_camera(packet, camera)[:3, 3]
        behind = np.linalg.norm(seen - eye) - np.linalg.norm(np.asarray(point) - eye)  # The depth's surface.
        if abs(behind) <= VISIBLE_M or (occluded and behind < VISIBLE_M):
            return dict(camera=camera, u=pixel[0], v=pixel[1])
    return None


def in_image(session, points) -> dict | None:
    """The pixel of the first of ``points`` a camera sees, else of the first hidden in a camera's image."""
    for occluded in (False, True):
        for point in points:
            seen = pixel_of(session, point, occluded=occluded)
            if seen is not None:
                return seen
    return None


def in_view(session, points, what: str, stance) -> dict:
    """A pixel of ``points`` (:func:`in_image`); while no camera's image holds one, after walking to
    ``stance`` (a composite skill's stance for them)."""
    seen = in_image(session, points)
    if seen is None:
        print(f"pointing oracle: no camera sees the {what}; walking to its stance", flush=True)
        walked = session.wait(session.navigation.navigate_to(*stance))
        if walked.status != "succeeded":
            raise AgentFailed(f"navigate_to its stance: {walked.reason}")
        seen = in_image(session, points)
    if seen is None:
        raise AgentFailed(f"no camera sees the {what}")
    return seen


def point_at(session, points, what: str) -> dict:
    """look_at one of ``points`` (from wherever it is in an image), then the pixel of the first of them
    that a view of the sweep sees, in the first view that sees it."""
    seen = in_image(session, points)
    if seen is None:
        raise AgentFailed(f"no camera sees the {what}")
    call(session, "look_at", **seen)
    views = tuple(name for name in with_views(session, session.observe()).cameras if name.startswith("view"))
    found = (pixel_of(session, point, views) for point in points)
    return next((pixel for pixel in found if pixel is not None), seen)


def run(session) -> None:
    skills = composite(session)
    call(session, "stow")
    target = session.hints.target()
    if target.inside is not None:
        part = session.hints.part(target.inside)
        handle = np.asarray(part.handle_center, dtype=float)
        call(session, "navigate_to", **in_view(session, (handle,), "drawer handle", skills.open_stance(part)))
        call(session, "open_drawer", **point_at(session, (handle,), "drawer handle"))
        call(session, "stow")
        target = session.hints.target()  # The open drawer moved it.
    center = np.asarray(target.center, dtype=float)
    spots = (center + [0.0, 0.0, float(target.size[2]) / 2], center)  # Its top, else its middle.
    if target.inside is None:
        stance = skills.reach_stances(target.center)[-1]
        call(session, "navigate_to", **in_view(session, spots, "target", stance))
    # In a drawer the robot stays where it pulled it open: the target is about as far ahead as the
    # handle was before the pull.
    seen = point_at(session, spots, "target")
    try:  # How well the pick's box from depth matches the target: a check of the skill, printed only.
        center, size = perception.object_box(with_views(session, session.observe()), **seen)
        print(
            f"pointing oracle: box from depth {np.round(center, 3).tolist()} size {np.round(size, 3).tolist()};"
            f" target {np.round(target.center, 3).tolist()} size {np.round(target.size, 3).tolist()}",
            flush=True,
        )
    except perception.PointingError:
        pass
    call(session, "pick", **seen)
    call(session, "stow")
    if not session.manipulation.holding:
        raise AgentFailed("the target dropped in the stow")
    session.finish("pointing oracle: target held, arm stowed")
