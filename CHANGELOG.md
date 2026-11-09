# Changelog

How to add an entry: one line under **Unreleased** in the right group (Added, Changed, Removed, Fixed), past tense, naming the file or symbol. A change to the rules, the tracks, the episodes or the PhyGS pin is a new benchmark version: say so.

## [Unreleased] (develop)

### Added (2026-11-09)

- `phygs_commit` in `configs/benchmark_v1.yaml`, beside `phygs_version`: the pinned PhyGS release's tag commit (0.12.0: `67fddf1`). `tests/test_pin.py` checks that it is the `third_party/phygs` commit in the index, so a pin bump changes the submodule, `phygs_version` and `phygs_commit` together. The pinned release is the same; not a benchmark version change.
- `foragebench.phygs_code()` (the imported PhyGS checkout's commit and whether it has uncommitted changes), `foragebench.commit_problem(commit, rules)` and `foragebench.dirty_problem(project)` (the reason texts), `foragebench.pin_problems(rules, version, code)` (why an installed PhyGS is not the pinned release; empty when it is), `foragebench.pin_text(rules, version, code)` (the pin in one line), and `results.pin_reasons(result, rules=None)` (why a run is not publishable).
- `provenance.unpinned` in `result.json`: the reasons the run's PhyGS is not the pinned release, empty when it is.

### Changed (2026-11-09)

- **A run is pinned only on the pinned PhyGS release: its version, its tag's commit, and no uncommitted changes.** Before, only `phygs.__version__` was compared, so a later PhyGS commit that still said 0.12.0 passed as pinned. A run on another PhyGS (another version, a development version, another commit, an install outside a git checkout, a dirty checkout) is no longer refused: it goes ahead, prints `foragebench: an unpinned run, its results are not publishable: <reasons>` at the start, and records the reasons in `provenance.unpinned`. Not a benchmark version change: the rules file's hash (`provenance.benchmark_rules`) changes with the new key, but what is pinned and what is scored do not, so results before and after pool.
- `results.unpinned(result, rules=None)` is `bool(pin_reasons(result, rules))`: the reasons the run recorded (from the commit and dirty flag PhyGS records for the run), a dirty PhyGS or ForageBench checkout and, given the rules, a PhyGS commit other than the pinned one, which also catches results written before `provenance.unpinned`. `results.summarize(folder, cost, rules=None)` passes the rules on, and `foragebench results`, `suite` and `leaderboard add` give them. The results table says "<n> of these runs are unpinned: do not publish them" (was "came from a dirty checkout").
- `foragebench leaderboard add` refuses a folder with any unpinned run and names the reasons (e.g. "PhyGS commit 47e3edc is not v0.12.0 at 67fddf1").
- `foragebench version` and `foragebench describe` print the pinned and the installed PhyGS, each at its commit, then `pinned` or `unpinned (<reasons>)`. `describe` exits 1 only for a missing scene (it also did for another PhyGS version, marked `REFUSED`).
- **`dev/house_drawer` moved to the house scene's release 1.3.0** (was 1.1.0; SimReady kitchen models since 1.2.0, every loose object a different model, contents 0.30 m behind the drawer and door fronts); `episodes/manifest_v0.yaml` records its archive's SHA-256 (`5d056604…`). The start moved clear of the 1.2.0 dishwasher, which 1.2.0's kitchen models put 0.54 m from the old start: from (10.2, 6.0) to (10.14, 5.59), heading 0, the nearest point, on a 5 cm grid inside the kitchen, whose 0.94 m disk (the robot's padded half-diagonal plus a margin) is clear of every collider between 0.02 and 1.2 m. The description became "the small dark bottle" (was "the dark bottle"): 1.3.0 also has larger dark bottles (a gin bottle, a beer bottle and another generated bottle, 0.21-0.26 m tall; the target is 0.15 m). `answer.matches` became empty and only the target counts: every loose object in 1.3.0 is a different model, so 1.1.0's three other copies of the bottle are gone. `house_drawer` results from before this ran a different episode and do not compare. Needs PhyGS 0.13.0 (the composite pick's wider approach set: on 0.12.0 every pick option on this bottle is refused). Not a benchmark version change (dev manifest v0).

### Removed (2026-11-09)

- `foragebench.check_phygs_version()`, which refused to run against another PhyGS version. `foragebench.pin_problems(rules, foragebench.phygs_version(), foragebench.phygs_code())` says why the installed PhyGS is not the pinned release (empty when it is); a run on it is marked unpinned instead of refused.

