# Copyright (c) 2022-2026, The Isaac Lab Project Developers (https://github.com/isaac-sim/IsaacLab/blob/main/CONTRIBUTORS.md).
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""What a run would do, without the simulator: ``foragebench describe``.

Takes ``foragebench run``'s episode, track and agent and prints the resolved run: the benchmark rules
and the PhyGS pin, the episode and whether its scene is present, the track's actions and grants, the
task's rules version, the agent, the budget and the seed. The exit code is 1 when the run would be
refused (the installed PhyGS is not the pinned one, or the scene is missing). Check a run here before
spending a simulator on it.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import yaml
from phygs.scene.registry import scene_file
from phygs.world.spec import EpisodeSpec

import foragebench
from foragebench.agents import load_agent
from foragebench.episodes import load_episode
from foragebench.tasks import load_task

ROOT = Path(__file__).resolve().parents[2]  # The ForageBench checkout (installed editable).


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--episode", required=True, help="Manifest id (dev/grid_table) or an episode file")
    parser.add_argument("--track", default="privileged", help="A track in foragebench/tracks, or a path")
    parser.add_argument("--agent", required=True, help="A module of foragebench.agents, or path/to/file.py:function")
    parser.add_argument("--benchmark", type=Path, default=ROOT / "configs" / "benchmark_v1.yaml")
    parser.add_argument("--seed", type=int, default=None, help="Override the episode's seed")
    args = parser.parse_args(argv)
    rules = yaml.safe_load(args.benchmark.read_text())
    episode = load_episode(args.episode, track=args.track, manifest=ROOT / rules["manifest"])
    spec = EpisodeSpec.from_dict(episode.spec, base=episode.path.parent)
    if args.seed is not None:
        spec = spec.with_seed(args.seed)
    task = load_task(spec.task)
    agent, _, prepare = load_agent(args.agent)
    pinned, installed = str(rules["phygs_version"]), foragebench.phygs_version()
    try:
        scene = f"present: {scene_file(spec.scene.id, spec.scene.version)}"
        scene_ok = True
    except (FileNotFoundError, ValueError) as error:
        scene, scene_ok = f"MISSING: {error}", False
    release = spec.scene.id if spec.scene.version is None else f"{spec.scene.id}@{spec.scene.version}"
    rows = [
        ("benchmark", f"{rules['benchmark']} ({args.benchmark})"),
        ("PhyGS", f"pinned {pinned}, installed {installed}" + ("" if pinned == installed else "  REFUSED")),
        ("backends", ", ".join(f"{key} {value}" for key, value in rules["backends"].items())),
        ("clock", rules["clock"]),
        ("episode", f"{episode.set or '-'}/{episode.id} ({episode.path})"),
        ("scene", f"{release}, {scene}"),
        ("robot", f"{spec.robot.model}, start {list(spec.robot.start)}"),
        ("track", f"{episode.track}: actions {list(spec.actions)}, grants {list(spec.grants)}"),
        ("task", f"{task.goal}: {task.description!r}"),
        ("rules", f"version {getattr(task, 'rules_version', None)}"),
        ("agent", agent + (" (prepares before the run)" if prepare else "")),
        ("budget", f"{spec.sim_seconds} s simulated, seed {spec.seed}"),
    ]
    for key, value in rows:
        print(f"{key:<10} {value}")
    return 0 if pinned == installed and scene_ok else 1
