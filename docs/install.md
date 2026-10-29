# Installation

ForageBench runs inside PhyGS's Isaac Lab container. Three steps:

1. **The container.** Build and enter PhyGS's container ([PhyGS docker/README.md](https://github.com/m-and-m-lab/PhyGS/blob/develop/docker/README.md)): Isaac Lab's base image with ROS 2 Jazzy, Nav2, explore_lite, MoveIt and cuRobo V2 installed. Clone ForageBench (step 2) into `IsaacLab/scripts` first, so the container sees it.
2. **Clone and install.** In the container, from the Isaac Lab `scripts` folder:

   ```bash
   git clone --recursive -b develop https://github.com/m-and-m-lab/ForageBench.git
   cd ForageBench
   ../../isaaclab.sh -p -m pip install -e third_party/phygs --no-deps   # PhyGS at the pinned release
   ../../isaaclab.sh -p -m pip install -e . --no-deps                   # foragebench and its command
   ../../isaaclab.sh -p -m pytest tests -q                              # unit tests, no simulator
   ```

   `third_party/phygs` is PhyGS at the pinned release; never edit inside it (see AGENTS.md). Both packages must be installed: ForageBench takes PhyGS from the installed package, never from a path, and refuses to run when the installed version differs from `configs/benchmark_v1.yaml`. Installed editable, a PhyGS checkout elsewhere works too, at the pinned version.
3. **Scenes.** The grid episodes use a fixture scene shipped with PhyGS. The house needs its release from the scene dataset (private for now):

   ```bash
   ./isaaclab.sh -p -m huggingface_hub.cli.hf auth login
   ./isaaclab.sh -p -m phygs.scene.fetch fetch --scene_id bear_loop_house --scene_version 1.1.0
   ```

   Releases install under `~/.cache/phygs/scenes` (`$PHYGS_SCENES` to move them); episodes find them by id and version.

Then `./isaaclab.sh -p -m foragebench describe --episode dev/grid_table --track privileged --agent null` checks the setup without the simulator, and the same arguments with `run --output <folder>` print a scored result.
