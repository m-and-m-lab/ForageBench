# Changelog

How to add an entry: one line under **Unreleased** in the right group (Added, Changed, Removed, Fixed), past tense, naming the file or symbol. A change to the rules, the tracks, the episodes or the PhyGS pin is a new benchmark version: say so.

## [Unreleased] (develop)

### Changed

- **Rebuilt on PhyGS 0.3.0 (2026-10-28).** The May beta (`agent/`, `eval/`, `scenes/`, `tasks/`, AO-Grasp and cuRobo submodules, 60 Hz, `report_found`) was removed from `develop`; it stays on `main`. The benchmark is now the package `foragebench` on the PhyGS simulation framework, carried as the git submodule `third_party/phygs` pinned to a tagged release.

### Added

- The retrieve task (`foragebench/tasks/retrieve/`): brief, evaluator (held, stowed, upright, in time; conduct: unintended contacts, drawers left open; `clean`), `thresholds.yaml` hashed into every result. Copied from the lab's development tree, where it was written and scored first.
- Tracks `privileged` and `gt_localization` (`foragebench/tracks/`): actions and grants applied over an episode file.
- Episode manifest v0 (`foragebench/episodes/manifest_v0.yaml`): the three development episodes, each naming its scene release (`bear_loop_house@1.1.0` with the archive's SHA-256) or fixture.
- Reference agents `null`, `template` and `oracle` (PhyGS's scripted retrieve plan through `phygs_robot_tests.routines`).
- `foragebench/run.py` (one run, `result.json`), `suite.py` (a set, one simulator process per run), `results.py` (success and clean rates with Wilson 95% intervals, per-episode rates, `unpinned` count).
- `configs/benchmark_v1.yaml`: the PhyGS version pin (checked at import), backend pins, end-of-episode settings applied over PhyGS's environment settings.
- Unit tests (fake ground truth, episodes and tracks, the import guards), `Makefile` (`install`, `test`, `smoke`, `oracle`), the task card, the install guide, the design record and research notes (`docs/`).
