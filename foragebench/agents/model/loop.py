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

import numpy as np
import phygs_robot_tests.routines as routines

from foragebench.agents.model import perception
from foragebench.agents.model.orchestrator import Observation, Orchestrator, SkillCall
from foragebench.agents.model.perception import PointingError
from foragebench.agents.model.skills import SKILLS, SkillResult


@dataclass
class LoopConfig:
    max_calls: int = 40
    repeat_limit: int = 3


def observe(session) -> tuple[Observation, object, dict[str, tuple[int, tuple[int, ...]]]]:
    """What the model is shown, the packet it came from (the skills read the pixels' depth in it),
    and per camera the quarter turns that stood its image up with the image's own shape."""
    packet = session.observe()
    images, turned = {}, {}
    for name, camera in packet.cameras.items():
        rgb = getattr(camera, "rgb", None)
        if rgb is not None:
            rgb = rgb.cpu().numpy() if hasattr(rgb, "cpu") else np.asarray(rgb)
            turns = perception.upright_turns(packet, name) if getattr(camera, "extrinsics", None) else 0
            images[name] = np.ascontiguousarray(np.rot90(rgb, turns))
            turned[name] = (turns, rgb.shape)
    pose = None
    localization = getattr(packet, "localization", None)
    if localization is not None and getattr(localization, "valid", False):
        import math

        m = localization.pose.matrix
        pose = (float(m[0, 3]), float(m[1, 3]), math.atan2(float(m[1, 0]), float(m[0, 0])))
    return Observation(images=images, pose=pose), packet, turned


def pointed(orchestrator: Orchestrator, call: SkillCall, observation: Observation) -> SkillCall:
    """A call that names its target in words, with the pixel (u, v) where the model finds it in the
    named camera's (upright) image, else in the first other camera that shows it (the result's
    reason then says which); other calls as they are."""
    if "target" not in call.args:
        return call
    camera, target = call.args["camera"], str(call.args["target"])
    if camera not in observation.images:
        raise PointingError(f"no camera {camera!r}; the cameras are {sorted(observation.images)}")
    for name in [camera, *(other for other in observation.images if other != camera)]:
        point = orchestrator.point(observation.images[name], target)
        if point is not None:
            return SkillCall(call.name, {"camera": name, "u": point[0], "v": point[1]})
    raise PointingError(f"could not find {target!r} in any camera image")


def camera_pixels(call: SkillCall, turned: dict[str, tuple[int, tuple[int, ...]]]) -> SkillCall:
    """The call with its point in the camera's own pixels (the model pointed in the upright image)."""
    if "u" not in call.args or call.args.get("camera") not in turned:
        return call
    turns, shape = turned[call.args["camera"]]
    u, v = perception.raw_pixel(float(call.args["u"]), float(call.args["v"]), turns, shape)
    return SkillCall(call.name, {**call.args, "u": u, "v": v})


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
        observation, packet, turned = observe(session)
        observation.history = list(history)
        try:
            call = orchestrator.act(observation)
        except ValueError as error:  # No skill in the reply.
            history.append(SkillResult(SkillCall("(unparseable)"), "refused", str(error)))
            continue
        skill = SKILLS[call.name]
        try:
            found = pointed(orchestrator, call, observation)
            status, reason = skill.run(session, packet, **camera_pixels(found, turned).args)
            if found.args.get("camera") != call.args.get("camera"):
                reason = f"(found in {found.args['camera']!r}, not {call.args['camera']!r}) {reason}"
        except PointingError as error:  # The target was not found in any image.
            status, reason = "refused", str(error)
        except Exception as error:  # A refused or failed session call: the model is told why.
            status, reason = "refused", f"{type(error).__name__}: {error}"
        result = SkillResult(call, status, reason)
        history.append(result)
        print(f"model agent: {call.name}{call.args} -> {status} {reason}", flush=True)
        if call.name == "done":  # The skill, not a client's own "done" status (locomotion ends with it).
            break
        if len(history) >= config.repeat_limit and all(r.call == call for r in history[-config.repeat_limit :]):
            history.append(
                SkillResult(call, "refused", f"the same call {config.repeat_limit} times in a row; stopping")
            )
            break
    session.finish(f"model agent: {len(history)} skill calls, last {history[-1].status if history else 'none'}")
    return history
