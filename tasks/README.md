# tasks/

Episode definitions and metadata for ForageBench.

ForageBench has **100 episodes** across **25 scenes**, with four episodes per scene, one for each
difficulty tier:

| Tier | Name | Requires |
|---|---|---|
| 1 | `SEPARATE_ROOM_VISIBLE` | Target is visible in another room. Open doors, but not receptacles. |
| 2 | `SAME_ROOM_NOT_PERCEIVABLE` | Target is in the starting room but hidden. Use semantic cues and open receptacles. |
| 3 | `SEPARATE_ROOM_NOT_PERCEIVABLE` | Target is hidden in another room. Traverse rooms and open receptacles. |
| 4 | `SEPARATE_ROOM_OCCLUDED` | Same as tier 3, plus moving non-target objects that occlude the target. |

## Layout

- `episode.py`: `Episode` dataclass, `DifficultyTier`, and loaders
- `episodes/`: one YAML file per released episode
- `examples/episode.yaml`: a placeholder episode documenting the schema

## Episode schema

```yaml
episode_id: scene_000_tier1       # unique ID
scene_id: scene_000               # resolved to a USD by scenes/registry.py
tier: 1                           # DifficultyTier
target:
  description: a ceramic mug      # natural-language goal given to the agent
  prim_path: /World/...           # USD prim of the target (unique within the scene)
  position: [x, y, z]             # world frame, metres
start_pose:                       # collision-free start pose
  position: [x, y, z]
  yaw: 0.0
required_interactions:            # manipulations on the optimal solution
  - skill: open_door
    reference: /World/...
optimal_path_length: 9.8          # metres; SPL denominator
```

At the start of each episode, every articulated object is closed (doors, cabinets, drawers,
windows, ovens, and dishwashers).
