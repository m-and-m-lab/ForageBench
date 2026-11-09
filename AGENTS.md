# Agent rules

How contributors and coding agents work in this repository. ForageBench is a benchmark: what is asked and how it is scored must be exact, reproducible and honest about its limits.

## The split

| Repository | Owns | Never |
| --- | --- | --- |
| PhyGS (`third_party/phygs`, submodule) | The robot, the world, the runtime, the skills, the measurement, the scenes | Names a task; imports ForageBench |
| ForageBench (this) | Tasks, tracks, episodes, evaluators, reference agents, results | Imports PhyGS internals; edits files under `third_party/phygs` |

`tests/test_imports.py` enforces the import side: benchmark code imports `phygs.session`, `phygs.composite`, `phygs.world` (never its submodules), `phygs.scene.registry` and `phygs.robots.description` only, and never the robot tests (`phygs_robot_tests`); the reference agents (`foragebench/agents/`) import only the session and the composite skills of PhyGS.

## Submodule rules

1. Never edit files under `third_party/phygs` in a ForageBench change. A framework fix goes to the PhyGS repository, gets a tag, and ForageBench bumps the pin in its own commit titled "Pin PhyGS X.Y.Z", with `configs/benchmark_v1.yaml: phygs_version` and `phygs_commit` (the tag's full commit) updated in the same commit; `tests/test_pin.py` fails when either does not match the submodule (a benchmark version change: say so in CHANGELOG).
2. The submodule commit must be a tagged PhyGS release. A run on any other PhyGS (another version or commit, or uncommitted changes) goes ahead, marked `unpinned`.
3. Both repositories work on `develop`; `main` stays frozen until a release. No other branches.

## Rules

- **Measurement over self-report.** The evaluator reads ground truth after the stop; it never reads skill feedback. A new metric needs a fake-ground-truth unit test and a line in the task card.
- **Nothing changes silently.** Thresholds, rules, tracks and episode files are hashed into every result; a change to any of them is a new benchmark version.
- **Fail fast.** A missing scene release, a bad episode file or an unknown track fails before Isaac Sim starts.
- **Agents are functions.** `run(session)`; an agent that needs setup exposes `prepare(spec, robot)` (the oracle does). No agent reads a report, a spec or the scene.
- **Results are reproducible.** A result from a PhyGS other than the pinned release (another version or commit, or a dirty checkout) or from a dirty ForageBench checkout is marked `unpinned`; do not publish it.
- **Documentation.** User-visible change: a line in CHANGELOG.md. New claim or limit: the task card. New guide: a row in docs/README.md.
- **Commits.** Conventional, imperative subjects; no AI attribution lines; never commit outputs (`output_check/`).