### Added (2026-11-08)

- `foragebench leaderboard` (`eval/leaderboard.py`) and its results file `leaderboard/results.json`, with the oracle and null agents on the dev set (`privileged`, five runs per episode, PhyGS 0.12.0, rules version 3). `add <suite folder>` scores a suite's runs into the file, one entry per agent (with its model and prompt) on a track and episode set: n, successes with their Wilson 95% interval, per-episode results, reached and clean rates, the runs not scored, the PhyGS and rules versions, the date and the run folder; it refuses runs from a dirty checkout or on another PhyGS than the pin, and unscored runs it cannot place in one entry. `readme` writes the README's leaderboard table from the file (`--check`: exit 1 when the table is stale), and `tests/test_leaderboard.py` fails when the README's table is not the file's. Not a benchmark version change.
- `docs/submitting.md` (what to send, and how a result enters the results file), `CITATION.cff`, and `LICENSE`, a placeholder until the licence is chosen.

### Changed (2026-11-08, docs)

- `README.md` became the front door: what ForageBench measures and why, the requirements, the install with a check and its output, the oracle quick start with its video, the leaderboard written from `leaderboard/results.json` (in place of the baselines table of 2026-10-29, on PhyGS 0.6.0 and rules version 2), and a "Where to go next" table. The agent example moved into `foragebench/agents/README.md`, the submission rules into `docs/submitting.md`. The teaser became `assets/imgs/teaser.jpg` (204 KB; it was an 8.1 MB PNG), and the "where this fits" figure was added as `docs/figures/where_it_fits.svg` and `where_it_fits_dark.svg`, the same files as PhyGS's.

### Changed (2026-11-08)

- **Pinned PhyGS 0.12.0** (was 0.11.0): every episode recorded in one Rerun file (`episode.rrd`) and `phygs replay` from it, `AgentSession.log` (the agent's own records, which the model harness now uses), scenes whose furniture is articulated (`bear_loop_house` 1.2.0 and later), cuRoboV2-Fast, Nav2's point clouds on the GPU, the World's live video removed. A benchmark version change.
- **The model's side of a run is in the episode's recording**, not in `agent/turns.jsonl` and JPEG files: `orchestrator.TurnLog` keeps it through PhyGS's `session.log` (`/agent/log/model/*` in `episode.rrd`): the system prompt; each turn and pointing query as it went over the wire (the request with each image named, the raw response, the request id, the model that answered, the client's retries, the seconds, the token counts) with the images exactly as sent (PNG); what the harness made of each reply and what the model was told (`model/result`); every error with its origin, `model`, `api`, `harness` or `phygs` (`model/error`, with the traceback). Each turn's skill runs in a step `turn N: skill`, so its PhyGS calls sit inside it in the audit. A pointing query on a turn's image sends the turn's own PNG bytes. Needs PhyGS 0.12.0 (`session.log`). Not a benchmark version change: the model is sent the same.
- `result.json` has `run_id` (the recording's) and `model` (a model agent's totals from the recording: turns, pointing queries, errors by origin, tokens, seconds, retries); `agent/model.json` (in `agent_setup`) has `prompt_sha256` (the system prompt's template, the skill menu, the grounding query and the turn text's form) and `menu_sha256`.
- `foragebench results` groups by (track, agent, model, prompt hash): runs of different models or prompts no longer pool (B39).

### Removed (2026-11-08)

- `agent/turns.jsonl` and the per-turn JPEGs (`TurnLog(folder)`), and the orchestrators' `log_dir`: the recording holds it all.
- `run.py --record` (the live third-person video; PhyGS 0.12.0 removes it from the World). `suite.py --record` now renders each run's video after the run from its recording, with `phygs replay` (`replay/replay.mp4` beside each `episode.rrd`; needs PhyGS 0.12.0's recording). Not a benchmark version change.

### Changed (2026-11-07)

- **Pinned PhyGS 0.11.0** (was 0.10.0): Isaac Lab main (Isaac Sim 6.2.0), one stowed limit (`Truth.stowed`), the composite look_at sweep, drawer strokes that end stowed, the shoulder-line handle grasp, one cuRobo planner for every gripper angle. A benchmark version change.
- **Runs on Isaac Lab main (Isaac Sim 6.2.0, Python 3.12), with PhyGS 0.11.0.** Commands are `isaaclab -p ...` (was `./isaaclab.sh -p ...`); `requires-python` is `>=3.12`. `foragebench suite` no longer passes `--headless` to its runs (Isaac Lab main has no such option and is headless by default; every suite run stopped on it) and forwards `--kit_args` to each run (GPU choice). Not a benchmark version change by itself; the PhyGS pin bump that goes with it is one.

