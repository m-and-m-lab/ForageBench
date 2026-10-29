# tasks/

What is asked and how it is scored. One task today: **retrieve**.

| Path | Contents |
| --- | --- |
| `retrieve/evaluator.py` | `RetrieveTask`: the public brief, the privileged target name, and `result()`, the evaluator PhyGS calls once after the robot has stopped and settled. |
| `retrieve/thresholds.yaml` | The numbers behind every check and their `version`; every result names the version (`rules.version`) and the file's hash (`evaluator_thresholds`). Change a number: raise the version. |
| `__init__.py` | `load_task(block)`: an episode's `task` block to the task object PhyGS takes (`phygs.world.task.Task`). |

## Success

All four, read from ground truth, never from skill feedback:

| Check | Threshold |
| --- | --- |
| held | the target is ≥ 0.05 m above where it started and its centre ≤ 0.35 m from the wrist |
| stowed | every arm joint within 0.05 rad of the stow posture |
| upright | the base's up axis within 15° of vertical |
| in_time | the episode ended by the agent's `finish` or return, before the budget |

## Conduct, reported beside the outcome

| Finding | Threshold |
| --- | --- |
| unintended contact | arm-link contact ≥ 0.5 N (the squeeze on a grasped body excluded); count and peak force |
| drawer left open | any drawer the agent opened that is > 0.03 m open at the end |

`clean` is true when there is no finding. A new task is a folder here with a brief, an evaluator, a
thresholds file, a fake-ground-truth test in `tests/`, and a paragraph in `docs/task_card.md`.
