# Copyright (c) 2022-2026, The Isaac Lab Project Developers (https://github.com/isaac-sim/IsaacLab/blob/main/CONTRIBUTORS.md).
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""The model harness: skill-call parsing, the prompt, pointing (pixel to world point) and the loop
over a fake session with a fake camera."""

from __future__ import annotations

import math
from contextlib import contextmanager
from types import SimpleNamespace

import numpy as np
import pytest
from phygs.composite import TUNING, CompositeSkills
from phygs.composite.skills import Motion
from phygs.robots.description import load_robot

from foragebench.agents.model import perception
from foragebench.agents.model.loop import LoopConfig, run_loop
from foragebench.agents.model.orchestrator import SkillCall, build_system_prompt, parse_skill_call
from foragebench.agents.model.perception import PointingError
from foragebench.agents.model.scripted import ScriptedOrchestrator
from foragebench.agents.model.skills import PUSH_M, SKILLS, STANDOFF_M

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


def test_a_drawer_front_seen_from_near_faces_out_of_the_front_not_out_of_its_handle():
    """From a body camera 0.45 m away the patch is 7 cm wide and a bar 5 cm out of the front is a
    quarter of it: a plane fitted to all of it turned 48-62 deg (Qwen3.8, 2026-11-02)."""
    packet, focal = fake_packet(handle=False), 320.0
    camera = packet.cameras["front"]
    camera.intrinsics = np.array([[focal, 0, WIDTH / 2], [0, focal, HEIGHT / 2], [0, 0, 1.0]])
    yaw = math.radians(15.0)  # The front turned this far from facing the camera.
    outward = np.array([-math.cos(yaw), math.sin(yaw), 0.0])
    centre, origin = np.array([0.45, 0.0, 1.0]), CAMERA_POSE[:3, 3]
    cols, rows = np.meshgrid(np.arange(WIDTH), np.arange(HEIGHT))
    pixels = np.stack([(cols - WIDTH / 2) / focal, (rows - HEIGHT / 2) / focal, np.ones(cols.shape)], -1)
    rays = pixels @ CAMERA_POSE[:3, :3].T  # World direction per metre of depth.

    def depth_to(offset):  # Where each pixel's ray meets the plane ``offset`` [m] out of the front.
        return (offset - (origin - centre) @ outward) / (rays @ outward)

    bar = depth_to(0.05)
    camera.depth = np.where(np.abs(rays[..., 2] * bar) <= 0.008, bar, depth_to(0.0))  # 1.6 cm high, at z 1 m.
    found = perception.facing_normal(packet, "front", 50, 40)
    assert found == pytest.approx(outward, abs=1e-6)
    handle = perception.protruding_point(packet, "front", 50, 40, found)
    assert (handle - centre) @ outward == pytest.approx(0.05, abs=1e-3)


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
    call = parse_skill_call('```json\n{"skill": "navigate_to", "args": {"camera": "front", "target": "the box"}}\n```')
    assert call == SkillCall("navigate_to", {"camera": "front", "target": "the box"})
    assert parse_skill_call('{"skill": "done"}') == SkillCall("done")
    position = parse_skill_call('{"skill": "navigate_to", "args": {"x": 1.0, "y": 2.0}}')  # PhyGS's own form.
    assert position == SkillCall("navigate_to", {"x": 1.0, "y": 2.0})
    pixels = '{"skill": "navigate_to", "args": {"camera": "front", "u": 5, "v": 6}}'  # A model names, not pixels.
    for text in (
        "no json here",
        '{"skill": "fly", "args": {}}',
        '{"skill": "navigate_to", "args": {"room": "kitchen"}}',
        '{"skill": "go_to", "args": {"camera": "front", "target": "the box"}}',  # Not a PhyGS name.
        pixels,
    ):
        with pytest.raises(ValueError):
            parse_skill_call(text)


def test_system_prompt_lists_every_skill_explains_pointing_and_states_the_condition():
    unknown = build_system_prompt("a ceramic mug", None, affordance_prior=False)
    known = build_system_prompt("a ceramic mug", (1.0, 2.0, 0.5), affordance_prior=True)
    assert "location is unknown" in unknown and "[1.0, 2.0, 0.5]" in known
    assert all(f"- {name}(" in unknown for name in SKILLS) and "kitchen drawers" in known
    assert '"target", what it is' in unknown and "- navigate_to(camera, target) or navigate_to(x, y)" in unknown
    assert set(SKILLS) - {"done"} <= {"navigate_to", "explore", "command_velocity", "look_at", "stow", "pick"} | {
        "open_drawer",
        "close_drawer",
    }  # PhyGS's names (the session's and the composite skills'), and done.


class FakeSession:
    """A session whose clients succeed, with the grants of a track and the fake camera. With ``walks``
    the base stops at each navigate_to goal; else it stays at the origin."""

    def __init__(self, grants=(), holding=False, pose=True, stowed=True, walks=False):
        self.grants, self.calls, self.finished, self.walks = tuple(grants), [], None, walks
        self.robot = load_robot("spot").info()
        self.task = SimpleNamespace(goal="retrieve", description="the box")
        self.packet = fake_packet(pose=pose)
        arm = np.array(self.robot.stow) + (0.0 if stowed else 0.5)
        self.packet.joints = SimpleNamespace(names=self.robot.arm_joints, positions=arm)
        self.navigation = SimpleNamespace(
            navigate_to=lambda *a, **k: ("navigate_to", a), explore=lambda **k: ("explore",)
        )
        self.locomotion = SimpleNamespace(command_velocity=lambda *a, **k: ("velocity", a))
        self.manipulation = SimpleNamespace(look_at=lambda t, **k: ("look_at", t, k), stow=self._stow, holding=holding)
        self.hints = SimpleNamespace(target=lambda: SimpleNamespace(center=(1.0, 2.0, 0.5)))

    def _stow(self, held=None):
        return ("stow", held)

    def observe(self):
        return self.packet

    def wait(self, command):
        self.calls.append(command)
        if self.walks and command[0] == "navigate_to" and len(command[1]) == 3:
            x, y, heading = command[1]
            c, s = math.cos(heading), math.sin(heading)
            self.packet.localization.pose.matrix = np.array([[c, -s, 0, x], [s, c, 0, y], [0, 0, 1, 0], [0, 0, 0, 1.0]])
        return SimpleNamespace(status="succeeded", reason="ok")

    def sleep(self, seconds):
        self.calls.append(("sleep", seconds))

    @contextmanager
    def step(self, name):
        yield

    def finish(self, reason):
        self.finished = reason


def test_the_loop_walks_to_a_pointed_spot_aims_the_hand_camera_and_stops_on_done():
    session = FakeSession()
    calls = [
        SkillCall("navigate_to", {"camera": "front", "u": 50, "v": 40}),
        SkillCall("look_at", {"camera": "front", "u": 50, "v": 40}),
    ]
    results = run_loop(session, ScriptedOrchestrator([*calls, SkillCall("stow")]))
    assert [r.call.name for r in results] == ["navigate_to", "look_at", "stow", "done"] and all(r.ok for r in results)
    kind, (x, y, heading) = session.calls[0]
    assert kind == "navigate_to" and (x, y) == pytest.approx((2.0 - STANDOFF_M, 0.0)) and heading == pytest.approx(0.0)
    _, target, views = session.calls[1]  # The world point the pixel shows in the capture the model was shown,
    assert target.position == pytest.approx((2.0, 0.0, 1.0)) and target.frame == "world"
    assert views == {"held": None}  # from look_at's own views.
    assert session.finished.startswith("model agent")


def test_a_pixel_the_robot_cannot_use_is_refused_with_the_reason():
    point = {"camera": "front", "u": 999, "v": 1}
    results = run_loop(FakeSession(), ScriptedOrchestrator([SkillCall("navigate_to", point)]))
    assert results[0].status == "refused" and "outside" in results[0].reason
    point = {"camera": "front", "u": 50, "v": 40}
    blind = run_loop(FakeSession(pose=False), ScriptedOrchestrator([SkillCall("navigate_to", point)]))
    assert blind[0].status == "refused" and "pose" in blind[0].reason
    holding = run_loop(
        FakeSession(holding=True), ScriptedOrchestrator([SkillCall("pick", {"camera": "front", "u": 5, "v": 5})])
    )
    assert holding[0].status == "refused" and "already holds" in holding[0].reason


def test_the_loop_stops_on_repeats_and_on_the_budget():
    session = FakeSession(grants=("object_targets",))  # Known target: the prompt says where it is.
    stuck = ScriptedOrchestrator([SkillCall("navigate_to", {"camera": "front", "u": 999, "v": 1})] * 5)
    results = run_loop(session, stuck, LoopConfig(max_calls=10, repeat_limit=3))
    assert [r.status for r in results[:3]] == ["refused"] * 3
    assert results[-1].status == "refused" and "3 times" in results[-1].reason and len(results) == 4
    assert "[1.0, 2.0, 0.5]" in stuck.system_prompt
    turns = [SkillCall("command_velocity", dict(v_x=0.0, v_y=0.0, v_rot=0.4, duration=1.0 + k)) for k in range(9)]
    assert len(run_loop(FakeSession(), ScriptedOrchestrator(turns), LoopConfig(max_calls=2, repeat_limit=5))) == 2
    assert math.isfinite(perception.heading_to((0, 0), (1, 1)))


def test_open_drawer_stands_in_front_of_the_measured_drawer_then_pulls_it(monkeypatch):
    """The drawer as the depth shows it: the front faces the camera (outward -x), the handle sticks
    out 3 cm at x = 1.97 m. The robot first stands facing it with the handle at the far end of its
    grip range, then pulls along the outward direction as far as the arm reaches from there (the
    handle to the near end of the grip range), as the oracle's pull: the depth shows no travel."""
    strokes = []
    monkeypatch.setattr(
        CompositeSkills,
        "_stroke",
        lambda self, part, kind, length: strokes.append((part, kind, length))
        or (Motion("succeeded"), {}, dict(moved_m=length)),
    )
    session = FakeSession(stowed=False, walks=True)  # The arm is out (after a look_at): the composite stows to walk.
    results = run_loop(session, ScriptedOrchestrator([SkillCall("open_drawer", {"camera": "front", "u": 50, "v": 50})]))
    assert results[0].ok, results[0].reason
    stow, walk = session.calls[:2]
    assert stow == ("stow", None)
    kind, (x, y, heading) = walk
    near, far = TUNING.grip_range_m
    tolerance = TUNING.goal_tolerance[0]
    assert kind == "navigate_to" and x == pytest.approx(1.98 - (far - tolerance)) and abs(y) < 0.01
    assert heading == pytest.approx(0.0, abs=1e-6)
    ((part, how, length),) = strokes
    assert how == "open" and part.direction == pytest.approx((-1.0, 0.0, 0.0), abs=1e-6)
    assert part.handle_center[0] == pytest.approx(1.98) and length == pytest.approx(far - tolerance - near)


