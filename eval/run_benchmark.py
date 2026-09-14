"""Run an orchestrator over ForageBench episodes.

Run from the repo root inside the IsaacLab container:
    isaaclab.sh -p -m eval.run_benchmark --agent agent/configs/gemini_robotics_er.yaml --headless
"""

import argparse
from pathlib import Path

import yaml
from isaaclab.app import AppLauncher

parser = argparse.ArgumentParser(
    description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
)
parser.add_argument(
    "--agent", type=Path, required=True, help="Orchestrator config in agent/configs/"
)
parser.add_argument("--config", type=Path, default=Path("eval/configs/default.yaml"))
parser.add_argument("--episodes", nargs="*", help="Episode IDs to run (default: all)")
parser.add_argument(
    "--known-target-location",
    action="store_true",
    help="Give the orchestrator ground-truth target coordinates",
)
AppLauncher.add_app_launcher_args(parser)
args = parser.parse_args()
simulation_app = AppLauncher(args).app

# Modules that touch Isaac Sim can only be imported after the app is launched.
from agent.orchestrators import load_orchestrator
from agent.skills.executor import BaselineSkillAPI
from eval.env import ForageBenchEnv
from eval.episode_runner import RunnerConfig, run_episode
from eval.metrics import summarize
from eval.report import format_summary, write_results
from tasks.episode import load_episodes


def main() -> None:
    cfg = yaml.safe_load(args.config.read_text())

    episodes = load_episodes(Path(cfg["episodes_dir"]))
    if args.episodes:
        episodes = [e for e in episodes if e.episode_id in set(args.episodes)]

    orchestrator = load_orchestrator(args.agent)
    env = ForageBenchEnv(
        physics_hz=cfg["sim"]["physics_hz"],
        traversal_tolerance_m=cfg["metrics"]["traversal_tolerance_m"],
    )
    skills = BaselineSkillAPI(env.robot)
    runner_config = RunnerConfig(
        known_target_location=args.known_target_location,
        max_repeated_skill=cfg["termination"]["max_repeated_skill"],
        max_steps=cfg["termination"]["max_steps"],
    )

    outcomes = []
    for episode in episodes:
        outcome = run_episode(env, orchestrator, skills, episode, runner_config)
        print(f"{episode.episode_id}: {outcome.termination} (IOSS={outcome.ioss})")
        outcomes.append(outcome)
    env.close()

    summary = summarize(outcomes, cfg["metrics"]["spl_m_manipulation_cost"])
    condition = "known" if args.known_target_location else "unknown"
    write_results(
        outcomes, summary, Path(cfg["output_dir"]) / f"{args.agent.stem}_{condition}.json"
    )
    print(format_summary(summary))


if __name__ == "__main__":
    main()
    simulation_app.close()
