# Plans

Status on 2026-10-29 (develop, PhyGS 0.7.0): the unit tests pass; the oracle's noise floor on the dev set is measured (15/15 success, 5/15 clean over five seeds per episode; README baselines); the null agent is the floor.

The order is the build order of 2026-10-28: a scored run, a still end state, tracks and the oracle as an agent (all done), a model can play, a benchmark, then reach. Two steps went before a model plays (decided 2026-10-29): the structure, and the evaluator with the episode files, so that the first model runs are scored by the evaluator they will be compared under and need no rerun.

## Done (2026-10-29)

- **Phase A.** Every result has a `status` (`completed`, `setup_error`, `error`); only completed runs are rated. PhyGS checks the settled world before the agent starts. The thresholds carry a version and results never pool versions. CI checks the PhyGS pin (`.github/workflows/pin.yml`).
- **Phase B.** One `foragebench` command (describe, run, suite, results, scenes, version) in place of the scripts, the Makefile and the path setup; design history and research notes out of the repository; PhyGS holds no scene-building code.
- **Phase C.** Episode files split what the agent is told (`task`) from the hidden `answer`; a test checks that nothing of the answer reaches the agent. The evaluator samples the run (PhyGS's `reset`/`update`/`result`): held needs every jaw on the target; `reached` (within 1.5 m at the end, or holding: Spot picks from 0.9-1.2 m, so the paper's 0.6 m from the base centre would never count a pick); `progress` (reached, opened, touched, lifted, held); objects moved. No difficulty tiers.
- Not done: the oracle closing the drawer it opened. It holds the box by then, and pushing the drawer with the box in the jaws needs a routine that plans with the held box; that belongs to the routines' redesign.

## Next, in order

1. **A model can play.** PhyGS: the session over a wire, so an agent runs in its own process with no Isaac imports (it is also what keeps an agent away from ground truth). ForageBench: the client package, then the first model runs (Qwen3-VL, Gemini Robotics-ER; `agents/model/`, `--agent vlm`) on `gt_localization`, then on `privileged` as the known-target condition. Neither model has been run against this harness yet: expect prompt and image-format fixes.
2. **ForageBench as the gateway to the dataset.** Episode files are released on Hugging Face with the scene they belong to; ForageBench fetches both and runs them on PhyGS. One scene (`bear_loop_house`) is enough for development. New episodes start the robot in another room than the target (living room to kitchen); no difficulty tiers yet.
3. **A benchmark.** More scenes and episodes, each certified by the oracle; a frozen set with a hidden half; the noise floor with at least 20 repeats.
4. **Reach.** Track `onboard` (the agent localizes; needs PhyGS's camera-only localization), doors (the base and the arm together), results page and submissions.

## Known gaps

- The oracle leaves the drawer open and touches the unit on every drawer episode (see Done); its clean rate is not a ceiling for conduct.
- The oracle depends on the routines' stances (`phygs_robot_tests/configs/stances/<scene>.yaml`); a new scene needs stances before the oracle can run there.
- CI checks the pin only; the other unit tests need Isaac Lab's Python (`pytest tests` with Isaac Lab's Python, in the container).
- SPL is `null` for the dev episodes: no optimal path lengths until episodes state them (the oracle's measured path is not an optimum).

## Decisions

- 2026-10-28: PhyGS as a pinned submodule, not a pip dependency (not installable from an index yet); one copy of the routines, in PhyGS, imported by the oracle; the dataset keeps the name "ForageBench" on Hugging Face while the fetcher lives in PhyGS.
- 2026-10-29: the task stays `retrieve` until agents search (the oracle never searched); "held" needs both jaws touching the target; success needs the arm stowed; "reached" is read at the end (1.5 m, from the oracle's stances); no early stop when nothing progresses (the budget ends the episode); design history and research notes leave the public repositories; scene-building code (builders, the Infinigen fork, the publisher) leaves PhyGS; no difficulty tiers until episodes vary in difficulty.
