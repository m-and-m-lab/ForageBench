# Copyright (c) 2022-2026, The Isaac Lab Project Developers (https://github.com/isaac-sim/IsaacLab/blob/main/CONTRIBUTORS.md).
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""ForageBench tasks. :func:`load_task` turns an episode's ``task`` block into the task object PhyGS
takes (:class:`phygs.world.task.Task`): today ``retrieve`` only."""

from __future__ import annotations

from phygs.world import NoTask, Task

from foragebench.tasks.retrieve import RetrieveTask

GOALS = ("retrieve", "none")


def load_task(block: dict) -> Task:
    """The task object for an episode's ``task`` block: ``{goal: retrieve, description, target}`` and
    optionally ``matches`` (other objects the description fits; holding one counts)."""
    if not isinstance(block, dict) or "goal" not in block:
        raise ValueError("The task block needs a goal.")
    goal = block["goal"]
    if goal not in GOALS:
        raise ValueError(f"Unknown goal {goal!r}; expected one of {GOALS}.")
    if goal == "none":
        if set(block) != {"goal"}:
            raise ValueError("A goal of none has no other fields.")
        return NoTask()
    keys = {"goal", "description", "target"}
    if not keys <= set(block) <= keys | {"matches"} or not (block["description"] and block["target"]):
        raise ValueError("A retrieve task is {goal, description, target}, all given, and optionally matches.")
    matches = block.get("matches") or []
    if not isinstance(matches, list):
        raise ValueError("A retrieve task's matches are a list of scene names.")
    return RetrieveTask(str(block["description"]), str(block["target"]), matches=tuple(map(str, matches)))
