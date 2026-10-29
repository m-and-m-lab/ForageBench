# Copyright (c) 2022-2026, The Isaac Lab Project Developers (https://github.com/isaac-sim/IsaacLab/blob/main/CONTRIBUTORS.md).
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""The retrieve evaluator scores a settled end state from ground truth: outcome and conduct apart."""

from __future__ import annotations

import numpy as np
import pytest
from phygs.world.task import NoTask, Task

from foragebench.tasks import load_task
from foragebench.tasks.retrieve import THRESHOLDS, RetrieveTask, load_thresholds, rules_version


class FakeTruth:
    """Ground truth of one end state: the target's height, whether it is held, the arm, the base."""

    def __init__(self, *, held=True, height=0.9, stow_error=0.01, up_cos=1.0, openings=None):
        self._held, self._height, self._stow, self._up = held, height, stow_error, up_cos
        self._openings = {} if openings is None else openings
        self.asked = None

    def object_pose(self, name):
        pose = np.eye(4)
        pose[2, 3] = self._height
        return pose

    def held(self, name, *, lift_m, reach_m):
        self.asked = (name, lift_m, reach_m)
        return self._held

    def stow_error_rad(self):
        return self._stow

    def base_pose(self):
        pose = np.eye(4)
        pose[2, 2] = self._up
        return pose

    def part_openings(self):
        return dict(self._openings)


def evaluate(truth, ended_by="finish", contacts=(), at_start=None):
    return RetrieveTask("the box", "box").result(truth, ended_by, list(contacts), at_start or {})


def test_the_thresholds_file_is_complete_and_a_missing_key_is_an_error(tmp_path):
    thresholds = load_thresholds()
    assert set(thresholds) >= {"held_lift_m", "held_reach_m", "stow_tolerance_rad", "upright_min_cos"}
    assert THRESHOLDS.exists()
    partial = tmp_path / "thresholds.yaml"
    partial.write_text("held_lift_m: 0.05\n")
    with pytest.raises(ValueError, match="lacks"):
        load_thresholds(partial)


def test_a_result_names_the_rules_version_and_other_numbers_have_none():
    assert evaluate(FakeTruth())["rules_version"] == rules_version() >= 1
    numbers = dict(load_thresholds(), held_lift_m=0.01)
    task = RetrieveTask("the box", "box", thresholds=numbers)
    assert task.rules_version is None
    assert task.result(FakeTruth(), "finish", [], {})["rules_version"] is None


def test_success_needs_held_stowed_upright_and_in_time():
    truth = FakeTruth()
    result = evaluate(truth)
    assert result["outcome"] == "success" and result["clean"] is True
    assert truth.asked == ("box", 0.05, 0.35)
    for truth, ended_by, missing in (
        (FakeTruth(held=False), "finish", "held"),
        (FakeTruth(stow_error=0.2), "finish", "stowed"),
        (FakeTruth(up_cos=0.5), "finish", "upright"),
        (FakeTruth(), "budget", "in_time"),
    ):
        result = evaluate(truth, ended_by)
        assert result["outcome"] == "failure" and result["checks"][missing] is False
        assert missing in result["reason"]


def test_conduct_is_reported_beside_the_outcome_never_in_it():
    contacts = [
        dict(link="arm_link_fngr", body="table", peak_n=12.0),
        dict(link="arm_link_wr1", body="shelf", peak_n=0.2),
    ]
    result = evaluate(FakeTruth(), contacts=contacts)
    assert result["outcome"] == "success" and result["clean"] is False
    assert result["conduct"]["contacts"] == 1 and result["conduct"]["peak_contact_n"] == 12.0


def test_a_drawer_the_agent_left_open_counts_but_one_open_at_the_start_does_not():
    truth = FakeTruth(openings={"top": 0.25, "bottom": 0.30, "side": 0.0})
    result = evaluate(truth, at_start={"bottom": 0.30})
    assert result["conduct"]["drawers_left_open"] == {"top": 0.25} and result["clean"] is False


def test_task_blocks_build_task_objects_the_framework_accepts():
    task = load_task(dict(goal="retrieve", description="the box", target="box"))
    assert isinstance(task, Task) and task.target == "box" and "Retrieve the box" in task.brief()
    assert "evaluator_thresholds" in task.provenance()
    assert isinstance(load_task({"goal": "none"}), NoTask)
    for block, message in (
        (dict(goal="retrieve", description="a box"), "all given"),
        (dict(goal="deliver", description="a box", target="t"), "Unknown goal"),
        (dict(goal="none", target="t"), "no other fields"),
    ):
        with pytest.raises(ValueError, match=message):
            load_task(block)