### Changed (2026-11-06)

- **Stowed is the robot's own limit.** The retrieve evaluator's `stowed` check is PhyGS's `Truth.stowed()`: every arm joint within the robot's `arm.stow_tolerance` (robot.yaml; Spot 0.18 rad) of its stow, the limit its stow skill, the composite skills and navigation use. `thresholds.yaml` drops `stow_tolerance_rad` (was 0.05 rad) and goes to version 3. A held object sags Spot's stowed wrist 0.040-0.051 rad, so 0.05 scored a stow the stow skill reported as done 'not stowed' (pointing oracle, grid_table, 2026-11-05). Needs PhyGS 0.11.0 (`Truth.stowed`). A benchmark version change.

### Removed (2026-11-05)

- **The affordance prior in the model's prompt** (`prompts/affordance_prior.md`, `OrchestratorConfig.affordance_prior`, on by default). It told the model where household objects are usually kept and the skill order for a drawer (navigate_to the handle, open_drawer, look_at, pick, stow): the search and the plan the benchmark measures. The run settings no longer record it. A benchmark version change (the model's prompt).
- `PLANS.md`. Plans, known gaps and decisions are kept in the maintainers' project tracker, outside the repository; the README and `docs/README.md` no longer link it. Not a benchmark version change.

### Changed (2026-11-04)

- **The model's `look_at` is PhyGS's composite sweep (`CompositeSkills.look_at`), not one view.** It opens the empty gripper, looks at the pixel's point from five sides (-45 to 45 deg around it, 0.6 m out, 45 deg up, higher where that is out of reach), then folds the arm. The hand image at each view reached comes back as a camera of its own, `view1` to `view5` (`skills.with_views`): the model points in them and a pixel there is measured in that view's own capture. The views stay through a refused call and `stow`, and go after any call that moves the robot or the scene. In the Qwen3.8 house run, 10 of 10 "no depth near pixel" refusals were the model pointing at the gripper's black jaws in the hand image; with the gripper open, the share of the hand image without depth or nearer than 0.25 m fell from 26-32% to 1-6% (2026-11-04). The pointing oracle points in the first view that sees its point. The prompt (`prompts/system.md`) says what the views are. A benchmark version change (the model's menu and prompt).

### Added (2026-11-03)

- A Claude client for the model harness (`agents/model/claude.py`, `FORAGEBENCH_ORCHESTRATOR=claude`; `pip install anthropic`, the key in `ANTHROPIC_API_KEY`): the same prompt, turn text, images and reply as the other models through Anthropic's Messages API; default model `claude-opus-5-5` at effort `high` (`FORAGEBENCH_EFFORT`), its thinking summarized in `turns.jsonl`, the system prompt cached per episode, no fallback to another model. It points in the image's own pixels (`orchestrator.POINTERS["claude"]`). Both clients write the run log through `orchestrator.TurnLog` (the records are unchanged). Not a benchmark version change.

### Fixed (2026-11-03)

- **The model harness measures a drawer front's direction (`perception.facing_normal`) on the plane most of the depth patch lies on (`perception.on_main_plane`), not on a least-squares plane through all of it.** From a body camera 0.4-0.6 m away the patch is 7 cm wide, and the handle bar, 5 cm out of the front, is a quarter of its points: the fit turned 48-62 deg, so `open_drawer` stood at an angle and pulled along the wrong line, or its stance was an occupied Nav2 goal (Qwen3.8 on grid_drawer's target drawer and on the house island's top drawer, 2026-11-02). From the same poses it is now within 0.01 deg. `navigate_to` at a pixel uses the same direction. A benchmark version change (the harness's estimator).

### Changed (2026-11-02)

