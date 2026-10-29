# tracks/

A track says what the agent may do (`actions`) and what it is told (`grants`); the episode is the
same on every track. Every use of a granted channel is audited and listed in the result.

| Track | Actions | Granted | For |
| --- | --- | --- | --- |
| `privileged` | navigation, manipulation skills | true pose; the scene's known boxes (map, arm planning); the target's position; the drawers' handles | the oracle: the skills' ceiling, the physics' noise floor; the known-target condition for model agents |
| `gt_localization` | navigation, manipulation, direct walking | the true pose only: the map comes from the cameras, the arm plans on depth, the agent finds the target | model agents, first track |
| `onboard` (planned) | the same | nothing; localization is the agent's | full autonomy |

`actions` is a PhyGS action set (`skills`, `motion`, `joints`) or a list; `grants` a subset of
`gt_localization`, `known_map`, `object_targets`, `scene_hints`. A track file's hash is in every
result (`provenance.track`).
