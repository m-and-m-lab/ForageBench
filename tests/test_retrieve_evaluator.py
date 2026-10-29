# Copyright (c) 2022-2026, The Isaac Lab Project Developers (https://github.com/isaac-sim/IsaacLab/blob/main/CONTRIBUTORS.md).
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""The retrieve evaluator on a fake ground truth: reset, samples while the agent runs, the result.
Outcome, reached, progress and conduct are reported apart."""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest
from phygs.world.task import EpisodeEnd, NoTask, Task

from foragebench.tasks import load_task
from foragebench.tasks.retrieve import THRESHOLDS, RetrieveTask, load_thresholds, rules_version


class FakeTruth:
    """A world with a target in a drawer: the base at ``base_xy`` [m], the target at ``target``
    [m] (it starts at z 0.30), the drawer ``top`` open ``opening`` [m], arm ``contacts``, and
    other bodies' ``motion`` (speed, distance from where they were placed)."""

    def __init__(self, **state):
        self.state = dict(
            base_xy=(0.0, 0.0),
            up_cos=1.0,
            target=(1.2, 0.0, 0.30),
            held=False,
            pinched=False,
            stow_error=0.01,
            opening=0.0,
            contacts=(),
            motion={"top": (0.0, 0.0), "cup": (0.0, 0.0), "chair": (0.0, 0.0)},
            started_inside={"box": "top", "cup": "top"},
        )
        self.state.update(state)
        self.asked = None

    def set(self, **state):
        self.state.update(state)
        return self

    def object_pose(self, name):
        pose = np.eye(4)
        pose[:3, 3] = self.state["target"]
        return pose

    def base_pose(self):
        pose = np.eye(4)
        pose[:2, 3] = self.state["base_xy"]
        pose[2, 2] = self.state["up_cos"]
        return pose

    def held(self, name, *, lift_m, reach_m):
        self.asked = (name, lift_m, reach_m)
        return self.state["held"]

    def pinched(self, name, threshold_n):
        return self.state["pinched"]

    def arm_contacts(self, threshold_n):
        return [c for c in self.state["contacts"] if c[2] >= threshold_n]

    def started_inside(self, name):
        return self.state["started_inside"].get(name)

    def body_motion(self):
        return dict(self.state["motion"])

    def stow_error_rad(self):
        return self.state["stow_error"]

    def part_openings(self):
        return {"top": self.state["opening"], "side": 0.0}

    def part(self, name):
        return SimpleNamespace(opening=self.part_openings()[name])


def run(truth, samples=(), ended_by="finish", contacts=(), task=None):
    """Reset on ``truth`` as it is, apply each sample's changes and update, then the result."""
    task = task or RetrieveTask("the small box", "box")
    task.reset(truth)
    for changes in samples:
        task.update(truth.set(**changes))
    return task.result(truth, EpisodeEnd(ended_by, 60.0, tuple(contacts)))


# A run that opens the drawer, walks up, touches, lifts and holds the box, and closes the drawer.
GOOD = (
    dict(opening=0.30, base_xy=(0.5, 0.0)),
    dict(contacts=(("arm_link_fngr", "box", 8.0),)),
    dict(target=(0.8, 0.0, 0.50), held=True, pinched=True),
    dict(opening=0.0),
)
HOLDING_IN_AN_OPEN_DRAWER = GOOD[:-1]


def test_the_thresholds_file_is_complete_versioned_and_a_missing_key_is_an_error(tmp_path):
    assert THRESHOLDS.exists() and rules_version() >= 2
    assert set(load_thresholds()) >= {"held_lift_m", "jaw_contact_n", "near_target_m", "moved_m"}
    partial = tmp_path / "thresholds.yaml"
    partial.write_text("held_lift_m: 0.05\n")
    with pytest.raises(ValueError, match="lacks"):
        load_thresholds(partial)


def test_a_good_run_succeeds_with_every_progress_stage_and_its_path():
    truth = FakeTruth()
    result = run(truth, GOOD)
    assert result["outcome"] == "success" and result["clean"] is True and result["reached"] is True
    assert result["progress"] == dict(reached=True, opened=True, touched=True, lifted=True, held=True)
    assert result["furthest"] == "held" and truth.asked == ("box", 0.05, 0.35)
    assert result["measured"]["path_length_m"] == pytest.approx(0.5) and result["measured"]["hidden_in"] == "top"
    assert result["measured"]["target_lift_m"] == pytest.approx(0.2) and result["rules_version"] == rules_version()


def test_held_needs_every_jaw_pressing_on_the_target():
    """Lifted and at the wrist is not enough: a box resting on the arm is not held."""
    result = run(FakeTruth(), [*GOOD[:2], dict(target=(0.8, 0.0, 0.50), held=True, pinched=False)])
    assert (
        result["outcome"] == "failure" and result["checks"]["held"] is False and result["measured"]["pinched"] is False
    )
    assert result["progress"]["lifted"] is True and result["progress"]["held"] is False