- **The model harness's `open_drawer` pulls as far as the arm reaches from its stance (about 0.29 m), as the oracle's pull, instead of a fixed 0.25 m** (`PULL_M`, from before the composite skills, which limit the pull to the reach themselves); `close_drawer` pushes the drawer the harness opened back as far as it pulled it, else 0.25 m (`PUSH_M`). With the short pull the house drawer was open 0.23-0.24 m at the pick (the oracle's 0.25-0.30 m), and from the nearer stances Spot's forearm pressed on the drawer above in 3 of 12 pointing-oracle runs (the jaws stopped up to 12 mm off the bottle's middle; twice it rolled out on the lift). Pulling as far as the arm reaches: 0.24-0.26 m at the pick, house_drawer 4/4 with no forearm contact (from as near as 933 mm), grid_drawer 2/2 (2026-11-02). A benchmark version change (the model's menu).
- The model harness's `pick` hands the composite pick the drawer the harness last opened when the object lies in it (`skills.DRAWER_*`: at most 0.6 m behind its handle, 0.8 m to its side and 0.25 m from its height; the house's kitchen island drawer is 1.6 m wide), so it stands square to the drawer and first where the body is clear of it. Without it, every stance stood over the open drawer, which the cameras' costmap marks occupied (Qwen3.8, house_drawer, 2026-11-01). A close forgets the drawer.

### Changed (2026-11-01, model runs and drawer openings)

