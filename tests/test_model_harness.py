# Copyright (c) 2022-2026, The Isaac Lab Project Developers (https://github.com/isaac-sim/IsaacLab/blob/main/CONTRIBUTORS.md).
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""The model harness: skill-call parsing, the prompt, pointing (pixel to world point) and the loop
over a fake session with a fake camera."""

from __future__ import annotations

import math
from types import SimpleNamespace

import numpy as np
import pytest
from phygs.robots.description import load_robot

from foragebench.agents.model import perception, skills
from foragebench.agents.model.loop import LoopConfig, run_loop
from foragebench.agents.model.orchestrator import SkillCall, build_system_prompt, parse_skill_call
from foragebench.agents.model.perception import PointingError
from foragebench.agents.model.scripted import ScriptedOrchestrator
from foragebench.agents.model.skills import PULL_M, SKILLS, STANDOFF_M

WIDTH, HEIGHT, F = 100, 80, 100.0
# The camera 1 m up at the origin, looking along world +x (optical z forward, x right = world -y, y down).
CAMERA_POSE = np.array([[0, 0, 1, 0], [-1, 0, 0, 0], [0, -1, 0, 1.0], [0, 0, 0, 1.0]])
STAMP = ("episode 1", 2.5)


def fake_packet(wall_x=2.0, handle=True, pose=True):
    """A wall 2 m ahead (depth 2 everywhere) with a 3 cm deep handle around pixel (50, 50)."""
    depth = np.full((HEIGHT, WIDTH), wall_x)
    if handle:
        depth[48:53, 40:61] = wall_x - 0.03
    camera = SimpleNamespace(
        depth=depth,
        depth_valid=np.ones_like(depth, dtype=bool),
        intrinsics=np.array([[F, 0, WIDTH / 2], [0, F, HEIGHT / 2], [0, 0, 1.0]]),
        frame="front",
        stamp=STAMP,
        rgb=np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8),
    )

    def transform(target, source, stamp):
        if not pose:
            raise KeyError("no world frame")
        assert (target, source, stamp) == ("world", "front", STAMP)
        return CAMERA_POSE

    localization = SimpleNamespace(valid=pose, pose=SimpleNamespace(matrix=np.eye(4)))
    return SimpleNamespace(cameras={"front": camera}, transform=transform, localization=localization)


def test_a_pixel_becomes_the_world_point_the_camera_sees_and_projects_back():
    packet = fake_packet(handle=False)
    assert perception.world_point(packet, "front", 50, 40) == pytest.approx([2.0, 0.0, 1.0])
    point = perception.world_point(packet, "front", 70, 20)  # Right of centre and up: -y, +z.
    assert point == pytest.approx([2.0, -0.4, 1.4])
    assert perception.project(packet, "front", point) == pytest.approx((70.0, 20.0))
    assert perception.project(packet, "front", (-1.0, 0.0, 1.0)) is None  # Behind the camera.


def test_a_drawer_front_faces_the_camera_and_its_handle_is_the_point_sticking_out():
    packet = fake_packet()
    outward = perception.facing_normal(packet, "front", 50, 40)
    assert outward == pytest.approx([-1.0, 0.0, 0.0], abs=1e-6)
    handle = perception.protruding_point(packet, "front", 52, 45, outward)  # The model pointed a little off.
    assert handle[0] == pytest.approx(1.97) and handle[2] == pytest.approx(1.0 - 0.197, abs=0.01)  # Row 50.
    assert abs(handle[1]) < 0.03  # Near the pointed column along the bar (u 40-60), not at an end.


def test_pointing_errors_name_the_problem():
    packet = fake_packet()
    with pytest.raises(PointingError, match="outside"):
        perception.world_point(packet, "front", 500, 10)
    with pytest.raises(PointingError, match="no depth camera"):
        perception.world_point(packet, "hand", 10, 10)
    with pytest.raises(PointingError, match="world pose"):
        perception.world_point(fake_packet(pose=False), "front", 10, 10)
    packet.cameras["front"].depth_valid[:] = False
    with pytest.raises(PointingError, match="no depth near"):
        perception.world_point(packet, "front", 10, 10)


def test_parse_skill_call_strips_fences_and_checks_arguments():
    call = parse_skill_call('```json\n{"skill": "go_to", "args": {"camera": "front", "target": "the box"}}\n```')
    assert call == SkillCall("go_to", {"camera": "front", "target": "the box"})
    assert parse_skill_call('{"skill": "done"}') == SkillCall("done")
    pixels = '{"skill": "go_to", "args": {"camera": "front", "u": 5, "v": 6}}'  # A model names, not pixels.
    for text in (
        "no json here",
        '{"skill": "fly", "args": {}}',
        '{"skill": "go_to", "args": {"room": "kitchen"}}',
        pixels,
    ):
        with pytest.raises(ValueError):
            parse_skill_call(text)


def test_system_prompt_lists_every_skill_explains_pointing_and_states_the_condition():
    unknown = build_system_prompt("a ceramic mug", None, affordance_prior=False)
    known = build_system_prompt("a ceramic mug", (1.0, 2.0, 0.5), affordance_prior=True)
    assert "location is unknown" in unknown and "[1.0, 2.0, 0.5]" in known
    assert all(f"- {name}(" in unknown for name in SKILLS) and "kitchen drawers" in known
    assert '"target", what it is' in unknown and "- go_to(camera, target)" in unknown


class FakeSession:
    """A session whose clients succeed, with the grants of a track and the fake camera."""

    def __init__(self, grants=(), holding=False, pose=True, stowed=True):
        self.grants, self.calls, self.finished = tuple(grants), [], None
        self.robot = load_robot("spot").info()
        self.task = SimpleNamespace(goal="retrieve", description="the box")
        self.packet = fake_packet(pose=pose)
        arm = np.array(self.robot.stow) + (0.0 if stowed else 0.5)
        self.packet.joints = SimpleNamespace(names=self.robot.arm_joints, positions=arm)
        self.navigation = SimpleNamespace(
            navigate_to=lambda *a, **k: ("navigate_to", a), explore=lambda **k: ("explore",)
        )
        self.locomotion = SimpleNamespace(command_velocity=lambda *a, **k: ("velocity", a))
        self.manipulation = SimpleNamespace(
            look_at=lambda t, **k: ("look_at", t, k), stow=lambda held=None: ("stow",), holding=holding
        )
        self.refuse_views = 0  # look_at views refused as out of reach before one succeeds.
        self.hints = SimpleNamespace(target=lambda: SimpleNamespace(center=(1.0, 2.0, 0.5)))

    def observe(self):
        return self.packet

    def wait(self, command):
        self.calls.append(command)
        if command[0] == "look_at" and self.refuse_views > 0:
            self.refuse_views -= 1
            return SimpleNamespace(status="failed", reason="out of reach", failure=skills.arm.SkillFailure.OUT_OF_REACH)
        return SimpleNamespace(status="succeeded", reason="ok")

    def sleep(self, seconds):
        self.calls.append(("sleep", seconds))

    def finish(self, reason):
        self.finished = reason


def test_the_loop_walks_to_a_pointed_spot_aims_the_hand_camera_and_stops_on_done():
    session = FakeSession()
    calls = [
        SkillCall("go_to", {"camera": "front", "u": 50, "v": 40}),
        SkillCall("look_at", {"camera": "front", "u": 50, "v": 40}),
    ]
    results = run_loop(session, ScriptedOrchestrator([*calls, SkillCall("stow")]))
    assert [r.call.name for r in results] == ["go_to", "look_at", "stow", "done"] and all(r.ok for r in results)
    kind, (x, y, heading) = session.calls[0]
    assert kind == "navigate_to" and (x, y) == pytest.approx((2.0 - STANDOFF_M, 0.0)) and heading == pytest.approx(0.0)
    target = session.calls[1][1]  # The world point the pixel shows in the capture the model was shown.
    assert target.position == pytest.approx((2.0, 0.0, 1.0)) and target.frame == "world"
    assert session.finished.startswith("model agent")


def test_a_pixel_the_robot_cannot_use_is_refused_with_the_reason():
    results = run_loop(FakeSession(), ScriptedOrchestrator([SkillCall("go_to", {"camera": "front", "u": 999, "v": 1})]))
    assert results[0].status == "refused" and "outside" in results[0].reason
    blind = run_loop(FakeSession(pose=False), ScriptedOrchestrator([SkillCall("go_near", {"x": 1, "y": 0})]))
    assert blind[0].status == "refused" and "pose" in blind[0].reason
    holding = run_loop(
        FakeSession(holding=True), ScriptedOrchestrator([SkillCall("pick", {"camera": "front", "u": 5, "v": 5})])
    )
    assert holding[0].status == "refused" and "already holds" in holding[0].reason


def test_the_loop_stops_on_repeats_and_on_the_budget():
    session = FakeSession(grants=("object_targets",))  # Known target: the prompt says where it is.
    stuck = ScriptedOrchestrator([SkillCall("go_to", {"camera": "front", "u": 999, "v": 1})] * 5)
    results = run_loop(session, stuck, LoopConfig(max_calls=10, repeat_limit=3))
    assert [r.status for r in results[:3]] == ["refused"] * 3
    assert results[-1].status == "refused" and "3 times" in results[-1].reason and len(results) == 4
    assert "[1.0, 2.0, 0.5]" in stuck.system_prompt
    turns = [SkillCall("turn", {"yaw_rate": 0.4, "seconds": 1.0 + k}) for k in range(9)]
    assert len(run_loop(FakeSession(), ScriptedOrchestrator(turns), LoopConfig(max_calls=2, repeat_limit=5))) == 2
    assert math.isfinite(perception.heading_to((0, 0), (1, 1)))


def test_open_drawer_stands_in_front_of_the_measured_drawer_then_pulls_it(monkeypatch):
    """The drawer as the depth shows it: the front faces the camera (outward -x), the handle sticks
    out 3 cm at x = 1.97 m. The robot first stands facing it with the handle at the far end of its
    grip range, then pulls along the outward direction."""
    strokes = []
    monkeypatch.setattr(
        skills.drawer,
        "stroke",
        lambda session, part, kind, length: strokes.append((part, kind, length))
        or SimpleNamespace(status="succeeded", reason=""),
    )
    session = FakeSession(stowed=False)  # The arm is out (after a look_at): it stows to walk.
    results = run_loop(session, ScriptedOrchestrator([SkillCall("open_drawer", {"camera": "front", "u": 50, "v": 50})]))
    assert results[0].ok, results[0].reason
    stow, walk, settle = session.calls[:3]
    assert stow == ("stow",) and settle[0] == "sleep"
    kind, (x, y, heading) = walk
    near, far = skills.routines.PARAMS["grip_range_m"]
    tolerance = skills.routines.PARAMS["goal_tolerance"][0]
    assert kind == "navigate_to" and x == pytest.approx(1.98 - (far - tolerance)) and abs(y) < 0.01
    assert heading == pytest.approx(0.0, abs=1e-6)
    ((part, how, length),) = strokes
    assert how == "open" and part.direction == pytest.approx((-1.0, 0.0, 0.0), abs=1e-6)
    assert part.handle_center[0] == pytest.approx(1.98) and length == pytest.approx(PULL_M)


def test_walking_skills_stow_an_arm_that_is_out_first():
    session = FakeSession(stowed=False)
    run_loop(session, ScriptedOrchestrator([SkillCall("go_near", {"x": 3.0, "y": 0.0})]))
    assert session.calls[0] == ("stow",) and session.calls[1][0] == "navigate_to"


def test_look_at_tries_the_next_view_while_one_is_out_of_reach():
    session = FakeSession()
    session.refuse_views = 2
    results = run_loop(session, ScriptedOrchestrator([SkillCall("look_at", {"camera": "front", "u": 50, "v": 40})]))
    views = [call[2] for call in session.calls if call[0] == "look_at"]
    expected = skills.routines.PARAMS["look_views"]["target"][:3]
    assert results[0].ok and [(v["distance_m"], v["elevation_deg"]) for v in views] == [tuple(e) for e in expected]
    session = FakeSession()
    session.refuse_views = 99
    results = run_loop(session, ScriptedOrchestrator([SkillCall("look_at", {"camera": "front", "u": 50, "v": 40})]))
    assert results[0].status == "failed" and "move the base" in results[0].reason


def test_a_box_on_a_surface_is_measured_from_its_top_down_to_the_surface():
    """A camera 1 m up looking straight down at a floor (z = 0) with a 10 cm box (top at z = 0.1)
    under the centre pixels."""
    packet = fake_packet(handle=False)
    camera = packet.cameras["front"]
    camera.depth = np.full((HEIGHT, WIDTH), 1.0)
    camera.depth[30:51, 40:61] = 0.9  # The box top: 0.1 m above the floor, 0.18 m wide.
    down = np.array([[1, 0, 0, 0], [0, -1, 0, 0], [0, 0, -1, 1.0], [0, 0, 0, 1.0]])  # Optical z down.
    packet.transform = lambda target, source, stamp: down
    center, size = perception.object_box(packet, "front", 50, 40)
    assert size[2] == pytest.approx(0.1) and center[2] == pytest.approx(0.05)
    assert size[0] == pytest.approx(20 * 0.9 / F) and size[1] == pytest.approx(20 * 0.9 / F)
    assert center[:2] == pytest.approx([0.0, 0.0], abs=0.01)


def test_go_to_an_upright_surface_seen_at_an_angle_stands_in_front_of_it():
    """A wall through (2, 0, 1) turned 30 deg (normal (cos 30, sin 30, 0)), seen from the origin: the
    robot stands 1.05 m out along the wall's normal, facing it, not on the line of sight."""
    session = FakeSession()
    normal = np.array([math.cos(math.pi / 6), math.sin(math.pi / 6), 0.0])
    cols = np.arange(WIDTH)[None, :].repeat(HEIGHT, 0)
    session.packet.cameras["front"].depth = 2 * normal[0] / (normal[0] - (cols - WIDTH / 2) / F * normal[1])
    run_loop(session, ScriptedOrchestrator([SkillCall("go_to", {"camera": "front", "u": 50, "v": 40})]))
    kind, (x, y, heading) = session.calls[0]
    assert (x, y) == pytest.approx(tuple(np.array([2.0, 0.0]) - normal[:2] * STANDOFF_M), abs=1e-3)
    assert heading == pytest.approx(math.pi / 6, abs=1e-3)