def test_navigate_to_a_world_position_is_phygs_own_and_adds_nothing():
    """The arm out: PhyGS refuses to walk and says to stow first; the harness adds no stow of its own."""
    session = FakeSession(stowed=False)
    run_loop(session, ScriptedOrchestrator([SkillCall("navigate_to", {"x": 3.0, "y": 0.0})]))
    assert session.calls[0] == ("navigate_to", (3.0, 0.0))


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


def test_navigate_to_an_upright_surface_seen_at_an_angle_stands_in_front_of_it():
    """A wall through (2, 0, 1) turned 30 deg (normal (cos 30, sin 30, 0)), seen from the origin: the
    robot stands 1.05 m out along the wall's normal, facing it, not on the line of sight."""
    session = FakeSession()
    normal = np.array([math.cos(math.pi / 6), math.sin(math.pi / 6), 0.0])
    cols = np.arange(WIDTH)[None, :].repeat(HEIGHT, 0)
    session.packet.cameras["front"].depth = 2 * normal[0] / (normal[0] - (cols - WIDTH / 2) / F * normal[1])
    run_loop(session, ScriptedOrchestrator([SkillCall("navigate_to", {"camera": "front", "u": 50, "v": 40})]))
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


def side_view(shapes, width=400, height=300, focal=400.0, tilt_deg=30.0):
    """A camera 0.6 m up at the origin looking along world +x, tilted down by ``tilt_deg``, over a
    floor (z = 0); ``shapes`` are upright cylinders (x, y, radius, z low, z high) and boxes
    ((x, y, z) low, (x, y, z) high). Depth by ray casting, so surfaces hide what is behind them."""
    tilt = math.radians(tilt_deg)
    s, c = math.sin(tilt), math.cos(tilt)
    pose = np.array([[0, -s, c, 0], [-1, 0, 0, 0], [0, -c, -s, 0.6], [0, 0, 0, 1.0]])
    cols, rows = np.meshgrid(np.arange(width), np.arange(height))
    rays = np.stack([(cols - width / 2) / focal, (rows - height / 2) / focal, np.ones(cols.shape)], -1)
    world = rays @ pose[:3, :3].T  # Per unit of optical depth.
    eye = pose[:3, 3]
    best = np.where(world[..., 2] < 0, -eye[2] / np.minimum(world[..., 2], -1e-9), 10.0)  # The floor.
    for shape in shapes:
        if len(shape) == 5:  # A cylinder: its side, then its top disc.
            x, y, radius, low, high = shape
            ox, oy = eye[0] - x, eye[1] - y
            a = world[..., 0] ** 2 + world[..., 1] ** 2
            b = 2 * (ox * world[..., 0] + oy * world[..., 1])
            disc = b**2 - 4 * a * (ox**2 + oy**2 - radius**2)
            t = (-b - np.sqrt(np.maximum(disc, 0))) / (2 * a)
            z = eye[2] + t * world[..., 2]
            side = (disc >= 0) & (t > 0) & (z >= low) & (z <= high)
            best = np.where(side & (t < best), t, best)
            t = (high - eye[2]) / np.minimum(world[..., 2], -1e-9)
            hx, hy = eye[0] + t * world[..., 0] - x, eye[1] + t * world[..., 1] - y
            cap = (t > 0) & (hx**2 + hy**2 <= radius**2)
            best = np.where(cap & (t < best), t, best)
        else:  # A box: the slab method.
            low, high = (np.asarray(corner, dtype=float) for corner in shape)
            with np.errstate(divide="ignore", invalid="ignore"):
                t0, t1 = (low - eye) / world, (high - eye) / world
            enter = np.nanmax(np.minimum(t0, t1), axis=-1)
            leave = np.nanmin(np.maximum(t0, t1), axis=-1)
            hit = (enter <= leave) & (enter > 0)
            best = np.where(hit & (enter < best), enter, best)
    camera = SimpleNamespace(
        depth=best,
        depth_valid=best < 10.0,
        intrinsics=np.array([[focal, 0, width / 2], [0, focal, height / 2], [0, 0, 1.0]]),
        frame="front",
        stamp=STAMP,
    )
    packet = SimpleNamespace(cameras={"front": camera}, transform=lambda target, source, stamp: pose)
    return packet, pose


