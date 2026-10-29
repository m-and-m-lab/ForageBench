# episodes/

An episode file is a PhyGS episode spec plus the benchmark's facts about it (the hidden answer, the
optimal path), without `actions` and `grants` (the track supplies those). The manifest lists which
episodes form a set.

## Schema (schema 3 of PhyGS, plus the benchmark's blocks)

```yaml
schema: 3
id: house_drawer
scene: {id: bear_loop_house, version: 1.1.0, name: house, ground: false}   # a release of the scene dataset, or a fixture
robot: {model: spot, start: [10.2, 6.0, 0.0]}                           # x, y, heading [m, m, rad]
objects: {}                                                             # bodies moved before the run, [m]
task: {goal: retrieve, description: the small cardboard box}            # what the agent is told, nothing more
observations: {camera_roles: [planning], joint_state: true, imu: false}
budget: {sim_seconds: 600}
seed: 0
answer: {target: kitchen_island_compartment_0_item_1}                   # hidden: the target's scene name
optimal: {path_length_m: null, manipulations: 2}                        # the SPL and SPL-M denominators
```

`task` is all the agent gets: PhyGS's session hands it `goal` and `description`. `answer` is hidden:
the evaluator reads it, and so does the oracle on the privileged track, through the grants that give a
target's position (`object_targets`). A unit test (`tests/test_episodes.py`) checks for every episode
that the agent's part names nothing of the answer. `optimal.path_length_m` stays `null` until episodes
state it (SPL is then not reported). There are no difficulty tiers yet.

## Sets

`manifest_v0.yaml` lists the sets (`dev`: the three development episodes). Manifest v1 (25 scenes,
100 episodes, a hidden test split) replaces it. Every episode names its scene release, so a result
records the exact scene (`scenes/`).
