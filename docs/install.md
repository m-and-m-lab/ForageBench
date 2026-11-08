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

   `third_party/phygs` is PhyGS at the pinned release; never edit inside it (see AGENTS.md). Both packages must be installed: ForageBench takes PhyGS from the installed package, never from a path, and refuses to run when the installed version differs from `configs/benchmark_v1.yaml`. Installed editable, a PhyGS checkout elsewhere works too, at the pinned version.
3. **Scenes.** The grid episodes use a fixture scene shipped with PhyGS. The house needs its release from the scene dataset (private for now):

   ```bash
   isaaclab -p -m huggingface_hub.cli.hf auth login
   isaaclab -p -m phygs.scene.fetch fetch --repo_id mandmlabresearch/ForageBench --scene_id bear_loop_house --scene_version 1.1.0
   ```

   Releases install under `~/.cache/phygs/scenes`; episodes find them there by id and version (`$PHYGS_SCENES`, when set, is a folder searched first).

Then `isaaclab -p -m foragebench describe --episode dev/grid_table --track privileged --agent null` checks the setup without the simulator, and the same arguments with `run --output <folder>` print a scored result.
