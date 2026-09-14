"""Resolve benchmark scene IDs to local USD files."""

import os
from pathlib import Path

SCENES_DIR = Path(os.environ.get("FORAGEBENCH_SCENES_DIR", Path(__file__).parent / "data"))


def scene_usd_path(scene_id: str, scenes_dir: Path = SCENES_DIR) -> Path:
    """Return the USD for `scene_id`, raising if it has not been downloaded."""
    # TODO: match the on-disk layout of the released scenes.
    path = scenes_dir / scene_id / f"{scene_id}.usd"
    if not path.is_file():
        raise FileNotFoundError(
            f"Scene {scene_id!r} not found at {path}. "
            f"Run `python -m scenes.download --scene {scene_id}`."
        )
    return path


def list_local_scenes(scenes_dir: Path = SCENES_DIR) -> list[str]:
    if not scenes_dir.is_dir():
        return []
    return sorted(p.name for p in scenes_dir.iterdir() if p.is_dir())
