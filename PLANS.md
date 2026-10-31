# Plans

Status on 2026-10-29 (develop, PhyGS 0.8.0): the unit tests pass; the oracle's noise floor on the dev set is measured (15/15 success, 5/15 clean over five seeds per episode; README baselines); the null agent is the floor.

The order is the build order of 2026-10-28: a scored run, a still end state, tracks and the oracle as an agent (all done), a model can play, a benchmark, then reach. Two steps went before a model plays (decided 2026-10-29): the structure, and the evaluator with the episode files, so that the first model runs are scored by the evaluator they will be compared under and need no rerun.

## Done (2026-10-29)

- **Phase A.** Every result has a `status` (`completed`, `setup_error`, `error`); only completed runs are rated. PhyGS checks the settled world before the agent starts. The thresholds carry a version and results never pool versions. CI checks the PhyGS pin (`.github/workflows/pin.yml`).
- **Phase B.** One `foragebench` command (describe, run, suite, results, scenes, version) in place of the scripts, the Makefile and the path setup; design history and research notes out of the repository; PhyGS holds no scene-building code.
- **Phase C.** Episode files split what the agent is told (`task`) from the hidden `answer`; a test checks that nothing of the answer reaches the agent. The evaluator samples the run (PhyGS's `reset`/`update`/`result`): held needs every jaw on the target; `reached` (within 1.5 m at the end, or holding: Spot picks from 0.9-1.2 m, so the paper's 0.6 m from the base centre would never count a pick); `progress` (reached, opened, touched, lifted, held); objects moved. No difficulty tiers.
- Not done: the oracle closing the drawer it opened. It holds the box by then, and pushing the drawer with the box in the jaws needs a routine that plans with the held box; that belongs to the routines' redesign.

## Next, in order

1. **A model can play** (in progress, 2026-10-30). The agent stays in the simulator's process, like robosuite, RoboCasa and the recent agentic benchmarks; a model is reached over its API. The goal is a fair interface, not a model that succeeds: a model that decides badly fails, and that is the measurement. Done when:
   - **The skills can solve every episode.** The `pointing_oracle` drives the model's skills with perfect points and succeeds on every dev episode (2026-10-30: grid_table 2/2, grid_drawer 2/2, house_drawer 2/3; the house failure held the box while the gripper read as not holding).
   - **Every model failure is the model's decision.** The run's `agent/` log (each turn's images, text, reply, thinking and pointing query) shows what the model was given and chose; a failure the harness caused (what it showed, how it pointed, a skill that broke) is fixed, not scored.
   - **Two model families run through the same interface.** Only conventions differ per family (the pointing query, the thinking switch); nothing is tuned to one model, and the harness never teaches a strategy (the affordance prior is a declared condition that a run reports).

   Done so far: image-point skills and a drawer skill from depth, nothing privileged; a wall-clock limit (1800 s); one OpenAI-compatible client; images turned upright; the model names the target in words and points at it in one image with its own grounding query (an interface choice the task card states). Qwen3.5-9B on `gt_localization` (vLLM, 2026-10-30): grid_table 2/2 (thinking off and on), grid_drawer 0/2 (it never searched for or opened the drawer). Next: Qwen3.8-27B (4-bit) and Gemini Robotics-ER on the dev episodes, then `privileged` as the known-target condition. Gemini needs an API key in the environment.
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