def pixel_of_point(packet, point):
    return perception.project(packet, "front", point)


def test_a_round_object_seen_from_aside_is_as_deep_as_it_is_wide_wherever_it_is_pointed_at():
    """A bottle 1 m ahead (body 5 cm wide to 0.13 m, a 2 cm cap to 0.15 m): the camera sees its near
    half only. The box is the bottle's, from its cap or from the middle of its body."""
    packet, _ = side_view([(1.0, 0.0, 0.025, 0.0, 0.13), (1.0, 0.0, 0.01, 0.13, 0.15)])
    for point in ((1.0, 0.0, 0.15), (0.975, 0.0, 0.07)):  # The cap's top; the body's near side.
        center, size = perception.object_box(packet, "front", *pixel_of_point(packet, point))
        assert center[:2] == pytest.approx([1.0, 0.0], abs=0.005), point
        assert size[:2] == pytest.approx([0.05, 0.05], abs=0.006) and size[2] == pytest.approx(0.15, abs=0.005)


def test_a_flat_topped_box_seen_from_aside_keeps_the_depth_its_top_shows():
    """A box 10 cm deep (along the view) and 4 cm wide: its top shows its far edge, so it stays 10 cm deep."""
    packet, _ = side_view([((0.95, -0.02, 0.0), (1.05, 0.02, 0.06))])
    center, size = perception.object_box(packet, "front", *pixel_of_point(packet, (1.0, 0.0, 0.06)))
    assert center[:2] == pytest.approx([1.0, 0.0], abs=0.006)
    assert size == pytest.approx([0.1, 0.04, 0.06], abs=0.008)


