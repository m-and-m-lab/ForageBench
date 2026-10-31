# agents/

An agent is a function `run(session)`. The session (PhyGS's `AgentSession`) is the only object it
needs and the only thing it may import, plus PhyGS's robot-test routines for the oracle
(`tests/test_imports.py` enforces it). An agent that needs setup exposes `prepare(spec, robot)`.

| Agent | What it does | Track |
| --- | --- | --- |
| `null` | Observes once and finishes. The floor and the smoke test. | any |
| `template` | One call on every client the track allows, then finishes. Copy it to start yours. | any |
| `oracle` | PhyGS's scripted retrieve plan (stow, walk to the drawer or table, open, pick, stow). It only chooses the routines, which is why it is a ceiling and not a method. | `privileged` |
| `vlm` | A vision-language model choosing skills each turn through the harness in `model/`. | `gt_localization`, `privileged` (known target) |
| `pointing_oracle` | The harness's skills with perfect pointing: it projects where the drawer handle and the target are into the camera images and calls the skills a model calls with those pixels. The ceiling of the skills. | `privileged` |

Run yours with `--agent path/to/agent.py:run`.

## The model harness (`model/`)

| Module | Role |
| --- | --- |
| `orchestrator.py` | The prompt (`prompts/system.md`, the optional affordance prior), `parse_skill_call` (one JSON object, arguments checked), the `Orchestrator` base class |
| `skills.py` | The skills a model may name, each a few session calls returning the session's own status and reason |
| `perception.py` | A pixel the model points at to a world point with the robot's depth (a pixel without depth takes the nearest surface around it); a drawer front's outward direction; the handle near a pixel; an object's box from its top down to the surface it stands on. Nothing privileged |
| `loop.py` | Observe, ask, run, repeat; stops on `done`, the call budget, or the same call three times in a row |
| `scripted.py`, `openai_compatible.py`, `qwen3_vl.py` | A fixed sequence (smoke runs); any model behind an OpenAI-compatible endpoint (Gemini on Google's, an open model served by vLLM); Qwen3-VL in this process through transformers. |

A model names what to act on: `camera` names an image it was shown (each turned upright), `target`
says what the thing is in a few words. The harness asks the same model where that is in that one
image, with the grounding query the model family is trained on (Qwen's `point_2d`, Gemini's
`[y, x]` points), turns the point back into the camera's own pixel, and the robot's depth there gives
the world point. In one prompt with three images and a skill to choose, Qwen3.5-9B gave round
guesses for points; asked alone it pointed within a few pixels (2026-10-30).

| Skill | Arguments | What it does |
| --- | --- | --- |
| `go_to` | camera, target | stow, walk to 1.05 m from the point, facing it: in front of an upright surface (a drawer front), else along the line of sight (`navigation.navigate_to`) |
| `go_near` | x, y | stow, walk to 1.05 m from a world position [m] along the line of sight (the known-target condition) |
| `explore`, `turn` | seconds; yaw_rate, seconds | stow and `navigation.explore`; `locomotion.command_velocity` |
| `look_at` | camera, target | aim the hand camera at the point from the robot tests' views in turn (`manipulation.look_at`) |
| `open_drawer`, `close_drawer` | camera, target | measure the drawer at the pixel from depth (the handle sticking out of the front, the front's outward direction), stand in front of it (the robot tests' open stance, again a little nearer if the handle was out of reach) and pull (push) it 0.25 m (the robot tests' drawer stroke) |
| `pick` | camera, target | measure the object's box from depth, step (at most 0.6 m) so it is 0.95 m straight ahead, look down at it and measure it again, then the robot tests' pick (straight down first, then tilted; each grasp yaw in turn); later plans carry the box as the held object |
| `stow` | — | fold the arm (also holding, with the held object's box) |
| `done` | — | ends the episode; the evaluator decides the outcome |

`FORAGEBENCH_ORCHESTRATOR=scripted|openai|qwen3_vl`, `FORAGEBENCH_MODEL`, `FORAGEBENCH_BASE_URL`,
`FORAGEBENCH_API_KEY_ENV`, `FORAGEBENCH_MAX_CALLS` (default 40): `vlm.py`.
