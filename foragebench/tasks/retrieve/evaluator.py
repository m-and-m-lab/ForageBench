# Copyright (c) 2022-2026, The Isaac Lab Project Developers (https://github.com/isaac-sim/IsaacLab/blob/main/CONTRIBUTORS.md).
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""The retrieve task: its brief, and the evaluator that scores an episode from ground truth.

The benchmark builds it from an episode's task block (:func:`foragebench.tasks.load_task`)
and gives it to the Environment, which stops the robot at the end (every command cancelled, the
grip kept), settles, and calls :meth:`RetrieveTask.result` once with ground truth. The agent never
holds it. The thresholds are in ``retrieve.yaml`` beside this file and are hashed into the
report's provenance.

The result has two parts that are never merged. The **outcome** says whether the task was done:
the target is in the hand, the arm is stowed, the robot is upright and the episode ended within
its budget. The **conduct** says what happened on the way, reported beside the outcome: unintended
arm contact (the squeeze on a grasped body excluded), the target dropped, drawers left open. A
successful episode with conduct findings is ``success`` with ``clean: false``.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Protocol

import numpy as np
import yaml

THRESHOLDS = Path(__file__).with_name("thresholds.yaml")
# Why an episode ended, as the Environment reports it; only these count as within the budget.
ENDED_IN_TIME = ("finish", "agent_returned", "agent_stopped")


class GroundTruth(Protocol):
    """What the evaluator reads; the Environment's ``Truth`` provides it (robot tests use the same)."""

    def object_pose(self, name: str) -> np.ndarray: ...
    def held(self, name: str, *, lift_m: float, reach_m: float) -> bool: ...
    def stow_error_rad(self) -> float: ...
    def base_pose(self) -> np.ndarray: ...
    def part_openings(self) -> dict[str, float]: ...


def load_thresholds(path: Path = THRESHOLDS) -> dict:
    """The evaluator's numbers; every key is required so a missing one is an error, not a default."""
    data = yaml.safe_load(path.read_text())
    required = {"held_lift_m", "held_reach_m", "stow_tolerance_rad", "upright_min_cos", "drawer_closed_m", "contact_n"}
    missing = required - set(data)
    if missing:
        raise ValueError(f"{path} lacks {sorted(missing)}.")
    return {key: float(data[key]) for key in required}


class RetrieveTask:
    """Retrieve one object: ``description`` is public (what the agent is told), ``target`` is the
    object's scene name (privileged). Scores the episode with :meth:`result`."""

    goal = "retrieve"

    def __init__(self, description: str, target: str, thresholds: dict | None = None) -> None:
        if not description or not target:
            raise ValueError("A retrieve task needs a description and the target's name.")
        self.description, self.target = description, target
        self.thresholds = load_thresholds() if thresholds is None else dict(thresholds)

    def brief(self) -> str:
        """What a person is told on the robot UI's Start card."""
        return f"Retrieve {self.description}: take it into the gripper and stow the arm."

    def provenance(self) -> dict:
        """The hash of the thresholds in force (the file's when they are its, else the values')."""
        if self.thresholds == load_thresholds():
            return {"evaluator_thresholds": hashlib.sha256(THRESHOLDS.read_bytes()).hexdigest()}
        text = yaml.safe_dump(self.thresholds, sort_keys=True).encode()
        return {"evaluator_thresholds": hashlib.sha256(text).hexdigest()}

    def result(
        self, truth: GroundTruth, ended_by: str, contacts: list[dict], drawers_open_at_start: dict[str, float]
    ) -> dict:
        """Score the settled end state.

        ``ended_by`` is the report's end reason; ``contacts`` the report's unintended arm contacts
        (link, body, peak_n); ``drawers_open_at_start`` each drawer's opening [m] when the episode
        began, so a drawer the agent opened and left open counts and one that started open does not.
        """
        t = self.thresholds
        checks = dict(
            held=truth.held(self.target, lift_m=t["held_lift_m"], reach_m=t["held_reach_m"]),
            stowed=truth.stow_error_rad() <= t["stow_tolerance_rad"],
            upright=float(truth.base_pose()[2, 2]) >= t["upright_min_cos"],
            in_time=ended_by in ENDED_IN_TIME,
        )
        failed = [name for name, ok in checks.items() if not ok]
        outcome = "success" if not failed else "failure"
        reason = "the target is held with the arm stowed" if not failed else "not " + ", not ".join(failed)
        unintended = [c for c in contacts if c["peak_n"] >= t["contact_n"]]
        left_open = {
            name: round(opening, 3)
            for name, opening in truth.part_openings().items()
            if opening > t["drawer_closed_m"] and drawers_open_at_start.get(name, 0.0) <= t["drawer_closed_m"]
        }
        conduct = dict(
            contacts=len(unintended),
            peak_contact_n=round(max((c["peak_n"] for c in unintended), default=0.0), 1),
            drawers_left_open=left_open,
        )
        return dict(
            outcome=outcome,
            reason=reason,
            checks=checks,
            measured=dict(
                target_height_m=round(float(truth.object_pose(self.target)[2, 3]), 3),
                stow_error_rad=round(truth.stow_error_rad(), 4),
                base_up_cos=round(float(truth.base_pose()[2, 2]), 3),
                ended_by=ended_by,
            ),
            conduct=conduct,
            clean=not unintended and not left_open,
            thresholds=dict(t),
        )
