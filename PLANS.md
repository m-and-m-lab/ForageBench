# Plans

Status on 2026-10-28 (develop, PhyGS 0.3.2): `make test` passes (52 unit tests); the oracle's noise floor on the dev set is measured (15/15 success, 5/15 clean over five seeds per episode; README baselines); the null agent is the floor.

## Next, in order

1. **PhyGS pin and CI.** The submodule is pinned (v0.3.1 committed; v0.3.2 staged in `configs/benchmark_v1.yaml`, the submodule moves once PhyGS tags it). Add the CI job: the submodule commit is a tagged release equal to `phygs_version`.
2. **Oracle conduct.** The oracle leaves the drawer open (0.24–0.30 m) and touches the unit (5–119 N peak) on every drawer episode: add a close-drawer step to the plan (or accept it as the ceiling's conduct and say so in the task card). Then the oracle on `gt_localization` (it needs the hints; expect refusals: that is the point).
3. **Model baselines.** The harness exists (`agents/model/`, `--agent vlm`); run Qwen3-VL and Gemini Robotics-ER on `gt_localization` (neither has been run against a model here yet: expect prompt and image-format fixes), then on the privileged track as the known-target condition.
4. **Episode generator and manifest v1.** Scenes × difficulty parameters (room, visibility, receptacle, occluders); a certification pass (the oracle must succeed; the target must be reachable); the hidden test split; the 25-scene, 100-episode set of the paper.
5. **Track `onboard`.** No grants; the agent localizes. Needs PhyGS's camera-only localization path.
6. **Client package.** `foragebench-client`, no Isaac imports, for agents in their own process (PhyGS's out-of-process session is the prerequisite).
7. **Results page and submissions.** `eval/results.py` to a static page; verification reruns; the submission format in the README made binding.

## Known gaps

- The house scene's release (`bear_loop_house` 1.1.0) is prepared but not yet uploaded to the dataset; until then it must be fetched from the lab's cache.
- The oracle depends on the routines' stances (`phygs_robot_tests/configs/stances/<scene>.yaml`); a new scene needs stances before the oracle can run there.
- No CI yet; `make test` is run by hand.
- SPL is `null` for the dev episodes: no optimal path lengths until the episode generator states them (the oracle's measured path is not an optimum).

## Decisions

- 2026-10-28: PhyGS as a pinned submodule, not a pip dependency (not installable from an index yet); one copy of the routines, in PhyGS, imported by the oracle; the dataset keeps the name "ForageBench" on Hugging Face while the fetcher lives in PhyGS; reports and research notes committed under `docs/research/`.
