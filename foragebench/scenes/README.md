# scenes/

Which scenes the benchmark uses and how to get them. Scenes are framework data: PhyGS owns the
registry (`phygs.episodes.scenes`), the fetcher (`phygs.scenes.fetch`) and the publisher; the scene
dataset on Hugging Face is `mandmlabresearch/ForageBench` (private for now).

| Scene | Release | Used by | Get it |
| --- | --- | --- | --- |
| `grid_storage` | PhyGS fixture (`tests/robot_tests/scenes`) | `dev/grid_table`, `dev/grid_drawer` | nothing to do |
| `bear_loop_house` | 1.1.0 (the storage revision; archive SHA-256 `06b18741…`) | `dev/house_drawer` | `python -m foragebench.scenes fetch` |

```bash
./isaaclab.sh -p -m huggingface_hub.cli.hf auth login     # once
./isaaclab.sh -p -m foragebench.scenes list               # the scenes the manifest needs, and whether each is present
./isaaclab.sh -p -m foragebench.scenes fetch              # fetch the missing releases through PhyGS
```

Releases install under `~/.cache/phygs/scenes` (`$PHYGS_SCENES` to move them). A release is
immutable; a changed scene is a new version, pinned by the episode file and recorded in every result.
