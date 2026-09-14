# eval/

Evaluation scripts and post-episode metric reporting from IsaacLab.

## Running the benchmark

From the repo root, inside the IsaacLab container:

```bash
ISAACLAB=/workspace/isaaclab/isaaclab.sh

# Unknown target location (default)
$ISAACLAB -p -m eval.run_benchmark --agent agent/configs/gemini_robotics_er.yaml --headless

# Known target location: ground-truth target coordinates are added to the prompt
$ISAACLAB -p -m eval.run_benchmark --agent agent/configs/qwen3_vl.yaml --known-target-location --headless
```

Results are written to `outputs/` as per-episode outcomes plus a summary.

## Layout

- `run_benchmark.py`: entry point that launches IsaacSim and runs every episode
- `episode_runner.py`: the orchestrator → skill → termination loop for one episode
- `env.py`: PhyGS / IsaacLab environment (scene loading, reset, sim-state checks)
- `termination.py`: episode termination conditions
- `metrics.py`: TS, IOSS, skill execution success, SPL, SPL-M
- `report.py`: writes results and formats summaries
- `configs/default.yaml`: benchmark settings

## Episode termination

The simulator steps at 60 Hz. An episode ends in **failure** on any of:

- collision
- leaving the house bounds
- selecting an incompatible skill
- repeating the same skill three consecutive times
- calling `report_found` on the wrong object

An episode also ends if it exceeds the step budget.

## Metrics

| Metric | Definition |
|---|---|
| TS | Agent is within 0.6 m of the target location, required manipulations succeeded, and it signaled `report_found` or fail from there |
| IOSS | TS, plus the target was picked and `report_found` issued after the pick |
| Skill execution success | Fraction of skill invocations that returned no error |
| SPL | IOSS weighted by path length, including auxiliary inspection and articulation motions |
| SPL-M | SPL whose trajectory cost also counts manipulation actions |
