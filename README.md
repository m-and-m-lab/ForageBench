# ForageBench: A Photorealistic, Physically Grounded Benchmark for Interactive Object Search

[![Paper](https://img.shields.io/badge/paper-b31b1b.svg)](https://m-and-m-lab.github.io/ForageBench/assets/papers/foragebench.pdf)
[![Website](https://img.shields.io/badge/project-page-1f6feb.svg)](https://m-and-m-lab.github.io/ForageBench/)
[![IsaacSim](https://img.shields.io/badge/IsaacSim-5.1-76b900.svg)](https://developer.nvidia.com/isaac/sim)
[![License](https://img.shields.io/badge/license-TBD-lightgrey.svg)](LICENSE)

[Aparajito Saha](https://aparajitosaha.github.io)<sup>1</sup>, [Zhen Hao Gan](https://ganzh6880.github.io)<sup>1</sup>, Jinjia Guo<sup>1</sup>, Jacob Skwirsk<sup>1</sup>, Jeremy Acheampong<sup>1</sup>, [Anton Arapin](https://anton-arapin.github.io)<sup>1</sup>, [Chahyon Ku](https://chahyon-ku.github.io)<sup>1</sup>, [Yue Hu](https://phyllish.github.io)<sup>1</sup>, [Nima Fazeli](https://www.mmintlab.com/people/nima-fazeli/)<sup>1</sup>, [Bernadette Bucher](https://bucherb.github.io)<sup>1</sup>

<sup>1</sup>University of Michigan, Ann Arbor

**[Project page](https://m-and-m-lab.github.io/ForageBench)** &nbsp;·&nbsp; **[Paper](https://m-and-m-lab.github.io/ForageBench/assets/papers/foragebench.pdf)**

ForageBench is a benchmark for interactive object search: a mobile manipulator in a house has to find an object it was told about in words, open what hides it, and bring it into its hand. The robot is a simulated Boston Dynamics Spot with Arm; the houses are photorealistic, physically grounded scenes; nothing is faked on the way (no attached grasps, physical drawers, a legged base). ForageBench says what is asked and how it is scored. The simulation framework it runs on, [PhyGS](https://github.com/m-and-m-lab/PhyGS), is a git submodule of this repository, pinned to a release, so one recursive clone is the whole installation.

<p align="center">
  <img src="assets/imgs/CoRL26_ForageBench_Title.png" alt="An example episode in ForageBench" width="100%">
</p>

## 📄 Abstract

Interactive semantic object search is the task of locating and retrieving a target object in an unseen, house-scale environment. This task requires both long-horizon spatial reasoning for navigation and fine-grained skills for manipulation, often demanding that an agent physically interact with the environment to make an occluded target perceivable. Prior benchmarks have largely isolated one capability or the other; we present ForageBench, a benchmark designed to study them jointly on a mobile manipulator developed in our newly introduced simulation framework PhyGS. PhyGS integrates large-scale procedural scene generation with photorealism, physical grounding, and low-level robotic control. Using PhyGS, we build an evaluation dataset of 25 house-scale scenes and 100 episodes spanning a progression of difficulty, and benchmark state-of-the-art vision-language models acting as high-level skill orchestrators. Our best baseline on a simulated Boston Dynamics Spot with Arm achieves an interactive search success of 4\%. PhyGS provides a hardware-abstracted interface mirroring Spot's SDK for development transfer between and simulation and the physical robot.

## ⚠️ Note on usage

ForageBench is under active development at the [Mapping and Motion Lab](https://sites.google.com/umich.edu/mandmlab/), and this version of the repository is a beta release intended for early community testing and usage. Please file a GitHub issue detailing any bugs faced or major feature requests, and the team will respond to and resolve these issues as soon as possible.

The `main` branch is the May 2026 beta (VLM orchestrators over AO-Grasp and cuRobo skills, 60 Hz). The `develop` branch is the benchmark described below, on PhyGS 0.3: the retrieve task with a physical evaluator, tracks, Nav2 navigation, cuRobo or MoveIt arm planning, 250 Hz physics. The episode set in this branch is the three development episodes (manifest v0); the 25-scene, 100-episode set and the hidden test split follow with manifest v1.

## 🎯 What ForageBench measures

**The task: retrieve.** The agent is told what to find ("the small green box"), never where. It succeeds when, at the end of the episode, the target is in its hand (off its support and inside the jaws, measured, not assumed), the arm is stowed, the robot is upright and the budget was not exceeded. Nothing else counts as success: not standing next to the target, not a skill's "succeeded".

**Reported beside success, never folded into it: conduct.** Unintended arm contacts above 0.5 N with their peak force, and drawers the agent opened and left open. A run is `clean` when it has none. Both come from ground truth, read once after the robot has stopped and settled; the thresholds are in [thresholds.yaml](foragebench/tasks/retrieve/thresholds.yaml) and their hash is in every result.

**What is not claimed.** The dev episodes are not an unseen-house evaluation; photorealism is not measured; the oracle's success is the ceiling of the skills, not of any method. The [task card](docs/task_card.md) states the rest.

## 🛤️ Tracks

A track says what the agent may do and what it is told. The episode is the same on every track.

| Track | Actions | Granted | Who it is for |
| --- | --- | --- | --- |
| `privileged` | navigation, manipulation skills | true pose, the scene's known boxes (map and arm planning), the target's position, the drawers' handles | The oracle: the skills' ceiling and the physics' noise floor |
| `gt_localization` | navigation, manipulation and direct walking | the true pose only; the map comes from the cameras, the arm plans on depth, the agent finds the target | Model agents, first track |
| `onboard` (planned) | the same | nothing; localization is the agent's | Full autonomy |

Every use of a granted channel is audited and listed in the result.

## 🏠 Episodes and difficulty

An episode is a scene (a release of the scene dataset, by id and version), the robot's start, where objects start, the target and a time budget. The May beta's four difficulty tiers (visible in another room; hidden in the same room; hidden in another room; hidden and occluded) become the parameters of the episode generator: room, visibility, receptacle, occluders. Manifest v0 ([manifest_v0.yaml](foragebench/episodes/manifest_v0.yaml)) has three dev episodes:

| Episode | Scene | What the robot has to do |
| --- | --- | --- |
| `dev/grid_table` | grid storage (a PhyGS fixture, no download) | Walk to a table, pick the box next to the clutter, stow |
| `dev/grid_drawer` | grid storage | Find the box in a closed drawer, open it by the handle, pick, stow |
| `dev/house_drawer` | `bear_loop_house` 1.1.0 (the scene dataset) | The same in a two-storey house: the kitchen island's bottom drawer |

Every manifest entry names its scene release and the archive's SHA-256; every result records the USD's hash.

## 📦 What's in this repository

1. `foragebench/tasks/` — the retrieve task: brief, evaluator, thresholds.
2. `foragebench/tracks/`, `foragebench/episodes/` — the tracks and the episode files with their manifest.
3. `foragebench/agents/` — reference agents: `null` (the floor), `template` (a tour of the session), `oracle` (PhyGS's scripted retrieve plan on the privileged track).
4. `foragebench/run.py`, `suite.py`, `results.py` — one run, a set of runs, the summary with confidence intervals.
5. `configs/benchmark_v1.yaml` — the rules: the PhyGS version, the backends, the end-of-episode settings.
6. `tests/` — unit tests with a fake ground truth and the import guards; `docs/` — the task card, install, design and research pages.
7. `third_party/phygs` — PhyGS, the framework, as a pinned submodule.

## 🛠️ Installation

1. Build and enter PhyGS's Isaac Lab container and install ROS 2 Jazzy with Nav2 in it: [PhyGS installation](https://github.com/m-and-m-lab/PhyGS/blob/develop/README.md#%EF%B8%8F-installation). Nothing is repeated here.
2. Clone ForageBench with its submodule into the Isaac Lab `scripts` folder and install both packages:

```bash
cd /workspace/isaaclab/scripts
git clone --recursive -b develop https://github.com/m-and-m-lab/ForageBench.git
cd ForageBench && make install          # PhyGS (the submodule) and ForageBench, editable, into Isaac Lab's Python
```

3. In every shell: `source /opt/explore_ws/install/setup.bash`, `export ROS_DOMAIN_ID=48`, `export FORAGEBENCH=scripts/ForageBench` (relative to the Isaac Lab root, where every command below runs).

The house episode needs its scene release once: `./isaaclab.sh -p -m phygs.scenes.fetch fetch --scene_id bear_loop_house --scene_version 1.1.0` (the dataset is private for now; `hf auth login` first). The grid episodes need no download. Details: [docs/install.md](docs/install.md).

## 🚀 Quick start

```bash
cd /workspace/isaaclab
# The floor: the null agent observes once and finishes. Prints the scored result; ~1 minute.
./isaaclab.sh -p $FORAGEBENCH/foragebench/run.py --episode dev/grid_table --track privileged --agent null \
  --output $FORAGEBENCH/output_check/$(date +%Y%m%d-%H%M)_grid_table_null

# The ceiling: the oracle retrieves the box (success, clean; ~62 simulated seconds).
./isaaclab.sh -p $FORAGEBENCH/foragebench/run.py --episode dev/grid_table --track privileged --agent oracle \
  --output $FORAGEBENCH/output_check/$(date +%Y%m%d-%H%M)_grid_table_oracle

# The dev set, three repeats each, one simulator process per run; prints the summary table.
./isaaclab.sh -p $FORAGEBENCH/foragebench/suite.py --set dev --track privileged --agent oracle --repeats 3 \
  --output $FORAGEBENCH/output_check/$(date +%Y%m%d-%H%M)_dev_oracle
```

Each run writes `result.json` (benchmark, episode, track, agent, outcome, reason, checks, conduct, `clean`, how the episode ended, time used, the scene release and every provenance hash) beside PhyGS's `report.json` (the full record: commands, contacts, grants used, narration) and `audit.jsonl` (every session call). A suite writes `summary.json`: success rate per track and agent with a Wilson 95% interval, clean rate, per-episode rates.

## ✍️ Writing an agent

An agent is a function `run(session)`; the session is the only object it needs and the only thing it may import ([PhyGS's agent contract](https://github.com/m-and-m-lab/PhyGS/blob/develop/README.md#-the-agent-contract)):

```python
def run(session):
    brief = session.task.description                        # "the small green box": what, never where.
    packet = session.observe()                              # Calibrated RGB-D, joints, localization (as the track grants).
    goal = session.navigation.navigate_to(x=1.0, y=0.0, heading=0.0)
    session.wait(goal)                                      # Simulated time passes only while the agent waits.
    session.wait(session.manipulation.move_to_pose(pose))   # Planned by cuRobo or MoveIt; feedback says why it failed.
    session.wait(session.manipulation.close_gripper())
    session.wait(session.manipulation.stow())
    session.finish("done")                                  # Then the framework stops everything, keeps the grip, evaluates.
```

Start from [template.py](foragebench/agents/template.py); read [oracle.py](foragebench/agents/oracle.py) for a complete retrieve on the privileged track (it only chooses PhyGS's robot-test routines, which is why it is a ceiling and not a method). Run yours with `--agent path/to/agent.py:run`. Bring your own skills: the `gt_localization` track exposes direct walking and arm joint commands through the same session. A model-agent harness (a VLM choosing skills) and a client package without Isaac imports are planned ([PLANS.md](PLANS.md)).

## ⚖️ Evaluation

The evaluator is benchmark code that reads PhyGS's ground truth once, after the robot has stopped (every command cancelled, the grip kept, one second of settling). It never reads skill feedback. Outcome: held, stowed, upright, in time. Conduct: contacts and drawers left open. The rules and their hashes travel with every result: `configs/benchmark_v1.yaml` (PhyGS version, backends, end-of-episode settings), the track file, the episode file, the thresholds, the scene USD, the robot USD and policy, PhyGS's and ForageBench's commits. A result from an unpinned PhyGS (another version, or a dirty checkout) is marked in the summary.

## 📊 Baselines

| Agent | Track | Episodes | Success | Clean | Note |
| --- | --- | --- | --- | --- | --- |
| null | privileged | dev/grid_table | 0/1 | — | The floor; 2026-10-28 |
| oracle | privileged | dev/grid_table | 1/1 | 1/1 | 62 s simulated; 2026-10-28 |

The dev-set noise floor (oracle, three tracks, repeated) and the model baselines are the next entries ([PLANS.md](PLANS.md)).

## 📤 Submitting results

Send the suite's `summary.json` and the per-run `result.json` files, with a `provenance.foragebench.dirty` and `provenance.code.dirty` of `false` and `phygs_version` equal to the pinned one. We rerun a sample of episodes with your agent before listing a result.

## 📚 Documentation

[docs/README.md](docs/README.md): the [task card](docs/task_card.md), [installation](docs/install.md), the design record (framework/benchmark split, benchmark audit, positioning against 40+ benchmarks) and the research notes behind them. Changes: [CHANGELOG.md](CHANGELOG.md). Status and plans: [PLANS.md](PLANS.md). Rules for contributors and coding agents, including the submodule rules: [AGENTS.md](AGENTS.md).

## 📝 Citation

If you use ForageBench in your research, please cite:

```bibtex
@misc{2026foragebench,
  title     = {ForageBench: A Photorealistic, Physically Grounded Benchmark for Interactive Object Search},
  author    = {Saha, Aparajito and Gan, Zhen Hao and Guo, Jinjia and
               Skwirsk, Jacob and Acheampong, Jeremy and Arapin, Anton and
               Ku, Chahyon and Hu, Yue and Fazeli, Nima and Bucher, Bernadette},
  year      = {2026}
}
```

## 🙏 Acknowledgments

ForageBench builds on [PhyGS](https://github.com/m-and-m-lab/PhyGS) and, through it, on
[Infinigen / Infinigen-Indoors](https://github.com/princeton-vl/infinigen),
[NVIDIA IsaacSim](https://developer.nvidia.com/isaac/sim),
[IsaacLab](https://github.com/isaac-sim/IsaacLab),
[Objaverse-XL](https://objaverse.allenai.org/),
[cuRobo](https://curobo.org/),
[Nav2](https://nav2.org/),
[explore_lite (m-explore-ros2)](https://github.com/robo-friends/m-explore-ros2) and
[MoveIt 2](https://moveit.picknik.ai/).

We thank the authors and maintainers of these tools. Please refer to each project's license and cite them as appropriate.
