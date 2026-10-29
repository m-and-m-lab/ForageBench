# episodes/

An episode file is a PhyGS episode spec plus the benchmark's facts about it, without `actions` and
`grants` (the track supplies those). The manifest lists which episodes form a set.

## Schema (schema 3 of PhyGS, plus the benchmark fields)

```yaml
schema: 3
id: house_drawer
scene: {id: bear_loop_house, version: 1.1.0, name: house, ground: false}   # a release of the scene dataset, or a fixture
robot: {model: spot, start: [10.2, 6.0, 0.0]}                           # x, y, heading [m, m, rad]
objects: {}                                                             # bodies moved before the run, [m]
task: {goal: retrieve, description: the small cardboard box, target: kitchen_island_compartment_0_item_1}
observations: {cameras: [frontleft, frontright, hand], joint_state: true, imu: false}
budget: {sim_seconds: 600}
seed: 0
benchmark:                      # the benchmark's facts; not read by PhyGS
  tier: 2                       # foragebench.episodes.Tier
  optimal_path_length_m: null   # the SPL denominator; null until the episode generator states it
  optimal_manipulations: 2      # manipulations on the optimal solution (SPL-M)
```

`task.description` is what the agent is told; `task.target` is the scene name, privileged.

## Tiers

| Tier | Name | The target is |
| --- | --- | --- |
| 0 | `VISIBLE_SAME_ROOM` | in view from the start (dev episodes only; below the paper's progression) |
| 1 | `SEPARATE_ROOM_VISIBLE` | visible in another room; doors to open, no receptacles |
| 2 | `SAME_ROOM_NOT_PERCEIVABLE` | hidden in a receptacle in the starting room |
| 3 | `SEPARATE_ROOM_NOT_PERCEIVABLE` | hidden in a receptacle in another room |
| 4 | `SEPARATE_ROOM_OCCLUDED` | as 3, and occluding objects must be moved |

## Sets

`manifest_v0.yaml` lists the sets (`dev`: the three development episodes). Manifest v1 (25 scenes,
100 episodes, a hidden test split) replaces it. Every episode names its scene release, so a result
records the exact scene (`scenes/`).