def test_the_surface_under_a_box_is_the_table_not_the_floor_seen_past_its_edge():
    """The box (top 0.1 m) on a table (0.05 m) whose edge is near it, the floor (0) beyond."""
    packet = fake_packet(handle=False)
    camera = packet.cameras["front"]
    camera.depth = np.full((HEIGHT, WIDTH), 0.95)  # The table top.
    camera.depth[:, 70:] = 1.0  # The floor past the table's edge.
    camera.depth[30:51, 40:61] = 0.9  # The box top.
    camera.depth[29, 40:61] = 0.93  # Edge pixels between the box and the table: one more row (9 mm here).
    down = np.array([[1, 0, 0, 0], [0, -1, 0, 0], [0, 0, -1, 1.0], [0, 0, 0, 1.0]])
    packet.transform = lambda target, source, stamp: down
    center, size = perception.object_box(packet, "front", 50, 40)
    assert size[2] == pytest.approx(0.05) and center[2] == pytest.approx(0.075)
    assert size[0] == pytest.approx(20 * 0.9 / F, abs=0.01) and size[1] == pytest.approx(20 * 0.9 / F, abs=0.015)
    assert perception.support_height(np.array([0.5] * 5), 0.6, 0.01) is None  # Too few points below.


def test_pick_steps_square_to_put_the_object_in_reach_and_carries_the_box_it_measured(monkeypatch):
    """The box on the floor 1.4 m ahead (world x) and 0.1 m left; the robot at the origin facing +x
    keeps its heading and steps so the box is reach_in_ahead_m straight ahead. The box it measured
    goes to the robot tests' pick, and later stows carry the object it returned."""
    picked = []
    monkeypatch.setattr(skills.arm, "pick", lambda session, target, look: picked.append(target) or "held box")
    session = FakeSession()
    camera = session.packet.cameras["front"]
    camera.depth = np.full((HEIGHT, WIDTH), 1.0)  # A floor 1 m under a camera looking down at (1.4, 0.1).
    camera.depth[30:51, 40:61] = 0.9  # The box top, 0.1 m above the floor.
    down = np.array([[1, 0, 0, 1.4], [0, -1, 0, 0.1], [0, 0, -1, 1.0], [0, 0, 0, 1.0]])
    session.packet.transform = lambda target, source, stamp: down
    session.manipulation.holding = False
    results = run_loop(session, ScriptedOrchestrator([SkillCall("pick", {"camera": "front", "u": 50, "v": 40})]))
    assert results[0].ok, results[0].reason
    reach = skills.routines.PARAMS["reach_in_ahead_m"]
    kind, (x, y, heading) = session.calls[0]
    assert kind == "navigate_to" and (x, y, heading) == pytest.approx((1.4 - reach, 0.1, 0.0), abs=1e-3)
    (target,) = picked
    assert target.name is None and target.center == pytest.approx((1.4, 0.1, 0.05), abs=0.01)
    session.manipulation.holding = True
    run_loop(session, ScriptedOrchestrator([SkillCall("stow")]))
    assert skills._held(session) == "held box"


