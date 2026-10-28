# Plans

Status on 2026-10-28 (develop, PhyGS 0.3.0): `make test` passes (29 unit tests); `dev/grid_table` scored with the null agent (failure, the floor) and the oracle (success, clean, 62 s simulated) on the privileged track.

## Next, in order

1. **PhyGS pin.** Add `third_party/phygs` at the `v0.3.1` tag once PhyGS `develop` is committed and tagged; CI checks the submodule commit is a tagged release and equals `configs/benchmark_v1.yaml: phygs_version`.
2. **Noise floor.** `suite.py --set dev --track privileged --agent oracle --repeats 5`; put the numbers in the README's Baselines table. Then the oracle on `gt_localization` (it needs the hints; expect refusals: that is the point).
3. **Model agent harness.** A VLM choosing skills through the session (the May beta's orchestrators, re-targeted to the session's clients), as `foragebench/agents/model/`; the first `gt_localization` baseline.
4. **Episode generator and manifest v1.** Scenes × difficulty parameters (room, visibility, receptacle, occluders); a certification pass (the oracle must succeed; the target must be reachable); the hidden test split; the 25-scene, 100-episode set of the paper.
5. **Track `onboard`.** No grants; the agent localizes. Needs PhyGS's camera-only localization path.
6. **Client package.** `foragebench-client`, no Isaac imports, for agents in their own process (PhyGS's out-of-process session is the prerequisite).
7. **Results page and submissions.** `results.py` to a static page; verification reruns; the submission format in the README made binding.

## Known gaps

- The house scene's release (`bear_loop_house` 1.1.0) is prepared but not yet uploaded to the dataset; until then it must be fetched from the lab's cache.
- The oracle depends on the routines' stances (`phygs_robot_tests/configs/stances/<scene>.yaml`); a new scene needs stances before the oracle can run there.
- No CI yet; `make test` is run by hand.

## Decisions

- 2026-10-28: PhyGS as a pinned submodule, not a pip dependency (not installable from an index yet); one copy of the routines, in PhyGS, imported by the oracle; the dataset keeps the name "ForageBench" on Hugging Face while the fetcher lives in PhyGS; reports and research notes committed under `docs/research/`.
