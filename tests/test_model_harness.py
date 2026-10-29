# Copyright (c) 2022-2026, The Isaac Lab Project Developers (https://github.com/isaac-sim/IsaacLab/blob/main/CONTRIBUTORS.md).
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""The model harness: skill-call parsing, the prompt, and the loop over a fake session."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from foragebench.agents.model.loop import LoopConfig, run_loop
from foragebench.agents.model.orchestrator import SkillCall, build_system_prompt, parse_skill_call
from foragebench.agents.model.scripted import ScriptedOrchestrator
from foragebench.agents.model.skills import SKILLS


def test_parse_skill_call_strips_fences_and_checks_arguments():
    call = parse_skill_call('```json\n{"skill": "navigate", "args": {"x": 1.0, "y": 2.0, "heading": 0.0}}\n```')
    assert call == SkillCall("navigate", {"x": 1.0, "y": 2.0, "heading": 0.0})
    assert parse_skill_call('{"skill": "done"}') == SkillCall("done")
    for text in ("no json here", '{"skill": "fly", "args": {}}', '{"skill": "navigate", "args": {"room": "kitchen"}}'):
        with pytest.raises(ValueError):
            parse_skill_call(text)


def test_system_prompt_lists_every_skill_and_states_the_condition():
    unknown = build_system_prompt("a ceramic mug", None, affordance_prior=False)
    known = build_system_prompt("a ceramic mug", (1.0, 2.0, 0.5), affordance_prior=True)
    assert "location is unknown" in unknown and "[1.0, 2.0, 0.5]" in known
    assert all(f"- {name}(" in unknown for name in SKILLS) and "kitchen drawers" in known


class FakeSession:
    """A session whose clients succeed, with the grants of a track."""

    def __init__(self, grants=(), holding=False):
        self.grants, self.calls, self.finished = tuple(grants), [], None
        self.task = SimpleNamespace(goal="retrieve", description="the box")
        self.navigation = SimpleNamespace(
            navigate_to=lambda *a, **k: ("navigate_to", a), explore=lambda **k: ("explore",)
        )
        self.locomotion = SimpleNamespace(command_velocity=lambda *a, **k: ("velocity", a))
        self.manipulation = SimpleNamespace(
            look_at=lambda t: ("look_at", t),
            move_to_pose=lambda p: ("move", p),
            open_gripper=lambda: ("open",),
            close_gripper=lambda: ("close",),
            stow=lambda: ("stow",),
            holding=holding,
        )
        self.hints = SimpleNamespace(target=lambda: SimpleNamespace(center=(1.0, 2.0, 0.5)))

    def observe(self):
        return SimpleNamespace(cameras={}, localization=SimpleNamespace(valid=False))

    def wait(self, command):
        self.calls.append(command)
        return SimpleNamespace(status="succeeded", reason="ok")

    def finish(self, reason):
        self.finished = reason


def test_the_loop_runs_skills_through_the_session_and_stops_on_done():
    session = FakeSession()
    orchestrator = ScriptedOrchestrator([SkillCall("navigate", {"x": 1, "y": 0, "heading": 0}), SkillCall("stow")])
    results = run_loop(session, orchestrator)
    assert [r.call.name for r in results] == ["navigate", "stow", "done"] and all(r.ok for r in results)
    assert session.calls[0] == ("navigate_to", (1.0, 0.0, 0.0)) and session.finished.startswith("model agent")
    assert "location is unknown" in orchestrator.system_prompt


def test_the_loop_reports_failures_and_stops_on_repeats_and_budget():
    session = FakeSession(grants=("object_targets",))  # Known target: the prompt says where it is.
    stuck = ScriptedOrchestrator([SkillCall("close_gripper")] * 5)
    results = run_loop(session, stuck, LoopConfig(max_calls=10, repeat_limit=3))
    assert [r.status for r in results[:3]] == ["failed"] * 3 and "on nothing" in results[0].reason
    assert results[-1].status == "refused" and "3 times" in results[-1].reason and len(results) == 4
    assert "[1.0, 2.0, 0.5]" in stuck.system_prompt
    budget = run_loop(
        FakeSession(), ScriptedOrchestrator([SkillCall("open_gripper")] * 9), LoopConfig(max_calls=2, repeat_limit=5)
    )
    assert len(budget) == 2
