# Copyright (c) 2022-2026, The Isaac Lab Project Developers (https://github.com/isaac-sim/IsaacLab/blob/main/CONTRIBUTORS.md).
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""Run one ForageBench episode: an episode file, a track, an agent; write ``result.json``.

    ./isaaclab.sh -p $FORAGEBENCH/foragebench/run.py --episode dev/grid_table --track privileged \\
        --agent null --output $FORAGEBENCH/output_check/$(date +%Y%m%d-%H%M)_grid_table_null

``--episode`` is an id of the manifest's sets (``dev/grid_table``) or the path of an episode file;
``--track`` a name in ``foragebench/tracks`` or a path; ``--agent`` a module of
``foragebench.agents`` (``null``, ``template``, ``oracle``) or ``path/to/file.py:function``.
The benchmark rules (``configs/benchmark_v1.yaml``) pin the PhyGS version, the backends and the
end-of-episode settings; the result records them with the episode's scene release and every hash
PhyGS puts in the report's provenance. The exit code says the run completed (0) or broke (1); the
outcome is in ``result.json``.
"""

from __future__ import annotations

import argparse
import importlib
import importlib.util
import json
import sys
import traceback
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]  # The ForageBench checkout.
sys.path.insert(0, str(ROOT))  # Runs from a checkout without pip install (PhyGS: third_party/phygs or installed).
if (ROOT / "third_party" / "phygs" / "phygs").is_dir():
    sys.path.insert(1, str(ROOT / "third_party" / "phygs"))

from isaaclab.app import AppLauncher  # noqa: E402
from phygs.episodes.spec import EpisodeSpec  # noqa: E402

import foragebench  # noqa: E402 (after the path; checks the PhyGS version pin)
from foragebench.episodes import load_episode  # noqa: E402
from foragebench.tasks import load_task  # noqa: E402

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


def load_agent(reference: str):
    """(name, run function, prepare function or None)."""
    if ":" in reference:
        path, function = reference.rsplit(":", 1)
        path = Path(path).resolve(strict=True)
        module_spec = importlib.util.spec_from_file_location(f"agent_{path.stem}", path)
        module = importlib.util.module_from_spec(module_spec)
        module_spec.loader.exec_module(module)
        name = f"{path.name}:{function}"
    else:
        module = importlib.import_module(f"foragebench.agents.{reference}")
        function, name = "run", reference
    run = getattr(module, function, None)
    if not callable(run):
        raise ValueError(f"Agent {reference!r} has no function {function!r}.")
    return name, run, getattr(module, "prepare", None)


agent_name, agent, prepare = load_agent(args.agent)
if (args.output / "result.json").exists():
    parser.error(f"{args.output} holds a finished run; choose a fresh output folder")
args.output.mkdir(parents=True, exist_ok=True)
app = AppLauncher(args).app

from phygs.episodes.environment import SETTINGS, Environment  # noqa: E402 (after the app starts)
from phygs.episodes.provenance import code_version, file_sha256  # noqa: E402
from phygs.robots.description import load_robot  # noqa: E402

robot = load_robot(args.robot or spec.robot.model)
robot.validate_urdf()


def settings_for_benchmark() -> Path:
    """PhyGS's environment settings with the benchmark's pins applied, written beside the result."""
    values = yaml.safe_load(SETTINGS.read_text())
    values.update(rules["environment"])
    values["planner"]["backend"] = rules["backends"]["planner"]
    values["skills"]["backend"] = rules["backends"]["skills"]
    path = args.output / "environment.yaml"
    path.write_text(yaml.safe_dump(values, sort_keys=False))
    return path


def main() -> int:
    if prepare is not None:
        prepare(spec, robot)  # The oracle's routines learn the scene and the robot.
    settings = settings_for_benchmark()
    with Environment(
        spec,
        args.output,
        clock=rules["clock"],
        record=args.record,
        device=args.device,
        settings_path=settings,
        robot=robot,
        task=task,
    ) as environment:
        report = environment.run(agent, name=agent_name)
    evaluation = report["evaluation"]
    result = dict(
        benchmark=rules["benchmark"],
        episode=episode.id,
        set=episode.set,
        track=episode.track,
        agent=agent_name,
        robot=robot.name,
        seed=spec.seed,
        outcome=evaluation.get("outcome"),
        reason=evaluation.get("reason"),
        checks=evaluation.get("checks"),
        conduct=evaluation.get("conduct"),
        clean=evaluation.get("clean"),
        ended_by=report["ended_by"],
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
        f"{episode.set}/{episode.id} [{episode.track}] {agent_name}: {result['outcome']} ({result['reason']}),"
        f" clean={result['clean']}, ended by {result['ended_by']} after {result['sim_seconds']} s;"
        f" {args.output}/result.json",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    code = 1
    try:
        code = main()
    except BaseException:
        traceback.print_exc()  # Closing Isaac Sim ends the process before Python would print it.
        sys.stderr.flush()
    finally:
        app.close(exit_code=code)
