# Plans

Status on 2026-10-29 (develop, PhyGS 0.8.0): the unit tests pass; the oracle's noise floor on the dev set is measured (15/15 success, 5/15 clean over five seeds per episode; README baselines); the null agent is the floor.

The order is the build order of 2026-10-28: a scored run, a still end state, tracks and the oracle as an agent (all done), a model can play, a benchmark, then reach. Two steps went before a model plays (decided 2026-10-29): the structure, and the evaluator with the episode files, so that the first model runs are scored by the evaluator they will be compared under and need no rerun.

## Done (2026-10-29)

- **Phase A.** Every result has a `status` (`completed`, `setup_error`, `error`); only completed runs are rated. PhyGS checks the settled world before the agent starts. The thresholds carry a version and results never pool versions. CI checks the PhyGS pin (`.github/workflows/pin.yml`).
- **Phase B.** One `foragebench` command (describe, run, suite, results, scenes, version) in place of the scripts, the Makefile and the path setup; design history and research notes out of the repository; PhyGS holds no scene-building code.
- **Phase C.** Episode files split what the agent is told (`task`) from the hidden `answer`; a test checks that nothing of the answer reaches the agent. The evaluator samples the run (PhyGS's `reset`/`update`/`result`): held needs every jaw on the target; `reached` (within 1.5 m at the end, or holding: Spot picks from 0.9-1.2 m, so the paper's 0.6 m from the base centre would never count a pick); `progress` (reached, opened, touched, lifted, held); objects moved. No difficulty tiers.
- Not done: the oracle closing the drawer it opened. It holds the box by then, and pushing the drawer with the box in the jaws needs a routine that plans with the held box; that belongs to the routines' redesign.

## Next, in order

1. **A model can play** (in progress, 2026-10-30). The agent stays in the simulator's process, like robosuite, RoboCasa and the recent agentic benchmarks; a model is reached over its API. Steps: the skills take image points, and a drawer skill without privileged information (`open_drawer`/`close_drawer` from depth): working in simulation (the `pointing_oracle`, perfect pixels, 2026-10-30: grid_table 2/2, grid_drawer 2/2, house_drawer 2/3; the house box measures 3 cm deep of 5 behind the drawer front, and the failed run's grip held the box while the gripper read as not holding); a wall-clock limit (done, 1800 s); one OpenAI-compatible client for every model (done); then the model runs, Qwen3-VL and Gemini Robotics-ER, on `gt_localization`, then `privileged` as the known-target condition. Needs from the user: a Gemini API key in the environment, and either vLLM for a local Qwen3-VL server or its weights for the in-process orchestrator.
2. **Code-writing agents.** Many episodes per process (done in PhyGS 0.8.0, `World.next_episode`); a sandboxed executor for model-written code in its own process (the wire, justified for this kind of agent); a workspace that survives episodes for skill libraries; a code-as-policy baseline in the style of CaP-X.
3. **ForageBench as the gateway to the dataset.** Episode files are released on Hugging Face with the scene they belong to; ForageBench fetches both and runs them on PhyGS. One scene (`bear_loop_house`) is enough for development. New episodes start the robot in another room than the target (living room to kitchen); no difficulty tiers yet.
4. **A benchmark.** More scenes and episodes, each certified by the oracle; a frozen set with a hidden half; the noise floor with at least 20 repeats.
5. **Reach.** Track `onboard` (the agent localizes; needs PhyGS's camera-only localization), doors (the base and the arm together), results page and submissions.

## Known gaps

- The oracle leaves the drawer open and touches the unit on every drawer episode (see Done); its clean rate is not a ceiling for conduct.
- The oracle depends on the routines' stances (`phygs_robot_tests/configs/stances/<scene>.yaml`); a new scene needs stances before the oracle can run there.
- CI checks the pin only; the other unit tests need Isaac Lab's Python (`pytest tests` with Isaac Lab's Python, in the container).
- SPL is `null` for the dev episodes: no optimal path lengths until episodes state them (the oracle's measured path is not an optimum).

## Decisions

- 2026-10-28: PhyGS as a pinned submodule, not a pip dependency (not installable from an index yet); one copy of the routines, in PhyGS, imported by the oracle; the dataset keeps the name "ForageBench" on Hugging Face while the fetcher lives in PhyGS.
- 2026-10-29: the task stays `retrieve` until agents search (the oracle never searched); "held" needs both jaws touching the target; success needs the arm stowed; "reached" is read at the end (1.5 m, from the oracle's stances); no early stop when nothing progresses (the budget ends the episode); design history and research notes leave the public repositories; scene-building code (builders, the Infinigen fork, the publisher) leaves PhyGS; no difficulty tiers until episodes vary in difficulty.
