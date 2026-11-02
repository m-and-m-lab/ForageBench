# agents/

An agent is a function `run(session)`. The session (PhyGS's `AgentSession`) is the only object it
needs; it may import that and PhyGS's composite skills over it (`phygs.composite`), nothing else of
PhyGS (`tests/test_imports.py` enforces it). An agent that needs setup exposes `prepare(spec, robot)`.

| Agent | What it does | Track |
| --- | --- | --- |
| `null` | Observes once and finishes. The floor and the smoke test. | any |
| `template` | One call on every client the track allows, then finishes. Copy it to start yours. | any |
| `oracle` | PhyGS's scripted retrieve plan (stow, open the drawer, walk to reach the target, pick, stow) with the composite skills on the true affordances from the hints. It only chooses the skills, which is why it is the motion ceiling and not a method. | `privileged` |
| `vlm` | A vision-language model choosing skills each turn through the harness in `model/`. | `gt_localization`, `privileged` (known target) |
| `pointing_oracle` | The harness's skills with perfect pointing: it projects where the drawer handle and the target are into the camera images and calls the skills a model calls with those pixels. The ceiling of the skills with the estimator (`model/perception.py`) in the loop. | `privileged` |

Run yours with `--agent path/to/agent.py:run`.

## The model harness (`model/`)

| Module | Role |
| --- | --- |
| `orchestrator.py` | The prompt (`prompts/system.md`, the optional affordance prior), `parse_skill_call` (one JSON object, arguments checked), the `Orchestrator` base class |
| `skills.py` | The skills a model may name: each estimates the affordance (`perception.py`) and calls a PhyGS composite skill (`phygs.composite`) or a session client, returning a status and reason |
| `perception.py` | The estimator: a pixel the model points at to a world point with the robot's depth (a pixel without depth takes the nearest surface around it); a drawer front's outward direction; the handle near a pixel; an object's box from its top down to the surface it stands on. Nothing privileged. It stays in ForageBench: perception is the agent's side |
| `loop.py` | Observe, ask, run, repeat; stops on `done`, the call budget, or the same call three times in a row |
| `scripted.py`, `openai_compatible.py` | A fixed sequence (smoke runs); any model behind an OpenAI-compatible endpoint (Gemini on Google's, an open model such as Qwen served by vLLM). |

A model names what to act on: `camera` names an image it was shown (each turned upright), `target`
says what the thing is in a few words. The harness asks the same model where that is in that one
image, with the grounding query the model family is trained on (Qwen's `point_2d`, Gemini's
`[y, x]` points), turns the point back into the camera's own pixel, and the robot's depth there gives
the world point. In one prompt with three images and a skill to choose, Qwen3.5-9B gave round
guesses for points; asked alone it pointed within a few pixels (2026-10-30).

The skills are PhyGS's, under PhyGS's names (`model/skills.py`). Where a PhyGS skill takes a point,
a box or a drawer, the model names a camera and a target instead, and the estimator
(`model/perception.py`) turns the pixel into what the skill takes. That conversion and `done` are
all the harness adds.

| Skill | Arguments | PhyGS skill, and what the harness converts |
| --- | --- | --- |
| `navigate_to` | camera, target; or x, y | `navigation.navigate_to`: at a pixel, a pose 1.05 m short of the point, facing it (in front of an upright surface such as a drawer front, else along the line of sight); at x, y, that position [m]. Refused with the arm out: stow first |
| `explore` | timeout | `navigation.explore` [s]. Refused with the arm out |
| `command_velocity` | v_x, v_y, v_rot, duration | `locomotion.command_velocity` [m/s, m/s, rad/s, s]; all zeros stops |
| `look_at` | camera, target | `manipulation.look_at` at the pixel's point, from look_at's own views |
| `open_drawer`, `close_drawer` | camera, target | the composite drawer stroke on the drawer measured at the pixel from depth (the handle sticking out of the front, the front's outward direction): it stows, stands in front of it (again a walk tolerance nearer if the handle was out of reach) and pulls it as far as the arm reaches from there (as the oracle's pull: the depth shows no travel), or pushes it back as far as the harness pulled it (0.25 m for a drawer it did not open) |
| `pick` | camera, target | the composite pick on the object's box measured from depth: it stows, walks to where the arm reaches it, looks at it, then straight down first, then tilted, each grasp yaw in turn; later plans carry the box as the held object |
| `stow` | — | `manipulation.stow` (also holding, with the held object's box) |
| `done` | — | ends the episode; the evaluator decides the outcome |

`FORAGEBENCH_ORCHESTRATOR=scripted|openai`, `FORAGEBENCH_MODEL`, `FORAGEBENCH_BASE_URL`,
`FORAGEBENCH_API_KEY_ENV`, `FORAGEBENCH_MAX_CALLS` (default 40): `vlm.py`.