def test_pick_refuses_an_object_further_than_a_step():
    session = FakeSession()
    results = run_loop(session, ScriptedOrchestrator([SkillCall("pick", {"camera": "front", "u": 50, "v": 40})]))
    assert results[0].status == "refused" and "go_to it first" in results[0].reason  # The wall 2 m ahead.


def test_a_pixel_without_depth_takes_the_nearest_surface_around_it_not_the_background():
    packet = fake_packet(handle=False)  # The wall 2 m ahead.
    camera = packet.cameras["front"]
    camera.depth[38:43, 46:49] = 1.0  # A thin post 1 m ahead, left of the pixel.
    camera.depth_valid[38:43, 49:52] = False  # Its edge, around the pixel (50, 40), has no depth.
    assert perception.valid_pixel(packet, "front", 50, 40) == (48, 40)
    assert perception.valid_pixel(packet, "front", 30, 40) == (30, 40)  # A pixel with depth is itself.


def test_open_drawer_stands_a_tolerance_nearer_when_the_handle_was_out_of_reach(monkeypatch):
    strokes = iter([None, SimpleNamespace(status="succeeded", reason="")])  # Every pitch refused, then pulled.
    monkeypatch.setattr(skills.drawer, "stroke", lambda session, part, kind, length: next(strokes))
    session = FakeSession()
    results = run_loop(session, ScriptedOrchestrator([SkillCall("open_drawer", {"camera": "front", "u": 50, "v": 50})]))
    assert results[0].ok, results[0].reason
    walks = [call[1][0] for call in session.calls if call[0] == "navigate_to"]
    far, tolerance = skills.routines.PARAMS["grip_range_m"][1], skills.routines.PARAMS["goal_tolerance"][0]
    assert walks == pytest.approx([1.98 - (far - tolerance), 1.98 - (far - 2 * tolerance)])


