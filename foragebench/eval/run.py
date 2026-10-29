# Copyright (c) 2022-2026, The Isaac Lab Project Developers (https://github.com/isaac-sim/IsaacLab/blob/main/CONTRIBUTORS.md).
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""Run one ForageBench episode: an episode file, a track, an agent; write ``result.json``.

    ./isaaclab.sh -p -m foragebench run --episode dev/grid_table --track privileged \\
        --agent null --output $FORAGEBENCH/output_check/$(date +%Y%m%d-%H%M)_grid_table_null

``--episode`` is an id of the manifest's sets (``dev/grid_table``) or the path of an episode file;
``--track`` a name in ``foragebench/tracks`` or a path; ``--agent`` a module of
``foragebench.agents`` (``null``, ``template``, ``oracle``) or ``path/to/file.py:function``.
The benchmark rules (``configs/benchmark_v1.yaml``) pin the PhyGS version, the backends and the
end-of-episode settings; the result records them with the episode's scene release and every hash
PhyGS puts in the report's provenance. ``result.json`` is written in every case: its ``status`` is
``completed`` (scored), ``setup_error`` (PhyGS's start check failed; the agent never ran) or ``error``
(the simulator or the World broke). The exit code is 1 only for ``error``.
"""

from __future__ import annotations

import argparse
import json
import sys
import traceback
from pathlib import Path

import yaml
from isaaclab.app import AppLauncher
from phygs.world.spec import EpisodeSpec

import foragebench
from foragebench.agents import load_agent
from foragebench.episodes import load_episode
from foragebench.tasks import load_task

ROOT = Path(__file__).resolve().parents[2]  # The ForageBench checkout (installed editable).

parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument("--episode", required=True, help="Manifest id (dev/grid_table) or an episode file")
parser.add_argument("--track", default="privileged", help="A track in foragebench/tracks, or a path")
parser.add_argument("--agent", required=True, help="A module of foragebench.agents, or path/to/file.py:function")
parser.add_argument("--output", type=Path, required=True, help="A fresh output folder (date-time prefix)")
parser.add_argument("--benchmark", type=Path, default=ROOT / "configs" / "benchmark_v1.yaml")
parser.add_argument("--seed", type=int, default=None, help="Override the episode's seed")
parser.add_argument("--robot", default=None, help="Run with another robot: a PhyGS robot name or a robot.yaml")
parser.add_argument("--record", action="store_true", help="Write a third-person video")
AppLauncher.add_app_launcher_args(parser)
parser.set_defaults(device="cpu", enable_cameras=True)
args = parser.parse_args()

rules = yaml.safe_load(args.benchmark.read_text())
foragebench.check_phygs_version(rules["phygs_version"])
episode = load_episode(args.episode, track=args.track, manifest=ROOT / rules["manifest"])
spec = EpisodeSpec.from_dict(episode.spec, base=episode.path.parent)  # Validated before Isaac Sim starts.
if args.seed is not None:
    spec = spec.with_seed(args.seed)
task = load_task(spec.task)


agent_name, agent, prepare = load_agent(args.agent)
if (args.output / "result.json").exists():
    parser.error(f"{args.output} holds a finished run; choose a fresh output folder")
args.output.mkdir(parents=True, exist_ok=True)
app = AppLauncher(args).app

from phygs.robots.description import load_robot  # noqa: E402
from phygs.world import SETTINGS, World  # noqa: E402 (after the app starts)
from phygs.world.build import load_settings  # noqa: E402
from phygs.world.provenance import code_version, file_sha256  # noqa: E402

robot = load_robot(args.robot or spec.robot.model)
robot.validate_urdf()


def benchmark_overrides() -> dict:
    """The rules' pins over PhyGS's settings (``environment.yaml``): the end of the episode and the
    backends. The settings the run used are written beside the result, for the record."""
    overrides = dict(
        rules["environment"],
        planner={"backend": rules["backends"]["planner"]},
        skills={"backend": rules["backends"]["skills"]},
    )
    used = load_settings(SETTINGS, overrides)
    (args.output / "environment.yaml").write_text(yaml.safe_dump(used, sort_keys=False))
    return overrides


class PathLength:
    """Planar distance the base travelled [m], integrated from ground truth every ``every`` ticks."""

    def __init__(self, every: int = 25) -> None:
        self.every, self.calls, self.metres, self._last = every, 0, 0.0, None

    def __call__(self, world) -> None:
        self.calls += 1
        if self.calls % self.every:
            return
        xy = world.truth().base_pose()[:2, 3]
        if self._last is not None:
            self.metres += float(((xy - self._last) ** 2).sum() ** 0.5)
        self._last = xy.copy()


def skill_counts(commands: list[dict]) -> dict:
    """Commands issued per client and how many ended ``succeeded``/``done``, from the report's audit."""
    seen: dict[tuple[str, int], str] = {}
    for item in commands:
        client = item["call"].split(".")[0]
        feedback = next(iter(item["feedback"].values())) if isinstance(item.get("feedback"), dict) else {}
        seen[(client, item["command"])] = str(feedback.get("status", ""))
    manipulations = sum(1 for (client, _) in seen if client == "manipulation")
    return dict(
        skill_calls=len(seen),
        skill_successes=sum(status in ("succeeded", "done") for status in seen.values()),
        manipulations=manipulations,
    )


def identity() -> dict:
    """What every result names, whatever its status."""
    return dict(
        benchmark=rules["benchmark"],
        episode=episode.id,
        set=episode.set,
        track=episode.track,
        agent=agent_name,
        robot=robot.name,
        seed=spec.seed,
    )


def write_error(trace: str) -> None:
    """The result of a run that broke: status ``error`` and the last line of the traceback."""
    lines = trace.strip().splitlines()
    result = dict(
        **identity(),
        status="error",
        reason=lines[-1] if lines else "unknown",
        report="report.json" if (args.output / "report.json").exists() else None,
    )
    (args.output / "result.json").write_text(json.dumps(result, indent=1))


def main() -> int:
    if prepare is not None:
        prepare(spec, robot)  # The oracle's routines learn the scene and the robot.
    overrides = benchmark_overrides()
    path = PathLength()
    try:
        with World(
            spec,
            args.output,
            clock=rules["clock"],
            record=args.record,
            device=args.device,
            overrides=overrides,
            robot=robot,
            task=task,
        ) as world:
            report = world.run(agent, name=agent_name, during=path)
    except BaseException:
        write_error(traceback.format_exc())
        raise
    evaluation = report["evaluation"]
    counts = skill_counts(report["commands"])
    result = dict(
        **identity(),
        status=report["status"],
        outcome=evaluation.get("outcome"),
        # Not scored: why (the start check's problems), not the evaluation's "not evaluated".
        reason=evaluation.get("reason") if report["status"] == "completed" else report["reason"],
        checks=evaluation.get("checks"),
        conduct=evaluation.get("conduct"),
        clean=evaluation.get("clean"),
        ended_by=report["ended_by"],
        rules=dict(
            version=evaluation.get("rules_version"),
            thresholds_sha256=report["provenance"].get("evaluator_thresholds"),
        ),
        tier=None if episode.tier is None else int(episode.tier),
        path_length_m=round(path.metres, 3),
        optimal_path_length_m=episode.optimal_path_length_m,
        manipulations=counts["manipulations"],
        optimal_manipulations=episode.optimal_manipulations,
        skill_calls=counts["skill_calls"],
        skill_successes=counts["skill_successes"],
        sim_seconds=report["sim_seconds"],
        wall_seconds=report["wall_seconds"],
        usage=report["usage"],
        scene=dict(id=spec.scene.id, version=spec.scene.version, usd_sha256=report["provenance"]["scene_usd"]),
        provenance=dict(
            **report["provenance"],
            phygs_version=foragebench.phygs_version(),
            foragebench=code_version(ROOT),
            benchmark_rules=file_sha256(args.benchmark),
            track=episode.track_sha256,
            episode_file=file_sha256(episode.path),
        ),
        report="report.json",
    )
    (args.output / "result.json").write_text(json.dumps(result, indent=1))
    print(
        f"{episode.set}/{episode.id} [{episode.track}] {agent_name} {result['status']}: {result['outcome']}"
        f" ({result['reason']}), clean={result['clean']}, ended by {result['ended_by']} after"
        f" {result['sim_seconds']} s; {args.output}/result.json",
        flush=True,
    )
    return 1 if result["status"] == "error" else 0


if __name__ == "__main__":
    code = 1
    try:
        code = main()
    except BaseException:
        traceback.print_exc()  # Closing Isaac Sim ends the process before Python would print it.
        sys.stderr.flush()
    finally:
        app.close(exit_code=code)
