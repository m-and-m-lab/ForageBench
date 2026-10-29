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

Run yours with `--agent path/to/agent.py:run`.

## The model harness (`model/`)

| Module | Role |
| --- | --- |
| `orchestrator.py` | The prompt (`prompts/system.md`, the optional affordance prior), `parse_skill_call` (one JSON object, arguments checked), the `Orchestrator` base class |
| `skills.py` | The skills a model may name, each a few session calls returning the session's own status and reason |
| `loop.py` | Observe, ask, run, repeat; stops on `done`, the call budget, or the same call three times in a row |
| `scripted.py`, `qwen3_vl.py`, `gemini_robotics_er.py` | A fixed sequence (smoke runs); Qwen3-VL through transformers; Gemini Robotics-ER through the Google GenAI SDK (`GEMINI_API_KEY`). The two model orchestrators have not yet been run against a model here. |

| Skill | Arguments | Session calls |
| --- | --- | --- |
| `navigate` | x, y, heading | `navigation.navigate_to` |
| `explore` | seconds | `navigation.explore` |
| `turn` | yaw_rate, seconds | `locomotion.command_velocity` |
| `look_at` | x, y, z | `manipulation.look_at` |
| `move_hand_to` | x, y, z | `manipulation.move_to_pose` (hand pointing down) |
| `open_gripper`, `close_gripper`, `stow` | — | the same-named calls; `close_gripper` fails when nothing is held |
| `done` | — | ends the episode; the evaluator decides the outcome |

`FORAGEBENCH_ORCHESTRATOR=scripted|qwen3_vl|gemini_robotics_er`, `FORAGEBENCH_MODEL`,
`FORAGEBENCH_MAX_CALLS` (default 40).
