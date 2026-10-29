# Copyright (c) 2022-2026, The Isaac Lab Project Developers (https://github.com/isaac-sim/IsaacLab/blob/main/CONTRIBUTORS.md).
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""The retrieve task: its brief, and the evaluator that scores an episode from ground truth.

The benchmark builds it from an episode's task block and answer (:func:`foragebench.tasks.load_task`)
and gives it to PhyGS's World, which calls :meth:`RetrieveTask.reset` on the settled world before the
agent starts, :meth:`RetrieveTask.update` every ``evaluation_period_seconds`` while the agent runs,
and :meth:`RetrieveTask.result` once after the robot has stopped (every command cancelled, the grip
kept) and settled. The agent never holds it. The thresholds are in ``thresholds.yaml`` beside this
file, with a version every result names; the file is hashed into the report's provenance.

The result has parts that are never merged:

- **outcome**: the target is held (lifted, at the wrist, every jaw pressing on it), the arm is
  stowed, the robot is upright and the episode ended within its budget.
- **reached**: the base ended near the target, or holds it.
- **progress**: how far the run got, from the samples: reached, opened (the drawer the target started
  in), touched, lifted, held. It says where an agent failed.
- **conduct**: what happened on the way, beside the outcome: unintended arm contact (the squeeze on a
  grasped body excluded), drawers left open, other objects moved. A successful episode with conduct
  findings is ``success`` with ``clean: false``.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Protocol

import numpy as np
import yaml

THRESHOLDS = Path(__file__).with_name("thresholds.yaml")
REQUIRED = (
    "held_lift_m",
    "held_reach_m",
    "jaw_contact_n",
    "stow_tolerance_rad",
    "upright_min_cos",
    "near_target_m",
    "opened_m",
    "drawer_closed_m",
    "contact_n",
    "moved_m",
)
# Why an episode ended, as the World reports it; only these count as within the budget.
ENDED_IN_TIME = ("finish", "agent_returned", "agent_stopped")
STAGES = ("reached", "opened", "touched", "lifted", "held")  # Progress, in the order a run gets there.


class GroundTruth(Protocol):
    """What the evaluator reads; PhyGS's ``Truth`` provides it."""

    def object_pose(self, name: str) -> np.ndarray: ...
    def held(self, name: str, *, lift_m: float, reach_m: float) -> bool: ...
    def pinched(self, name: str, threshold_n: float) -> bool: ...
    def arm_contacts(self, threshold_n: float) -> list[tuple[str, str, float]]: ...
    def started_inside(self, name: str) -> str | None: ...
    def body_motion(self) -> dict[str, tuple[float, float]]: ...
    def stow_error_rad(self) -> float: ...
    def base_pose(self) -> np.ndarray: ...
    def part(self, name: str): ...  # An articulated part now; its ``opening`` [m].
    def part_openings(self) -> dict[str, float]: ...


def load_thresholds(path: Path = THRESHOLDS) -> dict:
    """The evaluator's numbers; every key is required so a missing one is an error, not a default."""
    data = yaml.safe_load(path.read_text())
    missing = set(REQUIRED) - set(data)
    if missing:
        raise ValueError(f"{path} lacks {sorted(missing)}.")
    return {key: float(data[key]) for key in REQUIRED}


def rules_version(path: Path = THRESHOLDS) -> int:
    """The thresholds file's ``version``: raised whenever a number changes."""
    version = yaml.safe_load(path.read_text()).get("version")
    if not isinstance(version, int):
        raise ValueError(f"{path} needs an integer version.")
    return version