def test_a_grounding_reply_gives_the_pixel_in_each_family_s_format():
    from foragebench.agents.model.orchestrator import parse_point, point_query

    shape = (HEIGHT, WIDTH, 3)
    qwen = '```json\n[{"point_2d": [500, 250], "label": "the box"}]\n```'
    assert parse_point(qwen, "qwen", shape) == pytest.approx((WIDTH / 2, HEIGHT / 4))
    gemini = '[{"point": [250, 500], "label": "the box"}]'  # [y, x].
    assert parse_point(gemini, "gemini", shape) == pytest.approx((WIDTH / 2, HEIGHT / 4))
    assert parse_point("I see no box.", "qwen", shape) is None
    assert parse_point('[{"point_2d": [1200, -5]}]', "qwen", shape) == (WIDTH - 1.0, 0.0)  # Kept in the image.
    assert "the box" in point_query("qwen", "the box") and "[y, x]" in point_query("gemini", "the box")


def test_the_loop_finds_a_named_target_in_the_camera_image_the_model_named():
    class Pointing(ScriptedOrchestrator):
        def point(self, image, target):
            self.asked = (image.shape, target)
            return None if target == "a unicorn" else (50.0, 40.0)

    session = FakeSession()
    orchestrator = Pointing(
        [
            SkillCall("look_at", {"camera": "front", "target": "the box"}),
            SkillCall("look_at", {"camera": "front", "target": "a unicorn"}),
            SkillCall("look_at", {"camera": "rear", "target": "the box"}),
        ]
    )
    results = run_loop(session, orchestrator)
    assert results[0].ok and session.calls[0][1].position == pytest.approx((2.0, 0.0, 1.0))
    assert results[1].status == "refused" and "could not find 'a unicorn' in any camera" in results[1].reason
    assert results[2].status == "refused" and "no camera 'rear'" in results[2].reason
    assert results[0].call.args == {"camera": "front", "target": "the box"}  # The model's own words in its history.


