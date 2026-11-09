# Copyright (c) 2022-2026, The Isaac Lab Project Developers (https://github.com/isaac-sim/IsaacLab/blob/main/CONTRIBUTORS.md).
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""Run one ForageBench episode: an episode file, a track, an agent; write ``result.json``.

    isaaclab -p -m foragebench run --episode dev/grid_table --track privileged \\
        --agent null --output $FORAGEBENCH/output_check/$(date +%Y%m%d-%H%M)_grid_table_null

``--episode`` is an id of the manifest's sets (``dev/grid_table``) or the path of an episode file;
``--track`` a name in ``foragebench/tracks`` or a path; ``--agent`` a module of
``foragebench.agents`` (``null``, ``template``, ``oracle``) or ``path/to/file.py:function``.
The benchmark rules (``configs/benchmark_v1.yaml``) pin the PhyGS release (version and commit), the
backends and the end-of-episode settings; the result records them with the episode's scene release
and every hash PhyGS puts in the report's provenance. A run on another PhyGS goes ahead and says why
it is unpinned (``provenance.unpinned``). ``result.json`` is written in every case: its ``status`` is
``completed`` (scored), ``setup_error`` (PhyGS's start check failed; the agent never ran) or ``error``
(the simulator or the World broke). The exit code is 1 only for ``error``. It names the run's
``run_id`` (its recording, ``episode.rrd``) and, for a model agent, the model's totals read from that
recording (turns, pointing queries, errors by origin, tokens, seconds, retries).

``--repeats N`` runs N episodes in this one simulator process (seeds ``seed`` to ``seed + N - 1``,
each in ``<output>/s<seed>``): PhyGS restores the start state between them (``World.next_episode``),
so only the first pays Isaac Sim's start-up. Every result says which episode of its process it was
(``episode_in_process``).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import traceback
from pathlib import Path

import yaml
from isaaclab.app import AppLauncher
from phygs.world import EpisodeSpec

import foragebench
from foragebench.agents import load_agent
from foragebench.episodes import load_episode
from foragebench.eval import results
from foragebench.eval.results import grasps
from foragebench.tasks import load_task

ROOT = Path(__file__).resolve().parents[2]  # The ForageBench checkout (installed editable).

parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument("--episode", required=True, help="Manifest id (dev/grid_table) or an episode file")
parser.add_argument("--track", default="privileged", help="A track in foragebench/tracks, or a path")
parser.add_argument("--agent", required=True, help="A module of foragebench.agents, or path/to/file.py:function")
parser.add_argument("--output", type=Path, required=True, help="A fresh output folder (date-time prefix)")
parser.add_argument("--benchmark", type=Path, default=ROOT / "configs" / "benchmark_v1.yaml")
parser.add_argument("--seed", type=int, default=None, help="Override the episode's seed")
parser.add_argument("--repeats", type=int, default=1, help="Episodes in this process, seeds seed..seed+N-1")
parser.add_argument("--robot", default=None, help="Run with another robot: a PhyGS robot name or a robot.yaml")
AppLauncher.add_app_launcher_args(parser)
parser.set_defaults(device="cpu", enable_cameras=True)
args = parser.parse_args()

rules = yaml.safe_load(args.benchmark.read_text())
pin = foragebench.pin_problems(rules, foragebench.phygs_version(), foragebench.phygs_code())
if pin:  # Another PhyGS runs, marked unpinned in result.json (provenance.unpinned).
    print(f"foragebench: an unpinned run, its results are not publishable: {'; '.join(pin)}.", flush=True)
episode = load_episode(args.episode, track=args.track, manifest=ROOT / rules["manifest"])
spec = EpisodeSpec.from_dict(episode.spec, base=episode.path.parent)  # Validated before Isaac Sim starts.
if args.seed is not None:
    spec = spec.with_seed(args.seed)
task = load_task(spec.task)  # One task object; the World resets it before each episode.


agent_name, agent, prepare = load_agent(args.agent)
if args.repeats < 1:
    parser.error("--repeats is at least 1")
SEEDS = [spec.seed + k for k in range(args.repeats)]
# One run: its result in --output; repeats: one folder per seed under it.
FOLDERS = [args.output] if args.repeats == 1 else [args.output / f"s{seed}" for seed in SEEDS]
for folder in FOLDERS:
    if (folder / "result.json").exists():
        parser.error(f"{folder} holds a finished run; choose a fresh output folder")
args.output.mkdir(parents=True, exist_ok=True)
app = AppLauncher(args).app

from phygs.robots.description import load_robot  # noqa: E402
from phygs.world import SETTINGS, World, code_version, file_sha256, load_settings  # noqa: E402 (after the app starts)

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


def skill_counts(commands: list[dict]) -> dict:
    """Commands issued per client and how many ended ``succeeded``/``done``, from the report's audit."""
    seen: dict[tuple[str, int], str] = {}
    for item in commands:
        client = item["call"].split(".")[0]
        feedback = next(iter(item["feedback"].values())) if isinstance(item.get("feedback"), dict) else {}
        seen[(client, item["command"])] = str(feedback.get("status", ""))
    return dict(
        skill_calls=len(seen),
        skill_successes=sum(status in ("succeeded", "done") for status in seen.values()),
        manipulation_commands=sum(1 for (client, _) in seen if client == "manipulation"),
    )


def identity(seed: int) -> dict:
    """What every result names, whatever its status."""
    return dict(
        benchmark=rules["benchmark"],
        episode=episode.id,
        set=episode.set,
        track=episode.track,
        agent=agent_name,
        robot=robot.name,
        seed=seed,
    )


def agent_setup(folder: Path) -> dict | None:
    """What the agent says produced the run: its ``agent/model.json`` (model, server, pointing,
    thinking, budgets), with that file's hash; None for an agent that writes none."""
    path = folder / "agent" / "model.json"
    if not path.is_file():
        return None
    return dict(json.loads(path.read_text()), sha256=file_sha256(path))


def model_totals(folder: Path) -> dict | None:
    """The model's totals (:func:`foragebench.eval.results.model_totals`) from the run's recording."""
    from phygs.recording.reader import Recording

    return results.model_totals(Recording(folder).agent_log()) if (folder / "episode.rrd").is_file() else None


def write_error(folder: Path, seed: int, reason: str) -> None:
    """The result of a run that broke, or never ran because an earlier one broke the process."""
    folder.mkdir(parents=True, exist_ok=True)
    report = folder / "report.json"
    result = dict(
        **identity(seed),
        status="error",
        reason=reason,
        run_id=json.loads(report.read_text()).get("run_id") if report.exists() else None,
        report="report.json" if report.exists() else None,
    )
    (folder / "result.json").write_text(json.dumps(result, indent=1))


def main() -> int:
    done, code = 0, 0
    try:
        if prepare is not None:
            prepare(spec, robot)  # An agent that needs the spec and the robot before the episode.
        overrides = benchmark_overrides()
        with World(
            spec.with_seed(SEEDS[0]),
            FOLDERS[0],
            clock=rules["clock"],
            device=args.device,
            overrides=overrides,
            robot=robot,
            task=task,
            target=episode.answer["target"],  # The privileged target; the grants decide what the agent learns.
        ) as world:
            for k, (seed, folder) in enumerate(zip(SEEDS, FOLDERS, strict=True)):
                if k:
                    world.next_episode(folder, seed=seed)
                os.environ["FORAGEBENCH_AGENT_DIR"] = str(folder / "agent")  # The agent's own log, if it keeps one.
                report = world.run(agent, name=agent_name)
                code = max(code, write_result(folder, seed, report, episode_in_process=world.episodes))
                done += 1
    except BaseException:
        if done < len(SEEDS):  # Else every episode has its result and closing the World broke.
            lines = traceback.format_exc().strip().splitlines()
            write_error(FOLDERS[done], SEEDS[done], lines[-1] if lines else "unknown")
            for seed, folder in zip(SEEDS[done + 1 :], FOLDERS[done + 1 :], strict=True):
                write_error(folder, seed, f"not run: the episode with seed {SEEDS[done]} broke this process")
        raise
    return code


def write_result(folder: Path, seed: int, report: dict, *, episode_in_process: int) -> int:
    """``result.json`` for one episode's report; returns the exit code it asks for (1 for error)."""
    evaluation = report["evaluation"]
    counts = skill_counts(report["commands"])
    result = dict(
        **identity(seed),
        run_id=report["run_id"],  # The recording's id (episode.rrd): every file of the run carries it.
        status=report["status"],
        outcome=evaluation.get("outcome"),
        # Not scored: why (the start check's problems), not the evaluation's "not evaluated".
        reason=evaluation.get("reason") if report["status"] == "completed" else report["reason"],
        checks=evaluation.get("checks"),
        reached=evaluation.get("reached"),
        progress=evaluation.get("progress"),
        furthest=evaluation.get("furthest"),
        conduct=evaluation.get("conduct"),
        clean=evaluation.get("clean"),
        ended_by=report["ended_by"],
        rules=dict(
            version=evaluation.get("rules_version"),
            thresholds_sha256=report["provenance"].get("evaluator_thresholds"),
        ),
        path_length_m=(evaluation.get("measured") or {}).get("path_length_m"),
        optimal_path_length_m=episode.optimal_path_length_m,
        manipulations=grasps(report.get("grasp_contacts", [])),  # Holds of a handle or an object (SPL-M's unit).
        manipulation_commands=counts["manipulation_commands"],
        optimal_manipulations=episode.optimal_manipulations,
        skill_calls=counts["skill_calls"],
        skill_successes=counts["skill_successes"],
        sim_seconds=report["sim_seconds"],
        wall_seconds=report["wall_seconds"],
        episode_in_process=episode_in_process,  # 1: a fresh process; more: a repeat after a reset.
        usage=report["usage"],
        agent_setup=agent_setup(folder),
        model=model_totals(folder),
        scene=dict(id=spec.scene.id, version=spec.scene.version, usd_sha256=report["provenance"]["scene_usd"]),
        provenance=dict(
            **report["provenance"],
            phygs_version=foragebench.phygs_version(),
            # Why PhyGS is not the pinned release, from the commit and dirty flag it recorded; empty when it is.
            unpinned=foragebench.pin_problems(rules, foragebench.phygs_version(), report["provenance"]["code"]),
            foragebench=code_version(ROOT),
            benchmark_rules=file_sha256(args.benchmark),
            track=episode.track_sha256,
            episode_file=file_sha256(episode.path),
        ),
        report="report.json",
    )
    (folder / "result.json").write_text(json.dumps(result, indent=1))
    print(
        f"{episode.set}/{episode.id} [{episode.track}] {agent_name} seed {seed} {result['status']}:"
        f" {result['outcome']} ({result['reason']}), clean={result['clean']}, ended by {result['ended_by']}"
        f" after {result['sim_seconds']} s; {folder}/result.json",
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
