# Changelog

How to add an entry: one line under **Unreleased** in the right group (Added, Changed, Removed, Fixed), past tense, naming the file or symbol. A change to the rules, the tracks, the episodes or the PhyGS pin is a new benchmark version: say so.

## [Unreleased] (develop)

### Changed (phase C, 2026-10-29)

- **Episode files split what the agent is told from the answer.** `task` is `{goal, description}` only; the target's scene name moved to a hidden `answer: {target}` block; the `benchmark` block became `optimal: {path_length_m, manipulations}`. `Episode` gains `public_task` and `answer`. Migrate an episode file by moving `task.target` to `answer.target` and renaming the block. A benchmark version change.
- **The retrieve evaluator samples the run** (PhyGS 0.6.0's `reset`/`update`/`result`). Held also needs every jaw pressing on the target; new `reached` (the base ends within 1.5 m of the target, or holds it), `progress` (reached, opened, touched, lifted, held) with `furthest`, the path length from the samples, and the conduct finding `objects_moved`. Thresholds version 2. A benchmark version change: results of version 1 and 2 are never pooled.
- `eval/results.py` reports the reached rate and the progress funnel; `eval/run.py` takes the path length from the evaluator (the path meter and `during` are gone).
- Pinned PhyGS 0.7.0: the evaluator's `reset`/`update`/`result` (0.6.0) and the per-run state log and `phygs replay` (0.7.0). A benchmark version change.

### Removed (phase C, 2026-10-29)

- Difficulty tiers (`foragebench.episodes.Tier`, the episodes' `tier`, the results' `tier`): no tiers until the episodes vary in difficulty.

### Added (phase B, 2026-10-29)

- The `foragebench` command (`./isaaclab.sh -p -m foragebench <command>`, and a console script): `describe` (what a run would do, without the simulator; exit 1 if it would be refused), `run`, `suite`, `results <folder>`, `scenes list|fetch`, `version`. `load_agent` moved to `foragebench.agents`.

### Removed (phase B, 2026-10-29)

- The `Makefile`: install with `pip install -e third_party/phygs` and `pip install -e .` (`docs/install.md`), test with `pytest tests`.
- The path setup in `eval/run.py`, `eval/suite.py` and `tests/conftest.py`: both packages must be installed; ForageBench never takes PhyGS from a path.
- `python -m foragebench.scenes`: use `foragebench scenes`.
- `docs/design/` and `docs/research/`: design proposals and research notes are not kept in the repository.

### Added (phase A, 2026-10-29)

- `result.json` has a `status`: `completed`, `setup_error` (PhyGS's start check failed; the agent never ran) or `error` (the simulator or the World broke). `run.py` writes a result in every case and exits 1 only for `error`; `eval/results.py` rates completed runs only and lists the others under `not_scored` with their reasons.
- `tasks/retrieve/thresholds.yaml` has a `version` (1); every result names it under `rules` with the file's hash, and `eval/results.py` refuses to pool runs scored under different versions.
- `tests/test_pin.py` and the CI workflow `.github/workflows/pin.yml`: `third_party/phygs` must be the tagged release `configs/benchmark_v1.yaml` pins, and that commit must carry the pinned version.

### Changed (phase A, 2026-10-29)

- Pinned PhyGS 0.5.0: report schema 2 (`status`, `start_check`) and the check before the agent starts. A benchmark version change.

### Changed

- **Rebuilt on PhyGS 0.3.0 (2026-10-28).** The May beta (`agent/`, `eval/`, `scenes/`, `tasks/`, AO-Grasp and cuRobo submodules, 60 Hz, `report_found`) was removed from `develop`; it stays on `main`. The benchmark is now the package `foragebench` on the PhyGS simulation framework, carried as the git submodule `third_party/phygs` pinned to a tagged release.

### Changed

- Removed `tools/sync_from_interactive_search.py` (2026-10-29): the evaluator and the agents are developed here now; nothing was left to copy from the lab's development tree.
- Pinned PhyGS 0.4.0 (`configs/benchmark_v1.yaml`, `third_party/phygs`): PhyGS's new layout. ForageBench imports `phygs.session` (agents), `phygs.world` and `phygs.scene.registry` (benchmark code) instead of `phygs.episodes.*`, and `eval/run.py` passes the rules' settings to `World(overrides=...)` instead of writing a settings file for PhyGS to read (the file it writes beside the result is the record of what was used). No behaviour changed. A benchmark version change.
- Pinned PhyGS 0.3.2: Ridgeback-Franka support synced in, the `phygs` command, the report schema, settings overrides. A benchmark version change.

### Fixed

- `eval/run.py` and the unit tests put `third_party/phygs` on the path even when another PhyGS checkout was installed, so a run could take modules from both (2026-10-29). They use the installed PhyGS and fall back to the submodule only when none is installed, as `docs/install.md` says.

### Added

- The retrieve task (`foragebench/tasks/retrieve/`): brief, evaluator (held, stowed, upright, in time; conduct: unintended contacts, drawers left open; `clean`), `thresholds.yaml` hashed into every result. Copied from the lab's development tree, where it was written and scored first.
- Tracks `privileged` and `gt_localization` (`foragebench/tracks/`): actions and grants applied over an episode file.
- Episode manifest v0 (`foragebench/episodes/manifest_v0.yaml`): the three development episodes, each naming its scene release (`bear_loop_house@1.1.0` with the archive's SHA-256) or fixture.
- Reference agents `null`, `template` and `oracle` (PhyGS's scripted retrieve plan through `phygs_robot_tests.routines`).
- `foragebench/eval/run.py` (one run, `result.json`), `suite.py` (a set, one simulator process per run), `eval/results.py` (success and clean rates with Wilson 95% intervals, per-episode rates, `unpinned` count).
- `configs/benchmark_v1.yaml`: the PhyGS version pin (checked at import), backend pins, end-of-episode settings applied over PhyGS's environment settings.
- Unit tests (fake ground truth, episodes and tracks, the import guards), `Makefile` (`install`, `test`, `smoke`, `oracle`), the task card, the install guide, the design record and research notes (`docs/`).
- Carried over from the May beta (2026-10-28): SPL, SPL-M and skill execution success in `eval/results.py` (over episodes whose manifest entry states an optimal path; `null` otherwise); difficulty tiers (`foragebench.episodes.Tier`) and the `tier`, `optimal_path_length_m`, `optimal_manipulations` fields of a manifest entry; the model-agent harness (`agents/model/`: prompt, argument-checked skill calls, the orchestrator loop with a call budget and a repeated-call stop, Qwen3-VL and Gemini Robotics-ER orchestrators, a scripted one) as the `vlm` agent. `run.py` records the path walked (integrated from ground truth), manipulations and skill calls in every result.
- Layout (2026-10-28, after the May beta's structure): `foragebench/{tasks,episodes,tracks,agents,scenes,eval}`, each with its own README; `run.py`, `suite.py` and `results.py` moved to `foragebench/eval/`; `foragebench.scenes` (`list`, `fetch`) says which scene releases the episodes need and fetches them through PhyGS; an episode file owns its benchmark facts (`benchmark: {tier, optimal_path_length_m, optimal_manipulations}`) and the manifest lists sets only.
- Noise floor (2026-10-28): the oracle on the dev set, five seeds per episode: 15/15 success, 5/15 clean (the drawer episodes leave the drawer open and touch the unit), skill execution success 0.90, mean 107 simulated seconds; in the README's baselines table.