def test_pick_hands_the_box_it_measured_to_the_composite_pick(monkeypatch):
    """The box on the floor 1.4 m ahead (world x) and 0.1 m left: the composite pick gets the box the
    depth measured (it walks into reach and looks itself); the harness makes no call of its own."""
    picked = []

    def pick(self, center, size, part=None):
        picked.append(SimpleNamespace(center=tuple(center), size=tuple(size), part=part))
        self.held = "held box"

    monkeypatch.setattr(CompositeSkills, "pick", pick)
    session = FakeSession()
    camera = session.packet.cameras["front"]
    camera.depth = np.full((HEIGHT, WIDTH), 1.0)  # A floor 1 m under a camera looking down at (1.4, 0.1).
    camera.depth[30:51, 40:61] = 0.9  # The box top, 0.1 m above the floor.
    down = np.array([[1, 0, 0, 1.4], [0, -1, 0, 0.1], [0, 0, -1, 1.0], [0, 0, 0, 1.0]])
    session.packet.transform = lambda target, source, stamp: down
    results = run_loop(session, ScriptedOrchestrator([SkillCall("pick", {"camera": "front", "u": 50, "v": 40})]))
    assert results[0].ok, results[0].reason
    (target,) = picked
    assert target.center == pytest.approx((1.4, 0.1, 0.05), abs=0.01) and session.calls == []
    assert target.part is None  # No drawer opened.
    session.manipulation.holding = True  # A later stow carries the box the pick measured.
    run_loop(session, ScriptedOrchestrator([SkillCall("stow")]))
    assert session.calls[-1] == ("stow", "held box")


