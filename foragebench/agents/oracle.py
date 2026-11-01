# Copyright (c) 2022-2026, The Isaac Lab Project Developers (https://github.com/isaac-sim/IsaacLab/blob/main/CONTRIBUTORS.md).
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""The oracle: the retrieve plan on the privileged track with PhyGS's composite skills; the
benchmark's motion ceiling (the skills on true affordances) and the noise floor of the physics. It
is not a method: it reads the target's box and the drawers' parts from the privileged hints, and
the skills compute where to stand from them.
"""

from __future__ import annotations

from phygs.composite import CompositeSkills
from phygs.session import AgentFailed


def run(session) -> None:
    """Hold the target in the gripper with the arm stowed (PhyGS's ``check_retrieve`` plan)."""
    skills = CompositeSkills(session)
    target, part = session.hints.target(), None
    if target.inside is not None:
        skills.open_drawer(session.hints.part(target.inside))
        target = session.hints.target()  # The open drawer moved it.
        part = session.hints.part(target.inside)
    skills.pick(target.center, target.size, name=target.name, part=part)
    stowed = session.wait(session.manipulation.stow(held=skills.held))
    if stowed.status != "succeeded":
        raise AgentFailed(f"stow: {stowed.reason}")
    if not session.manipulation.holding:
        raise AgentFailed("The target dropped in the stow.")
    session.finish("oracle: target held, arm stowed")