def test_the_openai_client_sends_the_thinking_switch_and_logs_each_turn(tmp_path, monkeypatch):
    from foragebench.agents.model import openai_compatible
    from foragebench.agents.model.orchestrator import Observation, OrchestratorConfig

    sent = []

    def post(url, json, headers, timeout):
        sent.append(json)
        message = {"content": '{"skill": "stow", "args": {}}', "reasoning_content": "fold the arm"}
        return SimpleNamespace(raise_for_status=lambda: None, json=lambda: {"choices": [{"message": message}]})

    monkeypatch.setattr(openai_compatible.requests, "post", post)
    client = openai_compatible.OpenAICompatibleOrchestrator(
        OrchestratorConfig(model="m", thinking=False), "http://x/v1", None, log_dir=tmp_path / "agent"
    )
    client.reset("the box")
    image = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
    assert client.act(Observation(images={"front": image}, pose=None)) == SkillCall("stow")
    assert sent[0]["chat_template_kwargs"] == {"enable_thinking": False}
    import json as json_module

    (turn,) = [json_module.loads(line) for line in (tmp_path / "agent" / "turns.jsonl").read_text().splitlines()]
    assert turn["thought"] == "fold the arm" and turn["images"] == ["front"]
    assert (tmp_path / "agent" / "turn_001_front.jpg").exists()