- The evaluator reports `progress.opened` as none when the target's drawer starts open (an episode's `parts`, PhyGS 0.11.0): there was nothing to open. No current episode starts with a drawer open, so no result changes.
- The pointing oracle points at the target's middle when no camera sees its top (a box on a table seen edge-on from the stance): the grid_table failure "no camera sees the target".
- **house_drawer told the agent "the small cardboard box", but its target (`kitchen_island_compartment_0_item_1`) is a sealed bottle**; the drawer's printed box is another object (`item_0`). The description is now "the dark bottle". An episode change: a benchmark version change; model results on house_drawer before this measured the wrong instruction.
- **An episode's answer may list `matches`**: other objects the description fits as well; holding any of them counts (`RetrieveTask(..., matches=...)`), progress follows them all, and the result names the `held_object`. house_drawer lists the three other copies of its bottle (one in the drawer above; the same mesh and materials at 6.5 x 6.5 x 18 cm). The oracle still goes for `target`.
- The model harness's box from depth (`perception.object_box`) joins only neighbouring pixels whose points are within 2 cm (a surface behind the object is not joined), takes the object's top as the highest point it sees (a point on an object's side used to cut the box at that height), and takes an object whose top is much narrower than it (a bottle) as round: as deep as it is wide, its near side where the depth saw it. The house bottle measured 4.4 x 3.2 cm of 5 x 5 cm before (its far half hidden), 4.6 x 4.6 cm now, centred within 1 mm; the pick's grasp went 2 cm too deep and the elbow hit the drawer above (pointing oracle, 3 of 4 failures on 2026-11-01).

### Changed (2026-11-01, composite skills)

- Pinned PhyGS 0.10.0 (`phygs.composite`, one skill list, each skill's machinery under `phygs.skills.<name>.execution`). A benchmark version change.
- The reference agents use PhyGS's composite skills (`phygs.composite`, PhyGS 0.10.0) instead of the robot tests' routines: the oracle on the true affordances from the hints, the model harness's skills on the affordances its estimator (`agents/model/perception.py`) measures. Stances are computed from the drawer or the target, so the oracle needs no per-scene stance file; the table stance faces the target along the line from the robot. Benchmark code no longer imports `phygs_robot_tests` (`tests/test_imports.py`).
- The gripper reads a box held by its edge as held (PhyGS 0.10.0 `hold_tolerance`): the pointing oracle's house-drawer failure of 2026-10-30.
- The task card and README state the question v1 answers and its ceilings (the oracle, the pointing oracle, the noise floor).
- **The model's skills are PhyGS's, under PhyGS's names.** `go_to` (camera, target) and `go_near` (x, y) are `navigate_to` (either form; x, y now walks to that position, not 1.05 m short of it); `turn` (yaw_rate, seconds) is `command_velocity` (v_x, v_y, v_rot, duration); `explore` takes `timeout`. The harness only converts a pixel into the point, box or drawer the PhyGS skill takes, and adds `done`: the walking skills no longer stow first (PhyGS refuses with "stow it first"; the prompt says so), `look_at` uses PhyGS's own view list, and `pick` no longer steps at most 0.6 m and measures the box again from above: the composite pick walks into reach (keeping the robot's heading when the object is within 45 deg of it, as the harness's step did) and looks itself. A benchmark version change (the model's menu).

### Removed (2026-11-01, composite skills)

- `prepare(spec, robot)` of `agents/oracle.py` and `agents/pointing_oracle.py`: the composite skills read the robot from the session and need no scene data. `foragebench run` still calls an agent's `prepare` when it has one.

### Changed (2026-11-01)

- Pinned PhyGS 0.9.0 (`World(target=...)`, `Truth.lifted_near_wrist`, the evaluator gets the grasp contacts, the settings hash in every report). A benchmark version change.
- **SPL-M counts in one unit.** `result.manipulations` is now how many times the gripper held a body (a drawer handle, an object; `eval/results.py` `grasps`, from the report's `grasp_contacts`), the unit of the episodes' `optimal.manipulations`. Before, it counted every manipulation command (stows, looks, gripper moves), so SPL-M compared two units; do not pool SPL-M from earlier results. The command count is `manipulation_commands`.
- The summary reports `finishes` and `false_finishes`: runs the agent ended itself, and how many of those the evaluator did not confirm.
- An agent's `prepare` and the settings step run inside the run's error handling, so a failure there still writes `result.json`.
- The rules no longer name a navigation backend that was never passed to PhyGS (Nav2 is its only one).

### Removed (2026-11-01)

- `agents/model/qwen3_vl.py` and `FORAGEBENCH_ORCHESTRATOR=qwen3_vl`: the in-process Qwen client had no pointing query, so every pointing skill was refused. Qwen runs through vLLM and the OpenAI-compatible client.

### Changed (2026-10-31)

- Every result names what produced it: `agent_setup` is the agent's `agent/model.json` (model, server, pointing, thinking, budgets) with its hash, or null for an agent that writes none.
- `foragebench run` passes the episode's answer target to the World (`World(target=...)`, PhyGS 0.9.0); the track's grants decide what the agent learns.
- The benchmark imports only PhyGS's public modules by name (`phygs.world`, never its submodules); only the reference agents import the robot tests' routines (`tests/test_imports.py`).
- The evaluator reads `Truth.lifted_near_wrist` (the measurement formerly called `held`); the rules are unchanged.
- `foragebench scenes fetch` names the scene dataset (`--repo_id mandmlabresearch/ForageBench`); the grid episodes' scene is built into PhyGS (`phygs/scene/builtin`).
- The model prompts are package data; `requests` is a declared dependency.

### Added (stage 4, 2026-10-30)

- Repeats in one process: `foragebench run --repeats N` runs N seeds in one simulator process (PhyGS 0.8.0's `World.next_episode`), each in `<output>/s<seed>`, and every result names `episode_in_process`. `foragebench suite` runs each episode's repeats in one process (`--fresh` for one process per run); `results` reads the `s<seed>` folders.
- `agent_wall_seconds: 1800` in the rules: a run whose agent takes longer ends as `agent_timeout`, a failure.
- The model harness points: the model names a camera and the target in words (`go_to`, `look_at`, `open_drawer`, `close_drawer`, `pick`), the same model points at it in that image with its own grounding query, and the pixel becomes a world point with the robot's own depth (`agents/model/perception.py`). The model sees each camera turned upright (Spot's front cameras and its folded hand camera are on their side); `go_near` takes a world position for the known-target condition. The drawer skills find the handle near the pixel and the front's outward direction from depth, step in front of that drawer (the robot tests' open stance, on the measured drawer; again a tolerance nearer when the handle was out of reach) and use the robot tests' drawer stroke. `pick` measures the object's box from depth, steps into reach, measures it again from above and runs the robot tests' pick; later arm plans carry that box. `go_to` stands in front of upright surfaces; `look_at` tries the robot tests' views in turn; the walking skills stow the arm first. Nothing privileged.
- `agents/model/openai_compatible.py`: one client for any model behind an OpenAI-compatible endpoint (Gemini on Google's, an open model served by vLLM); the key from an environment variable.
- The `pointing_oracle` agent: the harness's skills driven with perfect pixels on the privileged track (`go_to`, `look_at`, `open_drawer`, `pick`); while no camera sees the handle or the target it first walks to the robot tests' stance, where a model would explore.

### Changed (stage 4, 2026-10-30)

- Pinned PhyGS 0.8.0. A benchmark version change.

### Removed (stage 4, 2026-10-30)

- The harness's world-coordinate skills (`navigate`, `look_at` on a point, `move_hand_to`) and the raw gripper skills: a model points at pixels instead. `agents/model/gemini_robotics_er.py` (the Google SDK client): Gemini runs through the OpenAI-compatible client.

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