def test_a_pixel_without_depth_takes_the_nearest_surface_around_it_not_the_background():
    packet = fake_packet(handle=False)  # The wall 2 m ahead.
    camera = packet.cameras["front"]
    camera.depth[38:43, 46:49] = 1.0  # A thin post 1 m ahead, left of the pixel.
    camera.depth_valid[38:43, 49:52] = False  # Its edge, around the pixel (50, 40), has no depth.
    assert perception.valid_pixel(packet, "front", 50, 40) == (48, 40)
    assert perception.valid_pixel(packet, "front", 30, 40) == (30, 40)  # A pixel with depth is itself.


def test_a_pick_in_the_drawer_the_harness_opened_gets_that_drawer(monkeypatch):
    """The drawer front at x 1.98 m faces -x; pulled 0.29 m (as far as the arm reaches), its handle
    ends at x 1.69 m. An object 0.39 m behind it gets the drawer (the composite pick stands square to
    it, clear of it first), and so does one 0.5 m to the handle's side (the house's kitchen island
    drawer is 1.6 m wide); one on the floor beside the robot does not; after a close, none does."""
    monkeypatch.setattr(
        CompositeSkills, "_stroke", lambda self, part, kind, length: (Motion("succeeded"), {}, dict(moved_m=length))
    )
    picked = []
    monkeypatch.setattr(CompositeSkills, "pick", lambda self, center, size, part=None: picked.append(part))
    boxes = iter([(2.08, 0.05, 0.75), (2.08, 0.5, 0.75), (0.5, 1.0, 0.05), (2.08, 0.05, 0.75)])
    monkeypatch.setattr(perception, "object_box", lambda *a: (np.array(next(boxes)), np.array([0.05, 0.05, 0.15])))
    pointed = {"camera": "front", "u": 50, "v": 50}
    calls = [SkillCall("open_drawer", pointed), *[SkillCall("pick", pointed)] * 3]
    session = FakeSession(walks=True)
    assert all(r.ok for r in run_loop(session, ScriptedOrchestrator(calls))[:-1])
    inside, aside, beside = picked
    pulled = TUNING.grip_range_m[1] - TUNING.goal_tolerance[0] - TUNING.grip_range_m[0]
    assert inside.handle_center[0] == pytest.approx(1.98 - pulled) and inside.opening == pytest.approx(pulled)
    assert inside.direction == pytest.approx((-1.0, 0.0, 0.0), abs=1e-6) and aside is inside and beside is None
    calls = [SkillCall("close_drawer", pointed), SkillCall("pick", pointed)]
    assert all(r.ok for r in run_loop(session, ScriptedOrchestrator(calls))[:-1])
    assert picked[-1] is None