@pytest.mark.parametrize(
    ("changes", "ended_by", "missing"),
    [(dict(stow_error=0.2), "finish", "stowed"), (dict(up_cos=0.5), "finish", "upright"), ({}, "budget", "in_time")],
)
def test_success_also_needs_the_arm_stowed_the_robot_upright_and_the_end_in_time(changes, ended_by, missing):
    result = run(FakeTruth(), [*GOOD, changes], ended_by=ended_by)
    assert result["outcome"] == "failure" and result["checks"][missing] is False and missing in result["reason"]


def test_progress_says_where_a_failed_run_stopped():
    """The agent walked up and opened the drawer, then gave up: reached and opened, nothing more."""
    result = run(FakeTruth(), [dict(base_xy=(0.2, 0.0)), dict(opening=0.25)])
    assert result["outcome"] == "failure" and result["reached"] is True and result["furthest"] == "opened"
    assert result["progress"] == dict(reached=True, opened=True, touched=False, lifted=False, held=False)


def test_reached_is_read_at_the_end_and_from_the_samples():
    far = run(FakeTruth(base_xy=(-3.0, 0.0)))
    assert far["reached"] is False and far["progress"]["reached"] is False and far["furthest"] is None
    came_and_left = run(FakeTruth(base_xy=(-3.0, 0.0)), [dict(base_xy=(0.0, 0.0)), dict(base_xy=(-3.0, 0.0))])
    assert came_and_left["reached"] is False and came_and_left["progress"]["reached"] is True


def test_a_target_in_the_open_has_nothing_to_open():
    result = run(FakeTruth(started_inside={}), GOOD)
    assert result["progress"]["opened"] is None and result["measured"]["hidden_in"] is None


def test_conduct_is_reported_beside_the_outcome_never_in_it():
    contacts = [
        dict(link="arm_link_fngr", body="table", peak_n=12.0),
        dict(link="arm_link_wr1", body="shelf", peak_n=0.2),
    ]
    result = run(FakeTruth(), GOOD, contacts=contacts)
    assert result["outcome"] == "success" and result["clean"] is False
    assert result["conduct"]["contacts"] == 1 and result["conduct"]["peak_contact_n"] == 12.0  # 0.2 N is under the bar.


def test_a_drawer_the_agent_left_open_counts_but_one_open_at_the_start_does_not():
    opened = run(FakeTruth(), HOLDING_IN_AN_OPEN_DRAWER)
    assert opened["outcome"] == "success" and opened["clean"] is False
    assert opened["conduct"]["drawers_left_open"] == {"top": 0.3}
    open_from_the_start = run(FakeTruth(opening=0.3), HOLDING_IN_AN_OPEN_DRAWER[1:])
    assert open_from_the_start["conduct"]["drawers_left_open"] == {}


def test_a_moved_object_counts_but_one_riding_in_its_opened_drawer_does_not():
    motion = {"top": (0.0, 0.30), "cup": (0.0, 0.30), "chair": (0.0, 0.40)}  # The drawer and its cup slid 0.3 m.
    result = run(FakeTruth(), [*HOLDING_IN_AN_OPEN_DRAWER, dict(motion=motion)])
    assert result["conduct"]["objects_moved"] == {"chair": 0.4}
    knocked = {"top": (0.0, 0.30), "cup": (0.0, 0.40), "chair": (0.0, 0.0)}  # The cup was knocked 0.1 m in the drawer.
    moved = run(FakeTruth(), [*HOLDING_IN_AN_OPEN_DRAWER, dict(motion=knocked)])["conduct"]["objects_moved"]
    assert moved == {"cup": pytest.approx(0.1)}


def test_a_body_that_settled_before_the_start_did_not_move():
    settled = {"top": (0.0, 0.0), "cup": (0.0, 0.0), "chair": (0.0, 0.03)}  # 3 cm in the settle, before reset.
    result = run(FakeTruth(motion=settled), GOOD)
    assert result["conduct"]["objects_moved"] == {}


def test_result_needs_a_reset_and_other_numbers_have_no_version():
    with pytest.raises(RuntimeError, match="reset"):
        RetrieveTask("the box", "box").result(FakeTruth(), EpisodeEnd("finish", 1.0, ()))
    task = RetrieveTask("the box", "box", thresholds=dict(load_thresholds(), held_lift_m=0.01))
    assert task.rules_version is None and run(FakeTruth(), GOOD, task=task)["rules_version"] is None


def test_task_blocks_build_task_objects_the_framework_accepts():
    task = load_task(dict(goal="retrieve", description="the box", target="box"))
    assert isinstance(task, Task) and task.target == "box" and "Retrieve the box" in task.brief()
    assert "evaluator_thresholds" in task.provenance()
    assert isinstance(load_task({"goal": "none"}), NoTask)
    for block, message in (
        (dict(goal="retrieve", description="a box"), "all given"),
        (dict(goal="deliver", description="a box", target="box"), "Unknown goal"),
        (dict(goal="none", description="x"), "no other fields"),
    ):
        with pytest.raises(ValueError, match=message):
            load_task(block)
