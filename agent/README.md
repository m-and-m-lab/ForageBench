# agent/

Baseline agent: a vision-language model orchestrating a library of low-level skills on a Boston
Dynamics Spot with Arm.

| Path | Contents |
|---|---|
| `interface/` | Skill and perception APIs that mirror the Boston Dynamics Spot SDK |
| `skills/` | Baseline skill implementations using AO-Grasp, Contact-GraspNet, and cuRobo |
| `orchestrators/` | Qwen3-VL-8B-Instruct and Gemini Robotics ER-1.6 orchestrators, plus prompts |
| `configs/` | Orchestrator configs, passed to `eval/run_benchmark.py --agent` |

## Skill API

| Skill | Argument |
|---|---|
| `navigate` | `target` |
| `place` | `receptacle` |
| `open_door` / `close_door` | `reference` |
| `open_drawer` / `close_drawer` | `reference` |
| `report_found` | `object` |

Skills can be called synchronously (`execute`) or asynchronously (`execute_async`). Each call
returns a `SkillResult` with a status. Perception goes through `get_image_from_sources`, and frame
helpers convert camera-frame detections to the world frame.

This interface is optional. ForageBench exposes continuous control of the robot, so methods can
bring their own skills or autonomy stack.

## Adding an orchestrator

1. Subclass `Orchestrator` in `orchestrators/base.py`.
2. Register it in `orchestrators/__init__.py`.
3. Add a config under `configs/`.
