# scenes/

Helper scripts for pulling the released ForageBench scenes into the local environment.

Scenes are generated with PhyGS, which extends Infinigen-Indoors: articulations are re-injected
at USD export, colliders and rigid-body properties are added, and Objaverse-XL manipulands are
placed. The released set is 25 single-story homes with two, three, or four bedrooms, each also
having a bathroom, kitchen, living room, and dining room. Scenes contain 50–200 manipulands.

- `download.py`: CLI that downloads scenes into `scenes/data/` (ignored by git)
- `registry.py`: resolves a `scene_id` to its local USD file

```bash
python -m scenes.download --all
```

Set `FORAGEBENCH_SCENES_DIR` to store scenes outside the repo.
