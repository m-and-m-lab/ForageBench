# 3. Download benchmark scenes

ForageBench evaluates on 25 house-scale scenes generated with PhyGS. Scenes are not stored in
git; pull them into `scenes/data/` with:

```bash
ISAACLAB=/workspace/isaaclab/isaaclab.sh

$ISAACLAB -p -m scenes.download --all
# Or specific scenes:
$ISAACLAB -p -m scenes.download --scene scene_000 --scene scene_001
```

To keep scenes elsewhere (e.g. a shared volume), set `FORAGEBENCH_SCENES_DIR`.

TODO: add the release location, total download size, and checksums once scenes are published.
