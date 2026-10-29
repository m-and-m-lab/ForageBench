# Changelog

How to add an entry: one line under **Unreleased** in the right group (Added, Changed, Removed, Fixed), past tense, naming the file or symbol. A change to the rules, the tracks, the episodes or the PhyGS pin is a new benchmark version: say so.

## [Unreleased] (develop)

### Changed

- **Rebuilt on PhyGS 0.3.0 (2026-10-28).** The May beta (`agent/`, `eval/`, `scenes/`, `tasks/`, AO-Grasp and cuRobo submodules, 60 Hz, `report_found`) was removed from `develop`; it stays on `main`. The benchmark is now the package `foragebench` on the PhyGS simulation framework, carried as the git submodule `third_party/phygs` pinned to a tagged release.

### Changed

- Pinned PhyGS 0.3.2 (`configs/benchmark_v1.yaml`, `third_party/phygs`): Ridgeback-Franka support synced in, the `phygs` command, the report schema, settings overrides. A benchmark version change.

### Added

- The retrieve task (`foragebench/tasks/retrieve/`): brief, evaluator (held, stowed, upright, in time; conduct: unintended contacts, drawers left open; `clean`), `thresholds.yaml` hashed into every result. Copied from the lab's development tree, where it was written and scored first.
- Tracks `privileged` and `gt_localization` (`foragebench/tracks/`): actions and grants applied over an episode file.
- Episode manifest v0 (`foragebench/episodes/manifest_v0.yaml`): the three development episodes, each naming its scene release (`bear_loop_house@1.1.0` with the archive's SHA-256) or fixture.
- Reference agents `null`, `template` and `oracle` (PhyGS's scripted retrieve plan through `phygs_robot_tests.routines`).
- `foragebench/eval/run.py` (one run, `result.json`), `suite.py` (a set, one simulator process per run), `eval/results.py` (success and clean rates with Wilson 95% intervals, per-episode rates, `unpinned` count).
- `configs/benchmark_v1.yaml`: the PhyGS version pin (checked at import), backend pins, end-of-episode settings applied over PhyGS's environment settings.
- Unit tests (fake ground truth, episodes and tracks, the import guards), `Makefile` (`install`, `test`, `smoke`, `oracle`), the task card, the install guide, the design record and research notes (`docs/`).
- Carried over from the May beta (2026-10-28): SPL, SPL-M and skill execution success in `eval/results.py` (over episodes whose manifest entry states an optimal path; `null` otherwise); difficulty tiers (`foragebench.episodes.Tier`) and the `tier`, `optimal_path_length_m`, `optimal_manipulations` fields of a manifest entry; the model-agent harness (`agents/model/`: prompt, argument-checked skill calls, the orchestrator loop with a call budget and a repeated-call stop, Qwen3-VL and Gemini Robotics-ER orchestrators, a scripted one) as the `vlm` agent. `run.py` records the path walked (integrated from ground truth), manipulations and skill calls in every result.
- `tools/sync_from_interactive_search.py`: copies the evaluator and the example agents from the lab's development tree.
- Layout (2026-10-28, after the May beta's structure): `foragebench/{tasks,episodes,tracks,agents,scenes,eval}`, each with its own README; `run.py`, `suite.py` and `results.py` moved to `foragebench/eval/`; `foragebench.scenes` (`list`, `fetch`) says which scene releases the episodes need and fetches them through PhyGS; an episode file owns its benchmark facts (`benchmark: {tier, optimal_path_length_m, optimal_manipulations}`) and the manifest lists sets only.
- Noise floor (2026-10-28): the oracle on the dev set, five seeds per episode: 15/15 success, 5/15 clean (the drawer episodes leave the drawer open and touch the unit), skill execution success 0.90, mean 107 simulated seconds; in the README's baselines table.
