# Copyright (c) 2022-2026, The Isaac Lab Project Developers (https://github.com/isaac-sim/IsaacLab/blob/main/CONTRIBUTORS.md).
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""The orchestrator loop: observe, ask the model for a skill, run it through the session, repeat.

Stops when the model says ``done``, when it has used its call budget, or when it repeats the same
call ``repeat_limit`` times in a row (the May beta's guard: a stuck model wastes the budget). An
unparseable reply counts as a call and is reported back to the model as a refused skill. The
episode's outcome is still the evaluator's, from ground truth; nothing here decides success.
"""

from __future__ import annotations

from dataclasses import dataclass

import phygs_robot_tests.routines as routines

from foragebench.agents.model.orchestrator import Observation, Orchestrator, SkillCall
from foragebench.agents.model.skills import SKILLS, SkillResult


@dataclass
class LoopConfig:
    max_calls: int = 40
    repeat_limit: int = 3


def observe(session) -> tuple[Observation, object]:
    """What the model is shown, and the packet it came from (the skills read the pixels' depth in it)."""
    packet = session.observe()
    images = {}
    for name, camera in packet.cameras.items():
        rgb = getattr(camera, "rgb", None)
        if rgb is not None:
            images[name] = rgb.cpu().numpy() if hasattr(rgb, "cpu") else rgb
    pose = None
    localization = getattr(packet, "localization", None)
    if localization is not None and getattr(localization, "valid", False):
        import math

        m = localization.pose.matrix
        pose = (float(m[0, 3]), float(m[1, 3]), math.atan2(float(m[1, 0]), float(m[0, 0])))
    return Observation(images=images, pose=pose), packet


def run_loop(session, orchestrator: Orchestrator, config: LoopConfig | None = None) -> list[SkillResult]:
    """Drive ``session`` with ``orchestrator`` until done or stopped; returns the skill results."""
    config = config or LoopConfig()
    target = None
    if "object_targets" in session.grants:  # The known-target condition: a track grants it.
        hint = session.hints.target()
        target = tuple(float(v) for v in hint.center)
    routines.use_robot(session.robot)  # The skills' motions read the robot's tools and arm.
    orchestrator.reset(session.task.description, target)
    history: list[SkillResult] = []
    for _ in range(config.max_calls):
        observation, packet = observe(session)
        observation.history = list(history)
        try:
            call = orchestrator.act(observation)
        except ValueError as error:  # No skill in the reply.
            history.append(SkillResult(SkillCall("(unparseable)"), "refused", str(error)))
            continue
        skill = SKILLS[call.name]
        try:
            status, reason = skill.run(session, packet, **call.args)
        except Exception as error:  # A refused or failed session call: the model is told why.
            status, reason = "refused", f"{type(error).__name__}: {error}"
        result = SkillResult(call, status, reason)
        history.append(result)
        if call.name == "done":  # The skill, not a client's own "done" status (locomotion ends with it).
            break
        if len(history) >= config.repeat_limit and all(r.call == call for r in history[-config.repeat_limit :]):
            history.append(
                SkillResult(call, "refused", f"the same call {config.repeat_limit} times in a row; stopping")
            )
            break
    session.finish(f"model agent: {len(history)} skill calls, last {history[-1].status if history else 'none'}")
    return history
