# Copyright (c) 2022-2026, The Isaac Lab Project Developers (https://github.com/isaac-sim/IsaacLab/blob/main/CONTRIBUTORS.md).
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""The oracle: PhyGS's scripted retrieve plan on the privileged track; the benchmark's ceiling for the
skills and the noise floor of the physics. It is not a method: it reads the target's position and the
drawers' handles from the privileged hints and stands where the routines' stances say.

The routines live in PhyGS (``phygs_robot_tests.routines``); this module only chooses them. The run
command calls :func:`prepare` before the episode so the routines know the scene and the robot.
"""

from __future__ import annotations

import phygs_robot_tests.routines as routines
from phygs.session import AgentFailed
from phygs_robot_tests.routines import arm, base, drawer


def prepare(spec, robot) -> None:
    """Give the routines the scene's stances and the robot's facts (``robot.info()``)."""
    routines.use_scene(spec.scene.name)
    routines.use_robot(robot.info())


def run(session) -> None:
    """Hold the target in the gripper with the arm stowed (PhyGS's ``check_retrieve`` plan)."""
    arm.stow(session)
    target = session.hints.target()
    if target.inside is not None:
        base.go_to(session, target.inside, "open")
        arm.look_at(session, session.hints.part(target.inside).handle_center, "handle")
        drawer.open_drawer(session, target.inside)
        arm.stow(session)
        target = session.hints.target()  # The open drawer moved it.
        base.go_to(session, target.inside, "reach_in", target.center)
    else:
        base.go_to(session, target.on, "reach")
    held = arm.pick(session, target)
    arm.stow(session, held)
    if not session.manipulation.holding:
        raise AgentFailed("The target dropped in the stow.")
    session.finish("oracle: target held, arm stowed")
