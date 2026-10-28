# Installation

ForageBench runs inside PhyGS's Isaac Lab container. Three steps:

1. **The container and ROS.** Follow [PhyGS's installation](https://github.com/m-and-m-lab/PhyGS/blob/develop/README.md#%EF%B8%8F-installation): build the Isaac Lab container with PhyGS's compose patch (cuRobo), enter it, install Isaac Lab, then ROS 2 Jazzy with Nav2 and the explore_lite overlay ([PhyGS docs/nav2.md](https://github.com/m-and-m-lab/PhyGS/blob/develop/docs/nav2.md#ros-2-jazzy-setup)). MoveIt is optional.
2. **Clone and install.** In the container, from the Isaac Lab `scripts` folder:

   ```bash
   git clone --recursive -b develop https://github.com/m-and-m-lab/ForageBench.git
   cd ForageBench && make install    # installs third_party/phygs and foragebench, editable, into Isaac Lab's Python
   make test                         # unit tests, no simulator
   ```

   `third_party/phygs` is PhyGS at the pinned release; never edit inside it (see AGENTS.md). If you already have a PhyGS checkout installed (`pip install -e`), `foragebench` uses that one and refuses to run when its version differs from `configs/benchmark_v1.yaml`.
3. **Scenes.** The grid episodes use a fixture scene shipped with PhyGS. The house needs its release from the scene dataset (private for now):

   ```bash
   ./isaaclab.sh -p -m huggingface_hub.cli.hf auth login
   ./isaaclab.sh -p -m phygs.scenes.fetch fetch --scene_id bear_loop_house --scene_version 1.1.0
   ```

   Releases install under `~/.cache/phygs/scenes` (`$PHYGS_SCENES` to move them); episodes find them by id and version.

Then `make smoke` runs the null agent on `dev/grid_table` and prints a scored result.