@pytest.mark.parametrize("turns", [0, 1, 2, 3])
def test_a_point_in_the_upright_image_maps_back_to_the_same_pixel_of_the_camera(turns):
    raw = np.zeros((HEIGHT, WIDTH), dtype=int)
    raw[13, 71] = 1
    rows, cols = np.nonzero(np.rot90(raw, turns))
    assert perception.raw_pixel(float(cols[0]), float(rows[0]), turns, raw.shape) == (71, 13)


def test_a_camera_mounted_on_its_side_is_turned_so_the_body_s_up_is_up():
    packet = fake_packet()
    level = np.array([[0, 0, 1, 0], [-1, 0, 0, 0], [0, -1, 0, 0], [0, 0, 0, 1.0]])  # Optical y down = body -z.
    packet.cameras["front"].extrinsics = SimpleNamespace(matrix=level)
    assert perception.upright_turns(packet, "front") == 0
    side = level.copy()
    side[:3, :3] = level[:3, :3] @ np.array([[0, -1, 0], [1, 0, 0], [0, 0, 1.0]])  # Rolled 90 deg about z.
    packet.cameras["front"].extrinsics = SimpleNamespace(matrix=side)
    turns = perception.upright_turns(packet, "front")
    up = side[:3, :3].T @ [0, 0, 1.0]  # Body up in the image (x right, y down) after the turns is (0, -1).
    after = [(up[0], up[1]), (up[1], -up[0]), (-up[0], -up[1]), (-up[1], up[0])][turns]
    assert after == pytest.approx((0.0, -1.0)) and turns in (1, 3)


def test_a_stow_with_no_plan_from_where_the_arm_is_lifts_the_hand_and_tries_again(monkeypatch):
    lifts = []
    monkeypatch.setattr(
        skills.arm,
        "move_straight",
        lambda session, axis, distance: lifts.append((tuple(axis), distance)) or SimpleNamespace(status="succeeded"),
    )
    session = FakeSession()
    answers = iter(["Joint planner failed: no_plan_within_budget", "ok"])
    session.wait = lambda command: SimpleNamespace(
        status="failed" if (reason := next(answers)) != "ok" else "succeeded", reason=reason
    )
    assert skills.SKILLS["stow"].run(session, session.packet) == ("succeeded", "ok")
    assert lifts == [((0.0, 0.0, 1.0), skills.UNSTICK_M)]


def test_a_target_the_named_camera_does_not_show_is_looked_for_in_the_other_cameras():
    class Pointing(ScriptedOrchestrator):
        def point(self, image, target):
            return None if image.shape[1] == WIDTH else (5.0, 5.0)  # Only the narrow camera shows it.

    session = FakeSession()
    session.packet.cameras["side"] = SimpleNamespace(**vars(session.packet.cameras["front"]))
    session.packet.cameras["side"].rgb = np.zeros((HEIGHT, WIDTH // 2, 3), dtype=np.uint8)
    results = run_loop(session, Pointing([SkillCall("look_at", {"camera": "front", "target": "the box"})]))
    assert results[0].ok and results[0].reason.startswith("(found in 'side', not 'front')")