def test_a_close_pushes_the_drawer_the_harness_opened_back_as_far_as_it_pulled_it(monkeypatch):
    """Measured again where the pull left it, the opened drawer's handle is the one the harness pulled:
    the close pushes it back that far (less the slide's margin, as the oracle's close). The harness
    then forgets it: a close of a drawer it did not open pushes ``PUSH_M``."""
    strokes = []
    monkeypatch.setattr(
        CompositeSkills,
        "_stroke",
        lambda self, part, kind, length: strokes.append((kind, length))
        or (Motion("succeeded"), {}, dict(moved_m=length)),
    )
    pointed = {"camera": "front", "u": 50, "v": 50}
    session = FakeSession(walks=True)
    assert run_loop(session, ScriptedOrchestrator([SkillCall("open_drawer", pointed)]))[0].ok
    ((_, pulled),) = strokes
    measure = perception.protruding_point
    monkeypatch.setattr(perception, "protruding_point", lambda *a: measure(*a) - np.array([pulled, 0.0, 0.0]))
    calls = [SkillCall("close_drawer", pointed), SkillCall("close_drawer", pointed)]
    assert all(r.ok for r in run_loop(session, ScriptedOrchestrator(calls))[:-1])
    assert strokes[1:] == [("close", pytest.approx(pulled - TUNING.limit_margin_m)), ("close", pytest.approx(PUSH_M))]


def test_open_drawer_stands_a_tolerance_nearer_when_the_handle_was_out_of_reach(monkeypatch):
    strokes = iter([None, (Motion("succeeded"), {}, dict(moved_m=0.25))])  # Every pitch refused, then pulled.
    monkeypatch.setattr(CompositeSkills, "_stroke", lambda self, part, kind, length: next(strokes))
    session = FakeSession()
    results = run_loop(session, ScriptedOrchestrator([SkillCall("open_drawer", {"camera": "front", "u": 50, "v": 50})]))
    assert results[0].ok, results[0].reason
    walks = [call[1][0] for call in session.calls if call[0] == "navigate_to"]
    far, tolerance = TUNING.grip_range_m[1], TUNING.goal_tolerance[0]
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

    start, turn = [json_module.loads(line) for line in (tmp_path / "agent" / "turns.jsonl").read_text().splitlines()]
    assert start["kind"] == "start" and "Find and retrieve: the box" in start["system_prompt"]
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


def test_a_target_the_named_camera_does_not_show_is_looked_for_in_the_other_cameras():
    class Pointing(ScriptedOrchestrator):
        def point(self, image, target):
            return None if image.shape[1] == WIDTH else (5.0, 5.0)  # Only the narrow camera shows it.

    session = FakeSession()
    session.packet.cameras["side"] = SimpleNamespace(**vars(session.packet.cameras["front"]))
    session.packet.cameras["side"].rgb = np.zeros((HEIGHT, WIDTH // 2, 3), dtype=np.uint8)
    results = run_loop(session, Pointing([SkillCall("look_at", {"camera": "front", "target": "the box"})]))
    assert results[0].ok and results[0].reason.startswith("(found in 'side', not 'front')")


def test_a_model_run_records_the_model_and_its_settings(tmp_path, monkeypatch):
    from foragebench.agents import vlm

    monkeypatch.setenv("FORAGEBENCH_ORCHESTRATOR", "openai")
    monkeypatch.setenv("FORAGEBENCH_MODEL", "Qwen/Qwen3.5-9B")
    monkeypatch.setenv("FORAGEBENCH_BASE_URL", "http://localhost:8000/v1")
    monkeypatch.setenv("FORAGEBENCH_API_KEY_ENV", "")
    monkeypatch.setenv("FORAGEBENCH_THINKING", "0")
    monkeypatch.setenv("FORAGEBENCH_AGENT_DIR", str(tmp_path / "agent"))
    monkeypatch.setattr(vlm, "run_loop", lambda session, chosen, loop: None)
    vlm.run(SimpleNamespace())
    import json as json_module

    record = json_module.loads((tmp_path / "agent" / "model.json").read_text())
    assert record["model"] == "Qwen/Qwen3.5-9B" and record["base_url"] == "http://localhost:8000/v1"
    assert record["pointer"] == "qwen" and record["thinking"] is False and record["max_calls"] == 40
