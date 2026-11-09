# Installation

ForageBench runs inside PhyGS's Isaac Lab container. Three steps:

1. **The container.** Build and enter PhyGS's container ([PhyGS docker/README.md](https://github.com/m-and-m-lab/PhyGS/blob/develop/docker/README.md)): Isaac Lab main's base image (Isaac Sim 6.2.0, Python 3.12) with ROS 2 Jazzy, Nav2, explore_lite, MoveIt and cuRobo V2 installed. Clone ForageBench (step 2) into `IsaacLab/scripts` first, so the container sees it. The container takes `ROS_DOMAIN_ID` from `docker/.env.ros2`: any ID no other ROS user on the machine uses.
2. **Clone and install.** In the container, from the Isaac Lab `scripts` folder:

   ```bash
   git clone --recursive -b develop https://github.com/m-and-m-lab/ForageBench.git   # --recursive: PhyGS and its Spot meshes
   cd ForageBench
   isaaclab -p -m pip install -e third_party/phygs --no-deps   # PhyGS at the pinned release
   isaaclab -p -m pip install -e . --no-deps                   # foragebench and its command
   PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 isaaclab -p -m pytest tests -q   # unit tests, no simulator
   ```

   `third_party/phygs` is PhyGS at the pinned release; never edit inside it (see AGENTS.md). Both packages must be installed: ForageBench takes PhyGS from the installed package, never from a path. Installed editable, a PhyGS checkout elsewhere works too; its runs are pinned only at the pinned release ([the PhyGS pin](#the-phygs-pin)).
3. **Scenes.** The grid episodes use a fixture scene shipped with PhyGS. The house needs its release from the scene dataset (private for now):

   ```bash
   isaaclab -p -m huggingface_hub.cli.hf auth login
   isaaclab -p -m phygs.scene.fetch fetch --repo_id mandmlabresearch/ForageBench --scene_id bear_loop_house --scene_version 1.1.0
   ```

   Releases install under `~/.cache/phygs/scenes`; episodes find them there by id and version (`$PHYGS_SCENES`, when set, is a folder searched first).

Then `isaaclab -p -m foragebench describe --episode dev/grid_table --track privileged --agent null` checks the setup without the simulator, and the same arguments with `run --output <folder>` print a scored result.

## The PhyGS pin

`configs/benchmark_v1.yaml` pins one PhyGS release by its version (`phygs_version`) and its tag's commit (`phygs_commit`); `tests/test_pin.py` checks that `third_party/phygs` is that commit. A run is pinned when the imported PhyGS has the pinned version, is a git checkout at the pinned commit, and has no uncommitted changes to its tracked files. The `third_party/phygs` of a fresh `--recursive` clone is.

A run on any other PhyGS (another version, a development version, another commit that still says the pinned version, an install outside a git checkout, a checkout with uncommitted changes) is unpinned. It is not refused: it goes ahead, prints `foragebench: an unpinned run, its results are not publishable: <reasons>` at the start, and records the reasons in `result.json` under `provenance.unpinned` (empty when pinned). A run from a ForageBench checkout with uncommitted changes (`provenance.foragebench.dirty`) is unpinned too. `foragebench results` counts unpinned runs, and `foragebench leaderboard add` refuses them ([submitting.md](submitting.md)).

`foragebench version` and `describe` say whether the installed PhyGS is the pinned release, and why not:

```
PhyGS      pinned 0.12.0 at 67fddf1, installed 0.12.0 at 47e3edc: unpinned (PhyGS commit 47e3edc is not v0.12.0 at 67fddf1)
```
