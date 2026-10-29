# tasks/

What is asked and how it is scored. One task today: **retrieve**.

| Path | Contents |
| --- | --- |
| `retrieve/evaluator.py` | `RetrieveTask`: the public brief, the target's scene name (from the episode's hidden `answer`), and the evaluator PhyGS drives: `reset` on the settled world before the agent starts, `update` every 0.2 s of simulated time while it runs, `result` once after the robot has stopped and settled. |
| `retrieve/thresholds.yaml` | The numbers behind every check and their `version`; every result names the version (`rules.version`) and the file's hash (`evaluator_thresholds`). Change a number: raise the version. |
| `__init__.py` | `load_task(block)`: an episode's task block (with the answer's target) to the task object PhyGS takes (`phygs.world.task.Task`). |

Everything is read from ground truth, never from skill feedback or from what the agent says.

## Success (outcome)

All four, at the end:

| Check | Threshold |
| --- | --- |
| held | the target is ≥ 0.05 m above where it started, its centre ≤ 0.35 m from the wrist, and every jaw presses on it with ≥ 0.5 N |
| stowed | every arm joint within 0.05 rad of the stow posture |
| upright | the base's up axis within 15° of vertical |
| in_time | the episode ended by the agent's `finish` or return, before the budget |

## Reached and progress

**Reached**: the base's centre ends within 1.5 m of the target, or the robot holds it. Spot picks from
0.9–1.2 m (the oracle's stances), so the paper's 0.6 m from the base centre would never count a pick.

**Progress**, from the samples during the run, in order: `reached` (ever within 1.5 m), `opened` (the
drawer the target started in opened more than 5 cm; `null` when it started in the open), `touched`
(an arm link pressed on it), `lifted` (≥ 5 cm above where it started), `held` (the outcome's check).
`furthest` names the last stage the run got to: where a failed run stopped.

## Conduct, reported beside the outcome

| Finding | Threshold |
| --- | --- |
| unintended contact | arm-link contact ≥ 0.5 N (the squeeze on a grasped body excluded); count and peak force |
| drawer left open | any drawer the agent opened that is > 0.03 m open at the end |
| object moved | any other body moved > 0.05 m during the run (one that started in a drawer is measured against that drawer, so riding along in an opened drawer is not moving) |

`clean` is true when there is no finding. A new task is a folder here with a brief, an evaluator, a
thresholds file, a fake-ground-truth test in `tests/`, and a paragraph in `docs/task_card.md`.