class RetrieveTask:
    """Retrieve one object: ``description`` is public (what the agent is told), ``target`` is the
    object's scene name (the episode's hidden answer)."""

    goal = "retrieve"

    def __init__(self, description: str, target: str, thresholds: dict | None = None) -> None:
        if not description or not target:
            raise ValueError("A retrieve task needs a description and the target's name.")
        self.description, self.target = description, target
        self.thresholds = load_thresholds() if thresholds is None else dict(thresholds)
        # The file's rules carry its version; other numbers (a test's) have none.
        self.rules_version = rules_version() if self.thresholds == load_thresholds() else None
        self._start: dict | None = None

    def brief(self) -> str:
        """What a person is told on the robot UI's Start card."""
        return f"Retrieve {self.description}: take it into the gripper and stow the arm."

    def provenance(self) -> dict:
        """The hash of the thresholds in force (the file's when they are its, else the values')."""
        if self.rules_version is not None:
            return {"evaluator_thresholds": hashlib.sha256(THRESHOLDS.read_bytes()).hexdigest()}
        text = yaml.safe_dump(self.thresholds, sort_keys=True).encode()
        return {"evaluator_thresholds": hashlib.sha256(text).hexdigest()}

    def reset(self, truth: GroundTruth) -> None:
        """The settled world before the agent starts: drawer openings, where the target and the
        other bodies are, the drawer the target is in, the base's position."""
        self._start = dict(
            openings=truth.part_openings(),
            motion=truth.body_motion(),
            target_z=float(truth.object_pose(self.target)[2, 3]),
            hidden_in=truth.started_inside(self.target),
        )
        self._last_xy = truth.base_pose()[:2, 3].copy()
        self._path_m = 0.0
        self._progress = dict.fromkeys(("reached", "opened", "touched", "lifted"), False)

    def update(self, truth: GroundTruth) -> None:
        """One sample while the agent runs: the base's path, and each progress stage seen so far."""
        t, progress = self.thresholds, self._progress
        xy = truth.base_pose()[:2, 3]
        self._path_m += float(np.linalg.norm(xy - self._last_xy))
        self._last_xy = xy.copy()
        target = truth.object_pose(self.target)[:3, 3]
        progress["reached"] |= float(np.linalg.norm(target[:2] - xy)) <= t["near_target_m"]
        hidden_in = self._start["hidden_in"]
        if hidden_in is not None:
            progress["opened"] |= truth.part(hidden_in).opening > t["opened_m"]  # One drawer, not all of them.
        if not progress["touched"]:
            progress["touched"] = any(body == self.target for _, body, _ in truth.arm_contacts(t["contact_n"]))
        progress["lifted"] |= float(target[2]) - self._start["target_z"] >= t["held_lift_m"]

    def result(self, truth: GroundTruth, end) -> dict:
        """Score the settled end state (the last sample too). ``end`` is PhyGS's ``EpisodeEnd``: how
        the episode ended, and the unintended arm contacts (link, body, peak_n)."""
        if self._start is None:
            raise RuntimeError("result() before reset(): the World resets the task before the agent starts.")
        self.update(truth)
        t, start = self.thresholds, self._start
        pinched = truth.pinched(self.target, t["jaw_contact_n"])
        checks = dict(
            held=truth.held(self.target, lift_m=t["held_lift_m"], reach_m=t["held_reach_m"]) and pinched,
            stowed=truth.stow_error_rad() <= t["stow_tolerance_rad"],
            upright=float(truth.base_pose()[2, 2]) >= t["upright_min_cos"],
            in_time=end.ended_by in ENDED_IN_TIME,
        )
        failed = [name for name, ok in checks.items() if not ok]
        target = truth.object_pose(self.target)[:3, 3]
        distance = float(np.linalg.norm(target[:2] - truth.base_pose()[:2, 3]))
        reached = checks["held"] or distance <= t["near_target_m"]
        progress = dict(self._progress, held=checks["held"])
        progress["reached"] |= reached
        if start["hidden_in"] is None:
            progress["opened"] = None  # Nothing to open: the target started in the open.
        furthest = next((stage for stage in reversed(STAGES) if progress[stage]), None)
        unintended = [c for c in end.contacts if c["peak_n"] >= t["contact_n"]]
        left_open = {
            name: round(opening, 3)
            for name, opening in truth.part_openings().items()
            if opening > t["drawer_closed_m"] and start["openings"].get(name, 0.0) <= t["drawer_closed_m"]
        }
        moved = self._moved(truth)
        return dict(
            outcome="failure" if failed else "success",
            reason="not " + ", not ".join(failed) if failed else "the target is held with the arm stowed",
            checks=checks,
            reached=reached,
            progress=progress,
            furthest=furthest,
            measured=dict(
                target_height_m=round(float(target[2]), 3),
                target_lift_m=round(float(target[2]) - start["target_z"], 3),
                pinched=pinched,
                distance_m=round(distance, 3),
                path_length_m=round(self._path_m, 3),
                hidden_in=start["hidden_in"],
                stow_error_rad=round(truth.stow_error_rad(), 4),
                base_up_cos=round(float(truth.base_pose()[2, 2]), 3),
                ended_by=end.ended_by,
            ),
            conduct=dict(
                contacts=len(unintended),
                peak_contact_n=round(max((c["peak_n"] for c in unintended), default=0.0), 1),
                drawers_left_open=left_open,
                objects_moved=moved,
            ),
            clean=not unintended and not left_open and not moved,
            thresholds=dict(t),
            rules_version=self.rules_version,
        )

    def _moved(self, truth: GroundTruth) -> dict[str, float]:
        """Other bodies the run moved more than ``moved_m`` [m], drawers and the target left out.
        PhyGS gives each body's distance from where the episode placed it; the change since the reset
        is the run's. A body that started in a drawer is measured against that drawer's own travel, so
        one riding along in an opened drawer did not move."""
        motion, before = truth.body_motion(), self._start["motion"]
        openings, limit = self._start["openings"], self.thresholds["moved_m"]
        moved = {}
        for name, (_, shift) in motion.items():
            was = before.get(name, (0.0, 0.0))[1]
            if name == self.target or name in openings or shift - was <= limit:
                continue
            drawer = truth.started_inside(name)
            if drawer is not None and drawer in motion:
                change = abs(shift - motion[drawer][1]) - abs(was - before.get(drawer, (0.0, 0.0))[1])
            else:
                change = shift - was
            if change > limit:
                moved[name] = round(change, 3)
        return moved
